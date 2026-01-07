"""
聊天路由
处理AI聊天相关的API接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from schemas.chat import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
    ChatRecordCreate, ChatRecordResponse,
    # ChatMessage,
    ChatHistoryParams
)
from schemas.common import ResponseModel, PaginatedResponse
from services.chat_service import chat_service
from services.auth_service import auth_service
from models import User

# 创建路由实例
router = APIRouter()

# 获取当前用户依赖（用于token验证）
async def get_current_user_dependency(request: Request, db: Session = Depends(get_db)):
    """获取当前认证用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未提供有效的认证令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise credentials_exception
        token = auth_header.split(" ")[1]
        user = auth_service.get_current_user(db, token)
        if not user:
            raise credentials_exception
        return user
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception


@router.post("/sessions")
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    创建聊天会话
    需要有效的认证令牌
    - **title**: 会话标题
    - **description**: 会话描述（可选）
    - **resource_id**: 关联的资源ID（可选）
    """
    # 创建会话
    session = chat_service.create_session(db, session_data, current_user.id)
    
    return ResponseModel(
        code=200,
        message="会话创建成功",
        data=session.to_dict()
    )


@router.get("/sessions")
async def get_chat_sessions(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    resource_id: Optional[int] = Query(None, description="关联的资源ID"),
    sort_by: str = Query("updated_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    获取用户的聊天会话列表
    需要有效的认证令牌
    """
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取会话列表
    sessions = chat_service.get_user_sessions(
        db, current_user.id, keyword, resource_id, sort_by, order, skip, page_size
    )
    
    # 获取总数
    total = chat_service.get_user_sessions_count(
        db, current_user.id, keyword, resource_id
    )
    
    return ResponseModel(
        code=200,
        message="获取会话列表成功",
        data={
            "items": [session.to_dict() for session in sessions],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    )


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取会话详情
    """
    # 获取会话
    session = chat_service.get_session_by_id(db, session_id, None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    return ResponseModel(
        code=200,
        message="获取会话成功",
        data=session.to_dict()
    )


@router.put("/sessions/{session_id}")
async def update_chat_session(
    session_id: int,
    session_update: ChatSessionUpdate,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    更新会话信息
    - **title**: 会话标题（可选）
    - **description**: 会话描述（可选）
    """
    # 更新会话
    updated_session = chat_service.update_session(db, session_id, session_update, None)
    
    return ResponseModel(
        code=200,
        message="会话更新成功",
        data=updated_session.to_dict()
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    删除聊天会话
    """
    # 删除会话
    chat_service.delete_session(db, session_id, None)
    
    return ResponseModel(
        code=200,
        message="会话删除成功"
    )


@router.post("/sessions/{session_id}/records")
async def send_chat_message(
    session_id: int,
    message_data: ChatRecordCreate,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    发送聊天消息
    - **content**: 消息内容
    - **type**: 消息类型
    """
    # 验证会话存在且属于当前用户
    session = chat_service.get_session_by_id(db, session_id, None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # 保存用户消息
    user_record = chat_service.save_chat_record(
        db, session_id, None, message_data
    )
    
    # 生成AI回复
    ai_response = chat_service.generate_ai_response(
        db, session_id, message_data.content, None
    )
    
    # 保存AI回复
    ai_record_data = ChatRecordCreate(
        content=ai_response,
        type="ai"
    )
    ai_record = chat_service.save_chat_record(
        db, session_id, None, ai_record_data
    )
    
    # 更新会话最后活动时间
    session.updated_at = datetime.utcnow()
    db.commit()
    
    # 返回AI回复
    return ResponseModel(
        code=200,
        message="消息发送成功",
        data=ai_record.to_dict()
    )


@router.get("/sessions/{session_id}/records")
async def get_chat_records(
    session_id: int,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取聊天记录
    """
    # 验证会话存在且属于当前用户
    session = chat_service.get_session_by_id(db, session_id, None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取聊天记录
    records = chat_service.get_chat_records(db, session_id, skip, page_size)
    
    # 获取总数
    total = chat_service.get_chat_records_count(db, session_id)
    
    return ResponseModel(
        code=200,
        message="获取聊天记录成功",
        data={
            "items": [record.to_dict() for record in records],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    )


@router.post("/chat-history")
async def get_chat_history(
    request: ChatHistoryParams,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取指定数量的聊天历史记录
    用于AI上下文理解
    - **session_id**: 会话ID
    - **limit**: 返回的消息数量限制
    """
    # 验证会话存在且属于当前用户
    session = chat_service.get_session_by_id(db, request.session_id, None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # 获取聊天历史
    history = chat_service.get_chat_history(db, request.session_id, request.limit)
    
    return ResponseModel(
        code=200,
        message="获取聊天历史成功",
        data=history
    )


@router.post("/sessions/{session_id}/clear")
async def clear_chat_records(
    session_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    清空会话的聊天记录
    """
    # 验证会话存在且属于当前用户
    session = chat_service.get_session_by_id(db, session_id, None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # 清空聊天记录
    chat_service.clear_chat_records(db, session_id)
    
    return ResponseModel(
        code=200,
        message="聊天记录清空成功"
    )


@router.delete("/history/clear")
async def clear_all_chat_history(
    db: Session = Depends(get_db)
):
    """
    清除所有聊天记录（不需要认证，用于前端调用）
    注意：此API会清除数据库中所有的聊天会话和记录
    """
    from models.chat import ChatSession, ChatRecord
    
    try:
        # 删除所有聊天记录
        db.query(ChatRecord).delete()
        # 删除所有聊天会话
        db.query(ChatSession).delete()
        db.commit()
        
        return ResponseModel(
            code=200,
            message="所有聊天记录已清除"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除聊天记录失败: {str(e)}"
        )


@router.post("/quick-chat")
async def quick_chat(
    content: str,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    快速聊天（不创建会话）
    - **content**: 消息内容
    """
    # 生成AI回复
    ai_response = chat_service.generate_quick_response(content, None)
    
    return ResponseModel(
        code=200,
        message="获取回复成功",
        data={
            "response": ai_response
        }
    )


# WebSocket端点
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: int,
    db: Session = Depends(get_db)
):
    """
    WebSocket聊天端点
    提供实时聊天功能
    """
    await websocket.accept()
    
    try:
        # 验证用户身份（从WebSocket连接中获取token）
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Missing authentication token")
            return
        
        # 解析token获取用户ID
        user_id = chat_service.verify_websocket_token(token)
        if not user_id:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
        
        # 验证会话存在且属于当前用户
        session = chat_service.get_session_by_id(db, session_id, user_id)
        if not session:
            await websocket.close(code=1008, reason="Chat session not found")
            return
        
        # WebSocket消息处理循环
        while True:
            # 接收用户消息
            data = await websocket.receive_json()
            content = data.get("content", "")
            
            if not content:
                await websocket.send_json({
                    "error": "Message content is required"
                })
                continue
            
            # 保存用户消息
            user_record_data = ChatRecordCreate(
                content=content,
                type="user"
            )
            user_record = chat_service.save_chat_record(
                db, session_id, user_id, user_record_data
            )
            
            # 发送用户消息确认
            await websocket.send_json({
                "type": "user",
                "message": user_record.to_dict()
            })
            
            # 生成AI回复
            try:
                ai_response = chat_service.generate_ai_response(
                    db, session_id, content, user_id
                )
                
                # 保存AI回复
                ai_record_data = ChatRecordCreate(
                    content=ai_response,
                    type="ai"
                )
                ai_record = chat_service.save_chat_record(
                    db, session_id, None, ai_record_data
                )
                
                # 发送AI回复
                await websocket.send_json({
                    "type": "ai",
                    "message": ai_record.to_dict()
                })
                
                # 更新会话最后活动时间
                session.updated_at = datetime.utcnow()
                db.commit()
                
            except Exception as e:
                # 发送错误消息
                await websocket.send_json({
                    "type": "error",
                    "message": "生成回复失败，请稍后重试"
                })
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {str(e)}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        # 清理资源
        db.close()