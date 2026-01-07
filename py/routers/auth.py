"""
认证路由
处理用户登录、注册等认证相关的API接口
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime

from database import get_db
from schemas.user import (
    UserCreate, UserLogin, UserResponse,
    PasswordReset, VerificationCodeCreate
)
from schemas.response import TokenResponse
from schemas.common import ResponseModel, ErrorResponse
from services.auth_service import auth_service
from models import User, VerificationCode

# 创建路由实例
router = APIRouter()


@router.post("/register", response_model=ResponseModel)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册
    - **username**: 用户名，3-20个字符
    - **email**: 邮箱地址
    - **password**: 密码，至少8个字符
    - **nickname**: 昵称
    - **avatar**: 头像URL（可选）
    """
    # 验证邮箱是否已被注册
    if auth_service.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )
    
    # 验证用户名是否已被使用
    if auth_service.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被使用"
        )
    
    # 创建用户
    user = auth_service.register_user(db, user_data)
    
    return ResponseModel(
        code=200,
        message="注册成功",
        data=user.to_dict()
    )


@router.post("/login", response_model=ResponseModel)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录（OAuth2兼容）
    使用用户名/邮箱和密码登录
    - **username**: 用户名或邮箱
    - **password**: 密码
    """
    # 验证用户
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员"
        )
    
    # 创建访问令牌
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})
    
    # 更新登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return ResponseModel(
        code=200,
        message="登录成功",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user.to_dict()
        }
    )


@router.post("/login/json", response_model=ResponseModel)
async def login_json(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    用户登录（JSON格式）
    使用邮箱和密码登录
    - **email**: 邮箱地址
    - **password**: 密码
    """
    # 验证用户
    user = auth_service.authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    # 检查用户是否被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员"
        )
    
    # 创建访问令牌
    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})
    
    # 更新登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return ResponseModel(
        code=200,
        message="登录成功",
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user.to_dict()
        }
    )


@router.post("/refresh", response_model=ResponseModel)
async def refresh_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    刷新访问令牌
    需要在请求头中提供刷新令牌
    """
    # 从请求头获取刷新令牌
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少有效的刷新令牌"
        )
    
    refresh_token = authorization.split(" ")[1]
    
    # 验证刷新令牌
    user_id = auth_service.verify_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的刷新令牌"
        )
    
    # 获取用户信息
    user = auth_service.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )
    
    # 创建新的访问令牌
    new_access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    
    return ResponseModel(
        code=200,
        message="令牌刷新成功",
        data={
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    )


@router.post("/verify-email")
async def verify_email(
    request: VerificationCodeCreate,
    db: Session = Depends(get_db)
):
    """
    验证邮箱
    - **email**: 邮箱地址
    - **code**: 验证码
    """
    # 验证邮箱和验证码
    success = auth_service.verify_email_code(db, request.email, request.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )
    
    # 更新用户邮箱状态为已验证
    user = auth_service.get_user_by_email(db, request.email)
    if user:
        user.email_verified = True
        db.commit()
    
    return ResponseModel(
        code=200,
        message="邮箱验证成功"
    )


@router.post("/send-code")
async def send_verification_code(
    request: VerificationCodeCreate,
    db: Session = Depends(get_db)
):
    """
    发送验证码
    - **email**: 邮箱地址
    """
    # 检查用户是否存在
    user = auth_service.get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 生成并发送验证码
    code = auth_service.generate_email_code(db, request.email)
    
    # 这里应该调用邮件服务发送验证码
    # 暂时模拟发送成功
    print(f"验证码 {code} 已发送到 {request.email}")
    
    return ResponseModel(
        code=200,
        message="验证码已发送"
    )


@router.post("/password-reset")
async def password_reset_request(
    request: VerificationCodeCreate,
    db: Session = Depends(get_db)
):
    """
    请求重置密码
    - **email**: 邮箱地址
    """
    # 检查用户是否存在
    user = auth_service.get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 生成并发送重置验证码
    code = auth_service.generate_email_code(db, request.email, "reset")
    
    # 这里应该调用邮件服务发送验证码
    print(f"重置密码验证码 {code} 已发送到 {request.email}")
    
    return ResponseModel(
        code=200,
        message="重置密码链接已发送到您的邮箱"
    )


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    确认重置密码
    - **email**: 邮箱地址
    - **code**: 验证码
    - **new_password**: 新密码
    """
    # 验证验证码
    success = auth_service.verify_email_code(db, reset_data.email, reset_data.code, "reset")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期"
        )
    
    # 重置密码
    user = auth_service.get_user_by_email(db, reset_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 更新密码
    hashed_password = auth_service.get_password_hash(reset_data.new_password)
    user.password_hash = hashed_password
    db.commit()
    
    return ResponseModel(
        code=200,
        message="密码重置成功"
    )


@router.post("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登出
    可选：将token加入黑名单
    """
    # 这里可以实现token黑名单功能
    # 暂时只返回成功消息
    return ResponseModel(
        code=200,
        message="登出成功"
    )