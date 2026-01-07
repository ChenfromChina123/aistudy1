"""
通用Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, List, Dict, Any

T = TypeVar('T')


class ResponseModel(BaseModel):
    """通用响应模型"""
    status: str = Field(default="success", description="操作状态")
    message: str = Field(default="", description="响应消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "操作成功",
                "data": {"key": "value"}
            }
        }


class ErrorResponse(BaseModel):
    """错误响应模型"""
    status: str = Field(default="error", description="操作状态")
    message: str = Field(..., description="错误消息")
    error_code: Optional[int] = Field(default=None, description="错误码")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "请求失败",
                "error_code": 400,
                "details": {"field": "email", "message": "邮箱格式错误"}
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    items: List[T] = Field(..., description="当前页的数据项")
    total: int = Field(..., description="总数据量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    
    @classmethod
    def calculate_pages(cls, total: int, page_size: int) -> int:
        """计算总页数"""
        return (total + page_size - 1) // page_size if page_size > 0 else 1
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [{"id": 1, "name": "示例"}],
                "total": 100,
                "page": 1,
                "page_size": 10,
                "pages": 10
            }
        }


class PaginationParams(BaseModel):
    """分页参数模型"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页大小")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 10
            }
        }