"""
身份验证服务
处理用户认证相关的业务逻辑
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import secrets
import string

from models import User, VerificationCode
from schemas.user import (
    UserCreate, UserLogin, Token, TokenData,
    VerificationCodeCreate, VerificationCodeVerify
)
from config import settings
from utils.email_utils import send_email, VerificationCodeGenerator


class AuthService:
    """身份验证服务类"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.code_generator = VerificationCodeGenerator()
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希值"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    def decode_token(self, token: str) -> TokenData:
        """解码令牌"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id: int = payload.get("sub")
            username: str = payload.get("username")
            if user_id is None:
                raise credentials_exception
            token_data = TokenData(user_id=int(user_id), username=username)
        except (JWTError, ValueError):
            raise credentials_exception
        
        return token_data
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """验证用户"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        return user
    
    def login(self, db: Session, login_data: UserLogin) -> Token:
        """用户登录"""
        # 验证用户
        user = self.authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 检查用户是否激活
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账户未激活"
            )
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.commit()
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires
        )
        
        # 返回令牌和用户信息
        from schemas.user import UserResponse
        user_response = UserResponse.model_validate(user)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
    
    def register(self, db: Session, user_data: UserCreate) -> User:
        """用户注册"""
        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该邮箱已被注册"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该用户名已被使用"
                )
        
        # 创建新用户
        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            is_active=True  # 直接激活，后续可以改为需要邮箱验证
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # 发送注册成功邮件（可选）
        try:
            send_email(
                to_email=db_user.email,
                subject="注册成功",
                content=f"亲爱的 {db_user.username}，您已成功注册！"
            )
        except Exception:
            # 邮件发送失败不影响注册
            pass
        
        return db_user
    
    def generate_verification_code(self, db: Session, code_data: VerificationCodeCreate) -> str:
        """生成验证码"""
        # 生成6位数字验证码
        code = self.code_generator.generate_numeric_code(length=6)
        
        # 删除该邮箱之前的验证码
        db.query(VerificationCode).filter(
            VerificationCode.email == code_data.email,
            VerificationCode.usage_type == code_data.usage_type
        ).delete()
        
        # 创建新验证码记录
        expires_at = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        db_code = VerificationCode(
            email=code_data.email,
            code=code,
            usage_type=code_data.usage_type,
            expires_at=expires_at
        )
        
        db.add(db_code)
        db.commit()
        
        # 发送验证码邮件
        subject_map = {
            "register": "注册验证码",
            "login": "登录验证码",
            "reset_password": "重置密码验证码"
        }
        
        subject = subject_map.get(code_data.usage_type, "验证码")
        content = f"您的验证码是：{code}，有效期{settings.VERIFICATION_CODE_EXPIRE_MINUTES}分钟，请尽快使用。"
        
        try:
            send_email(to_email=code_data.email, subject=subject, content=content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="验证码发送失败"
            )
        
        return code
    
    def verify_verification_code(self, db: Session, verify_data: VerificationCodeVerify) -> bool:
        """验证验证码"""
        # 查询验证码
        code_record = db.query(VerificationCode).filter(
            VerificationCode.email == verify_data.email,
            VerificationCode.code == verify_data.code,
            VerificationCode.usage_type == verify_data.usage_type
        ).first()
        
        if not code_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误"
            )
        
        # 检查是否过期
        if datetime.utcnow() > code_record.expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码已过期"
            )
        
        # 验证成功后删除验证码，防止重复使用
        db.delete(code_record)
        db.commit()
        
        return True
    
    def reset_password(self, db: Session, email: str, new_password: str) -> bool:
        """重置密码"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 更新密码
        user.password_hash = self.get_password_hash(new_password)
        db.commit()
        
        # 发送密码重置成功邮件
        try:
            send_email(
                to_email=user.email,
                subject="密码重置成功",
                content="您的密码已成功重置，请使用新密码登录。"
            )
        except Exception:
            # 邮件发送失败不影响密码重置
            pass
        
        return True


# 创建全局的认证服务实例
auth_service = AuthService()