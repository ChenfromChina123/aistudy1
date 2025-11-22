"""
用户相关数据库模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from passlib.context import CryptContext

from database import Base

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """用户表模型"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)  # 头像URL/路径
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    
    # 关系
    admin_role = relationship('Admin', back_populates='user', uselist=False)
    notes = relationship('Note', back_populates='user')
    user_files = relationship('UserFile', back_populates='user')
    user_folders = relationship('UserFolder', back_populates='user')
    chat_records = relationship('ChatRecord', back_populates='user')
    collections = relationship('Collection', back_populates='user')
    feedbacks = relationship('Feedback', back_populates='user')
    
    def set_password(self, password: str) -> None:
        """设置密码（加密存储）"""
        self.password_hash = pwd_context.hash(password)
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(password, self.password_hash)
    
    def update_password_by_email(self, new_password: str) -> None:
        """通过邮箱更新密码"""
        self.set_password(new_password)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar': self.avatar,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Admin(Base):
    """管理员表模型"""
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    # 关系
    user = relationship('User', back_populates='admin_role')
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'is_superadmin': self.is_superadmin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': self.user.to_dict() if self.user else None
        }


class VerificationCode(Base):
    """验证码表模型"""
    __tablename__ = 'verification_codes'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(120), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    usage_type = Column(String(20), nullable=False)  # 'register', 'login', 'reset_password'
    
    def is_expired(self) -> bool:
        """检查验证码是否过期"""
        return datetime.now(UTC) > self.expires_at
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'email': self.email,
            'code': self.code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_used': self.is_used,
            'usage_type': self.usage_type,
            'is_expired': self.is_expired()
        }