"""
反馈相关Pydantic模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class FeedbackType(str, Enum):
    """反馈类型枚举"""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"
    PRAISE = "praise"
    OTHER = "other"


class FeedbackStatus(str, Enum):
    """反馈状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


class FeedbackBase(BaseModel):
    """反馈基础模型"""
    type: FeedbackType = Field(..., description="反馈类型")
    subject: str = Field(..., min_length=5, max_length=200, description="反馈主题")
    content: str = Field(..., min_length=10, description="反馈内容")
    priority: Literal["low", "medium", "high", "urgent"] = Field(
        default="medium", description="优先级"
    )
    attachments: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="附件列表"
    )
    
    @field_validator('content')
    def content_validator(cls, v: str) -> str:
        """验证反馈内容"""
        if not v or not v.strip():
            raise ValueError('反馈内容不能为空')
        if len(v.strip()) < 10:
            raise ValueError('反馈内容至少需要10个字符')
        return v.strip()


class FeedbackCreate(FeedbackBase):
    """反馈创建模型"""
    email: Optional[str] = Field(None, description="联系方式（可选）")


class FeedbackUpdate(BaseModel):
    """反馈更新模型"""
    status: Optional[FeedbackStatus] = Field(None, description="反馈状态")
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = Field(
        None, description="优先级"
    )
    assignee_id: Optional[int] = Field(None, description="处理人ID")
    response: Optional[str] = Field(None, description="管理员回复")


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    id: int = Field(..., description="反馈ID")
    user_id: Optional[int] = Field(None, description="用户ID")
    type: FeedbackType = Field(..., description="反馈类型")
    subject: str = Field(..., description="反馈主题")
    content: str = Field(..., description="反馈内容")
    priority: str = Field(..., description="优先级")
    status: FeedbackStatus = Field(..., description="反馈状态")
    email: Optional[str] = Field(None, description="联系方式")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件列表")
    assignee_id: Optional[int] = Field(None, description="处理人ID")
    response: Optional[str] = Field(None, description="管理员回复")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    
    class Config:
        from_attributes = True


class FeedbackCommentCreate(BaseModel):
    """反馈评论创建模型"""
    feedback_id: int = Field(..., description="反馈ID")
    content: str = Field(..., min_length=1, description="评论内容")
    is_internal: bool = Field(default=False, description="是否内部评论")


class FeedbackCommentResponse(BaseModel):
    """反馈评论响应模型"""
    id: int = Field(..., description="评论ID")
    feedback_id: int = Field(..., description="反馈ID")
    user_id: int = Field(..., description="用户ID")
    content: str = Field(..., description="评论内容")
    is_internal: bool = Field(..., description="是否内部评论")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


class FeedbackSearchParams(BaseModel):
    """反馈搜索参数模型"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    type: Optional[FeedbackType] = Field(None, description="反馈类型")
    status: Optional[FeedbackStatus] = Field(None, description="反馈状态")
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = Field(
        None, description="优先级"
    )
    user_id: Optional[int] = Field(None, description="用户ID")
    assignee_id: Optional[int] = Field(None, description="处理人ID")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    sort_by: Literal["created_at", "updated_at", "priority"] = Field(
        default="created_at", description="排序字段"
    )
    order: Literal["asc", "desc"] = Field(default="desc", description="排序方向")


class FeedbackStatsResponse(BaseModel):
    """反馈统计响应模型"""
    total: int = Field(..., description="总反馈数")
    by_type: Dict[str, int] = Field(..., description="按类型统计")
    by_status: Dict[str, int] = Field(..., description="按状态统计")
    by_priority: Dict[str, int] = Field(..., description="按优先级统计")
    average_resolution_time: Optional[float] = Field(
        None, description="平均解决时间（小时）"
    )
    pending_count: int = Field(..., description="待处理数量")
    recent_feedback: List[FeedbackResponse] = Field(
        default_factory=list, description="最近的反馈"
    )