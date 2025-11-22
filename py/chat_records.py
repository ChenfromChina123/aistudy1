from datetime import datetime, UTC
import enum
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from sqlalchemy import func, desc

# 创建延迟导入的依赖函数
def get_db():
    from app import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user_dependency(request: Request, db: Session = Depends(get_db)):
    from app import get_current_user
    return await get_current_user(request, db)

async def get_current_admin_dependency(request: Request, db: Session = Depends(get_db)):
    from app import get_current_admin, get_current_user
    try:
        # 先获取当前用户
        current_user = await get_current_user(request, db)
        # 然后检查管理员权限
        admin = get_current_admin(current_user, db)
        return admin
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

# 定义消息发送者类型常量
USER_SENDER = 1
AI_SENDER = 2

# 定义消息状态枚举
class MessageStatus(enum.Enum):
    PENDING = "pending"      # 处理中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 用户取消


# Pydantic模型定义
class ChatRecordBase(BaseModel):
    content: str
    sender_type: int
    session_id: Optional[str] = None
    ai_model: Optional[str] = None

class ChatRecordCreate(ChatRecordBase):
    pass

class ChatRecordResponse(ChatRecordBase):
    id: int
    message_order: int
    send_time: str
    user_id: str
    status: str

    class Config:
        from_attributes = True

class SessionInfo(BaseModel):
    session_id: str
    last_message: str
    last_message_time: str

class SaveChatRecordResponse(BaseModel):
    message: str
    record: ChatRecordResponse

class CreateSessionResponse(BaseModel):
    session_id: str

class UserChatSession(BaseModel):
    session_id: str
    user_id: str
    username: Optional[str] = None
    last_message: str
    last_message_time: str
    message_count: int
    
    class Config:
        from_attributes = True

class AdminChatRecordResponse(ChatRecordResponse):
    username: Optional[str] = None
    
    class Config:
        from_attributes = True

# 创建FastAPI路由器
router = APIRouter(prefix="/api/chat-records", tags=["聊天记录"])

# 添加一个简单的测试端点，不需要认证
@router.get("/test-connection")
def test_connection(db: Session = Depends(get_db)):
    """测试数据库连接和ChatRecord模型导入"""
    try:
        print("测试端点被调用")
        # 导入ChatRecord模型
        from app import ChatRecord
        print("成功导入ChatRecord模型")
        
        # 尝试一个简单的查询
        try:
            count = db.query(func.count(ChatRecord.id)).scalar()
            print(f"查询成功，记录总数: {count}")
            
            # 特别查询用户ID为12的聊天记录
            user_12_records = db.query(ChatRecord).filter(ChatRecord.user_id == "12").all()
            print(f"用户ID 12 的聊天记录数量: {len(user_12_records)}")
            
            # 获取用户ID 12 的会话列表
            user_12_sessions = db.query(ChatRecord.session_id).filter(
                ChatRecord.user_id == "12"
            ).distinct().all()
            print(f"用户ID 12 的会话数量: {len(user_12_sessions)}")
            
            return {
                "status": "success", 
                "message": "数据库连接和查询正常", 
                "record_count": count,
                "user_12_records_count": len(user_12_records),
                "user_12_sessions_count": len(user_12_sessions)
            }
        except Exception as qe:
            print(f"查询错误: {str(qe)}")
            import traceback
            print("查询错误堆栈:", traceback.format_exc())
            return {"status": "error", "message": f"查询失败: {str(qe)}"}
            
    except Exception as e:
        print(f"端点执行错误: {str(e)}")
        import traceback
        print("端点错误堆栈:", traceback.format_exc())
        return {"status": "error", "message": f"执行失败: {str(e)}"}

def create_chat_record(
        db: Session,
        ChatRecord,
        content: str,
        sender_type: int,
        user_id: str,
        session_id: str = None,
        ai_model: str = None,
        status: str = MessageStatus.COMPLETED.value
):
    """创建一条聊天记录并保存到数据库"""
    try:
        if not session_id:
            session_id = str(uuid.uuid4()).replace("-", "")
        
        # 获取该会话中最新的消息顺序号，然后+1
        last_message = db.query(
            func.max(ChatRecord.message_order)
        ).filter(
            ChatRecord.session_id == session_id,
            ChatRecord.user_id == user_id
        ).scalar()
        
        message_order = (last_message or 0) + 1

        chat_record = ChatRecord(
            session_id=session_id,
            user_id=user_id,
            message_order=message_order,
            sender_type=sender_type,
            content=content,
            ai_model=ai_model,
            status=status
        )

        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)

        print(f"聊天记录创建成功！ID: {chat_record.id}")
        return chat_record

    except Exception as e:
        db.rollback()
        print(f"创建聊天记录失败：{str(e)}")
        raise

