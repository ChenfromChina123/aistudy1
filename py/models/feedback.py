"""
反馈相关数据库模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import enum

from database import Base


class FeedbackType(str, enum.Enum):
    """反馈类型枚举"""
    BUG = "bug"
    SUGGESTION = "suggestion"
    QUESTION = "question"
    OTHER = "other"


class FeedbackStatus(str, enum.Enum):
    """反馈状态枚举"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"  # 已解决
    CLOSED = "closed"  # 已关闭


class Feedback(Base):
    """反馈表模型"""
    __tablename__ = 'feedbacks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(Enum(FeedbackType), default=FeedbackType.OTHER)
    subject = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(FeedbackStatus), default=FeedbackStatus.PENDING)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    file_path = Column(String(500), nullable=True)  # 附件路径
    admin_response = Column(Text, nullable=True)  # 管理员回复
    resolved_at = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship('User', back_populates='feedbacks')
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type.value if self.type else None,
            'subject': self.subject,
            'content': self.content,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'file_path': self.file_path,
            'admin_response': self.admin_response,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'username': self.user.username if self.user else None,
            'email': self.user.email if self.user else None
        }