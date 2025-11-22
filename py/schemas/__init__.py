"""
Pydantic模型包
用于数据验证和序列化
"""
from .user import (
    UserCreate, UserLogin, UserResponse, UserUpdate,
    Token, TokenData, AdminCreate, AdminResponse,
    VerificationCodeCreate, VerificationCodeVerify
)
from .resource import (
    ResourceCreate, ResourceUpdate, ResourceResponse,
    CollectionCreate, CollectionResponse,
    PublicResourceCreate, PublicResourceUpdate, PublicResourceResponse
)
from .chat import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
    ChatRecordCreate, ChatRecordResponse
)
from .file import (
    UserFileUpload, UserFileResponse, UserFileUpdate,
    FileShareCreate, FileShareResponse
)
from .feedback import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse
)
from .common import (
    ResponseModel, ErrorResponse, PaginatedResponse
)

__all__ = [
    # 用户相关
    'UserCreate', 'UserLogin', 'UserResponse', 'UserUpdate',
    'Token', 'TokenData', 'AdminCreate', 'AdminResponse',
    'VerificationCodeCreate', 'VerificationCodeVerify',
    # 资源相关
    'ResourceCreate', 'ResourceUpdate', 'ResourceResponse',
    'CollectionCreate', 'CollectionResponse',
    'PublicResourceCreate', 'PublicResourceUpdate', 'PublicResourceResponse',
    # 聊天相关
    'ChatSessionCreate', 'ChatSessionUpdate', 'ChatSessionResponse',
    'ChatRecordCreate', 'ChatRecordResponse',
    # 文件相关
    'UserFileUpload', 'UserFileResponse', 'UserFileUpdate',
    'FileShareCreate', 'FileShareResponse',
    # 反馈相关
    'FeedbackCreate', 'FeedbackUpdate', 'FeedbackResponse',
    # 通用
    'ResponseModel', 'ErrorResponse', 'PaginatedResponse'
]