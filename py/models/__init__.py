"""
数据库模型包
"""
# 导入所有模型，以便在database.py中统一初始化
from .user import User, Admin, VerificationCode
from .resource import Resource, Collection, PublicResource, Category
from .chat import ChatRecord, ChatSession
from .file import UserFile, FileShare, UserFolder
from .feedback import Feedback
from .note import Note

__all__ = [
    # 用户相关
    'User', 'Admin', 'VerificationCode',
    # 资源相关
    'Resource', 'Collection', 'PublicResource', 'Category',
    # 聊天相关
    'ChatRecord', 'ChatSession',
    # 文件相关
    'UserFile', 'FileShare', 'UserFolder',
    # 反馈相关
    'Feedback',
    # 笔记相关
    'Note'
]