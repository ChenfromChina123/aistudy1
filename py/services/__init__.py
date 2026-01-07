"""
服务层包
负责封装业务逻辑，处理复杂的业务操作
"""
from .auth_service import AuthService
from .user_service import UserService
from .resource_service import ResourceService
from .chat_service import ChatService
from .file_service import FileService
from .feedback_service import FeedbackService
# AIService暂时不可用，稍后实现

__all__ = [
    'AuthService',
    'UserService', 
    'ResourceService',
    'ChatService',
    'FileService',
    'FeedbackService',
    'AIService'
]