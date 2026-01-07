"""
资源相关Pydantic模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class ResourceType(str, Enum):
    """资源类型枚举"""
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    LINK = "link"
    OTHER = "other"


class ResourceBase(BaseModel):
    """资源基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="资源标题")
    type: ResourceType = Field(..., description="资源类型")
    content: Optional[str] = Field(None, description="资源内容")
    url: Optional[str] = Field(None, description="资源URL")
    description: Optional[str] = Field(None, max_length=500, description="资源描述")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签列表")
    
    @field_validator('url')
    def url_validator(cls, v: Optional[str]) -> Optional[str]:
        """简单验证URL格式"""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL必须以http://或https://开头')
        return v


class ResourceCreate(ResourceBase):
    """资源创建模型"""
    pass


class ResourceUpdate(BaseModel):
    """资源更新模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="资源标题")
    content: Optional[str] = Field(None, description="资源内容")
    url: Optional[str] = Field(None, description="资源URL")
    description: Optional[str] = Field(None, max_length=500, description="资源描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_private: Optional[bool] = Field(None, description="是否私有")
    
    @field_validator('url')
    def url_validator(cls, v: Optional[str]) -> Optional[str]:
        """简单验证URL格式"""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL必须以http://或https://开头')
        return v


class ResourceResponse(BaseModel):
    """资源响应模型"""
    id: int = Field(..., description="资源ID")
    title: str = Field(..., description="资源标题")
    type: ResourceType = Field(..., description="资源类型")
    content: Optional[str] = Field(None, description="资源内容")
    url: Optional[str] = Field(None, description="资源URL")
    description: Optional[str] = Field(None, description="资源描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    user_id: int = Field(..., description="创建者ID")
    is_private: bool = Field(default=False, description="是否私有")
    views: int = Field(default=0, description="查看次数")
    likes: int = Field(default=0, description="点赞次数")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    """收藏创建模型"""
    resource_id: int = Field(..., description="资源ID")
    notes: Optional[str] = Field(None, max_length=500, description="收藏备注")


class CollectionResponse(BaseModel):
    """收藏响应模型"""
    id: int = Field(..., description="收藏ID")
    user_id: int = Field(..., description="用户ID")
    resource_id: int = Field(..., description="资源ID")
    notes: Optional[str] = Field(None, description="收藏备注")
    created_at: Optional[datetime] = Field(None, description="收藏时间")
    resource: Optional[ResourceResponse] = Field(None, description="资源信息")
    
    class Config:
        from_attributes = True


class PublicResourceCreate(BaseModel):
    """公共资源创建模型"""
    resource_id: int = Field(..., description="资源ID")
    category: str = Field(..., max_length=50, description="分类")
    recommended: bool = Field(default=False, description="是否推荐")


class PublicResourceUpdate(BaseModel):
    """公共资源更新模型"""
    category: Optional[str] = Field(None, max_length=50, description="分类")
    recommended: Optional[bool] = Field(None, description="是否推荐")
    status: Optional[Literal["pending", "approved", "rejected"]] = Field(
        None, description="审核状态"
    )


class PublicResourceResponse(BaseModel):
    """公共资源响应模型"""
    id: int = Field(..., description="公共资源ID")
    resource_id: int = Field(..., description="资源ID")
    category: str = Field(..., description="分类")
    recommended: bool = Field(..., description="是否推荐")
    status: str = Field(..., description="审核状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    resource: Optional[ResourceResponse] = Field(None, description="资源信息")
    
    class Config:
        from_attributes = True


class ResourceSearchParams(BaseModel):
    """资源搜索参数模型"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    type: Optional[ResourceType] = Field(None, description="资源类型")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    user_id: Optional[int] = Field(None, description="用户ID")
    is_public: Optional[bool] = Field(None, description="是否公开")
    sort_by: Literal["created_at", "views", "likes"] = Field(
        default="created_at", description="排序字段"
    )
    order: Literal["asc", "desc"] = Field(default="desc", description="排序方向")