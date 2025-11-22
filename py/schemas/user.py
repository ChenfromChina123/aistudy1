"""
用户相关Pydantic模型
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import re


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=80, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    
    @field_validator('username')
    def username_validator(cls, v: str) -> str:
        """验证用户名格式"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=6, description="密码")
    
    @field_validator('password')
    def password_validator(cls, v: str) -> str:
        """验证密码强度"""
        # 至少包含一个字母和一个数字
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含至少一个字母和一个数字')
        return v


class UserLogin(BaseModel):
    """用户登录模型"""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=80, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: Optional[str] = Field(None, min_length=6, description="新密码")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    
    @field_validator('username')
    def username_validator(cls, v: Optional[str]) -> Optional[str]:
        """验证用户名格式"""
        if v and not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    avatar: Optional[str] = Field(None, description="头像URL")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    is_active: bool = Field(..., description="是否激活")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token响应模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    user: Optional[UserResponse] = Field(None, description="用户信息")


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[int] = Field(None, description="用户ID")
    username: Optional[str] = Field(None, description="用户名")


class AdminCreate(BaseModel):
    """管理员创建模型"""
    user_id: int = Field(..., description="用户ID")
    is_superadmin: bool = Field(default=False, description="是否超级管理员")


class AdminResponse(BaseModel):
    """管理员响应模型"""
    id: int = Field(..., description="管理员ID")
    user_id: int = Field(..., description="用户ID")
    is_superadmin: bool = Field(..., description="是否超级管理员")
    user: Optional[UserResponse] = Field(None, description="用户信息")
    
    class Config:
        from_attributes = True


class VerificationCodeCreate(BaseModel):
    """验证码创建模型"""
    email: EmailStr = Field(..., description="邮箱")
    usage_type: str = Field(..., pattern="^(register|login|reset_password)$", description="使用类型")


class VerificationCodeVerify(BaseModel):
    """验证码验证模型"""
    email: EmailStr = Field(..., description="邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")
    usage_type: str = Field(..., pattern="^(register|login|reset_password)$", description="使用类型")


class PasswordReset(BaseModel):
    """密码重置模型"""
    email: EmailStr = Field(..., description="邮箱")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")
    new_password: str = Field(..., min_length=6, description="新密码")
    
    @field_validator('new_password')
    def password_validator(cls, v: str) -> str:
        """验证密码强度"""
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含至少一个字母和一个数字')
        return v