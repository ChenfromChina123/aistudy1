"""
文件相关数据库模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

from database import Base


class UserFolder(Base):
    """用户文件夹表模型"""
    __tablename__ = 'user_folders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    folder_path = Column(String(500), nullable=False)  # 文件夹路径，如 /folder1/subfolder/
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    
    # 索引：用户ID + 文件夹路径
    __table_args__ = (
        {'extend_existing': True},
    )
    
    # 关系
    user = relationship('User', back_populates='user_folders')
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'folder_path': self.folder_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserFile(Base):
    """用户文件表模型"""
    __tablename__ = 'user_files'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, default=0)  # 文件大小（字节）
    file_extension = Column(String(50), nullable=True)
    mime_type = Column(String(100), nullable=True)
    upload_time = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    last_access = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    folder_id = Column(Integer, nullable=True, default=0)  # 0表示根目录
    
    # 关系
    user = relationship('User', back_populates='user_files')
    shares = relationship('FileShare', back_populates='file', cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_extension': self.file_extension,
            'mime_type': self.mime_type,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'last_access': self.last_access.isoformat() if self.last_access else None,
            'is_deleted': self.is_deleted,
            'folder_id': self.folder_id,
            'share_count': len(self.shares)
        }


class FileShare(Base):
    """文件分享表模型"""
    __tablename__ = 'file_shares'
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('user_files.id'), nullable=False)
    share_code = Column(String(50), unique=True, nullable=False, index=True)
    shared_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    shared_to = Column(Integer, ForeignKey('users.id'), nullable=True)  # 为空表示公开分享
    shared_at = Column(DateTime, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=True)  # 为空表示永不过期
    is_active = Column(Boolean, default=True)
    access_count = Column(Integer, default=0)
    
    # 关系
    file = relationship('UserFile', back_populates='shares')
    sharer = relationship('User', foreign_keys=[shared_by], backref='shared_files')
    recipient = relationship('User', foreign_keys=[shared_to], backref='received_files')
    
    def is_expired(self) -> bool:
        """检查分享是否过期"""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'file_id': self.file_id,
            'share_code': self.share_code,
            'shared_by': self.shared_by,
            'shared_to': self.shared_to,
            'shared_at': self.shared_at.isoformat() if self.shared_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'access_count': self.access_count,
            'is_expired': self.is_expired(),
            'file': self.file.to_dict() if self.file else None,
            'sharer_name': self.sharer.username if self.sharer else None
        }