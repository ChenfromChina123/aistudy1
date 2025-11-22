"""
API路由模块
提供所有HTTP接口的路由定义
"""

from fastapi import APIRouter

# 导入各个模块的路由
from .auth import router as auth_router
from .user import router as user_router
from .resource import router as resource_router
from .chat import router as chat_router
from .file import router as file_router
from .feedback import router as feedback_router

# 创建主路由实例
api_router = APIRouter()

# 注册子路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(user_router, prefix="/users", tags=["用户"])
api_router.include_router(resource_router, prefix="/resources", tags=["学习资源"])
api_router.include_router(chat_router, prefix="/chat", tags=["AI聊天"])
api_router.include_router(file_router, prefix="/files", tags=["文件管理"])
api_router.include_router(feedback_router, prefix="/feedback", tags=["反馈建议"])

__all__ = ["api_router"]