# FastAPI路由函数定义
@router.post("/save", response_model=SaveChatRecordResponse)
def save_chat_record(
    chat_record_data: ChatRecordCreate,
    current_user = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """保存一条聊天记录"""
    try:
        user_id = str(current_user.id)
        
        # 验证sender_type值
        if chat_record_data.sender_type not in [USER_SENDER, AI_SENDER]:
            raise HTTPException(status_code=400, detail="发送者类型无效，只能是1（用户）或2（AI）")
        
        # 导入ChatRecord模型（假设从fastapi_app.py导入）
        from app import ChatRecord
        
        # 创建聊天记录
        record = create_chat_record(
            db,
            ChatRecord,
            content=chat_record_data.content,
            sender_type=chat_record_data.sender_type,
            user_id=user_id,
            session_id=chat_record_data.session_id,
            ai_model=chat_record_data.ai_model
        )
        
        # 转换为响应模型
        record_dict = record.to_dict()
        return SaveChatRecordResponse(
            message="聊天记录保存成功",
            record=ChatRecordResponse(**record_dict)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")

@router.get("/sessions", response_model=Dict[str, List[SessionInfo]])
def get_chat_sessions(
    current_user = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """获取用户的所有聊天会话"""
    try:
        print("用户认证成功，用户ID:", current_user.id)
        user_id = str(current_user.id)
        
        # 导入ChatRecord模型和所需函数
        from app import ChatRecord
        from sqlalchemy import func, desc, text
        print("导入ChatRecord模型成功")
        
        # 执行完整的会话查询
        sessions = db.query(
            ChatRecord.session_id,
            func.max(ChatRecord.send_time).label('last_message_time'),
            func.substr(
                func.max(func.concat(ChatRecord.send_time, ChatRecord.content)),
                20
            ).label('last_message')
        ).filter(
            ChatRecord.user_id == user_id
        ).group_by(
            ChatRecord.session_id
        ).order_by(
            desc(text('last_message_time'))
        ).all()
        
        # 格式化结果
        result = []
        for session in sessions:
            result.append({
                "session_id": session.session_id,
                "last_message": session.last_message,
                "last_message_time": session.last_message_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        print(f"为用户ID {user_id} 找到 {len(result)} 个会话")
        return {"sessions": result}
        
    except Exception as e:
        print(f"函数执行错误: {str(e)}")
        import traceback
        print("错误堆栈:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")

@router.get("/session/{session_id}", response_model=Dict[str, List[ChatRecordResponse]])
def get_chat_session_messages(
    session_id: str,
    current_user = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """获取特定会话的所有消息"""
    try:
        user_id = str(current_user.id)
        print(f"获取会话消息请求 - 用户ID: {user_id}, 会话ID: {session_id}")
        
        # 导入ChatRecord模型
        from app import ChatRecord
        print("导入ChatRecord模型成功")
        
        # 获取会话中的所有消息
        messages = db.query(ChatRecord).filter(
            ChatRecord.user_id == user_id,
            ChatRecord.session_id == session_id
        ).order_by(
            ChatRecord.message_order  # 使用message_order而不是send_time来确保正确顺序
        ).all()
        
        print(f"找到 {len(messages)} 条消息")
        
        # 格式化结果
        result = []
        for message in messages:
            message_dict = message.to_dict()
            result.append(ChatRecordResponse(**message_dict))
            print(f"消息 {message.id}: 发送者类型={message.sender_type}, 内容长度={len(message.content)}")
        
        return {"messages": result}
    except Exception as e:
        print(f"获取会话消息失败: {str(e)}")
        import traceback
        print("错误堆栈:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取失败：{str(e)}")

@router.delete("/session/{session_id}")
def delete_chat_session(
    session_id: str,
    current_user = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """删除特定会话的所有消息"""
    try:
        user_id = str(current_user.id)
        
        # 导入ChatRecord模型
        from app import ChatRecord
        
        # 删除会话中的所有消息
        db.query(ChatRecord).filter(
            ChatRecord.user_id == user_id,
            ChatRecord.session_id == session_id
        ).delete()
        db.commit()
        
        return {"message": "会话已删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")

@router.post("/new-session", response_model=CreateSessionResponse)
def create_new_chat_session(
    current_user = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """创建一个新的聊天会话"""
    try:
        # 生成新的会话ID
        session_id = str(uuid.uuid4()).replace("-", "")
        
        return CreateSessionResponse(session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败：{str(e)}")

# 管理员功能：获取所有用户的聊天会话
@router.get("/admin/sessions", response_model=Dict[str, List[UserChatSession]])
def get_all_chat_sessions(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回的最大记录数"),
    user_id: Optional[str] = Query(None, description="可选的用户ID筛选"),
    current_admin = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """
    获取所有用户的聊天会话列表（管理员权限）
    
    - **skip**: 跳过的记录数（默认0）
    - **limit**: 返回的最大记录数（默认20，最大100）
    - **user_id**: 可选的用户ID筛选
    """
    try:
        # 导入ChatRecord模型
        from app import ChatRecord
        
        # 构建查询
        subquery = db.query(
            ChatRecord.session_id,
            ChatRecord.user_id,
            func.max(ChatRecord.send_time).label('last_message_time'),
            func.substr(
                func.max(func.concat(ChatRecord.send_time, ChatRecord.content)),
                20
            ).label('last_message'),
            func.count(ChatRecord.id).label('message_count')
        )
        
        # 如果指定了用户ID，添加筛选条件
        if user_id:
            subquery = subquery.filter(ChatRecord.user_id == user_id)
        
        # 按会话ID分组
        subquery = subquery.group_by(ChatRecord.session_id, ChatRecord.user_id)
        
        # 执行查询并分页
        sessions = subquery.order_by(
            desc('last_message_time')
        ).offset(skip).limit(limit).all()
        
        # 格式化结果
        result = []
        for session in sessions:
            # 获取用户名
            username = None
            if session.user_id:
                from app import User
                user = db.query(User).filter(User.id == session.user_id).first()
                if user:
                    username = user.username
            
            result.append(UserChatSession(
                session_id=session.session_id,
                user_id=session.user_id,
                username=username,
                last_message=session.last_message,
                last_message_time=session.last_message_time.strftime("%Y-%m-%d %H:%M:%S"),
                message_count=session.message_count
            ))
        
        return {"sessions": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败：{str(e)}")

# 管理员功能：获取特定用户的聊天记录
@router.get("/admin/user/{user_id}/session/{session_id}", response_model=Dict[str, List[AdminChatRecordResponse]])
def get_user_chat_session(
    user_id: str,
    session_id: str,
    current_admin = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """
    获取指定用户特定会话的所有消息（管理员权限）
    
    - **user_id**: 用户ID
    - **session_id**: 会话ID
    """
    try:
        # 导入ChatRecord模型
        from app import ChatRecord
        
        # 获取用户信息
        from app import User
        user = db.query(User).filter(User.id == user_id).first()
        username = user.username if user else None
        
        # 获取会话中的所有消息
        messages = db.query(ChatRecord).filter(
            ChatRecord.user_id == user_id,
            ChatRecord.session_id == session_id
        ).order_by(
            ChatRecord.message_order
        ).all()
        
        # 格式化结果
        result = []
        for message in messages:
            message_dict = message.to_dict()
            admin_response = AdminChatRecordResponse(**message_dict)
            admin_response.username = username
            result.append(admin_response)
        
        return {"messages": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取聊天记录失败：{str(e)}")

# 管理员功能：删除用户的聊天会话
@router.delete("/admin/user/{user_id}/session/{session_id}")
def delete_user_chat_session(
    user_id: str,
    session_id: str,
    current_admin = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """
    删除指定用户特定会话的所有消息（管理员权限）
    
    - **user_id**: 用户ID
    - **session_id**: 会话ID
    """
    try:
        # 导入ChatRecord模型
        from app import ChatRecord
        
        # 删除会话中的所有消息
        deleted_count = db.query(ChatRecord).filter(
            ChatRecord.user_id == user_id,
            ChatRecord.session_id == session_id
        ).delete()
        
        db.commit()
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="会话不存在或无消息")
        
        return {"message": f"成功删除{deleted_count}条消息"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除聊天记录失败：{str(e)}")

# 管理员功能：获取聊天统计信息
@router.get("/admin/stats", response_model=Dict[str, Any])
def get_chat_stats(
    current_admin = Depends(get_current_admin_dependency),
    db: Session = Depends(get_db)
):
    """
    获取聊天记录统计信息（管理员权限）
    """
    try:
        # 导入ChatRecord模型
        from app import ChatRecord
        
        # 总消息数
        total_messages = db.query(func.count(ChatRecord.id)).scalar()
        
        # 总会话数
        total_sessions = db.query(func.count(func.distinct(ChatRecord.session_id))).scalar()
        
        # 活跃用户数（有聊天记录的用户）
        active_users = db.query(func.count(func.distinct(ChatRecord.user_id))).scalar()
        
        # 今日新增消息数
        today = datetime.now(UTC).date()
        today_messages = db.query(func.count(ChatRecord.id)).filter(
            func.date(ChatRecord.send_time) == today
        ).scalar()
        
        return {
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "active_users": active_users,
            "today_messages": today_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败：{str(e)}")

# 导出注册函数
def register_chat_record_routes(app):
    """注册聊天记录相关的API路由到FastAPI应用"""
    # 直接注册路由，依赖通过动态导入解决
    app.include_router(router)