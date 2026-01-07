"""
聊天服务
处理AI聊天相关的业务逻辑
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status
from database import get_db
from datetime import datetime
import re
import json

from models import ChatSession, ChatRecord
from schemas.chat import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
    ChatRecordCreate, ChatRecordResponse, ChatCompletionRequest
)
from config import settings
# AIService暂时不可用，稍后实现


class ChatService:
    """聊天服务类"""
    
    def __init__(self):
        # AIService暂时不可用，稍后实现
        self.ai_service = None
    
    def get_session_by_id(self, db: Session, session_id: int) -> Optional[ChatSession]:
        """根据ID获取聊天会话"""
        return db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    def create_session(
        self, 
        db: Session, 
        session_data: ChatSessionCreate, 
        user_id: int
    ) -> ChatSession:
        """创建聊天会话"""
        # 设置默认标题（如果未提供）
        title = session_data.title or f"新会话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建会话（使用用户选择的模型，无默认模型）
        db_session = ChatSession(
            user_id=user_id,
            title=title,
            ai_model=session_data.ai_model,  # 用户必须明确选择模型
            is_active=True,
            metadata=json.dumps(session_data.metadata) if session_data.metadata else "{}"
        )
        
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return db_session
    
    def update_session(
        self, 
        db: Session, 
        session_id: int, 
        session_update: ChatSessionUpdate, 
        user_id: int
    ) -> ChatSession:
        """更新聊天会话"""
        # 获取会话
        session = self.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        # 检查权限
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改该会话"
            )
        
        # 准备更新数据
        update_data = session_update.model_dump(exclude_unset=True)
        
        # 处理元数据
        if "metadata" in update_data:
            update_data["metadata"] = json.dumps(update_data["metadata"])
        
        # 更新会话信息
        update_data["updated_at"] = datetime.utcnow()
        for field, value in update_data.items():
            setattr(session, field, value)
        
        db.commit()
        db.refresh(session)
        
        return session
    
    def delete_session(self, db: Session, session_id: int, user_id: int) -> bool:
        """删除聊天会话（软删除）"""
        # 获取会话
        session = self.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        # 检查权限
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除该会话"
            )
        
        # 软删除：设置为非激活状态
        session.is_active = False
        session.updated_at = datetime.utcnow()
        
        # 也可以选择硬删除所有相关聊天记录
        # db.query(ChatRecord).filter(ChatRecord.session_id == session_id).delete()
        
        db.commit()
        
        return True
    
    def get_user_sessions(
        self, 
        db: Session, 
        user_id: int, 
        is_active: Optional[bool] = None,
        skip: int = 0, 
        limit: int = 20
    ) -> List[ChatSession]:
        """获取用户的聊天会话列表"""
        query = db.query(ChatSession).filter(ChatSession.user_id == user_id)
        
        if is_active is not None:
            query = query.filter(ChatSession.is_active == is_active)
        
        # 获取会话列表
        sessions = query.order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()
        
        # 更新每个会话的消息数量和最后一条消息
        for session in sessions:
            # 获取最后一条消息
            last_message = db.query(ChatRecord).filter(
                ChatRecord.session_id == session.id
            ).order_by(desc(ChatRecord.created_at)).first()
            
            if last_message:
                session.last_message = last_message.content[:100]  # 截取前100个字符
                session.last_message_at = last_message.created_at
            
            # 获取消息数量
            session.message_count = db.query(ChatRecord).filter(
                ChatRecord.session_id == session.id
            ).count()
        
        return sessions
    
    def create_chat_record(
        self, 
        db: Session, 
        record_data: ChatRecordCreate, 
        user_id: int
    ) -> ChatRecord:
        """创建聊天记录"""
        # 验证会话是否属于该用户
        session = self.get_session_by_id(db, record_data.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作该会话"
            )
        
        # 创建聊天记录
        db_record = ChatRecord(
            session_id=record_data.session_id,
            message_type=record_data.message_type,
            content=record_data.content,
            is_from_user=record_data.is_from_user,
            attachments=json.dumps(record_data.attachments) if record_data.attachments else "[]",
            metadata="{}"
        )
        
        db.add(db_record)
        
        # 更新会话的最后活动时间
        session.updated_at = datetime.utcnow()
        session.last_message = record_data.content[:100]
        session.last_message_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_record)
        
        return db_record
    
    def get_chat_history(
        self, 
        db: Session, 
        session_id: int, 
        user_id: int,
        limit: int = 50, 
        offset: int = 0,
        before_id: Optional[int] = None,
        after_id: Optional[int] = None
    ) -> List[ChatRecord]:
        """获取聊天历史"""
        # 验证会话是否属于该用户
        session = self.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看该会话"
            )
        
        # 构建查询
        query = db.query(ChatRecord).filter(ChatRecord.session_id == session_id)
        
        # 根据ID过滤
        if before_id:
            query = query.filter(ChatRecord.id < before_id)
        if after_id:
            query = query.filter(ChatRecord.id > after_id)
        
        # 按时间排序并分页
        return query.order_by(desc(ChatRecord.created_at)).offset(offset).limit(limit).all()
    
    async def create_chat_completion(
        self, 
        db: Session, 
        completion_data: ChatCompletionRequest, 
        user_id: int
    ) -> Dict[str, Any]:
        """创建聊天完成（与AI对话）"""
        # 获取或创建会话
        if completion_data.session_id:
            session = self.get_session_by_id(db, completion_data.session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="会话不存在"
                )
            
            if session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权操作该会话"
                )
        else:
            # 创建新会话
            session_create = ChatSessionCreate(
                ai_model=completion_data.ai_model,
                title=f"对话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            session = self.create_session(db, session_create, user_id)
        
        # 保存用户消息
        user_message = self.create_chat_record(
            db, 
            ChatRecordCreate(
                session_id=session.id,
                content=completion_data.message,
                is_from_user=True
            ),
            user_id
        )
        
        try:
            # 获取历史消息作为上下文
            history = self.get_chat_history(
                db, 
                session.id, 
                user_id, 
                limit=settings.CHAT_HISTORY_LIMIT
            )
            
            # 构建上下文
            messages = []
            if completion_data.system_prompt:
                messages.append({"role": "system", "content": completion_data.system_prompt})
            else:
                messages.append({"role": "system", "content": settings.DEFAULT_SYSTEM_PROMPT})
            
            # 添加历史消息（按时间正序）
            for record in reversed(history):
                role = "user" if record.is_from_user else "assistant"
                messages.append({"role": role, "content": record.content})
            
            # 添加最新用户消息
            messages.append({"role": "user", "content": completion_data.message})
            
            # 调用AI服务获取回复
            ai_response = await self.ai_service.generate_response(
                messages=messages,
                model=completion_data.ai_model or session.ai_model,
                temperature=completion_data.temperature,
                max_tokens=completion_data.max_tokens
            )
            
            # 保存AI回复
            ai_message = self.create_chat_record(
                db, 
                ChatRecordCreate(
                    session_id=session.id,
                    content=ai_response,
                    is_from_user=False,
                    message_type="ai"
                ),
                user_id
            )
            
            return {
                "session_id": session.id,
                "user_message": user_message.content,
                "ai_response": ai_message.content,
                "created_at": ai_message.created_at
            }
            
        except Exception as e:
            # 记录错误
            error_message = str(e)
            # 创建系统消息记录错误
            self.create_chat_record(
                db, 
                ChatRecordCreate(
                    session_id=session.id,
                    content=f"系统错误: {error_message[:100]}",
                    is_from_user=False,
                    message_type="system"
                ),
                user_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI回复生成失败"
            )
    
    def clear_chat_history(self, db: Session, session_id: int, user_id: int) -> bool:
        """清空聊天历史"""
        # 验证会话是否属于该用户
        session = self.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
        
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作该会话"
            )
        
        # 删除该会话的所有聊天记录
        db.query(ChatRecord).filter(ChatRecord.session_id == session_id).delete()
        
        # 重置会话的最后消息信息
        session.last_message = None
        session.last_message_at = None
        session.updated_at = datetime.utcnow()
        
        db.commit()
        
        return True


# 创建全局的聊天服务实例
chat_service = ChatService()