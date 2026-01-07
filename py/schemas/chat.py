"""
聊天相关Pydantic模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    AI = "ai"


class ChatSessionBase(BaseModel):
    """聊天会话基础模型"""
    title: Optional[str] = Field(None, max_length=200, description="会话标题")
    is_active: bool = Field(default=True, description="是否激活")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="会话元数据")


class ChatSessionCreate(ChatSessionBase):
    """聊天会话创建模型"""
    ai_model: Optional[str] = Field(None, description="使用的AI模型")


class ChatSessionUpdate(BaseModel):
    """聊天会话更新模型"""
    title: Optional[str] = Field(None, max_length=200, description="会话标题")
    is_active: Optional[bool] = Field(None, description="是否激活")
    metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")
    ai_model: Optional[str] = Field(None, description="使用的AI模型")


class ChatSessionResponse(BaseModel):
    """聊天会话响应模型"""
    id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    title: str = Field(..., description="会话标题")
    ai_model: Optional[str] = Field(None, description="使用的AI模型")
    is_active: bool = Field(..., description="是否激活")
    message_count: int = Field(default=0, description="消息数量")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_message: Optional[str] = Field(None, description="最后一条消息内容")
    last_message_at: Optional[datetime] = Field(None, description="最后一条消息时间")
    
    class Config:
        from_attributes = True


class ChatRecordCreate(BaseModel):
    """聊天记录创建模型"""
    session_id: int = Field(..., description="会话ID")
    message_type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    content: str = Field(..., description="消息内容")
    is_from_user: bool = Field(default=True, description="是否来自用户")
    attachments: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="附件列表"
    )


class ChatRecordUpdate(BaseModel):
    """聊天记录更新模型"""
    content: Optional[str] = Field(None, description="消息内容")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")


class ChatRecordResponse(BaseModel):
    """聊天记录响应模型"""
    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="会话ID")
    message_type: MessageType = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    is_from_user: bool = Field(..., description="是否来自用户")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    session_id: Optional[int] = Field(None, description="会话ID，为空则创建新会话")
    message: str = Field(..., description="用户消息")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    ai_model: Optional[str] = Field(None, description="使用的AI模型")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=1000, ge=1, le=4000, description="最大令牌数")
    
    @field_validator('message')
    def message_validator(cls, v: str) -> str:
        """验证消息内容"""
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()


class ChatHistoryParams(BaseModel):
    """聊天历史参数模型"""
    session_id: int = Field(..., description="会话ID")
    limit: int = Field(default=50, ge=1, le=200, description="返回消息数量限制")
    offset: int = Field(default=0, ge=0, description="偏移量")
    before_id: Optional[int] = Field(None, description="获取此ID之前的消息")
    after_id: Optional[int] = Field(None, description="获取此ID之后的消息")


class ChatSessionListParams(BaseModel):
    """聊天会话列表参数模型"""
    is_active: Optional[bool] = Field(None, description="是否激活")
    search: Optional[str] = Field(None, description="搜索关键词")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量限制")
    offset: int = Field(default=0, ge=0, description="偏移量")