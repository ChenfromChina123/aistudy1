"""
聊天相关数据库模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import enum

from database import Base


class MessageType(str, enum.Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class ChatSession(Base):
    """聊天会话表模型"""
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), default="新会话")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_active = Column(Boolean, default=True)
    
    # 关系
    user = relationship('User', backref='chat_sessions')
    chat_records = relationship('ChatRecord', back_populates='session', cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'message_count': len(self.chat_records)
        }


class ChatRecord(Base):
    """聊天记录表模型"""
    __tablename__ = 'chat_records'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), ForeignKey('chat_sessions.session_id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    sender_id = Column(Integer, nullable=False)  # 1=用户, 2=AI
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    content = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    is_read = Column(Boolean, default=False)
    
    # 关系
    user = relationship('User', back_populates='chat_records')
    session = relationship('ChatSession', back_populates='chat_records')
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'sender_id': self.sender_id,
            'message_type': self.message_type.value if self.message_type else None,
            'content': self.content,
            'file_path': self.file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_read': self.is_read,
            'sender_type': "user" if self.sender_id == 1 else "ai" if self.sender_id == 2 else "system"
        }