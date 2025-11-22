"""
文件相关Pydantic模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import os


class UserFileBase(BaseModel):
    """用户文件基础模型"""
    filename: str = Field(..., description="文件名")
    content_type: str = Field(..., description="文件类型")
    description: Optional[str] = Field(None, max_length=500, description="文件描述")
    is_private: bool = Field(default=True, description="是否私有")
    
    @field_validator('filename')
    def filename_validator(cls, v: str) -> str:
        """验证文件名，防止路径遍历攻击"""
        # 检查是否包含危险字符
        dangerous_chars = ['..', '\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in v:
                raise ValueError('文件名包含非法字符')
        return v.strip()


class UserFileUpload(BaseModel):
    """用户文件上传模型"""
    description: Optional[str] = Field(None, max_length=500, description="文件描述")
    is_private: bool = Field(default=True, description="是否私有")


class UserFileResponse(BaseModel):
    """用户文件响应模型"""
    id: int = Field(..., description="文件ID")
    user_id: int = Field(..., description="用户ID")
    filename: str = Field(..., description="文件名")
    content_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小（字节）")
    file_path: str = Field(..., description="文件路径")
    description: Optional[str] = Field(None, description="文件描述")
    is_private: bool = Field(..., description="是否私有")
    download_count: int = Field(default=0, description="下载次数")
    created_at: Optional[datetime] = Field(None, description="上传时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    # 计算文件大小的可读表示
    @property
    def size_readable(self) -> str:
        """返回可读的文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    class Config:
        from_attributes = True


class UserFileUpdate(BaseModel):
    """用户文件更新模型"""
    filename: Optional[str] = Field(None, description="文件名")
    description: Optional[str] = Field(None, max_length=500, description="文件描述")
    is_private: Optional[bool] = Field(None, description="是否私有")
    
    @field_validator('filename')
    def filename_validator(cls, v: Optional[str]) -> Optional[str]:
        """验证文件名"""
        if v:
            dangerous_chars = ['..', '\\', '/', ':', '*', '?', '"', '<', '>', '|']
            for char in dangerous_chars:
                if char in v:
                    raise ValueError('文件名包含非法字符')
            return v.strip()
        return v


class FileShareCreate(BaseModel):
    """文件分享创建模型"""
    file_id: int = Field(..., description="文件ID")
    share_type: Literal["public", "password", "link"] = Field(
        default="public", description="分享类型"
    )
    password: Optional[str] = Field(None, description="分享密码")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    max_downloads: Optional[int] = Field(None, ge=1, description="最大下载次数")
    
    @field_validator('password')
    def password_validator(cls, v: Optional[str], info: Any) -> Optional[str]:
        """验证分享密码"""
        if info.data.get('share_type') == 'password' and not v:
            raise ValueError('分享类型为密码时必须提供密码')
        return v


class FileShareResponse(BaseModel):
    """文件分享响应模型"""
    id: int = Field(..., description="分享ID")
    file_id: int = Field(..., description="文件ID")
    user_id: int = Field(..., description="分享者ID")
    share_type: str = Field(..., description="分享类型")
    share_link: str = Field(..., description="分享链接")
    access_code: str = Field(..., description="访问码")
    password: Optional[str] = Field(None, description="分享密码")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    max_downloads: Optional[int] = Field(None, description="最大下载次数")
    current_downloads: int = Field(default=0, description="当前下载次数")
    is_active: bool = Field(default=True, description="是否有效")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    file: Optional[UserFileResponse] = Field(None, description="文件信息")
    
    class Config:
        from_attributes = True


class FileShareVerify(BaseModel):
    """文件分享验证模型"""
    access_code: str = Field(..., description="访问码")
    password: Optional[str] = Field(None, description="分享密码")


class FileSearchParams(BaseModel):
    """文件搜索参数模型"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    content_type: Optional[str] = Field(None, description="文件类型")
    min_size: Optional[int] = Field(None, ge=0, description="最小文件大小")
    max_size: Optional[int] = Field(None, ge=0, description="最大文件大小")
    is_private: Optional[bool] = Field(None, description="是否私有")
    sort_by: Literal["created_at", "file_size", "filename"] = Field(
        default="created_at", description="排序字段"
    )
    order: Literal["asc", "desc"] = Field(default="desc", description="排序方向")


class FileDownloadStats(BaseModel):
    """文件下载统计模型"""
    file_id: int = Field(..., description="文件ID")
    total_downloads: int = Field(..., description="总下载次数")
    unique_downloads: int = Field(..., description="独立下载次数")
    download_by_date: List[Dict[str, Any]] = Field(..., description="按日期的下载统计")