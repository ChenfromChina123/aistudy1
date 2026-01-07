"""
统一响应模型定义
"""
from typing import Optional, Any, TypeVar, Generic
from pydantic import BaseModel, Field

T = TypeVar('T')

class ResponseModel(BaseModel, Generic[T]):
    """
    统一响应模型
    
    示例：
    {
        "code": 200,
        "message": "操作成功",
        "data": {...}
    }
    """
    code: int = Field(200, description="状态码，200表示成功")
    message: str = Field("操作成功", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "操作成功",
                "data": {}
            }
        }

class ErrorResponse(BaseModel):
    """
    错误响应模型
    
    示例：
    {
        "code": 400,
        "message": "参数错误",
        "detail": "缺少必要参数"
    }
    """
    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 400,
                "message": "参数错误",
                "detail": "缺少必要参数"
            }
        }

class PaginationResponse(BaseModel, Generic[T]):
    """
    分页响应模型
    
    示例：
    {
        "code": 200,
        "message": "操作成功",
        "data": {
            "items": [...],
            "total": 100,
            "page": 1,
            "page_size": 10,
            "pages": 10
        }
    }
    """
    code: int = Field(200, description="状态码")
    message: str = Field("操作成功", description="响应消息")
    data: dict = Field(..., description="分页数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "操作成功",
                "data": {
                    "items": [],
                    "total": 100,
                    "page": 1,
                    "page_size": 10,
                    "pages": 10
                }
            }
        }

class TokenResponse(BaseModel):
    """
    Token响应模型
    
    示例：
    {
        "access_token": "eyJ...",
        "token_type": "bearer",
        "expires_in": 3600
    }
    """
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(3600, description="过期时间（秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }