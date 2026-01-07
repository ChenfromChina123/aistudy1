"""
资源相关数据库模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
import enum

from database import Base


class Category(Base):
    """分类表模型"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    # 关系
    resources = relationship('Resource', backref='category')


class ResourceType(str, enum.Enum):
    """资源类型枚举"""
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    LINK = "link"
    NOTE = "note"
    OTHER = "other"


class Resource(Base):
    """资源表模型"""
    __tablename__ = 'resources'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(Enum(ResourceType), default=ResourceType.OTHER)
    file_path = Column(String(500), nullable=True)
    url = Column(String(500), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_public = Column(Boolean, default=False)
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    
    # 关系
    user = relationship('User', backref='resources')
    collections = relationship('Collection', back_populates='resource')
    public_resource = relationship('PublicResource', back_populates='resource', uselist=False)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value if self.type else None,
            'file_path': self.file_path,
            'url': self.url,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_public': self.is_public,
            'view_count': self.view_count,
            'download_count': self.download_count,
            'username': self.user.username if self.user else None
        }


class Collection(Base):
    """收藏表模型"""
    __tablename__ = 'collections'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    # 关系
    user = relationship('User', back_populates='collections')
    resource = relationship('Resource', back_populates='collections')
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'resource_id': self.resource_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resource': self.resource.to_dict() if self.resource else None
        }


class PublicResource(Base):
    """公共资源表模型"""
    __tablename__ = 'public_resources'
    
    id = Column(Integer, primary_key=True)
    resource_id = Column(Integer, ForeignKey('resources.id'), unique=True, nullable=False)
    approved = Column(Boolean, default=False)
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # 关系
    resource = relationship('Resource', back_populates='public_resource')
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'resource_id': self.resource_id,
            'approved': self.approved,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'resource': self.resource.to_dict() if self.resource else None
        }