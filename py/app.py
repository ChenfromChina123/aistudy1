from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form
from urllib.parse import quote
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.formparsers import MultiPartParser
from starlette.datastructures import FormData, UploadFile as StarletteUploadFile
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, func, UniqueConstraint, Index, desc, text, inspect, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime, timedelta, UTC
from pydantic import BaseModel, Field, EmailStr, validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
import json
import os
import re
import socket
import netifaces
import logging
import secrets
import string
import uuid
import asyncio
import smtplib
import random
import shutil
import zipfile
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from passlib.context import CryptContext
import enum
from openai import OpenAI

from werkzeug.security import check_password_hash, generate_password_hash

# 从自定义模块导入JWT功能，保持与app.py一致
from utils.jwt_utils import generate_jwt, verify_jwt
from utils.email_utils import send_reset_email_last
from config import settings

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 使用统一配置管理
from config import settings

# 验证配置
missing_configs = settings.validate()
if missing_configs:
    logger.warning("配置验证警告:")
    for config in missing_configs:
        logger.warning(f"  - {config}")
else:
    logger.info("配置验证通过 ✓")

# 修改 Starlette 的默认文件大小限制
# 这是解决 HTTP 413 错误的关键方法
import starlette.formparsers

# 直接修改 Starlette 的默认常量
# 这会影响所有的 multipart 解析
if hasattr(starlette.formparsers, 'MAX_FILE_SIZE'):
    original_max_file_size = starlette.formparsers.MAX_FILE_SIZE
    starlette.formparsers.MAX_FILE_SIZE = settings.MAX_FILE_SIZE * 2
    logger.info(f"已修改 Starlette MAX_FILE_SIZE: {original_max_file_size / (1024 * 1024):.0f}MB -> {starlette.formparsers.MAX_FILE_SIZE / (1024 * 1024):.0f}MB")

# 同时修改其他可能的限制常量
if hasattr(starlette.formparsers, 'MAX_FIELD_SIZE'):
    starlette.formparsers.MAX_FIELD_SIZE = settings.MAX_FILE_SIZE * 2
    logger.info(f"已修改 Starlette MAX_FIELD_SIZE: {starlette.formparsers.MAX_FIELD_SIZE / (1024 * 1024):.0f}MB")

# 尝试修改 MultiPartParser 类的默认属性
try:
    # 修改类级别的默认值
    if hasattr(starlette.formparsers.MultiPartParser, 'max_file_size'):
        starlette.formparsers.MultiPartParser.max_file_size = settings.MAX_FILE_SIZE * 2
    
    # 创建一个补丁函数来修改实例
    original_init = starlette.formparsers.MultiPartParser.__init__
    
    def patched_init(self, headers, stream, *, max_files=1000, max_fields=1000):
        original_init(self, headers, stream, max_files=max_files, max_fields=max_fields)
        # 设置更大的文件大小限制
        self.max_file_size = settings.MAX_FILE_SIZE * 2
    
    starlette.formparsers.MultiPartParser.__init__ = patched_init
    logger.info(f"已修补 MultiPartParser，最大文件大小: {settings.MAX_FILE_SIZE * 2 / (1024 * 1024):.0f}MB")
    
except Exception as e:
    logger.warning(f"修补 MultiPartParser 失败: {e}")

logger.info("Starlette 文件大小限制修改完成")

# 初始化FastAPI应用
# 注意：现在使用自定义的 MultiPartParser 来支持大文件上传
app = FastAPI(
    title="AI智能学习导师", 
    description="基于IPv6的AI智能学习助手", 
    version="4.0"
)

# 请求体大小限制中间件（用于额外的检查和日志）
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """限制请求体大小的中间件（用于日志和额外检查）"""
    async def dispatch(self, request: StarletteRequest, call_next):
        # 检查 Content-Length 头并记录日志
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                max_request_size = settings.MAX_FILE_SIZE * 2
                logger.info(f"请求体大小: {size / (1024 * 1024):.2f}MB, 限制: {max_request_size / (1024 * 1024):.2f}MB")
                
                if size > max_request_size:
                    logger.warning(f"请求体超过限制: {size} > {max_request_size}")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "请求体过大",
                            "detail": f"请求体大小 ({size / (1024 * 1024):.2f}MB) 超过限制 ({max_request_size / (1024 * 1024):.2f}MB)",
                            "max_size": max_request_size
                        }
                    )
            except ValueError:
                pass  # 如果无法解析 Content-Length，继续处理
        
        response = await call_next(request)
        return response

# 添加请求体大小限制中间件（在其他中间件之前）
app.add_middleware(RequestSizeLimitMiddleware)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 处理@vite/client请求，避免404错误
@app.get("/@vite/client")
async def handle_vite_client():
    return Response(status_code=204)  # 返回空响应，状态码204

# 数据库配置 - 使用统一配置
DATABASE_URL = settings.DATABASE_URL
logger.info(f"使用数据库URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 数据库会话依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT配置 - 使用统一配置
JWT_KEY = settings.JWT_SECRET_KEY

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# AI模型配置 - 使用统一配置（去首尾空格）
DEEPSEEK_API_KEY = (settings.DEEPSEEK_API_KEY or "").strip()
MAX_TOKEN = settings.MAX_TOKEN
DOUBAO_BASEURL = settings.DOUBAO_BASEURL

# 定义消息发送者类型常量 - 使用配置
USER_SENDER = settings.USER_SENDER
AI_SENDER = settings.AI_SENDER

# 定义消息状态枚举
class MessageStatus(str, enum.Enum):
    PENDING = "pending"      # 处理中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 用户取消

# 文件存储相关常量 - 使用统一配置
BASE_DIR = settings.BASE_DIR
UPLOAD_DIR = settings.UPLOAD_DIR
CLOUD_DISK_DIR = settings.CLOUD_DISK_DIR
NOTES_FOLDER_NAME = settings.NOTES_FOLDER_NAME
MAX_FILE_SIZE = settings.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS

# 确保上传目录和云盘目录存在（已在settings中确保）
logger.info(f"上传目录设置为: {UPLOAD_DIR}")
logger.info(f"云盘目录设置为: {CLOUD_DISK_DIR}")
logger.info(f"最大文件大小限制: {MAX_FILE_SIZE / (1024 * 1024):.0f}MB (可通过环境变量 MAX_FILE_SIZE 配置)")

# 挂载静态文件目录
# 注意：这仅用于开发环境，生产环境应使用专门的文件服务器
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的初始化任务"""
    logger.info("应用正在启动，开始执行初始化任务...")
    
    # 创建所有数据库表（包括新添加的admins表）
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建/检查完成")
    except Exception as e:
        logger.error(f"创建数据库表时出错: {str(e)}")
    
    try:
        if engine.dialect.name == "mysql":
            inspector = inspect(engine)
            cols = inspector.get_columns("users")
            length = None
            for c in cols:
                if c.get("name") == "password_hash":
                    t = c.get("type")
                    try:
                        length = getattr(t, "length", None)
                    except Exception:
                        length = None
                    break
            if not length or (isinstance(length, int) and length < 255):
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255)"))
                    conn.commit()
                logger.info("已自动迁移users.password_hash长度为255")
    except Exception as e:
        logger.error(f"密码哈希列迁移失败: {str(e)}")
    
    
    # 初始化user_favorites表（同步调用）
    init_user_favorites_if_needed()
    # 确保上传目录和云盘目录存在（使用配置方法）
    settings.ensure_directories()
    logger.info("应用启动时确认目录存在")
    
    # 初始化预设单词表（将在路由注册时完成，这里不再重复初始化）
    # 注意：预设单词表的初始化现在在 register_language_learning_routes 中完成
    
    logger.info("初始化任务完成，应用启动成功！")

# 笔记管理类 - 用于专门管理用户笔记
class NoteManager:
    @staticmethod
    def get_user_notes_folder(user_id: int) -> str:
        """获取用户专有的笔记文件夹路径"""
        notes_folder = settings.get_notes_dir_for_user(user_id)
        return str(notes_folder)
    
    @staticmethod
    def get_note_file_path(user_id: int, note_filename: str) -> str:
        """获取笔记文件的完整路径"""
        notes_folder = NoteManager.get_user_notes_folder(user_id)
        return os.path.join(notes_folder, note_filename)
    
    @staticmethod
    def list_user_notes(user_id: int) -> list:
        """列出用户的所有笔记文件（仅返回文件名列表）"""
        notes_folder = NoteManager.get_user_notes_folder(user_id)
        try:
            # 只列出.txt文件
            return [f for f in os.listdir(notes_folder) if f.endswith('.txt')]
        except Exception as e:
            logger.error(f"列出用户笔记失败: {str(e)}")
            return []

# 数据库模型
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)  # 用户头像URL
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    def set_password(self, password: str):
        """设置用户密码（哈希加密）"""
        if len(password) < 6 or len(password) > 20:
            raise ValueError("密码长度需在6-20字符之间")
        self.password_hash = generate_password_hash(password)
    
    @classmethod
    def update_password_by_email(cls, db: Session, email: str, new_password: str):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"开始更新密码，邮箱: {email}")
            user = db.query(cls).filter_by(email=email).first()
            if not user:
                logger.warning(f"更新密码失败：用户不存在，邮箱: {email}")
                return False, "修改失败，请检查信息后重试"

            logger.info(f"找到用户，开始设置新密码")
            user.set_password(new_password)
            logger.info(f"密码已设置，开始提交事务")
            db.commit()
            logger.info(f"密码更新成功，邮箱: {email}")
            return True, "密码修改成功"

        except ValueError as e:
            logger.error(f"密码更新失败（密码验证错误）: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"密码更新失败（系统异常）: {str(e)}", exc_info=True)
            db.rollback()
            return False, f"系统异常，修改失败，请稍后重试: {str(e)}"
    
    def check_password(self, password: str) -> bool:
        """验证密码是否正确"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """将用户信息转换为字典格式"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default=None):
        return getattr(self, key, default) if hasattr(self, key) else default

# 管理员表 - 专门用于记录管理员信息
class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, comment='用户ID')
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    created_at = Column(DateTime, default=datetime.now(UTC), comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), comment='更新时间')
    
    # 建立与用户的关联
    user = relationship('User', backref='admin_role')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'email': self.user.email if self.user else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(UTC))

    resources = relationship('Resource', backref='category', lazy=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

class Resource(Base):
    __tablename__ = 'resources'

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    title = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Integer, default=1, nullable=False)  # 0: 私有, 1: 公共
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    def to_dict(self) -> Dict[str, Any]:
        """将资源对象转换为字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '未分类',
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# 笔记存储模型 - 专门用于笔记管理
class Note(Base):
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    title = Column(String(255), nullable=False, comment='笔记标题')
    file_path = Column(String(255), nullable=False, comment='文件路径')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    
    # 建立与用户的关联
    user = relationship('User', backref='notes')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'file_path': self.file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id
        }

# 用户文件夹模型 - 管理用户创建的文件夹
class UserFolder(Base):
    __tablename__ = 'user_folders'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    folder_path = Column(String(500), nullable=False, comment='文件夹路径')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    
    user = relationship('User', backref='user_folders', lazy=True)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'folder_path', name='unique_user_folder_path'),
    )

# 文件存储模型 - 按照新表结构重新设计
class UserFile(Base):
    __tablename__ = 'files'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    file_uuid = Column(String(36), nullable=False, unique=True, comment='文件唯一标识')
    original_name = Column(String(255), nullable=False, comment='原始文件名')
    save_path = Column(String(255), nullable=False, comment='存储路径')
    file_size = Column(Integer, nullable=False, comment='文件大小（字节）')
    file_type = Column(String(50), nullable=True, comment='MIME类型')
    upload_time = Column(DateTime, default=datetime.now, comment='上传时间')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    folder_path = Column(String(500), default='/', nullable=False, comment='文件所在的文件夹路径，默认根目录')
    
    # 建立与用户的关联
    user = relationship('User', backref='user_files')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'file_uuid': self.file_uuid,
            'original_name': self.original_name,
            'save_path': self.save_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'upload_time': self.upload_time.isoformat() if self.upload_time else None,
            'user_id': self.user_id,
            'folder_path': self.folder_path
        }

class UserFavorite(Base):
    __tablename__ = 'user_favorites'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    resource_id = Column(Integer, ForeignKey('resources.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))

    user = relationship('User', backref='favorites', lazy=True)
    resource = relationship('Resource', backref='favorited_by', lazy=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'resource_id', name='unique_user_resource'),
    )

class VerificationCode(Base):
    __tablename__ = 'verification_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    code = Column(String(6), nullable=False)
    expiration_time = Column(DateTime, nullable=False)
    created_time = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    is_blocked = Column(Boolean, nullable=False, default=False)
    blocked_until = Column(DateTime, nullable=True)
    
    @classmethod
    def get_valid_code(cls, db: Session, email: str) -> Optional['VerificationCode']:
        now = datetime.now(UTC)
        return db.query(cls).filter(
            cls.email == email,
            cls.expiration_time > now
        ).order_by(cls.created_time.desc()).first()

    @classmethod
    def delete_old_codes(cls, db: Session, email: str):
        now = datetime.now(UTC)
        db.query(cls).filter(cls.expiration_time <= now).delete()
        db.query(cls).filter(
            cls.email == email,
            cls.expiration_time > now
        ).delete()
        db.commit()
    
    @classmethod
    def is_email_blocked(cls, db: Session, email: str) -> tuple[bool, str]:
        """检查邮箱是否被封禁"""
        now = datetime.now(UTC)
        
        # 查找该邮箱最近的封禁记录
        blocked_record = db.query(cls).filter(
            cls.email == email,
            cls.is_blocked == True,
            cls.blocked_until > now
        ).first()
        
        if blocked_record:
            # 确保时间对象都有时区信息
            blocked_until = blocked_record.blocked_until
            if blocked_until.tzinfo is None:
                # 如果没有时区信息，假设是UTC
                blocked_until = blocked_until.replace(tzinfo=UTC)
            # 计算剩余封禁时间
            remaining_time = blocked_until - now
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return True, f"该邮箱已被封禁，剩余 {hours} 小时 {minutes} 分钟"
            else:
                return True, f"该邮箱已被封禁，剩余 {minutes} 分钟 {seconds} 秒"
        
        return False, ""
    
    @classmethod
    def can_send_code(cls, db: Session, email: str) -> tuple[bool, str]:
        """检查是否可以发送验证码：60秒限制和一小时内20次限制"""
        now = datetime.now(UTC)
        
        # 1. 检查是否被封禁
        blocked, message = cls.is_email_blocked(db, email)
        if blocked:
            return False, message
        
        # 2. 检查60秒内是否已发送过
        one_minute_ago = now - timedelta(seconds=60)
        recent_code = db.query(cls).filter(
            cls.email == email,
            cls.created_time > one_minute_ago
        ).first()
        
        if recent_code:
            # 确保时间对象都有时区信息
            created_time = recent_code.created_time
            if created_time.tzinfo is None:
                # 如果没有时区信息，假设是UTC
                created_time = created_time.replace(tzinfo=UTC)
            elapsed = now - created_time
            remaining = 60 - elapsed.seconds
            return False, f"验证码发送过于频繁，请等待 {remaining} 秒后重试"
        
        # 3. 检查一小时内发送次数
        one_hour_ago = now - timedelta(hours=1)
        count = db.query(func.count(cls.id)).filter(
            cls.email == email,
            cls.created_time > one_hour_ago
        ).scalar()
        
        if count >= 20:
            # 封禁一天
            blocked_until = now + timedelta(days=1)
            # 创建封禁记录
            block_record = cls(
                email=email,
                code="",  # 封禁记录不需要验证码
                expiration_time=blocked_until,
                created_time=now,
                is_blocked=True,
                blocked_until=blocked_until
            )
            db.add(block_record)
            db.commit()
            return False, "一小时内发送验证码次数过多，该邮箱已被封禁24小时"
        
        return True, ""

    @classmethod
    def insert_verify_code(cls, db: Session, email: str, code: str, expiration_minutes: int = 5) -> Optional['VerificationCode']:
        try:
            if not email or not code:
                raise ValueError("邮箱和验证码不能为空")
            if len(code) != 6:
                raise ValueError("验证码必须为6位")
            if '@' not in email or '.' not in email.split('@')[-1]:
                raise ValueError("请输入有效的邮箱格式")

            cls.delete_old_codes(db, email)

            expiration_time = datetime.now(UTC) + timedelta(minutes=expiration_minutes)
            new_code = cls(
                email=email,
                code=code,
                expiration_time=expiration_time
            )

            db.add(new_code)
            db.commit()
            db.refresh(new_code)
            return new_code

        except ValueError:
            return None
        except Exception:
            db.rollback()
            return None

# 自动初始化user_favorites表函数
def init_user_favorites_if_needed():
    """自动为所有用户标记公共资源连接，仅在需要时执行"""
    logger.info("开始检查user_favorites表初始化状态...")
    
    try:
        # 创建数据库会话
        db = SessionLocal()
        
        # 检查数据库表是否存在
        inspector = inspect(db.bind)
        if not inspector.has_table('user_favorites'):
            logger.warning("user_favorites表不存在，创建表...")
            Base.metadata.create_all(bind=db.bind)
            logger.info("表创建完成")
        
        # 获取所有用户
        users = db.query(User).all()
        logger.info(f"找到 {len(users)} 个用户")
        
        # 获取所有公共资源（is_public=1）
        public_resources = db.query(Resource).filter_by(is_public=1).all()
        logger.info(f"找到 {len(public_resources)} 个公共资源")
        
        # 计算应该有的收藏记录总数
        expected_total = len(users) * len(public_resources)
        
        # 获取当前已有的收藏记录总数
        current_total = db.query(UserFavorite).count()
        logger.info(f"当前已有 {current_total} 条收藏记录，期望值: {expected_total}")
        
        # 如果记录数量不足，进行初始化
        if current_total < expected_total:
            logger.info("开始初始化user_favorites表...")
            
            # 初始化计数器
            total_created = 0
            already_exists = 0
            
            # 为每个用户与每个公共资源创建连接
            for user in users:
                for resource in public_resources:
                    # 检查是否已经存在连接
                    existing = db.query(UserFavorite).filter_by(
                        user_id=user.id,
                        resource_id=resource.id
                    ).first()
                    
                    if not existing:
                        # 创建新的收藏记录
                        new_favorite = UserFavorite(
                            user_id=user.id,
                            resource_id=resource.id,
                            created_at=datetime.now(UTC)
                        )
                        db.add(new_favorite)
                        total_created += 1
                        
                        # 每100条提交一次
                        if total_created % 100 == 0:
                            db.commit()
                            logger.info(f"已创建 {total_created} 条收藏记录...")
                    else:
                        already_exists += 1
            
            # 提交剩余的记录
            db.commit()
            
            logger.info(f"初始化完成！")
            logger.info(f"创建了 {total_created} 条新的收藏记录")
            logger.info(f"跳过了 {already_exists} 条已存在的记录")
        else:
            logger.info("收藏记录数量充足，无需初始化")
            
    except Exception as e:
        logger.error(f"初始化user_favorites表失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

class ChatRecord(Base):
    __tablename__ = "chat_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False)
    message_order = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    sender_type = Column(Integer, nullable=False)
    send_time = Column(
        DateTime,
        default=datetime.now(UTC),
        nullable=False
    )
    user_id = Column(String(64), nullable=False)
    status = Column(
        String(20),
        default=MessageStatus.COMPLETED.value
    )
    ai_model = Column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_session_order", "session_id", "message_order"),
        Index("idx_user_id", "user_id"),
        {"extend_existing": True}
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "message_order": self.message_order,
            "content": self.content,
            "sender_type": self.sender_type,
            "send_time": self.send_time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": self.user_id,
            "status": self.status,
            "ai_model": self.ai_model
        }

# 用户设置模型 - 用于保存用户的AI模型配置
class UserSettings(Base):
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, comment='用户ID')
    model_name = Column(String(100), nullable=True, comment='AI模型名称')
    api_base = Column(String(500), nullable=True, comment='API访问地址')
    api_key = Column(String(500), nullable=True, comment='API密钥')
    model_params = Column(Text, nullable=True, comment='模型参数（JSON格式）')
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    # 建立与用户的关联
    user = relationship('User', backref='settings', lazy=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "api_base": self.api_base,
            "api_key": "***" if self.api_key else None,  # 不返回实际的API密钥
            "model_params": json.loads(self.model_params) if self.model_params else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

# 单词卡片模型 - 用于单词记忆
class WordCard(Base):
    __tablename__ = 'word_cards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 核心字段 - 按照用户要求：单词 音标 词性
    word = Column(String(100), nullable=False, comment='单词')
    phonetic = Column(String(100), nullable=True, comment='音标')
    part_of_speech = Column(String(50), nullable=True, comment='词性')
    definition = Column(Text, nullable=True, comment='释义')
    context = Column(Text, nullable=True, comment='例句/语境')
    
    # SRS (Spaced Repetition System) 字段
    next_review = Column(DateTime, default=datetime.now(UTC), nullable=False, comment='下次复习时间')
    interval = Column(Integer, default=0, comment='复习间隔(毫秒)')
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    user = relationship('User', backref='word_cards', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'term': self.word,
            'phonetic': self.phonetic,
            'part_of_speech': self.part_of_speech,
            'definition': self.definition,
            'context': self.context,
            'nextReview': int(self.next_review.timestamp() * 1000),
            'interval': self.interval
        }

# 用户自定义AI模型
class CustomAIModel(Base):
    __tablename__ = 'custom_ai_models'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    model_name = Column(String(100), nullable=False, comment='模型名称')
    model_display_name = Column(String(100), nullable=False, comment='模型显示名称')
    api_base_url = Column(String(500), nullable=False, comment='API基础URL')
    api_key = Column(String(500), nullable=False, comment='API密钥')
    is_active = Column(Boolean, default=True, comment='是否启用')
    last_test_status = Column(String(20), nullable=True, comment='最后测试状态: success/failed')
    last_test_time = Column(DateTime, nullable=True, comment='最后测试时间')
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # 建立与用户的关联
    user = relationship('User', backref='custom_models', lazy=True)
    
    def to_dict(self, include_api_key=False) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "model_name": self.model_name,
            "model_display_name": self.model_display_name,
            "api_base_url": self.api_base_url,
            "api_key": self.api_key if include_api_key else ("***" + self.api_key[-4:] if self.api_key and len(self.api_key) > 4 else "***"),
            "is_active": self.is_active,
            "last_test_status": self.last_test_status,
            "last_test_time": self.last_test_time.isoformat() if self.last_test_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

# 用户反馈模型
class FeedbackType(str, enum.Enum):
    SUGGESTION = "suggestion"  # 建议
    PROBLEM = "problem"        # 问题
    BUG = "bug"                # 缺陷
    OTHER = "other"            # 其他

class FeedbackStatus(str, enum.Enum):
    PENDING = "pending"        # 未处理
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"      # 已解决
    REJECTED = "rejected"      # 已拒绝

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    feedback_type = Column(String(20), nullable=False, default=FeedbackType.OTHER.value)
    status = Column(String(20), nullable=False, default=FeedbackStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    contact_info = Column(String(255), nullable=True)

    user = relationship('User', backref='feedbacks', lazy=True)

    __table_args__ = (
        Index("idx_user_status", "user_id", "status"),
        {"extend_existing": True}
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "content": self.content,
            "feedback_type": self.feedback_type,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "contact_info": self.contact_info
        }

# 文件存储模型 - 已在前面定义

    __table_args__ = (
        Index("idx_user_files", "user_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "is_compressed": self.is_compressed,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic模型定义
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=20)
    createVerifyCode_value: str = Field(..., min_length=6, max_length=6)
    agree_terms: bool = Field(..., description="是否同意使用条款和隐私政策")

class UserLogin(BaseModel):
    useremail: EmailStr
    password: str
    agree_terms: bool = Field(..., description="是否同意使用条款和隐私政策")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None

class ResourceCreate(BaseModel):
    category_name: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=500)

class FavoriteCreate(BaseModel):
    user_id: int
    resource_id: int

class VerifyCodeRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    verifyCode: str
    newPassword: str = Field(..., min_length=6, max_length=20)

class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[str] = None

# 用户反馈相关Pydantic模型
class FeedbackCreate(BaseModel):
    content: str = Field(..., min_length=5, max_length=2000, description="反馈内容")
    feedback_type: str = Field(default="other", description="反馈类型: suggestion, problem, bug, other")
    contact_info: Optional[str] = Field(None, max_length=255, description="联系方式")

    @validator('feedback_type')
    def validate_feedback_type(cls, v):
        valid_types = [item.value for item in FeedbackType]
        if v not in valid_types:
            raise ValueError(f"无效的反馈类型，有效值为: {', '.join(valid_types)}")
        return v

class FeedbackUpdate(BaseModel):
    status: str = Field(..., description="反馈状态: pending, processing, resolved, rejected")

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = [item.value for item in FeedbackStatus]
        if v not in valid_statuses:
            raise ValueError(f"无效的状态值，有效值为: {', '.join(valid_statuses)}")
        return v

class FeedbackResponse(BaseModel):
    id: int
    user_id: int
    username: Optional[str] = None
    content: str
    feedback_type: str
    status: str
    created_at: str
    updated_at: str
    contact_info: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic V2使用from_attributes替代orm_mode

# 用户设置相关Pydantic模型
class UserSettingsCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    model_name: Optional[str] = Field(None, max_length=100, description="AI模型名称")
    api_base: Optional[str] = Field(None, max_length=500, description="API访问地址")
    api_key: Optional[str] = Field(None, max_length=500, description="API密钥")
    model_params: Optional[Union[str, Dict[str, Any]]] = Field(None, description="模型参数（JSON对象或JSON字符串）")

    @validator('model_params')
    def validate_json(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False)
        if isinstance(v, str):
            try:
                json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("模型参数必须是有效的JSON格式")
            return v
        raise ValueError("模型参数必须是字典或JSON字符串")

class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)
    
    id: int
    user_id: int
    model_name: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model_params: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

# 文件相关Pydantic模型
class UserFileResponse(BaseModel):
    id: int
    file_uuid: str
    original_name: str
    save_path: str
    file_size: int
    file_type: str
    upload_time: str
    user_id: int

    class Config:
        from_attributes = True

# JWT工具函数



# 认证依赖
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="未提供有效的JWT令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise credentials_exception
        token = auth_header.split(' ')[1]
        user_info = verify_jwt(token)
        if 'error' in user_info:
            raise HTTPException(status_code=401, detail=user_info['error'])
        user = db.query(User).filter(User.id == user_info['user_id']).first()
        if user is None:
            raise credentials_exception
        return user
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception

# 获取当前用户信息API端点
@app.get("/api/users/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前登录用户的信息
    """
    return {
        "status": "success",
        "message": "获取用户信息成功",
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "avatar": current_user.avatar,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "is_admin": db.query(Admin).filter(Admin.user_id == current_user.id).first() is not None
        }
    }

# 用户设置相关API端点
@app.get("/api/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的设置
    如果用户没有设置，则返回默认设置
    """
    # 查找用户设置
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    
    if not user_settings:
        # 如果没有设置，创建空设置（用户必须添加自定义模型）
        user_settings = UserSettings(
            user_id=current_user.id,
            model_name=None,  # 不设置默认模型
            api_base=None,
            api_key=None,
            model_params='{"temperature": 0.7, "max_tokens": 2000, "top_p": 1.0}'
        )
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    
    # 使用to_dict方法确保datetime字段正确序列化为字符串
    return user_settings.to_dict()

@app.post("/api/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    settings: UserSettingsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新或创建用户设置
    """
    try:
        logger.info(f"用户 {current_user.id} 尝试保存AI设置")
        logger.debug(f"收到的设置数据: {settings}")
        
        # 获取实际设置的字段（排除未设置的字段）
        settings_dict = settings.model_dump(exclude_unset=True)
        logger.debug(f"实际设置的字段 (exclude_unset=True): {list(settings_dict.keys())}")
        
        # 查找现有设置
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
        logger.debug(f"用户现有设置: model_name={user_settings.model_name if user_settings else None}, has_api_key={bool(user_settings.api_key) if user_settings else False}")
        
        if user_settings:
            # 更新现有设置（只更新实际提供的字段）
            if 'model_name' in settings_dict:
                user_settings.model_name = settings_dict['model_name']
            if 'api_base' in settings_dict:
                user_settings.api_base = settings_dict['api_base']
            if 'api_key' in settings_dict:
                # 如果api_key是空字符串，设置为None；否则使用提供的值
                user_settings.api_key = settings_dict['api_key'] if settings_dict['api_key'] else None
            if 'model_params' in settings_dict:
                # 如果提供了model_params，使用提供的值；否则保持现有值
                if settings_dict['model_params']:
                    user_settings.model_params = settings_dict['model_params']
                # 如果model_params是None或空字符串，使用默认值
                elif not user_settings.model_params:
                    user_settings.model_params = '{"temperature": 0.7, "max_tokens": 2000, "top_p": 1.0}'
            # 如果用户设置中没有model_params，且当前也没有，设置默认值
            elif not user_settings.model_params:
                user_settings.model_params = '{"temperature": 0.7, "max_tokens": 2000, "top_p": 1.0}'
            user_settings.updated_at = datetime.now(UTC)
        else:
            # 创建新设置
            user_settings = UserSettings(
                user_id=current_user.id,
                model_name=settings_dict.get('model_name'),
                api_base=settings_dict.get('api_base'),
                api_key=settings_dict.get('api_key'),
                model_params=settings_dict.get('model_params') or '{"temperature": 0.7, "max_tokens": 2000, "top_p": 1.0}'
            )
            db.add(user_settings)
        
        db.commit()
        db.refresh(user_settings)
        
        logger.info(f"用户 {current_user.id} 的AI设置已保存: model_name={user_settings.model_name}, api_base={user_settings.api_base}, has_api_key={bool(user_settings.api_key)}, updated_fields={list(settings_dict.keys())}")
        logger.debug(f"保存后的完整数据: {user_settings.to_dict()}")
        
        # 使用to_dict方法确保datetime字段正确序列化为字符串
        # 确保返回的数据中API密钥被掩码（在to_dict方法中已处理）
        return user_settings.to_dict()
    except Exception as e:
        db.rollback()
        logger.error(f"保存用户设置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新设置失败: {str(e)}")

@app.delete("/api/settings")
async def delete_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除用户设置
    """
    try:
        # 查找用户设置
        user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
        
        if not user_settings:
            raise HTTPException(status_code=404, detail="用户设置不存在")
        
        db.delete(user_settings)
        db.commit()
        
        return {"message": "用户设置已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除设置失败: {str(e)}")

# ========== 自定义AI模型相关API端点 ==========
def get_user_model_params(db: Session, user_id: int) -> dict:
    """获取用户的模型参数设置，返回解析后的字典"""
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if user_settings and user_settings.model_params:
        try:
            import json
            return json.loads(user_settings.model_params)
        except Exception as e:
            logger.warning(f"解析用户模型参数失败: {str(e)}")
    # 返回默认值
    return {"temperature": 0.7, "max_tokens": 2000, "top_p": 1.0}

@app.get("/api/custom-models")
async def get_custom_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的自定义AI模型列表"""
    try:
        models = db.query(CustomAIModel).filter(CustomAIModel.user_id == current_user.id).all()
        
        # 获取用户的模型参数设置
        model_params = get_user_model_params(db, current_user.id)
        
        return {
            "status": "success",
            "data": [model.to_dict() for model in models],
            "model_params": model_params  # 添加模型参数到响应中
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")

@app.post("/api/custom-models")
async def create_custom_model(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建自定义AI模型"""
    try:
        data = await request.json()
        model_name = data.get('model_name', '').strip()
        model_display_name = data.get('model_display_name', '').strip()
        api_base_url = data.get('api_base_url', '').strip()
        api_key = data.get('api_key', '').strip()
        
        if not all([model_name, model_display_name, api_base_url, api_key]):
            raise HTTPException(status_code=400, detail="所有字段都是必填的")
        
        # 检查是否已存在同名模型
        existing = db.query(CustomAIModel).filter(
            CustomAIModel.user_id == current_user.id,
            CustomAIModel.model_name == model_name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="该模型名称已存在")
        
        # 创建新模型
        new_model = CustomAIModel(
            user_id=current_user.id,
            model_name=model_name,
            model_display_name=model_display_name,
            api_base_url=api_base_url,
            api_key=api_key,
            is_active=True
        )
        
        db.add(new_model)
        db.commit()
        db.refresh(new_model)
        
        # 获取用户的模型参数设置
        model_params = get_user_model_params(db, current_user.id)
        
        return {
            "status": "success",
            "message": "模型添加成功",
            "data": new_model.to_dict(),
            "model_params": model_params  # 添加模型参数到响应中
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加模型失败: {str(e)}")

@app.put("/api/custom-models/{model_id}")
async def update_custom_model(
    model_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新自定义AI模型"""
    try:
        model = db.query(CustomAIModel).filter(
            CustomAIModel.id == model_id,
            CustomAIModel.user_id == current_user.id
        ).first()
        
        if not model:
            raise HTTPException(status_code=404, detail="模型不存在")
        
        data = await request.json()
        
        if 'model_display_name' in data:
            model.model_display_name = data['model_display_name'].strip()
        if 'api_base_url' in data:
            model.api_base_url = data['api_base_url'].strip()
        if 'api_key' in data:
            model.api_key = data['api_key'].strip()
        if 'is_active' in data:
            model.is_active = data['is_active']
        
        db.commit()
        db.refresh(model)
        
        # 获取用户的模型参数设置
        model_params = get_user_model_params(db, current_user.id)
        
        return {
            "status": "success",
            "message": "模型更新成功",
            "data": model.to_dict(),
            "model_params": model_params  # 添加模型参数到响应中
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新模型失败: {str(e)}")

@app.delete("/api/custom-models/{model_id}")
async def delete_custom_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除自定义AI模型"""
    try:
        model = db.query(CustomAIModel).filter(
            CustomAIModel.id == model_id,
            CustomAIModel.user_id == current_user.id
        ).first()
        
        if not model:
            raise HTTPException(status_code=404, detail="模型不存在")
        
        db.delete(model)
        db.commit()
        
        return {
            "status": "success",
            "message": "模型删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除模型失败: {str(e)}")

@app.post("/api/custom-models/{model_id}/test")
async def test_custom_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """测试自定义AI模型连通性"""
    try:
        import httpx
        from datetime import datetime
        
        model = db.query(CustomAIModel).filter(
            CustomAIModel.id == model_id,
            CustomAIModel.user_id == current_user.id
        ).first()
        
        if not model:
            raise HTTPException(status_code=404, detail="模型不存在")
        
        # 测试API连通性 - 支持多种API格式
        base_url = model.api_base_url.rstrip('/')
        
        # 智能处理API端点，避免重复路径
        possible_endpoints = []
        
        # 如果base_url已经包含/v1，则不再添加/v1前缀
        if base_url.endswith('/v1'):
            possible_endpoints = [
                '/chat/completions',      # 直接使用chat/completions
                '/models',                # 测试models端点
            ]
        else:
            # 如果base_url不包含/v1，则尝试多种格式
            possible_endpoints = [
                '/v1/chat/completions',   # OpenAI标准格式
                '/chat/completions',      # Ollama等格式
                '/api/v1/chat/completions',  # 其他格式
            ]
        
        headers = {
            'Authorization': f'Bearer {model.api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': model.model_name,
            'messages': [{'role': 'user', 'content': 'hi'}],
            'max_tokens': 10
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            last_error = None
            for endpoint in possible_endpoints:
                try:
                    test_url = base_url + endpoint
                    
                    # 根据端点类型选择请求方法
                    if endpoint == '/models':
                        # models端点使用GET请求
                        response = await client.get(test_url, headers={'Authorization': f'Bearer {model.api_key}'})
                    else:
                        # chat/completions端点使用POST请求
                        response = await client.post(test_url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        model.last_test_status = 'success'
                        model.last_test_time = datetime.now(UTC)
                        db.commit()
                        
                        # 计算响应时间（毫秒）
                        response_time = f"{response.elapsed.total_seconds() * 1000:.0f}ms"
                        
                        return {
                            "status": "success",
                            "message": "API连接测试成功",
                            "response_time": response_time,
                            "data": {
                                "test_status": "success",
                                "test_time": model.last_test_time.isoformat(),
                                "endpoint": endpoint,
                                "response_time": response_time
                            }
                        }
                    else:
                        # 记录错误，尝试下一个端点
                        try:
                            error_detail = response.json()
                            last_error = f"HTTP {response.status_code}: {error_detail.get('error', {}).get('message', response.text[:100])}"
                        except:
                            last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                        continue
                except httpx.TimeoutException:
                    last_error = "连接超时"
                    continue
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # 所有端点都失败了
            model.last_test_status = 'failed'
            model.last_test_time = datetime.now(UTC)
            db.commit()
            
            error_msg = last_error or "所有端点都无法连接"
            return {
                "status": "error",
                "message": f"API连接失败: {error_msg}",
                "data": {
                    "test_status": "failed",
                    "test_time": model.last_test_time.isoformat(),
                    "tried_endpoints": possible_endpoints
                }
            }
    except Exception as e:
        logger.error(f"测试API模型失败: {str(e)}")
        return {
            "status": "error",
            "message": f"测试失败: {str(e)}",
            "data": {"test_status": "failed"}
        }

# ========== 用户头像相关API端点 ==========
from pathlib import Path
from PIL import Image

# 头像配置
AVATAR_DIR = Path(__file__).parent / "avatars"
AVATAR_MAX_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
AVATAR_SIZE = (200, 200)  # 头像压缩尺寸

@app.post("/api/users/avatar/upload")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传用户头像
    - **file**: 头像图片文件（支持 JPG、PNG、GIF、WebP格式）
    - 自动压缩为 200x200 像素
    - 最大文件大小：5MB
    """
    user_id = current_user.id
    
    # 验证文件类型
    if file.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持的类型：{', '.join(AVATAR_ALLOWED_TYPES)}"
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 验证文件大小
    if len(content) > AVATAR_MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大{AVATAR_MAX_SIZE / 1024 / 1024}MB）"
        )
    
    try:
        # 打开图片
        image = Image.open(io.BytesIO(content))
        
        # 转换为RGB模式（处理PNG透明背景）
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 裁剪为正方形（取中心部分）
        width, height = image.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        image = image.crop((left, top, right, bottom))
        
        # 调整大小
        image = image.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)
        
        # 生成唯一文件名
        file_extension = ".jpg"  # 统一保存为JPG格式
        filename = f"{user_id}_{uuid.uuid4().hex}{file_extension}"
        filepath = AVATAR_DIR / filename
        
        # 确保目录存在
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存图片
        image.save(filepath, "JPEG", quality=85, optimize=True)
        
        # 更新用户头像字段
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 删除旧头像文件（如果存在）
        if user.avatar:
            old_filename = user.avatar.split('/')[-1]
            old_filepath = AVATAR_DIR / old_filename
            if old_filepath.exists():
                old_filepath.unlink()
        
        # 更新数据库
        avatar_url = f"/api/users/avatar/{filename}"
        user.avatar = avatar_url
        db.commit()
        
        return {
            "code": 200,
            "message": "头像上传成功",
            "data": {
                "avatar_url": avatar_url,
                "filename": filename
            }
        }
        
    except Exception as e:
        logger.error(f"头像处理失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"头像处理失败：{str(e)}"
        )


@app.get("/api/users/avatar/{filename}")
async def get_avatar(filename: str):
    """
    获取用户头像（公开访问）
    - **filename**: 头像文件名
    """
    # 基本安全检查：防止目录遍历攻击
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(
            status_code=400,
            detail="无效的文件名"
        )
    
    filepath = AVATAR_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail="头像文件不存在"
        )
    
    return FileResponse(filepath, media_type="image/jpeg")


@app.delete("/api/users/avatar")
async def delete_avatar(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除用户头像
    """
    user_id = current_user.id
    
    # 获取用户信息
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 删除头像文件
    if user.avatar:
        filename = user.avatar.split('/')[-1]
        filepath = AVATAR_DIR / filename
        if filepath.exists():
            filepath.unlink()
        
        # 更新数据库
        user.avatar = None
        db.commit()
        
        return {
            "code": 200,
            "message": "头像删除成功"
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="用户未设置头像"
        )

# ========== 头像功能结束 ==========

# Token验证端点
@app.post("/api/auth/verify")
async def verify_token(request: Request, db: Session = Depends(get_db)):
    """验证用户token的有效性
    
    用于前端在跳转或访问受保护资源前验证token是否有效
    返回用户的基本信息（user_id, username）
    """
    try:
        # 尝试从请求体获取token
        try:
            request_data = await request.json()
            token = request_data.get('token')
        except:
            token = None
        
        # 如果请求体中没有token，尝试从Authorization头获取
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        # 如果仍然没有token，返回错误
        if not token:
            raise HTTPException(status_code=401, detail="未提供token")
        
        # 验证token
        user_info = verify_jwt(token)
        
        # 检查验证结果
        if isinstance(user_info, dict) and 'error' in user_info:
            raise HTTPException(status_code=401, detail=user_info['error'])
        
        # 验证用户是否存在
        user = db.query(User).filter(User.id == user_info['user_id']).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        
        # 返回用户信息
        return {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "message": "Token验证成功"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token验证失败: {str(e)}")

# 文件上传API端点
@app.post("/api/files/upload")
async def upload_file(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文件到云盘（支持多文件）"""
    logger.info(f"用户 {current_user.id} 尝试上传文件")
    
    # 存储上传结果
    uploaded_files = []
    errors = []
    
    try:
        # 确保用户目录存在 - 添加详细日志
        user_dir = settings.get_upload_dir_for_user(current_user.id)
        logger.info(f"用户目录路径: {user_dir}")
        
        try:
            # 目录已在settings方法中确保存在，转换为字符串
            user_dir_str = str(user_dir)
            # 测试写入权限
            test_file = os.path.join(user_dir_str, "test_write_permission.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"用户目录创建成功且有写入权限")
        except Exception as e:
            error_msg = f"创建用户目录或写入权限错误: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 解析multipart/form-data请求
        form = await request.form()
        
        # 优先查找'file'参数，因为前端对每个文件都使用相同的键名'file'
        files = form.getlist("file")  # 使用getlist获取多个文件
        
        # 如果没有使用file参数，尝试获取files参数作为兼容
        if not files:
            files = form.getlist("files")
        
        if not files:
            logger.warning(f"用户 {current_user.id} 没有提供要上传的文件")
            raise HTTPException(status_code=400, detail="请选择要上传的文件")
        
        logger.info(f"找到 {len(files)} 个待上传文件")
        
        # 循环处理每个文件
        for idx, file in enumerate(files):
            logger.info(f"处理文件 {idx+1}/{len(files)}: {file.filename}")
            
            # 检查文件扩展名
            if not allowed_file(file.filename):
                error_msg = f"不支持的文件类型: {file.filename}"
                logger.warning(error_msg)
                errors.append({
                    "filename": file.filename,
                    "error": error_msg
                })
                continue
            
            try:
                # 检查文件大小
                file.file.seek(0, 2)
                file_size = file.file.tell()
                file.file.seek(0)
                logger.info(f"文件大小: {file_size} 字节")
                
                if file_size > MAX_FILE_SIZE:
                    error_msg = f"文件大小超过限制: {file_size} > {MAX_FILE_SIZE}"
                    logger.warning(error_msg)
                    errors.append({
                        "filename": file.filename,
                        "error": "文件大小超过限制（100MB）"
                    })
                    continue
                
                # 生成唯一文件名
                filename = generate_unique_filename(file.filename, current_user.id)
                
                # 保存文件
                file_path = os.path.join(user_dir_str, filename)
                logger.info(f"准备保存文件到: {file_path}")
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                logger.info(f"文件保存成功: {file_path}")
                
                # 保存到数据库
                file_uuid = str(uuid.uuid4())
                # 确定文件类型
                file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
                file_type = f"application/{file_extension}" if file_extension != 'unknown' else 'application/octet-stream'
                
                # 创建数据库记录
                new_file = UserFile(
                    file_uuid=file_uuid,
                    original_name=file.filename,
                    save_path=file_path,
                    file_size=file_size,
                    file_type=file_type,
                    upload_time=datetime.now(),
                    user_id=current_user.id
                )
                db.add(new_file)
                db.commit()
                
                uploaded_files.append({
                    "id": new_file.id,
                    "filename": file.filename,
                    "stored_filename": filename,
                    "status": "success"
                })
                logger.info(f"数据库记录创建成功，文件ID: {new_file.id}")
                
            except Exception as e:
                # 删除已上传的文件
                if 'file_path' in locals() and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"删除失败的文件: {file_path}")
                    except:
                        logger.error(f"无法删除失败的文件: {file_path}")
                
                error_msg = str(e)
                logger.error(f"处理文件 {file.filename} 时出错: {error_msg}")
                errors.append({
                    "filename": file.filename,
                    "error": "服务器内部错误，请稍后重试"
                })
                db.rollback()
        
        # 返回上传结果
        result = {
            "message": "文件上传完成",
            "success_count": len(uploaded_files),
            "error_count": len(errors),
            "uploaded_files": uploaded_files
        }
        
        if errors:
            result["errors"] = errors
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传过程中发生错误: {str(e)}")

# 获取用户文件列表
@app.get("/api/files", response_model=List[UserFileResponse])
async def get_user_files(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的文件列表"""
    files = db.query(UserFile).filter(
        UserFile.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    # 构建符合响应模型的数据列表
    result = []
    for file in files:
        result.append({
            "id": file.id,
            "file_uuid": file.file_uuid,
            "original_name": file.original_name,
            "save_path": file.save_path,
            "file_size": file.file_size,
            "file_type": file.file_type,
            "upload_time": file.upload_time.isoformat(),
            "user_id": file.user_id
        })
    
    return result

# 下载文件
@app.get("/api/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载文件"""
    # 查询文件
    file = db.query(UserFile).filter(
        UserFile.id == file_id,
        UserFile.user_id == current_user.id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查文件是否存在
    if not os.path.exists(file.save_path):
        raise HTTPException(status_code=404, detail="文件不存在于服务器")
    
    # 对于压缩的视频文件，下载时需要解压
    file_path = file.save_path
    is_temp_file = False
    
    # 检查是否是视频文件且被压缩（以.zip结尾）
    if file.save_path.endswith('.zip') and file.file_type == "video":
        file_path = decompress_file(file.save_path)
        is_temp_file = True
    
    try:
        # 读取文件内容以返回
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # 确定正确的文件名（去掉.zip后缀）
        download_filename = file.original_name
        if file.save_path.endswith('.zip'):
            # 如果数据库中的原始文件名已经包含.zip，保持不变
            # 否则使用压缩前的文件名
            if not download_filename.endswith('.zip'):
                pass  # 使用原始文件名
        
        # 对文件名进行正确的编码处理
        # 支持中文和其他非ASCII字符的文件名
        try:
            # 尝试ASCII编码，如果失败则使用RFC 5987格式
            download_filename.encode('ascii')
            # 如果可以用ASCII编码，直接使用
            content_disposition = f"attachment; filename=\"{download_filename}\""
        except UnicodeEncodeError:
            # 包含非ASCII字符，使用RFC 5987格式
            encoded_filename = quote(download_filename)
            content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}; filename=\"{download_filename}\""
        
        return Response(
            content=file_content,
            media_type=file.file_type or "application/octet-stream",
            headers={
                "Content-Disposition": content_disposition,
                "Content-Length": str(len(file_content))
            }
        )
    finally:
        # 清理临时解压文件
        if is_temp_file and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass  # 忽略删除错误

# 删除文件
@app.delete("/api/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文件"""
    # 查询文件
    file = db.query(UserFile).filter(
        UserFile.id == file_id,
        UserFile.user_id == current_user.id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 删除物理文件
    if os.path.exists(file.save_path):
        try:
            os.remove(file.save_path)
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
    
    # 删除数据库记录
    db.delete(file)
    db.commit()
    
    return {"message": "文件删除成功"}

# 管理员权限检查依赖
def get_current_admin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    管理员权限检查依赖
    
    从专门的admins表中查询用户是否具有管理员权限
    """
    # 从admins表中查询用户是否为管理员且处于激活状态
    admin_record = db.query(Admin).filter(
        Admin.user_id == current_user.id,
        Admin.is_active == True
    ).first()
    
    if not admin_record:
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限才能执行此操作"
        )
    
    logger.debug(f"管理员验证成功: 用户ID={current_user.id}, 用户名={current_user.username}")
    return current_user

# 管理员验证端点 - 用于登录后检查用户是否为管理员
@app.get("/api/admin/verify", response_model=Dict[str, bool])
def verify_admin_role(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    验证当前用户是否具有管理员权限
    
    这个端点用于登录成功后，前端检查用户是否是管理员，以决定跳转路径
    """
    try:
        # 检查用户是否在管理员表中且处于激活状态
        admin_record = db.query(Admin).filter(
            Admin.user_id == current_user.id,
            Admin.is_active == True
        ).first()
        
        is_admin = admin_record is not None
        logger.debug(f"管理员角色验证: 用户ID={current_user.id}, 结果={is_admin}")
        
        return {"is_admin": is_admin}
    except Exception as e:
        logger.error(f"管理员角色验证失败: {str(e)}")
        return {"is_admin": False}

# 创建初始管理员（开发时使用）
@app.post("/api/admin/init", response_model=Dict[str, str])
def init_admin(
    db: Session = Depends(get_db)
):
    """
    创建初始管理员账户
    
    注意：此端点仅用于初始化系统，生产环境应禁用
    """
    try:
        # 检查是否已有管理员
        existing_admin = db.query(Admin).first()
        if existing_admin:
            return {"message": "系统已有管理员账户，请不要重复创建"}
        
        # 检查是否有ID为1的用户
        admin_user = db.query(User).filter(User.id == 1).first()
        if not admin_user:
            return {"message": "未找到用户ID为1的用户，请先创建用户"}
        
        # 创建管理员记录
        new_admin = Admin(user_id=1, is_active=True)
        db.add(new_admin)
        db.commit()
        
        logger.info(f"初始管理员创建成功: 用户ID={admin_user.id}, 用户名={admin_user.username}")
        return {"message": "初始管理员创建成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"创建初始管理员失败: {str(e)}")
        return {"message": f"创建失败: {str(e)}"}

# 管理员仪表盘数据
@app.get("/api/admin/dashboard", response_model=Dict[str, Any])
def admin_dashboard(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取管理员仪表盘统计数据
    """
    # 获取用户总数
    total_users = db.query(User).count()
    
    # 获取文件总数
    total_files = db.query(UserFile).count()
    
    # 获取资源总数
    total_resources = db.query(Resource).count()
    
    # 获取最近注册的用户（最近10个）
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    
    # 获取最近上传的文件（最近10个）
    recent_files = db.query(UserFile).order_by(UserFile.upload_time.desc()).limit(10).all()
    
    return {
        "total_users": total_users,
        "total_files": total_files,
        "total_resources": total_resources,
        "recent_users": [user.to_dict() for user in recent_users],
        "recent_files": [{
            "id": file.id,
            "original_name": file.original_name,
            "file_size": file.file_size,
            "upload_time": file.upload_time.isoformat() if file.upload_time else None,
            "user_id": file.user_id
        } for file in recent_files]
    }

# 获取所有用户列表
@app.get("/api/admin/users", response_model=Dict[str, Any])
def get_all_users(
    page: int = 1,
    page_size: int = 20,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取所有用户列表（分页）
    """
    offset = (page - 1) * page_size
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    total = db.query(User).count()
    
    return {
        "users": [user.to_dict() for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

# 获取所有文件列表
@app.get("/api/admin/files", response_model=Dict[str, Any])
def get_all_files(
    page: int = 1,
    page_size: int = 20,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取所有文件列表（分页）
    """
    offset = (page - 1) * page_size
    files = db.query(UserFile).order_by(UserFile.upload_time.desc()).offset(offset).limit(page_size).all()
    total = db.query(UserFile).count()
    
    return {
        "files": [{
            "id": file.id,
            "file_uuid": file.file_uuid,
            "original_name": file.original_name,
            "file_size": file.file_size,
            "file_type": file.file_type,
            "upload_time": file.upload_time.isoformat() if file.upload_time else None,
            "user_id": file.user_id
        } for file in files],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

# 删除用户
@app.delete("/api/admin/users/{user_id}", response_model=Dict[str, Any])
def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    删除用户（管理员专用）
    """
    # 不允许删除自己
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    try:
        # 删除相关文件记录
        db.query(UserFile).filter(UserFile.user_id == user_id).delete()
        # 删除收藏记录
        db.query(UserFavorite).filter(UserFavorite.user_id == user_id).delete()
        # 删除用户
        db.delete(user)
        db.commit()
        
        return {"message": "用户删除成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="删除用户失败: " + str(e))

# 删除重复的管理员验证端点，保留第一个完整的验证逻辑

# 验证码生成器类
class VerificationCodeGenerator:
    @staticmethod
    def generate_6digit_code() -> str:
        return str(random.randint(100000, 999999))

    @staticmethod
    def generate_mixed_code() -> str:
        characters = string.digits + string.ascii_letters
        return ''.join(random.choice(characters) for _ in range(6))

    @staticmethod
    def is_valid(code: str, stored_code: Dict[str, Any], expiration_minutes: int = 5) -> bool:
        if code != stored_code['code']:
            return False
        current_time = datetime.now(UTC)
        if current_time > stored_code['expiration_time']:
            return False
        return True

# 工具函数：检查文件扩展名
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 工具函数：压缩文件
def compress_file(file_path: str) -> str:
    """压缩文件并返回压缩后的文件路径，为视频文件提供更高压缩率"""
    zip_path = file_path + '.zip'
    
    # 为视频文件使用最高压缩级别
    compression_method = zipfile.ZIP_DEFLATED
    
    # 创建ZipFile对象并设置最高压缩级别
    with zipfile.ZipFile(zip_path, 'w', compression=compression_method) as zipf:
        # 对于视频文件，使用更高的压缩设置
        # 通过调整ZIP文件的压缩级别参数
        info = zipfile.ZipInfo(os.path.basename(file_path))
        info.compress_type = compression_method
        
        # 读取文件内容并以最高压缩级别写入
        with open(file_path, 'rb') as f:
            # 使用zipfile的writestr方法可以提供更好的压缩控制
            zipf.writestr(info, f.read(), compress_type=compression_method)
    
    # 检查压缩效果
    original_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    compressed_size = os.path.getsize(zip_path)
    print(f"压缩前大小: {original_size} bytes, 压缩后大小: {compressed_size} bytes, 压缩率: {compressed_size/original_size*100:.2f}%")
    
    # 删除原始文件，只保留压缩包
    if os.path.exists(file_path):
        os.remove(file_path)
    return zip_path

def decompress_file(zip_path: str) -> str:
    """解压文件并返回解压后的文件路径"""
    # 确保是zip文件
    if not zip_path.endswith('.zip'):
        return zip_path
    
    # 创建临时解压目录
    temp_dir = os.path.join(os.path.dirname(zip_path), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 解压文件
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(temp_dir)
        # 获取解压后的第一个文件路径
        extracted_files = zipf.namelist()
        if extracted_files:
            return os.path.join(temp_dir, extracted_files[0])
    return zip_path

# 工具函数：生成唯一文件名
def generate_unique_filename(original_filename: str, user_id: int) -> str:
    """生成唯一的文件名"""
    extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"user_{user_id}_{timestamp}_{unique_id}.{extension}"

# 邮件发送函数
def send_email(sender_email: str, sender_password: str, receiver_email: str, subject: str, message: str, 
               smtp_server: str, smtp_port: int, attachments: Optional[List[str]] = None, use_ssl: bool = False) -> bool:
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain', 'utf-8'))

        if attachments:
            for file_path in attachments:
                if os.path.isfile(file_path):
                    # 附件处理逻辑（简化版）
                    pass

        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()

        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False



# 创建聊天记录
def create_chat_record(
        db: Session,
        content: str,
        sender_type: int,
        user_id: str,
        session_id: Optional[str] = None,
        ai_model: Optional[str] = None,
        status: str = MessageStatus.COMPLETED.value
) -> Dict[str, Any]:
    try:
        if not session_id:
            session_id = str(uuid.uuid4()).replace("-", "")
        
        last_message = db.query(
            func.max(ChatRecord.message_order)
        ).filter(
            ChatRecord.session_id == session_id,
            ChatRecord.user_id == user_id
        ).scalar()
        
        message_order = (last_message or 0) + 1

        chat_record = ChatRecord(
            session_id=session_id,
            user_id=user_id,
            message_order=message_order,
            sender_type=sender_type,
            content=content,
            ai_model=ai_model,
            status=status
        )

        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)

        return chat_record.to_dict()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建聊天记录失败: {str(e)}")

# 获取对话历史
def get_conversation_history(db: Session, session_id: str, user_id: str, max_messages: int = 10, max_tokens: int = 2000) -> List[Dict[str, str]]:
    history_messages = []
    total_tokens = 0
    
    try:
        messages = db.query(ChatRecord).filter(
            ChatRecord.session_id == session_id,
            ChatRecord.user_id == str(user_id),
            ChatRecord.status == MessageStatus.COMPLETED.value
        ).order_by(ChatRecord.message_order.desc()).limit(max_messages * 2).all()
        
        for message in reversed(messages):
            message_tokens = len(message.content)
            if total_tokens + message_tokens > max_tokens:
                break
            
            role = "user" if message.sender_type == USER_SENDER else "assistant"
            history_messages.append({
                "role": role,
                "content": message.content
            })
            
            total_tokens += message_tokens
    except:
        pass
    
    return history_messages

# API调用函数
def call_doubao_api_stream(
    user_query: str,
    history_messages: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: float = 1.0,
):
    try:
        client = OpenAI(
            base_url=os.environ.get("DOUBAO_BASEURL"),
            api_key=os.environ.get("DOUBAO_KEY"),
        )
        
        messages = [
            {"role": "system",
             "content": "你是一位专业的学习导师，用简洁清晰的方式解答学生的学术问题。请确保回答格式清晰，保留适当的空格和换行。"}
        ]
        
        if history_messages:
            messages.extend(history_messages)
        
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": user_query}]
        })
        
        response = client.chat.completions.create(
            model="doubao-seed-1-6-250615",
            messages=messages,
            temperature=temperature,
            max_tokens=(max_tokens if max_tokens else int(MAX_TOKEN)),
            top_p=top_p,
            stream=True,
        )
        return response
    except:
        return None

def call_deepseek_api_stream(user_query: str, model_name: str, history_messages: Optional[List[Dict[str, str]]] = None, 
                             user_api_key: Optional[str] = None, user_api_base: Optional[str] = None,
                             temperature: float = 0.7, max_tokens: int = None, top_p: float = 1.0):
    """
    调用DeepSeek API（支持用户自定义设置）
    
    Args:
        user_query: 用户查询
        model_name: 模型名称
        history_messages: 历史消息
        user_api_key: 用户自定义API密钥（如果提供则使用，否则使用全局默认值）
        user_api_base: 用户自定义API地址（如果提供则使用，否则使用默认值）
        temperature: 温度参数
        max_tokens: 最大token数
        top_p: top_p参数
    """
    try:
        # 优先使用用户自定义的API配置，否则使用系统默认配置
        api_key = user_api_key if user_api_key else DEEPSEEK_API_KEY
        api_base = user_api_base if user_api_base else "https://api.deepseek.com/v1"
        max_tokens_value = max_tokens if max_tokens else int(MAX_TOKEN)
        
        if not api_key:
            logger.error("API密钥未设置")
            return None
        
        logger.debug(f"使用API配置 - 密钥: {'已设置' if api_key else '未设置'}, 地址: {api_base}, 温度: {temperature}, 最大tokens: {max_tokens_value}, top_p: {top_p}")
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        messages = [
            {"role": "system",
             "content": "你是一位专业的学习导师，用简洁清晰的方式解答学生的学术问题。请确保回答格式清晰，保留适当的空格和换行。"}
        ]
        
        if history_messages:
            messages.extend(history_messages)
        
        messages.append({"role": "user", "content": user_query})
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens_value,
            top_p=top_p,
            stream=True
        )
        return response
    except Exception as e:
        logger.error(f"DeepSeek API调用失败: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"API密钥是否设置: {api_key is not None if 'api_key' in locals() else False}")
        logger.error(f"调用参数 - 模型: {model_name}, API地址: {api_base if 'api_base' in locals() else 'N/A'}, 查询长度: {len(user_query)}")
        return None

def call_custom_model_api_stream(custom_model: CustomAIModel, user_query: str, history_messages: Optional[List[Dict[str, str]]] = None,
                                 temperature: float = 0.7, max_tokens: int = None, top_p: float = 1.0):
    """调用自定义模型API（支持用户参数）"""
    try:
        client = OpenAI(
            api_key=custom_model.api_key,
            base_url=custom_model.api_base_url
        )
        
        messages = [
            {"role": "system",
             "content": "你是一位专业的学习导师，用简洁清晰的方式解答学生的学术问题。请确保回答格式清晰，保留适当的空格和换行。"}
        ]
        
        if history_messages:
            messages.extend(history_messages)
        
        messages.append({"role": "user", "content": user_query})
        
        max_tokens_value = max_tokens if max_tokens else int(MAX_TOKEN)
        
        response = client.chat.completions.create(
            model=custom_model.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens_value,
            top_p=top_p,
            stream=True
        )
        return response
    except Exception as e:
        logger.error(f"自定义模型API调用失败: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"模型信息: {custom_model.model_display_name} ({custom_model.model_name})")
        logger.error(f"API地址: {custom_model.api_base_url}")
        logger.error(f"调用参数 - 查询长度: {len(user_query)}")
        return None

# 提取关键词和获取学习资源
def extract_keywords(text: str, db: Session) -> List[str]:
    keywords = []
    categories = db.query(Category).all()
    for category in categories:
        if category.name.lower() in text.lower():
            keywords.append(category.name)
    return keywords[:3]

def get_learning_resources(answer: str, db: Session) -> List[Dict[str, Any]]:
    keywords = extract_keywords(answer, db)
    resources = []

    for keyword in keywords:
        category = db.query(Category).filter_by(name=keyword).first()
        if category:
            category_resources = db.query(Resource).filter_by(category_id=category.id).limit(3).all()
            resources.extend([r.to_dict() for r in category_resources])

    return resources[:3]

# 检查IPv6支持
def check_ipv6_support():
    logger.info(f"IPv6 supported: {socket.has_ipv6}")

    try:
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET6 in addrs:
                ipv6_addrs = addrs[netifaces.AF_INET6]
                logger.info(f"Interface {interface} IPv6 addresses: {ipv6_addrs}")
    except:
        logger.error("检查IPv6支持时出错")

# 初始化数据库数据
def init_database():
    db = SessionLocal()
    try:
        # 定义初始数据结构
        initial_data = {
            "微积分": [
                {
                    "title": "微积分精讲课程",
                    "url": "https://pan.baidu.com/s/1uE22dq1lnymU0h3YrlFngg?pwd=8888",
                    "description": "清华大学微积分完整课程视频",
                    "is_public": 1
                },
                {
                    "title": "导数计算器",
                    "url": "https://www.runoob.com/python/python-tutorial.htmle",
                    "description": "在线导数计算与可视化工具",
                    "is_public": 1
                }
            ],
            "编程": [
                {
                    "title": "Python入门教程",
                    "url": "https://www.bilibili.com/video/BV1hx41167mE/",
                    "description": "浙江大学Python编程基础课程",
                    "is_public": 1
                }
            ],
            "量子力学": [
                {
                    "title": "量子力学基础讲座",
                    "url": "http://[2001:da8:202:10::36]/physics/quantum_basic.mp4",
                    "description": "北京大学物理学院量子力学入门讲座",
                    "is_public": 1
                },
                {
                    "title": "双缝实验模拟",
                    "url": "http://[2001:da8:8000:1::1234]/simulations/double-slit",
                    "description": "交互式双缝实验模拟工具",
                    "is_public": 1
                }
            ]
        }
        
        categories = [
            {"name": "微积分", "description": "高等数学中的微积分相关资源"},
            {"name": "编程", "description": "各种编程语言学习资源"},
            {"name": "量子力学", "description": "物理学中的量子力学相关资源"}
        ]
        
        # 存储所有公开资源的ID
        public_resource_ids = []
        
        # 检查并创建分类
        for cat_data in categories:
            category = db.query(Category).filter_by(name=cat_data["name"]).first()
            if not category:
                category = Category(**cat_data)
                db.add(category)
                db.commit()
                logger.info(f"创建新分类: {cat_data['name']}")
            
            # 获取该分类的资源列表
            resources = initial_data.get(cat_data["name"], [])
            
            for res_data in resources:
                # 检查资源是否已存在
                existing_resource = db.query(Resource).filter_by(
                    category_id=category.id,
                    title=res_data["title"]
                ).first()
                
                if existing_resource:
                    # 更新现有资源的is_public属性
                    if existing_resource.is_public != res_data.get("is_public", 0):
                        existing_resource.is_public = res_data.get("is_public", 0)
                        db.commit()
                        logger.info(f"更新资源 '{res_data['title']}' 的公开状态为 {res_data.get('is_public', 0)}")
                    
                    # 如果是公开资源，记录其ID
                    if res_data.get("is_public") == 1:
                        public_resource_ids.append(existing_resource.id)
                else:
                    # 创建新资源
                    resource = Resource(
                        category_id=category.id,
                        title=res_data["title"],
                        url=res_data["url"],
                        description=res_data["description"],
                        is_public=res_data.get("is_public", 0)
                    )
                    db.add(resource)
                    db.flush()
                    
                    # 如果是公开资源，记录其ID
                    if res_data.get("is_public") == 1:
                        public_resource_ids.append(resource.id)
                    
                    logger.info(f"创建新资源: {res_data['title']} (公开状态: {res_data.get('is_public', 0)})")
        
        db.commit()
        
        # 直接查询数据库中所有is_public=1的资源，并为它们创建收藏记录
        # 使用默认用户ID 1，假设系统中至少有一个用户
        default_user_id = 1
        
        # 首先检查是否存在任何用户
        any_user = db.query(User).first()
        if any_user:
            default_user_id = any_user.id
            logger.info(f"使用现有用户ID {default_user_id} 进行收藏记录初始化")
        else:
            # 如果没有用户，使用ID 1作为默认值
            logger.warning("数据库中没有用户，使用默认用户ID 1进行收藏记录初始化")
        
        # 查询所有is_public=1的资源
        all_public_resources = db.query(Resource).filter_by(is_public=1).all()
        created_count = 0
        
        for resource in all_public_resources:
            # 检查是否已有收藏记录
            existing_favorite = db.query(UserFavorite).filter_by(
                user_id=default_user_id,
                resource_id=resource.id
            ).first()
            
            if not existing_favorite:
                # 创建新的收藏记录
                favorite = UserFavorite(
                    user_id=default_user_id,
                    resource_id=resource.id,
                    created_at=datetime.now()
                )
                db.add(favorite)
                created_count += 1
                logger.info(f"为资源ID {resource.id} ({resource.title}) 创建收藏记录")
        
        db.commit()
        logger.info(f"初始数据更新完成，已为 {created_count} 个公开资源创建收藏记录")
            
    except Exception as e:
        db.rollback()
        logger.error(f"初始化数据库失败: {str(e)}")
    finally:
        db.close()

# 用户认证相关API
@app.post("/api/register/email", response_model=Dict[str, str])
def register_email(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=request.email).first()
    if user:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    # 检查是否可以发送验证码
    can_send, message = VerificationCode.can_send_code(db, request.email)
    if not can_send:
        raise HTTPException(status_code=429, detail=message)
    
    # 第1363行：使用自动邮箱模块中的send_reset_email_last函数
    info = send_reset_email_last(request.email)
    if not info:
        raise HTTPException(status_code=400, detail="发送验证码失败！")
    
    res = VerificationCode.insert_verify_code(db, info['email'], info['code'])
    if res:
        return {"message": "已成功发送验证码！"}
    else:
        raise HTTPException(status_code=400, detail="发送验证码失败！")

@app.post("/api/register", response_model=Dict[str, Any])
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # 验证是否同意使用条款和隐私政策
    if not user_data.agree_terms:
        raise HTTPException(status_code=400, detail="请阅读并同意使用条款和隐私政策")
        
    if db.query(User).filter_by(username=user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    if db.query(User).filter_by(email=user_data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    valid_code = VerificationCode.get_valid_code(db, user_data.email)
    if not valid_code:
        raise HTTPException(status_code=400, detail="验证码已过期或不存在，请重新获取")
    
    if valid_code.code != user_data.createVerifyCode_value:
        raise HTTPException(status_code=400, detail="验证码错误，请重新输入")
    
    user = User(username=user_data.username, email=user_data.email)
    user.set_password(user_data.password)
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 自动为新用户收藏所有公开资源
        public_resources = db.query(Resource).filter(Resource.is_public == 1).all()
        created_count = 0
        for resource in public_resources:
            # 检查是否已存在收藏记录（防止重复）
            existing_favorite = db.query(UserFavorite).filter(
                UserFavorite.user_id == user.id,
                UserFavorite.resource_id == resource.id
            ).first()
            if not existing_favorite:
                favorite = UserFavorite(
                    user_id=user.id,
                    resource_id=resource.id
                )
                db.add(favorite)
                created_count += 1
        
        if created_count > 0:
            db.commit()
            logger.info(f"为用户 {user.id} 自动收藏了 {created_count} 个公开资源")
        
        return {"message": "注册成功", "user": user.to_dict()}
    except Exception as e:
        db.rollback()
        logger.error(f"注册失败: {str(e)}")
        raise HTTPException(status_code=500, detail="注册失败")

@app.post("/api/login", response_model=Dict[str, Any])
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # 验证是否同意使用条款和隐私政策
    if not login_data.agree_terms:
        raise HTTPException(status_code=400, detail="请阅读并同意使用条款和隐私政策")
        
    user = db.query(User).filter_by(email=login_data.useremail).first()
    print(login_data)
    if not user or not user.check_password(login_data.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    token = generate_jwt(user.id, user.username)
    return {
        "message": "登录成功",
        "user": user.to_dict(),
        "access_token": token
    }

import os
import shutil

@app.delete("/api/delete-account", response_model=Dict[str, str])
def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # 删除用户的云盘文件
        user_upload_dir = f"uploads/user_{current_user.id}"
        if os.path.exists(user_upload_dir):
            shutil.rmtree(user_upload_dir)
            print(f"已删除用户 {current_user.id} 的云盘文件")
        
        # 先删除用户关联的记录（解决外键约束问题）
        from sqlalchemy.sql import text
        # 删除用户的文件记录
        db.execute(text(f"DELETE FROM files WHERE user_id = {current_user.id}"))
        # 删除用户的反馈记录
        db.execute(text(f"DELETE FROM feedback WHERE user_id = {current_user.id}"))
        
        # 删除用户的聊天记录
        db.query(ChatRecord).filter_by(user_id=str(current_user.id)).delete()
        
        # 删除用户的收藏
        db.query(UserFavorite).filter_by(user_id=current_user.id).delete()
        
        # 删除用户账户
        db.delete(current_user)
        db.commit()
        
        return {"message": "账户已成功注销，所有云盘资源已删除"}
    except Exception as e:
        db.rollback()
        print(f"删除账户时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="删除账户失败，请稍后再试")



# 资源相关API

# 聊天记录路由将在文件末尾导入以避免循环依赖
@app.post("/api/resources", response_model=Dict[str, Any])
def add_resource(resource_data: ResourceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    category = db.query(Category).filter_by(name=resource_data.category_name).first()
    if not category:
        category = Category(name=resource_data.category_name)
        db.add(category)
        db.commit()
        db.refresh(category)
    
    # 创建资源，默认设为私有状态
    resource = Resource(
        category_id=category.id,
        title=resource_data.title,
        url=resource_data.url,
        description=resource_data.description or '',
        is_public=0  # 0: 私有
    )
    
    try:
        db.add(resource)
        db.commit()
        db.refresh(resource)
        
        # 自动创建收藏记录
        favorite = UserFavorite(
            user_id=current_user.id,
            resource_id=resource.id
        )
        db.add(favorite)
        db.commit()
        
        return {"message": "资源添加成功", "resource": resource.to_dict()}
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="添加资源失败")

@app.get("/api/resources", response_model=Dict[str, List[Dict[str, Any]]])
def get_all_resources(category_name: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 获取用户收藏的资源ID列表
    favorite_resource_ids = db.query(UserFavorite.resource_id).filter_by(user_id=current_user.id).all()
    favorite_resource_ids = [item[0] for item in favorite_resource_ids]
    
    # 构建查询：只获取用户收藏的资源
    query = db.query(Resource).filter(Resource.id.in_(favorite_resource_ids))
    
    # 如果指定了分类
    if category_name:
        category = db.query(Category).filter_by(name=category_name).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        query = query.filter_by(category_id=category.id)
    
    resources = query.all()
    
    # 为每个资源添加是否收藏的标记
    resources_with_favorite_status = []
    for resource in resources:
        resource_dict = resource.to_dict()
        resource_dict['is_favorite'] = resource.id in favorite_resource_ids
        resources_with_favorite_status.append(resource_dict)
    
    return {"resources": resources_with_favorite_status}



@app.post("/api/favorites/remove", response_model=Dict[str, str])
async def remove_favorite(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await request.json()
    resource_id = data.get('resource_id')
    
    if not resource_id:
        raise HTTPException(status_code=400, detail="资源ID不能为空")
    
    # 查找用户对该资源的收藏记录
    favorite = db.query(UserFavorite).filter_by(
        user_id=current_user.id,
        resource_id=resource_id
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="收藏不存在")
    
    # 查找对应的资源信息
    resource = db.query(Resource).filter_by(id=resource_id).first()
    
    try:
        # 无论是否为公共资源，都要删除用户与该课程的连接（收藏记录）
        db.delete(favorite)
        
        # 检查该资源是否为公共资源（is_public=1）
        # 如果不是公共资源，需要删除该资源
        if resource and resource.is_public == 0:
            # 检查是否有其他用户也收藏了这个资源（排除当前用户）
            other_favorites_count = db.query(UserFavorite).filter(
                UserFavorite.resource_id == resource_id,
                UserFavorite.user_id != current_user.id
            ).count()
            if other_favorites_count == 0:  # 如果没有其他用户收藏，则删除资源
                db.delete(resource)
                logger.info(f"删除非公共资源: ID={resource_id}, 标题={resource.title}")
        
        db.commit()
        return {"message": "取消收藏成功"}
    except Exception as e:
        logger.error(f"取消收藏失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="取消收藏失败")

# 聊天相关API
@app.post("/api/ask-stream")
async def ask_question_stream(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await request.json()
    model = request.headers.get("model", "deepseek")
    think_way = request.headers.get("think", "deepseek-chat")
    
    user_query = data.get('question', '')
    session_id = data.get('session_id')
    
    if not user_query:
        raise HTTPException(status_code=400, detail="问题不能为空")
    
    # 读取用户的AI设置
    user_settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    
    # 解析用户设置的模型参数
    user_temperature = 0.7
    user_max_tokens = None
    user_top_p = 1.0
    user_api_key = None
    user_api_base = None
    user_model_name = None
    
    if user_settings:
        try:
            params = get_user_model_params(db, current_user.id)
            user_temperature = params.get('temperature', 0.7)
            user_max_tokens = params.get('max_tokens')
            user_top_p = params.get('top_p', 1.0)
        except Exception as e:
            logger.warning(f"解析用户模型参数失败: {str(e)}，使用默认值")
    
    # 如果用户设置了API密钥和地址，使用用户的设置
    if user_settings:
        if user_settings.api_key:
            user_api_key = user_settings.api_key
        if user_settings.api_base:
            user_api_base = user_settings.api_base
        if user_settings.model_name:
            user_model_name = user_settings.model_name
    
    # 如果没有会话ID，生成一个新的
    if not session_id:
        session_id = str(uuid.uuid4()).replace("-", "")
    
    # 保存用户的问题
    user_message_order = 1
    try:
        existing_message = db.query(ChatRecord).filter(
            ChatRecord.session_id == session_id,
            ChatRecord.user_id == str(current_user.id),
            ChatRecord.content == user_query,
            ChatRecord.sender_type == USER_SENDER
        ).order_by(ChatRecord.id.desc()).first()
        
        if existing_message:
            user_message_order = existing_message.message_order
        else:
            result = create_chat_record(
                db,
                content=user_query,
                sender_type=USER_SENDER,
                user_id=str(current_user.id),
                session_id=session_id,
                ai_model=model
            )
            # 确保result是一个字典
            if isinstance(result, dict):
                user_message_order = result.get('message_order', 1)
            else:
                user_message_order = getattr(result, 'message_order', 1)
    except Exception as e:
        logger.error(f"保存用户问题失败: {str(e)}")
    
    # 立即创建AI回复的占位记录
    ai_message_id = None
    try:
        ai_record = ChatRecord(
            session_id=session_id,
            user_id=str(current_user.id),
            message_order=user_message_order + 1,
            sender_type=AI_SENDER,
            content="",
            ai_model=model,
            status=MessageStatus.PENDING.value
        )
        db.add(ai_record)
        db.flush()
        ai_message_id = ai_record.id
        db.commit()
    except Exception as e:
        logger.error(f"创建AI回复占位记录失败: {str(e)}")
        db.rollback()
    
    # 获取对话历史记录
    history_messages = get_conversation_history(db, session_id, current_user.id, max_messages=5, max_tokens=2000)
    
    # 保存AI回复的函数 - 添加断点续存机制
    def save_ai_response(content: str, status: str = MessageStatus.COMPLETED.value):
        try:
            # 使用新的数据库会话进行保存操作，确保不依赖于请求的数据库会话
            save_db = SessionLocal()
            try:
                if ai_message_id:
                    # 查找现有的AI回复记录
                    ai_record = save_db.query(ChatRecord).get(ai_message_id)
                    if ai_record:
                        # 无论内容是否变化都更新，确保完整保存所有回复内容
                        ai_record.content = content
                        ai_record.status = status
                        save_db.commit()
                        logger.debug(f"AI回复已更新: 消息ID={ai_message_id}, 内容长度={len(content)}, 状态={status}")
                else:
                    # 如果没有找到现有记录，创建新记录
                    create_chat_record(
                        save_db,
                        ChatRecord,  # 传入ChatRecord类
                        content=content,
                        sender_type=AI_SENDER,
                        user_id=str(current_user.id),
                        session_id=session_id,
                        ai_model=model,
                        status=status
                    )
                    logger.debug(f"已创建新的AI回复记录: 用户ID={current_user.id}, 会话ID={session_id}")
            except Exception as e:
                save_db.rollback()
                logger.error(f"保存AI回复失败: {str(e)}")
            finally:
                save_db.close()
        except Exception as e:
            logger.error(f"保存AI回复过程中出现严重错误: {str(e)}")
    
    def close_stream(stream_obj):
        if not stream_obj:
            return
        try:
            close_method = getattr(stream_obj, "close", None)
            if callable(close_method):
                close_method()
        except Exception as e:
            logger.debug(f"关闭流对象失败: {e}")
        try:
            response_obj = getattr(stream_obj, "response", None)
            if response_obj and hasattr(response_obj, "close"):
                response_obj.close()
        except Exception as e:
            logger.debug(f"关闭流响应失败: {e}")
    
    # 生成器函数 - 添加断点续存机制
    async def generate_reasoner():
        stream = None
        cancelled = False
        full_response = ""
        content_only = ""
        sign_reasoner = True
        sign_content = True
        chunk_count = 0
        save_interval = 5  # 每5个chunk保存一次，确保及时保存部分内容
        
        try:
            # 始终使用请求头中的思考方式（系统默认模型）
            model_to_use = think_way
            # 使用用户设置的API密钥和地址（如果已设置）
            api_key_to_use = user_api_key if user_api_key else None
            api_base_to_use = user_api_base if user_api_base else None
            stream = call_deepseek_api_stream(
                user_query, 
                model_to_use, 
                history_messages,
                user_api_key=api_key_to_use,
                user_api_base=api_base_to_use,
                temperature=user_temperature,
                max_tokens=user_max_tokens,
                top_p=user_top_p
            )
            if not stream:
                error_msg = "抱歉，暂时无法获取答案，请稍后再试。"
                yield error_msg.encode()
                save_ai_response(error_msg, MessageStatus.FAILED.value)
                return
            
            for chunk in stream:
                if await request.is_disconnected():
                    cancelled = True
                    break
                
                chunk_count += 1
                
                if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content is not None:
                    reasoning_content = chunk.choices[0].delta.reasoning_content
                    full_response += reasoning_content
                    if sign_reasoner:
                        yield '<div class="thought-process"><strong>思考过程</strong><div class="thought-content">'.encode('utf-8')
                        yield reasoning_content.encode()
                        sign_reasoner = False
                    else:
                        yield reasoning_content.encode()
                
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    content_only += content
                    converted_content = convert_table_format(content)
                    if sign_content:
                        if not sign_reasoner and sign_content:
                            yield '</div></div>'.encode('utf-8')
                        yield '<div class="main-answer"><strong>正文解答</strong><div class="answer-content">'.encode('utf-8')
                        yield converted_content.encode()
                        sign_content = False
                    else:
                        yield converted_content.encode()
                
                if chunk_count % save_interval == 0:
                    save_ai_response(content_only, MessageStatus.PENDING.value)
            
            if cancelled:
                return
            
            if not sign_reasoner:
                yield '</div></div>'.encode('utf-8')
            if not sign_content:
                yield '</div></div>'.encode('utf-8')
            
            save_ai_response(content_only, MessageStatus.COMPLETED.value)
        except asyncio.CancelledError:
            cancelled = True
            return
        except Exception as e:
            logger.error(f"生成AI回复时出错: {str(e)}")
            error_msg = "抱歉，处理请求时出现错误。"
            yield error_msg.encode()
            save_ai_response(error_msg, MessageStatus.FAILED.value)
        finally:
            close_stream(stream)
            if cancelled:
                partial = content_only or full_response
                save_ai_response(partial, MessageStatus.CANCELLED.value)
    
    async def generate():
        stream = None
        cancelled = False
        full_response = ""
        chunk_count = 0
        save_interval = 5  # 每5个chunk保存一次，确保及时保存部分内容
        
        try:
            # 始终使用请求头中的思考方式（系统默认模型）
            model_to_use = think_way
            # 使用用户设置的API密钥和地址（如果已设置）
            api_key_to_use = user_api_key if user_api_key else None
            api_base_to_use = user_api_base if user_api_base else None
            stream = call_deepseek_api_stream(
                user_query, 
                model_to_use, 
                history_messages,
                user_api_key=api_key_to_use,
                user_api_base=api_base_to_use,
                temperature=user_temperature,
                max_tokens=user_max_tokens,
                top_p=user_top_p
            )
            if not stream:
                error_msg = "抱歉，暂时无法获取答案，请稍后再试。"
                yield error_msg.encode()
                save_ai_response(error_msg, MessageStatus.FAILED.value)
                return
            
            yield '<div class="main-answer"><strong>正文解答</strong><div class="answer-content">'.encode('utf-8')
            
            for chunk in stream:
                if await request.is_disconnected():
                    cancelled = True
                    break
                
                chunk_count += 1
                
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    converted_content = convert_table_format(content)
                    yield converted_content.encode()
                
                if chunk_count % save_interval == 0:
                    save_ai_response(full_response, MessageStatus.PENDING.value)
            
            if cancelled:
                return
            
            yield '</div></div>'.encode('utf-8')
            save_ai_response(full_response, MessageStatus.COMPLETED.value)
        except asyncio.CancelledError:
            cancelled = True
            return
        except Exception as e:
            logger.error(f"生成AI回复时出错: {str(e)}")
            error_msg = "抱歉，处理请求时出现错误。"
            yield error_msg.encode()
            save_ai_response(error_msg, MessageStatus.FAILED.value)
        finally:
            close_stream(stream)
            if cancelled:
                save_ai_response(full_response, MessageStatus.CANCELLED.value)
    
    async def generate_doubao():
        stream = None
        cancelled = False
        full_response = ""
        chunk_count = 0
        save_interval = 5  # 每5个chunk保存一次，确保及时保存部分内容
        
        try:
            stream = call_doubao_api_stream(
                user_query,
                history_messages,
                temperature=user_temperature,
                max_tokens=user_max_tokens,
                top_p=user_top_p,
            )
            if not stream:
                error_msg = "抱歉，暂时无法获取答案，请稍后再试。"
                yield error_msg.encode()
                save_ai_response(error_msg, MessageStatus.FAILED.value)
                return
            
            yield '<div class="main-answer"><strong>正文解答</strong><div class="answer-content">'.encode('utf-8')
            
            for chunk in stream:
                if await request.is_disconnected():
                    cancelled = True
                    break
                
                chunk_count += 1
                
                try:
                    if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        if hasattr(choice, "delta") and hasattr(choice.delta, "content") and choice.delta.content is not None:
                            content = choice.delta.content
                            full_response += content
                            converted_content = convert_table_format(content)
                            yield converted_content.encode()
                except Exception as e:
                    logger.error(f"处理Doubao API响应块时出错: {str(e)}")
                    continue
                
                if chunk_count % save_interval == 0:
                    save_ai_response(full_response, MessageStatus.PENDING.value)
            
            if cancelled:
                return
            
            yield '</div></div>'.encode('utf-8')
            save_ai_response(full_response, MessageStatus.COMPLETED.value)
        except asyncio.CancelledError:
            cancelled = True
            return
        except Exception as e:
            logger.error(f"生成Doubao AI回复时出错: {str(e)}")
            error_msg = "抱歉，处理请求时出现错误。"
            yield error_msg.encode()
            save_ai_response(error_msg, MessageStatus.FAILED.value)
        finally:
            close_stream(stream)
            if cancelled:
                save_ai_response(full_response, MessageStatus.CANCELLED.value)
    
    async def generate_custom_model(custom_model: CustomAIModel):
        """自定义模型生成器"""
        stream = None
        cancelled = False
        full_response = ""
        chunk_count = 0
        save_interval = 5  # 每5个chunk保存一次，确保及时保存部分内容
        
        try:
            stream = call_custom_model_api_stream(
                custom_model, 
                user_query, 
                history_messages,
                temperature=user_temperature,
                max_tokens=user_max_tokens,
                top_p=user_top_p
            )
            if not stream:
                error_msg = f"抱歉，暂时无法连接到自定义模型 {custom_model.model_display_name}，请稍后再试。"
                yield error_msg.encode()
                save_ai_response(error_msg, MessageStatus.FAILED.value)
                return
            
            yield '<div class="main-answer"><strong>正文解答</strong><div class="answer-content">'.encode('utf-8')
            
            for chunk in stream:
                if await request.is_disconnected():
                    cancelled = True
                    break
                
                chunk_count += 1
                
                try:
                    if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        if hasattr(choice, "delta") and hasattr(choice.delta, "content") and choice.delta.content is not None:
                            content = choice.delta.content
                            full_response += content
                            converted_content = convert_table_format(content)
                            yield converted_content.encode()
                except Exception as e:
                    logger.error(f"处理自定义模型API响应块时出错: {str(e)}")
                    continue
                
                if chunk_count % save_interval == 0:
                    save_ai_response(full_response, MessageStatus.PENDING.value)
            
            if cancelled:
                return
            
            yield '</div></div>'.encode('utf-8')
            save_ai_response(full_response, MessageStatus.COMPLETED.value)
        except asyncio.CancelledError:
            cancelled = True
            return
        except Exception as e:
            logger.error(f"生成自定义模型AI回复时出错: {str(e)}")
            error_msg = f"抱歉，使用自定义模型 {custom_model.model_display_name} 处理请求时出现错误。"
            yield error_msg.encode()
            save_ai_response(error_msg, MessageStatus.FAILED.value)
        finally:
            close_stream(stream)
            if cancelled:
                save_ai_response(full_response, MessageStatus.CANCELLED.value)
    
    def convert_table_format(text):
        """检测并转换表格格式
        识别包含 | 分隔符的表格行，并将其转换为HTML表格格式
        """
        lines = text.split('\n')
        if len(lines) < 3:  # 表格至少需要表头、分隔线和一行数据
            return text
            
        # 检查是否包含表格格式
        has_table = False
        for line in lines:
            if '|' in line and ':' in line and '-' in line:  # 检查是否有分隔线
                has_table = True
                break
        
        if not has_table:
            return text
            
        # 转换表格格式
        result = []
        in_table = False
        table_started = False
        
        for line in lines:
            stripped = line.strip()
            
            # 检查是否是表格行
            if stripped.startswith('|') and stripped.endswith('|'):
                if not in_table:
                    in_table = True
                    if not table_started:
                        result.append('<table class="table table-bordered table-hover">')
                        table_started = True
                
                # 处理表格行
                cells = [cell.strip() for cell in stripped.split('|')[1:-1]]  # 去掉首尾的|
                
                # 检查是否是分隔线
                if all('-' in cell or ':' in cell for cell in cells):
                    continue  # 跳过分隔线
                
                # 构建表格行
                result.append('<tr>')
                for cell in cells:
                    # 检查是否是表头（包含**）
                    if '**' in cell:
                        cell = cell.replace('**', '')
                        result.append(f'<th>{cell}</th>')
                    else:
                        result.append(f'<td>{cell}</td>')
                result.append('</tr>')
            else:
                # 非表格行
                if in_table:
                    # 结束表格
                    result.append('</table>')
                    in_table = False
                result.append(line)
        
        # 确保表格正确闭合
        if in_table:
            result.append('</table>')
            
        return '\n'.join(result)
    
    # 根据模型类型和思考方式返回相应的流式响应
    if model == 'deepseek':
        if think_way == 'deepseek-chat':
            return StreamingResponse(generate(), media_type='text/plain')
        else:
            return StreamingResponse(generate_reasoner(), media_type='text/plain')
    elif model == 'doubao':
        return StreamingResponse(generate_doubao(), media_type='text/plain')
    elif model.startswith('custom_'):
        # 处理自定义模型
        try:
            custom_model_id = int(model.replace('custom_', ''))
            custom_model = db.query(CustomAIModel).filter(
                CustomAIModel.id == custom_model_id,
                CustomAIModel.user_id == current_user.id,
                CustomAIModel.is_active == True
            ).first()
            
            if not custom_model:
                error_msg = "自定义模型不存在或已被禁用"
                async def error_generator():
                    yield error_msg.encode()
                    save_ai_response(error_msg, MessageStatus.FAILED.value)
                return StreamingResponse(error_generator(), media_type='text/plain')
            
            return StreamingResponse(generate_custom_model(custom_model), media_type='text/plain')
        except ValueError:
            error_msg = "无效的自定义模型ID"
            async def error_generator():
                yield error_msg.encode()
                save_ai_response(error_msg, MessageStatus.FAILED.value)
            return StreamingResponse(error_generator(), media_type='text/plain')
    else:
        return StreamingResponse(generate(), media_type='text/plain')

# 聊天记录相关API
@app.post("/api/chat-records/save", response_model=Dict[str, Any])
async def save_chat_record(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await request.json()
    user_id = str(current_user.id)  # 确保是字符串类型
    
    # 验证必要字段
    if 'content' not in data or 'sender_type' not in data:
        raise HTTPException(status_code=400, detail="内容和发送者类型不能为空")
    
    # 验证sender_type值
    sender_type = data['sender_type']
    if sender_type not in [USER_SENDER, AI_SENDER]:
        raise HTTPException(status_code=400, detail="发送者类型无效，只能是1（用户）或2（AI）")
    
    # 创建聊天记录
    record = create_chat_record(
        db,
        content=data['content'],
        sender_type=sender_type,
        user_id=user_id,
        session_id=data.get('session_id'),
        ai_model=data.get('ai_model')
    )
    
    return {"message": "聊天记录保存成功", "record": record}

@app.get("/api/chat-records/sessions", response_model=Dict[str, List[Dict[str, Any]]])
def get_chat_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(
        ChatRecord.session_id,
        func.max(ChatRecord.send_time).label('last_message_time'),
        func.substr(
            func.max(func.concat(ChatRecord.send_time, ChatRecord.content)),
            20
        ).label('last_message')
    ).filter(
        ChatRecord.user_id == str(current_user.id)
    ).group_by(
        ChatRecord.session_id
    ).order_by(
        desc(text('last_message_time'))
    ).all()
    
    result = []
    for session in sessions:
        result.append({
            "session_id": session.session_id,
            "last_message": session.last_message,
            "last_message_time": session.last_message_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return {"sessions": result}

@app.get("/api/chat-records/session/{session_id}", response_model=Dict[str, List[Dict[str, Any]]])
def get_chat_session_messages(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    messages = db.query(ChatRecord).filter(
        ChatRecord.user_id == str(current_user.id),
        ChatRecord.session_id == session_id
    ).order_by(
        ChatRecord.send_time
    ).all()
    
    return {"messages": [message.to_dict() for message in messages]}

@app.delete("/api/chat-records/session/{session_id}", response_model=Dict[str, str])
def delete_chat_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        db.query(ChatRecord).filter(
            ChatRecord.user_id == str(current_user.id),
            ChatRecord.session_id == session_id
        ).delete()
        db.commit()
        
        return {"message": "会话已删除"}
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="删除失败")

@app.post("/api/chat-records/new-session", response_model=Dict[str, str])
def create_new_chat_session(current_user: User = Depends(get_current_user)):
    session_id = str(uuid.uuid4()).replace("-", "")
    return {"session_id": session_id}

# 导入管理员认证依赖
from chat_records import get_current_admin_dependency

# 测试邮箱验证端点（仅用于开发测试）
@app.post("/api/test-email-validation", response_model=Dict[str, Any])
def test_email_validation(
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """
    测试邮箱验证功能是否正常工作
    """
    try:
        from email_validator import validate_email, EmailNotValidError
        
        # 获取email参数
        email = request.get('email', '')
        print(f"测试邮箱: '{email}'")
        
        if not email:
            return {"message": "邮箱不能为空"}
        
        # 使用开发模式的邮箱验证
        validate_email(email, check_deliverability=False)
        
        return {
            "message": "邮箱验证通过",
            "email": email,
            "status": "valid"
        }
        
    except EmailNotValidError as e:
        print(f"邮箱验证失败: '{email}', 错误: {str(e)}")
        return {
            "message": "邮箱验证失败",
            "email": email,
            "status": "invalid",
            "error": str(e)
        }
    except Exception as e:
        print(f"服务器错误: {str(e)}")
        return {
            "message": "验证过程出错",
            "error": str(e)
        }

# 管理员创建用户API
@app.post("/api/admin/create-user", response_model=Dict[str, Any])
def admin_create_user(
    user_data: dict,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin_dependency)
):
    """
    管理员创建新用户
    """
    try:
        # 添加调试日志
        print(f"收到创建用户请求，数据: {user_data}")
        
        # 验证必要字段
        if 'username' not in user_data or 'email' not in user_data or 'password' not in user_data:
            print(f"缺少必要字段: username={user_data.get('username')}, email={user_data.get('email')}, password={user_data.get('password')}")
            raise HTTPException(status_code=400, detail="缺少必要字段")
        
        username = user_data['username'].strip()
        email = user_data['email'].strip()
        password = user_data['password']
        
        print(f"处理用户数据: username='{username}', email='{email}', password_length={len(password)}")
        
        # 验证数据格式
        if not username or len(username) < 3 or len(username) > 80:
            print(f"用户名验证失败: '{username}' (长度: {len(username)})")
            raise HTTPException(status_code=400, detail="用户名长度必须在3-80位之间")
        
        # 验证邮箱格式
        from email_validator import validate_email, EmailNotValidError
        try:
            # 在开发环境中，不检查域名是否真实存在
            # 仅验证邮箱格式是否正确
            validate_email(email, check_deliverability=False)
        except EmailNotValidError as e:
            print(f"邮箱验证失败: '{email}', 错误: {str(e)}")
            raise HTTPException(status_code=400, detail="邮箱格式无效")
        
        if len(password) < 6 or len(password) > 20:
            print(f"密码长度验证失败: 长度={len(password)}")
            raise HTTPException(status_code=400, detail="密码长度必须在6-20位之间")
        
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                print(f"用户名已存在: '{username}'")
                raise HTTPException(status_code=400, detail="用户名已存在")
            else:
                print(f"邮箱已被注册: '{email}'")
                raise HTTPException(status_code=400, detail="邮箱已被注册")
        
        # 创建新用户
        new_user = User(
            username=username,
            email=email
        )
        
        # 设置密码（会自动加密）
        new_user.set_password(password)
        
        # 添加到数据库
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"用户创建成功: ID={new_user.id}, username={new_user.username}")
        
        return {
            "message": "用户创建成功",
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
        
    except HTTPException as e:
        print(f"HTTP错误: {e.status_code}, {e.detail}")
        raise
    except Exception as e:
        print(f"服务器错误: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")

# 其他API@app.get("/api/get-resources", response_model=Dict[str, List[Dict[str, Any]]])
def get_resources(text: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    learning_resources = get_learning_resources(text, db)
    return {"resources": learning_resources}

@app.get("/api/client-ip", response_model=Dict[str, str])
def get_client_ip(request: Request, current_user: User = Depends(get_current_user)):
    if request.headers.get('x-forwarded-for'):
        ip = request.headers.get('x-forwarded-for').split(',')[0].strip()
    else:
        ip = request.client.host
    
    return {'ip': ip, 'version': 'IPv6' if ':' in ip else 'IPv4'}

@app.get("/api/ipv6-test", response_model=Dict[str, List[Dict[str, Any]]])
def ipv6_test(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    test_resources = db.query(Resource).limit(3).all()
    test_urls = [r.url for r in test_resources]
    
    if not test_urls:
        test_urls = [
            "http://[2001:da8:202:10::36]/physics/quantum_basic.mp4",
            "http://[2001:da8:8000:1::1234]/simulations/double-slit",
            "http://[2001:da8:202:10::47]/math/calculus_full"
        ]
    
    results = []
    for url in test_urls:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.hostname.strip('[]')
            port = parsed.port or 80
            
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((hostname, port))
            sock.close()
            
            results.append({
                'url': url,
                'status': '可达' if result == 0 else '不可达',
                'error': os.strerror(result) if result != 0 else None
            })
        except Exception as e:
            results.append({
                'url': url,
                'status': '错误',
                'error': str(e)
            })
    
    return {'tests': results}

@app.get("/api/health", response_model=Dict[str, str])
def health_check(current_user: User = Depends(get_current_user)):
    return {"status": "healthy", "message": "API服务正常"}

@app.post("/api/forgot-password/email", response_model=Dict[str, str])
def forgot_password_email(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="该邮箱未被注册")
    
    # 检查是否可以发送验证码
    can_send, message = VerificationCode.can_send_code(db, request.email)
    if not can_send:
        raise HTTPException(status_code=429, detail=message)
    
    info = send_reset_email_last(request.email)
    if not info:
        raise HTTPException(status_code=400, detail="发送验证码失败！")
    
    res = VerificationCode.insert_verify_code(db, info['email'], info['code'])
    if res:
        return {"message": "已成功发送验证码！"}
    else:
        raise HTTPException(status_code=400, detail="发送验证码失败！")

@app.post("/api/token", response_model=Dict[str, str])
async def verify_token(request: Request):
    data = await request.json()
    token = data.get('token')
    res = verify_jwt(token)
    if 'error' in res:
        return {'res': 'Failure'}
    else:
        return {'res': 'success'}

@app.post("/api/forgot-password", response_model=Dict[str, str])
def forgot_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"开始处理密码重置请求，邮箱: {request.email}")
        
        user = db.query(User).filter_by(email=request.email).first()
        if not user:
            logger.warning(f"密码重置失败：邮箱 {request.email} 未被注册")
            raise HTTPException(status_code=400, detail="该邮箱未被注册")
        
        if not request.verifyCode.isdigit() or len(request.verifyCode) != 6:
            logger.warning(f"密码重置失败：验证码格式不正确，长度={len(request.verifyCode)}")
            raise HTTPException(status_code=400, detail="验证码必须为6位数字")
        
        valid_code = VerificationCode.get_valid_code(db, request.email)
        if not valid_code:
            logger.warning(f"密码重置失败：邮箱 {request.email} 的验证码不存在或已过期")
            raise HTTPException(status_code=400, detail="验证码已过期或不存在，请重新获取")
        
        if valid_code.code != request.verifyCode:
            logger.warning(f"密码重置失败：验证码错误，期望={valid_code.code}, 实际={request.verifyCode}")
            raise HTTPException(status_code=400, detail="验证码错误，请重新输入")
        
        logger.info(f"验证码验证成功，开始更新密码")
        
        # 保存验证码ID，以便在密码更新后删除
        valid_code_id = valid_code.id
        
        # 更新密码（此方法内部会提交事务）
        success, message = User.update_password_by_email(db, request.email, request.newPassword)
        if not success:
            logger.error(f"密码更新失败：{message}")
            raise HTTPException(status_code=400, detail=message)
        
        logger.info(f"密码更新成功，开始删除验证码")
        
        # 删除已使用的验证码（重新查询以确保对象在会话中）
        try:
            # 重新查询验证码，因为之前的commit可能使对象脱离会话
            code_to_delete = db.query(VerificationCode).filter_by(id=valid_code_id).first()
            if code_to_delete:
                db.delete(code_to_delete)
                db.commit()
                logger.info(f"验证码删除成功")
            else:
                logger.warning(f"验证码已不存在，可能已被删除")
        except Exception as e:
            logger.warning(f"删除验证码失败（不影响密码重置）: {str(e)}")
            db.rollback()
            # 验证码删除失败不影响密码重置成功
        
        logger.info(f"密码重置成功，邮箱: {request.email}")
        return {"message": "密码重置成功，请用新密码登录"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"密码重置过程中发生异常: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"密码重置失败，请稍后重试: {str(e)}")

# 用户反馈系统API
@app.post("/api/feedback", response_model=FeedbackResponse, summary="提交用户反馈")
def submit_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    提交用户反馈
    
    - **content**: 反馈内容（5-2000字符）
    - **feedback_type**: 反馈类型（suggestion, problem, bug, other）
    - **contact_info**: 可选的联系方式
    """
    try:
        new_feedback = Feedback(
            user_id=current_user.id,
            content=feedback_data.content,
            feedback_type=feedback_data.feedback_type,
            contact_info=feedback_data.contact_info
        )
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)
        
        logger.info(f"用户 {current_user.id} 提交了反馈: {new_feedback.id}")
        
        # 返回符合Pydantic模型的响应数据
        return {
            "id": new_feedback.id,
            "user_id": new_feedback.user_id,
            "username": current_user.username,
            "content": new_feedback.content,
            "feedback_type": new_feedback.feedback_type,
            "status": new_feedback.status,
            "created_at": new_feedback.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": new_feedback.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "contact_info": new_feedback.contact_info
        }
    except Exception as e:
        db.rollback()
        logger.error(f"提交反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail="提交反馈失败，请稍后重试")

@app.get("/api/feedback", response_model=List[FeedbackResponse], summary="获取用户反馈列表")
def get_user_feedbacks(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的反馈列表
    
    - **skip**: 跳过的记录数（默认0）
    - **limit**: 返回的最大记录数（默认10）
    """
    feedbacks = db.query(Feedback)\
        .filter(Feedback.user_id == current_user.id)\
        .order_by(Feedback.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    return feedbacks

@app.get("/api/feedback/{feedback_id}", response_model=FeedbackResponse, summary="获取反馈详情")
def get_feedback_detail(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取特定反馈的详细信息
    
    - **feedback_id**: 反馈的ID
    """
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    # 确保用户只能查看自己的反馈
    if feedback.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此反馈")
    
    return feedback

# 管理员功能：获取所有反馈（需要管理员权限）
@app.get("/api/admin/feedback", response_model=List[FeedbackResponse], summary="获取所有用户反馈")
def get_all_feedbacks(
    skip: int = 0,
    limit: int = 20,
    feedback_type: Optional[str] = None,
    status: Optional[str] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取所有用户的反馈列表（管理员权限）
    
    - **skip**: 跳过的记录数（默认0）
    - **limit**: 返回的最大记录数（默认20）
    - **feedback_type**: 可选的反馈类型筛选
    - **status**: 可选的状态筛选
    """
    # 使用get_current_admin依赖已进行管理员权限检查
    query = db.query(Feedback)
    
    if feedback_type:
        query = query.filter(Feedback.feedback_type == feedback_type)
    if status:
        query = query.filter(Feedback.status == status)
    
    feedbacks = query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()
    
    # 手动构建响应数据，确保datetime对象转换为字符串
    result = []
    for feedback in feedbacks:
        # 查询用户信息获取username
        user = db.query(User).filter(User.id == feedback.user_id).first()
        username = user.username if user else "未知用户"
        
        feedback_dict = {
            "id": feedback.id,
            "user_id": feedback.user_id,
            "username": username,
            "content": feedback.content,
            "feedback_type": feedback.feedback_type,
            "status": feedback.status,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
            "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None
        }
        result.append(feedback_dict)
    
    return result

# 管理员功能：更新反馈状态
@app.put("/api/admin/feedback/{feedback_id}", response_model=FeedbackResponse, summary="更新反馈状态")
def update_feedback_status(
    feedback_id: int,
    update_data: FeedbackUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    更新反馈的处理状态（管理员权限）
    
    - **feedback_id**: 反馈的ID
    - **status**: 新的状态（pending, processing, resolved, rejected）
    """
    # 使用get_current_admin依赖已进行管理员权限检查
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    try:
        feedback.status = update_data.status
        db.commit()
        db.refresh(feedback)
        
        logger.info(f"反馈 {feedback_id} 状态已更新为: {update_data.status}")
        
        # 查询用户信息获取username
        user = db.query(User).filter(User.id == feedback.user_id).first()
        username = user.username if user else "未知用户"
        
        # 构建响应数据，确保datetime对象转换为字符串
        return {
            "id": feedback.id,
            "user_id": feedback.user_id,
            "username": username,
            "content": feedback.content,
            "feedback_type": feedback.feedback_type,
            "status": feedback.status,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
            "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None,
            "contact_info": feedback.contact_info
        }
    except Exception as e:
        db.rollback()
        logger.error(f"更新反馈状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新反馈状态失败")

# 管理员功能：删除反馈
@app.delete("/api/admin/feedback/{feedback_id}", response_model=Dict[str, str], summary="删除反馈")
def delete_feedback(
    feedback_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    删除指定的反馈（管理员权限）
    
    - **feedback_id**: 反馈的ID
    """
    # 使用get_current_admin依赖已进行管理员权限检查
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    
    try:
        db.delete(feedback)
        db.commit()
        
        logger.info(f"反馈 {feedback_id} 已删除")
        return {"message": "反馈已成功删除"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除反馈失败")

# 静态文件和页面路由
@app.get("/")
def index():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(current_dir, '..', 'html', 'index.html')
        
        if not os.path.exists(index_path):
            raise HTTPException(status_code=404, detail="index.html not found")
        
        return FileResponse(index_path)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/test")
def test():
    return "服务器运行正常！测试端点工作正常。"

@app.get("/api/resources/add")
def get_add_resource(current_user: User = Depends(get_current_user)):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_dir = os.path.join(current_dir, '..', 'html')
        file_path = os.path.join(html_dir, 'add_resources.html')
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="添加资源页面不存在")
        
        return FileResponse(file_path)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500, detail="服务器错误")

@app.get("/api/resources/del")
def get_del_resource(current_user: User = Depends(get_current_user)):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_dir = os.path.join(current_dir, '..', 'html')
        file_path = os.path.join(html_dir, 'del_resources.html')
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="删除资源页面不存在")
        
        return FileResponse(file_path)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500, detail="服务器错误")

# 云盘相关API端点 - 完全重构
# 1. 文件上传（支持多文件）
@app.post("/api/cloud_disk/upload")
async def upload_file(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logger.info(f"用户 {current_user.id} 尝试上传文件到云盘")
    
    try:
        # 确保用户目录存在
        user_dir = settings.get_cloud_disk_dir_for_user(current_user.id)
        logger.info(f"用户目录路径: {user_dir}")
        
        # 目录已在settings方法中确保存在，转换为字符串
        user_dir_str = str(user_dir)
        
        # 解析multipart/form-data请求
        try:
            form = await request.form()
            logger.info(f"成功解析表单数据")
        except Exception as e:
            logger.error(f"解析表单数据失败: {str(e)}")
            raise HTTPException(status_code=400, detail="表单数据格式错误")
        
        # 获取文件夹路径参数（前端发送的文件夹路径）
        folder_path = form.get("folder_path", "/")
        logger.info(f"前端指定的文件夹路径: {folder_path}")
        
        # 获取所有文件，支持多文件上传
        # 优先查找'file'参数，因为前端对每个文件都使用相同的键名'file'
        files = form.getlist("file")  # 使用getlist获取多个文件
        logger.info(f"获取file参数文件数量: {len(files)}")
        
        # 如果没有使用file参数，尝试获取files参数作为兼容
        if not files:
            files = form.getlist("files")
            logger.info(f"获取files参数文件数量: {len(files)}")
        
        if not files:
            logger.warning(f"用户 {current_user.id} 未选择文件")
            raise HTTPException(status_code=400, detail="请选择要上传的文件")
        
        # 存储上传结果
        uploaded_files = []
        errors = []
        
        # 循环处理每个文件
        for i, file in enumerate(files):
            logger.info(f"处理文件 {i+1}/{len(files)}: {file.filename}")
            
            try:
                # 检查文件大小
                file.file.seek(0, 2)
                file_size = file.file.tell()
                file.file.seek(0)
                logger.info(f"文件 {file.filename} 大小: {file_size} 字节")
                
                if file_size > MAX_FILE_SIZE:
                    logger.warning(f"文件 {file.filename} 大小超过限制")
                    errors.append({
                        "filename": file.filename,
                        "error": f"文件大小不能超过{MAX_FILE_SIZE / 1024 / 1024:.1f}MB"
                    })
                    continue
                
                # 生成文件唯一标识
                file_uuid = str(uuid.uuid4())
                original_name = file.filename
                
                # 获取文件MIME类型
                file_type = getattr(file, 'content_type', 'application/octet-stream')
                logger.info(f"文件 {original_name} MIME类型: {file_type}")
                
                # 生成存储文件名（使用UUID）
                file_ext = os.path.splitext(original_name)[1]
                stored_filename = f"{file_uuid}{file_ext}"
                
                # 保存文件路径
                save_path = os.path.join(str(user_dir), stored_filename)
                logger.info(f"文件保存路径: {save_path}")
                
                # 保存文件到本地
                try:
                    with open(save_path, "wb") as buffer:
                        content = await file.read()
                        buffer.write(content)
                    logger.info(f"成功保存文件: {save_path}")
                    
                    # 验证文件是否成功保存
                    if not os.path.exists(save_path) or os.path.getsize(save_path) != file_size:
                        logger.error(f"文件保存验证失败: {save_path}")
                        raise Exception("文件保存失败或文件大小不匹配")
                    
                    # 保存文件信息到数据库
                    db_file = UserFile(
                        file_uuid=file_uuid,
                        original_name=original_name,
                        save_path=save_path,
                        file_size=file_size,
                        file_type=file_type,
                        user_id=current_user.id,
                        folder_path=folder_path  # 保存文件夹路径
                    )
                    db.add(db_file)
                    logger.info(f"成功添加文件记录到数据库: {original_name}, 文件夹: {folder_path}")
                    
                    uploaded_files.append({
                        "id": db_file.id,
                        "file_name": original_name,
                        "status": "success"
                    })
                except Exception as e:
                    logger.error(f"保存文件 {original_name} 失败: {str(e)}")
                    # 删除已上传的文件
                    if os.path.exists(save_path):
                        try:
                            os.remove(save_path)
                            logger.info(f"删除部分上传的文件: {save_path}")
                        except Exception as remove_error:
                            logger.error(f"删除部分上传的文件失败: {str(remove_error)}")
                    errors.append({
                        "filename": original_name,
                        "error": f"保存文件失败: {str(e)}"
                    })
            except Exception as e:
                logger.error(f"处理文件 {getattr(file, 'filename', 'unknown')} 时发生错误: {str(e)}")
                errors.append({
                    "filename": getattr(file, 'filename', 'unknown'),
                    "error": f"处理文件失败: {str(e)}"
                })
        
        # 提交数据库事务
        try:
            db.commit()
            logger.info(f"数据库事务提交成功，成功上传 {len(uploaded_files)} 个文件")
        except Exception as e:
            db.rollback()
            logger.error(f"数据库事务提交失败: {str(e)}")
            raise HTTPException(status_code=500, detail="保存文件信息到数据库失败")
        
        # 返回上传结果
        result = {
            "message": "文件上传完成",
            "success_count": len(uploaded_files),
            "error_count": len(errors),
            "uploaded_files": uploaded_files
        }
        
        if errors:
            result["errors"] = errors
        
        return result
    except HTTPException as http_exc:
        logger.error(f"HTTP异常: {str(http_exc)}")
        raise
    except Exception as e:
        logger.error(f"上传过程中发生未预期错误: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传过程中发生错误: {str(e)}")

# 2. 获取用户文件列表
@app.get("/api/cloud_disk/files")
async def get_files(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 确保用户只能访问自己的文件
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权访问其他用户的文件")
    
    # 查询用户的所有文件，按上传时间倒序排列
    files = db.query(UserFile).filter(
        UserFile.user_id == user_id
    ).order_by(desc(UserFile.upload_time)).all()
    
    # 查询用户的所有文件夹
    user_folders = db.query(UserFolder).filter(
        UserFolder.user_id == user_id
    ).all()
    
    # 构建树形结构（支持空文件夹）
    def build_tree_structure():
        # 1. 首先，收集所有文件夹路径
        all_folder_paths = set()
        folders_dict = {}
        
        # 添加来自用户创建的文件夹的路径
        for folder in user_folders:
            all_folder_paths.add(folder.folder_path)
        
        # 添加来自文件的文件夹路径
        for file in files:
            folder_path = file.folder_path if hasattr(file, 'folder_path') and file.folder_path else '/'
            all_folder_paths.add(folder_path)
        
        # 2. 初始化所有文件夹（包括空文件夹和父文件夹）
        for folder_path in all_folder_paths:
            # 添加该文件夹
            if folder_path not in folders_dict:
                folders_dict[folder_path] = {
                    "path": folder_path,
                    "name": folder_path.strip('/').split('/')[-1] or "根目录",
                    "type": "folder",
                    "children": []
                }
            
            # 添加所有父文件夹
            parts = folder_path.strip('/').split('/')
            for i in range(len(parts)):
                parent_path = '/' + '/'.join(parts[:i]) + '/' if i > 0 else '/'
                if parent_path not in folders_dict:
                    folders_dict[parent_path] = {
                        "path": parent_path,
                        "name": parent_path.strip('/').split('/')[-1] or "根目录",
                        "type": "folder",
                        "children": []
                    }
        
        # 3. 将文件分配到对应的文件夹
        for file in files:
            folder_path = file.folder_path if hasattr(file, 'folder_path') and file.folder_path else '/'
            if folder_path not in folders_dict:
                folders_dict[folder_path] = {
                    "path": folder_path,
                    "name": folder_path.strip('/').split('/')[-1] or "根目录",
                    "type": "folder",
                    "children": []
                }
            
            folders_dict[folder_path]["children"].append({
                "id": file.id,
                "file_uuid": file.file_uuid,
                "original_name": file.original_name,
                "file_size": file.file_size,
                "file_type": file.file_type,
                "upload_time": file.upload_time.isoformat(),
                "user_id": file.user_id,
                "folder_path": folder_path,
                "type": "file"
            })
        
        # 如果没有文件夹和文件，至少创建根目录
        if not folders_dict:
            folders_dict['/'] = {
                "path": '/',
                "name": "根目录",
                "type": "folder",
                "children": []
            }
        
        # 4. 构建嵌套树结构
        def build_nested_tree(parent_path="/", all_folders=None):
            if all_folders is None:
                all_folders = folders_dict
            
            result = []
            
            # 添加当前文件夹
            if parent_path in all_folders:
                folder_info = all_folders[parent_path]
                # 递归构建子文件夹的children
                children = list(folder_info["children"])  # 先添加文件
                
                # 查找所有直接子文件夹
                for folder_path in sorted(all_folders.keys()):
                    if folder_path != parent_path and folder_path.startswith(parent_path):
                        # 检查是否是直接子文件夹
                        relative_path = folder_path[len(parent_path):].strip('/')
                        if relative_path and '/' not in relative_path:  # 直接子文件夹
                            # 递归构建子文件夹
                            sub_tree = build_nested_tree(folder_path, all_folders)
                            if sub_tree:
                                children.extend(sub_tree)
                
                result.append({
                    "path": folder_info["path"],
                    "name": folder_info["name"],
                    "type": "folder",
                    "children": children,
                    "is_expanded": parent_path == "/"  # 默认展开根目录
                })
            
            return result
        
        return build_nested_tree()
    
    tree_structure = build_tree_structure()
    
    # 返回树形结构和平坦列表两种格式
    return {
        "tree": tree_structure,
        "folders": sorted(set(file.folder_path if hasattr(file, 'folder_path') and file.folder_path else '/' for file in files)),
        "total_files": len(files),
        "total_size": sum(file.file_size for file in files)
    }

# 3. 下载文件
@app.get("/api/cloud_disk/download/{file_id}")
async def download_file(file_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 确保用户只能访问自己的文件
        if current_user.id != user_id:
            logger.warning(f"用户 {current_user.id} 尝试访问用户 {user_id} 的文件 {file_id}")
            raise HTTPException(status_code=403, detail="无权访问其他用户的文件")
        
        # 查询文件
        file = db.query(UserFile).filter(
            UserFile.id == file_id,
            UserFile.user_id == user_id
        ).first()
        
        if not file:
            logger.warning(f"文件 {file_id} 不存在或不属于用户 {user_id}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查 save_path 是否有效
        if not file.save_path:
            logger.error(f"文件 {file_id} 的 save_path 为空")
            raise HTTPException(status_code=500, detail="文件路径无效")
        
        # 处理路径，确保文件存在
        file_path_to_check = file.save_path
        
        # 如果是相对路径，尝试转换为绝对路径
        if not os.path.isabs(file_path_to_check):
            logger.warning(f"文件 {file_id} 的路径是相对的，尝试转换为绝对路径: {file_path_to_check}")
            user_dir = settings.get_cloud_disk_dir_for_user(user_id)
            file_path_to_check = os.path.join(str(user_dir), file_path_to_check)
            logger.info(f"转换后的路径: {file_path_to_check}")
        
        # 检查文件是否存在
        if not os.path.exists(file_path_to_check):
            logger.error(f"文件 {file_id} 在路径 {file_path_to_check} 中不存在")
            # 如果绝对路径不存在，尝试查找备选路径
            logger.info(f"尝试查找备选路径...")
            
            # 备选方案1: 使用 file_uuid 查找文件
            if file.file_uuid:
                file_ext = os.path.splitext(file.original_name)[1]
                alt_filename = f"{file.file_uuid}{file_ext}"
                user_dir = settings.get_cloud_disk_dir_for_user(user_id)
                alt_path = os.path.join(str(user_dir), alt_filename)
                
                if os.path.exists(alt_path):
                    logger.info(f"使用备选路径: {alt_path}")
                    file_path_to_check = alt_path
                else:
                    logger.error(f"备选路径也不存在: {alt_path}")
                    raise HTTPException(status_code=404, detail="文件已被删除或路径无效")
            else:
                raise HTTPException(status_code=404, detail="文件已被删除或路径无效")
        
        # 对于压缩的视频文件，下载时需要解压
        file_path = file_path_to_check
        is_temp_file = False
        
        # 检查是否是视频文件且被压缩（以.zip结尾）
        if file_path_to_check.endswith('.zip') and file.file_type == "video":
            logger.info(f"文件 {file_id} 需要解压")
            file_path = decompress_file(file_path_to_check)
            is_temp_file = True
        
        # 读取文件内容以返回
        logger.info(f"正在读取文件 {file_id}: {file.original_name}, 路径: {file_path}")
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        logger.info(f"文件 {file_id} 读取成功，大小: {len(file_content)} 字节")
        
        # 确定正确的文件名（去掉.zip后缀）
        download_filename = file.original_name
        if file_path_to_check.endswith('.zip'):
            # 如果数据库中的原始文件名已经包含.zip，保持不变
            # 否则使用压缩前的文件名
            if not download_filename.endswith('.zip'):
                pass  # 使用原始文件名
        
        logger.info(f"准备返回文件，文件名: {download_filename}")
        
        # 使用 FileResponse 自动处理文件名编码，支持中文和其他非ASCII字符
        # FileResponse 会自动处理 Content-Disposition 头的编码
        try:
            return FileResponse(
                path=file_path,
                filename=download_filename,
                media_type=file.file_type or "application/octet-stream"
            )
        except Exception as e:
            logger.error(f"FileResponse 返回失败: {str(e)}")
            # 如果 FileResponse 失败，尝试手动处理
            try:
                # 对文件名进行正确的编码处理
                # 支持中文和其他非ASCII字符的文件名
                try:
                    # 尝试ASCII编码，如果失败则使用RFC 5987格式
                    download_filename.encode('ascii')
                    # 如果可以用ASCII编码，直接使用
                    content_disposition = f"attachment; filename=\"{download_filename}\""
                    logger.info(f"使用 ASCII 编码的文件名")
                except UnicodeEncodeError:
                    # 包含非ASCII字符，使用RFC 5987格式
                    # RFC 5987: filename*=UTF-8''<percent-encoded-filename>
                    encoded_filename = quote(download_filename.encode('utf-8'), safe='')
                    # 只使用 filename* 参数，避免 latin-1 编码问题
                    content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}"
                    logger.info(f"使用 RFC 5987 编码的文件名")
                
                return Response(
                    content=file_content,
                    media_type=file.file_type or "application/octet-stream",
                    headers={
                        "Content-Disposition": content_disposition,
                        "Content-Length": str(len(file_content))
                    }
                )
            except Exception as e2:
                logger.error(f"手动处理 Response 也失败: {str(e2)}")
                raise
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        logger.error(f"文件下载失败 - 文件ID: {file_id}, 用户ID: {user_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")
    finally:
        # 清理临时解压文件
        try:
            if 'is_temp_file' in locals() and is_temp_file and 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"临时文件已删除: {file_path}")
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {file_path}, 错误: {str(e)}")
        except:
            pass  # 忽略删除错误

# 3.5 更新文件内容（用于编辑功能）
@app.post("/api/cloud_disk/update-file/{file_id}")
async def update_file_content(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新文件内容（用于代码编辑）"""
    logger.info(f"用户 {current_user.id} 尝试更新文件 {file_id}")
    
    try:
        # 查询文件
        file = db.query(UserFile).filter(
            UserFile.id == file_id,
            UserFile.user_id == current_user.id
        ).first()
        
        if not file:
            logger.warning(f"文件 {file_id} 不存在或不属于用户 {current_user.id}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 只允许编辑文本和代码文件
        editable_extensions = [
            'txt', 'log', 'md', 'json', 'xml', 'yaml', 'yml', 'ini', 'conf', 'config',
            'cpp', 'c', 'h', 'hpp', 'cc', 'cxx', 'js', 'py', 'java', 'css', 'html', 'sh', 'bat', 'sql'
        ]
        file_ext = os.path.splitext(file.original_name)[1].lstrip('.').lower()
        
        if file_ext not in editable_extensions:
            logger.warning(f"文件类型 .{file_ext} 不支持编辑")
            raise HTTPException(status_code=400, detail="此文件类型不支持编辑")
        
        # 解析上传的文件
        form = await request.form()
        uploaded_file = form.get("file")
        
        if not uploaded_file:
            raise HTTPException(status_code=400, detail="未提供更新内容")
        
        # 读取新内容
        new_content = await uploaded_file.read()
        
        logger.info(f"读取新文件内容，大小: {len(new_content)} 字节")
        
        # 备份原文件（可选）
        backup_path = f"{file.save_path}.backup"
        if os.path.exists(file.save_path):
            try:
                import shutil
                shutil.copy2(file.save_path, backup_path)
                logger.info(f"已创建备份文件: {backup_path}")
            except Exception as e:
                logger.warning(f"创建备份失败: {str(e)}")
        
        # 写入新内容
        try:
            with open(file.save_path, "wb") as f:
                f.write(new_content)
            
            logger.info(f"文件 {file_id} 更新成功，新大小: {len(new_content)} 字节")
            
            # 更新数据库中的文件大小
            file.file_size = len(new_content)
            db.commit()
            
            logger.info(f"数据库记录已更新")
            
            return {
                "message": "文件更新成功",
                "file_id": file.id,
                "file_name": file.original_name,
                "new_size": len(new_content)
            }
        except Exception as e:
            logger.error(f"写入文件失败: {str(e)}")
            # 尝试从备份恢复
            if os.path.exists(backup_path):
                try:
                    import shutil
                    shutil.copy2(backup_path, file.save_path)
                    logger.info(f"已从备份恢复文件")
                except Exception as restore_error:
                    logger.error(f"恢复备份失败: {str(restore_error)}")
            
            raise HTTPException(status_code=500, detail=f"文件更新失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文件失败 - 文件ID: {file_id}, 用户ID: {current_user.id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件更新失败: {str(e)}")

# 4. 删除文件
@app.delete("/api/cloud_disk/delete/{file_id}")
async def delete_file_cloud_disk(file_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 使用当前登录用户ID
    user_id = current_user.id
    
    # 查询文件
    file = db.query(UserFile).filter(
        UserFile.id == file_id,
        UserFile.user_id == user_id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 删除文件
    try:
        # 删除物理文件
        if os.path.exists(file.save_path):
            os.remove(file.save_path)
        
        # 删除数据库记录
        db.delete(file)
        db.commit()
        
        return {"message": "文件删除成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")

# ===================== 文件夹管理 API =====================

# 0. 初始化现有文件到根目录
@app.post("/api/cloud_disk/init-folder-structure")
async def init_folder_structure(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将所有现有文件初始化到根目录"""
    try:
        # 获取用户所有没有设置 folder_path 或 folder_path 为空的文件
        files = db.query(UserFile).filter(
            UserFile.user_id == current_user.id,
            (UserFile.folder_path == None) | (UserFile.folder_path == '')
        ).all()
        
        # 将这些文件设置为根目录
        updated_count = 0
        for file in files:
            file.folder_path = '/'
            updated_count += 1
        
        db.commit()
        
        return {
            "message": "文件夹结构初始化成功",
            "updated_files": updated_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")

# 1. 获取文件夹树结构
@app.get("/api/cloud_disk/folders")
async def get_folder_structure(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的文件夹树结构"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权访问其他用户的文件")
    
    # 查询用户的所有文件
    files = db.query(UserFile).filter(
        UserFile.user_id == user_id
    ).all()
    
    # 构建文件夹树结构
    folders = {}
    for file in files:
        folder = file.folder_path
        if folder not in folders:
            folders[folder] = []
        folders[folder].append({
            "id": file.id,
            "name": file.original_name,
            "size": file.file_size,
            "type": file.file_type,
            "upload_time": file.upload_time.isoformat(),
            "file_uuid": file.file_uuid
        })
    
    return {
        "folders": sorted(folders.keys()),
        "files_by_folder": folders
    }

# 2. 创建文件夹
@app.post("/api/cloud_disk/create-folder")
async def create_folder(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新文件夹（虚拟文件夹）"""
    data = await request.json()
    folder_path = data.get("folder_path", "/").strip()
    
    if not folder_path:
        raise HTTPException(status_code=400, detail="文件夹路径不能为空")
    
    # 确保路径以/开头和结尾
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path
    if not folder_path.endswith('/'):
        folder_path = folder_path + '/'
    
    try:
        # 检查文件夹是否已存在
        existing_folder = db.query(UserFolder).filter(
            UserFolder.user_id == current_user.id,
            UserFolder.folder_path == folder_path
        ).first()
        
        if existing_folder:
            return {
                "message": "文件夹已存在",
                "folder_path": folder_path
            }
        
        # 创建新文件夹记录
        new_folder = UserFolder(
            user_id=current_user.id,
            folder_path=folder_path
        )
        db.add(new_folder)
        db.commit()
        
        logger.info(f"用户 {current_user.id} 创建文件夹: {folder_path}")
        
        return {
            "message": "文件夹创建成功",
            "folder_path": folder_path
        }
    except Exception as e:
        db.rollback()
        logger.error(f"创建文件夹失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建文件夹失败: {str(e)}")

# 3. 删除文件夹
@app.post("/api/cloud_disk/delete-folder")
async def delete_folder(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除文件夹及其内的所有文件"""
    logger.info(f"用户 {current_user.id} 尝试删除文件夹")
    
    try:
        data = await request.json()
        folder_path = data.get("folder_path", "/").strip()
        logger.info(f"要删除的文件夹路径: {folder_path}")
        
        # 验证文件夹路径
        if not folder_path or folder_path == "/" or folder_path == "/root/files":
            logger.warning(f"用户 {current_user.id} 尝试删除根目录")
            raise HTTPException(status_code=400, detail="不能删除根文件夹")
        
        # 查找该文件夹下的所有文件
        files = db.query(UserFile).filter(
            UserFile.user_id == current_user.id,
            UserFile.folder_path.startswith(folder_path)
        ).all()
        
        logger.info(f"找到 {len(files)} 个文件要删除")
        
        # 删除文件
        deleted_count = 0
        for file in files:
            try:
                # 删除磁盘上的文件
                if file.save_path and os.path.exists(file.save_path):
                    os.remove(file.save_path)
                    logger.info(f"已删除文件: {file.save_path}")
            except Exception as e:
                logger.error(f"删除文件 {file.save_path} 失败: {str(e)}")
            
            # 删除数据库记录
            db.delete(file)
            deleted_count += 1
        
        # 删除文件夹记录（从UserFolder表中）
        try:
            # 查询该文件夹及其所有子文件夹
            from models import UserFolder
            
            folders_to_delete = db.query(UserFolder).filter(
                UserFolder.user_id == current_user.id,
                UserFolder.folder_path.startswith(folder_path)
            ).all()
            
            deleted_folder_count = 0
            for folder in folders_to_delete:
                db.delete(folder)
                deleted_folder_count += 1
                logger.info(f"已删除文件夹记录: {folder.folder_path}")
            
            logger.info(f"共删除 {deleted_folder_count} 个文件夹记录")
        except Exception as e:
            logger.warning(f"删除文件夹记录时出错: {str(e)}")
            # 继续执行，不影响删除流程
        
        # 提交事务
        db.commit()
        logger.info(f"文件夹 {folder_path} 删除成功，共删除 {deleted_count} 个文件")
        
        return {
            "message": "文件夹删除成功",
            "deleted_count": deleted_count
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除文件夹失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件夹删除失败: {str(e)}")

# 4. 移动文件到文件夹
@app.put("/api/cloud_disk/move-file")
async def move_file(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """将文件移动到指定文件夹"""
    data = await request.json()
    file_id = data.get("file_id")
    target_folder = data.get("target_folder", "/").strip()
    
    if not file_id:
        raise HTTPException(status_code=400, detail="文件ID不能为空")
    
    if not target_folder.startswith('/'):
        target_folder = '/' + target_folder
    if not target_folder.endswith('/'):
        target_folder = target_folder + '/'
    
    try:
        # 查询文件
        file = db.query(UserFile).filter(
            UserFile.id == file_id,
            UserFile.user_id == current_user.id
        ).first()
        
        if not file:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 更新文件夹路径
        file.folder_path = target_folder
        db.commit()
        db.refresh(file)
        
        return {"message": "文件移动成功", "file": file.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"文件移动失败: {str(e)}")

# 5. 重命名文件夹
@app.put("/api/cloud_disk/rename-folder")
async def rename_folder(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重命名文件夹"""
    data = await request.json()
    old_path = data.get("old_path", "/").strip()
    new_name = data.get("new_name", "").strip()
    
    if not new_name:
        raise HTTPException(status_code=400, detail="新文件夹名称不能为空")
    
    if not old_path.startswith('/'):
        old_path = '/' + old_path
    
    # 构建新路径
    parent_path = '/'.join(old_path.rstrip('/').split('/')[:-1]) or '/'
    if not parent_path.endswith('/'):
        parent_path = parent_path + '/'
    new_path = parent_path + new_name + '/'
    
    try:
        # 查找该文件夹下的所有文件
        files = db.query(UserFile).filter(
            UserFile.user_id == current_user.id,
            UserFile.folder_path.startswith(old_path)
        ).all()
        
        # 更新所有文件的文件夹路径
        for file in files:
            # 将旧路径替换为新路径
            new_file_path = file.folder_path.replace(old_path, new_path, 1)
            file.folder_path = new_file_path
        
        db.commit()
        return {"message": "文件夹重命名成功", "new_path": new_path}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"文件夹重命名失败: {str(e)}")

# 翻译相关API
@app.post("/api/ask/translate")
async def translate_text(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """翻译文本接口，强制要求用户认证后才能使用"""
    # 强制认证：如果没有通过认证，get_current_user会抛出401错误
    # 记录成功认证的用户信息
    logger.info(f"用户 {current_user.id}({current_user.username}) 已成功认证并尝试翻译文本")
    
    try:
        # 解析请求体
        data = await request.json()
        question = data.get("question", "")
        
        if not question:
            raise HTTPException(status_code=400, detail="翻译内容不能为空")

        # 调用豆包 API 进行翻译
        try:
            client = OpenAI(
                api_key=(settings.DEEPSEEK_API_KEY or "").strip(),
                base_url="  https://api.deepseek.com/v1"
            )
            # 正确格式：messages应该是一个消息对象数组
            messages = [
                {"role": "user", "content": question}
            ]
            response = client.chat.completions.create(
                model='deepseek-chat',
                messages=messages,
                temperature=0.7,
                max_tokens=int(MAX_TOKEN),
            )
            response_content = response.choices[0].message.content.strip()
            logger.info(f"用户 {current_user.id} 翻译请求处理成功")
        except Exception as api_err:
            logger.error(f"deepseek翻译 API 调用失败: {api_err}")
            response_content = f"翻译结果：这是对 '{question[:20]}...' 的翻译内容"
        return {
            "content": response_content,
            "session_id": data.get("session_id", "translate_session_" + str(uuid.uuid4()))
        }
    except HTTPException:
        # 重新抛出HTTPException以保持原有错误处理
        raise
    except Exception as e:
        logger.error(f"用户 {current_user.id} 翻译请求处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="翻译服务暂时不可用，请稍后再试")

# 笔记相关API
# 1. 创建/更新笔记
@app.post("/api/notes/save")
async def save_note(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"用户 {current_user.id} 尝试保存笔记")
    
    try:
        # 解析请求体
        data = await request.json()
        title = data.get("title", "").strip()
        content = data.get("content", "")
        note_id = data.get("id")  # 用于更新现有笔记
        
        # 验证标题
        if not title:
            raise HTTPException(status_code=400, detail="笔记标题不能为空")
        
        # 生成文件名（使用UUID确保唯一性）
        file_uuid = str(uuid.uuid4())
        filename = f"{file_uuid}.txt"
        
        # 获取用户笔记文件夹路径
        note_path = NoteManager.get_note_file_path(current_user.id, filename)
        
        # 保存笔记内容到文件
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        if note_id:
            # 更新现有笔记
            note = db.query(Note).filter(
                Note.id == note_id,
                Note.user_id == current_user.id
            ).first()
            
            if note:
                # 如果文件路径变了，删除旧文件
                if note.file_path != note_path and os.path.exists(note.file_path):
                    try:
                        os.remove(note.file_path)
                    except Exception as e:
                        logger.error(f"删除旧笔记文件失败: {str(e)}")
                
                note.title = title
                note.file_path = note_path
                note.updated_at = datetime.now()
                db.commit()
                db.refresh(note)
                return note.to_dict()
            else:
                raise HTTPException(status_code=404, detail="笔记不存在")
        else:
            # 创建新笔记
            new_note = Note(
                title=title,
                file_path=note_path,
                user_id=current_user.id
            )
            db.add(new_note)
            db.commit()
            db.refresh(new_note)
            
            return new_note.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"保存笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存笔记失败: {str(e)}")

# 2. 获取笔记列表
@app.get("/api/notes/list")
async def get_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 查询用户的所有笔记，按更新时间倒序排列
    notes = db.query(Note).filter(
        Note.user_id == current_user.id
    ).order_by(desc(Note.updated_at)).all()
    
    return {
        "notes": [note.to_dict() for note in notes]
    }

# 3. 获取笔记内容
@app.get("/api/notes/{note_id}")
async def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 查询笔记
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    # 检查文件是否存在
    if not os.path.exists(note.file_path):
        raise HTTPException(status_code=404, detail="笔记文件已被删除")
    
    # 读取笔记内容
    try:
        with open(note.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        result = note.to_dict()
        result['content'] = content
        return result
    except Exception as e:
        logger.error(f"读取笔记内容失败: {str(e)}")
        raise HTTPException(status_code=500, detail="读取笔记内容失败")

# 4. 删除笔记
@app.delete("/api/notes/{note_id}")
async def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 查询笔记
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user.id
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    # 删除文件
    try:
        if os.path.exists(note.file_path):
            os.remove(note.file_path)
        
        # 删除数据库记录
        db.delete(note)
        db.commit()
        
        return {"message": "笔记删除成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除笔记失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除笔记失败: {str(e)}")

# 5. 创建新文件
@app.post("/api/cloud_disk/create_file")
async def create_new_file(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"用户 {current_user.id} 尝试创建新文件")
    
    try:
        # 解析表单数据
        form = await request.form()
        file_name = form.get("file_name", "").strip()
        file_type = form.get("file_type", "txt")
        file_content = form.get("file_content", "")
        
        # 验证文件名
        if not file_name:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 验证文件类型
        allowed_types = ["txt", "docx"]
        if file_type not in allowed_types:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        # 确保文件名包含扩展名
        if not file_name.endswith(f".{file_type}"):
            file_name += f".{file_type}"
        
        # 确保用户目录存在
        user_dir = settings.get_cloud_disk_dir_for_user(current_user.id)
        # 目录已在settings方法中确保存在
        
        # 生成文件唯一标识和存储路径
        file_uuid = str(uuid.uuid4())
        stored_filename = f"{file_uuid}.{file_type}"
        save_path = os.path.join(user_dir, stored_filename)
        
        # 保存文件内容
        if file_type == "txt":
            # 对于文本文件，直接写入内容
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(file_content)
        elif file_type == "docx":
            # 对于docx文件，我们需要创建一个简单的docx文件
            # 这里使用一个简化的方法，实际项目中可能需要使用python-docx库
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"[这是一个Word文档占位符]\n{file_content}")
        
        # 计算文件大小
        file_size = os.path.getsize(save_path)
        
        # 确定MIME类型
        mime_type = "text/plain" if file_type == "txt" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        # 保存到数据库
        new_file = UserFile(
            file_uuid=file_uuid,
            original_name=file_name,
            save_path=save_path,
            file_size=file_size,
            file_type=mime_type,
            user_id=current_user.id
        )
        db.add(new_file)
        db.commit()
        
        logger.info(f"文件创建成功: {file_name}，路径: {save_path}")
        
        return {
            "message": "文件创建成功",
            "file_id": new_file.id,
            "file_name": new_file.original_name
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建文件失败: {str(e)}")

# 云盘页面路由
@app.get("/cloud_disk.html")
def get_cloud_disk():
    try:
        # 获取py目录的父目录（项目根目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        template_path = os.path.join(project_root, 'html', 'cloud_disk.html')
        
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="云盘页面不存在")
        
        return FileResponse(template_path)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500, detail="服务器错误")

# 配置静态文件服务
# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
html_dir = os.path.join(project_root, 'html')

# 将/html路径前缀挂载为静态文件目录，支持通过/html/path访问
app.mount("/html", StaticFiles(directory=html_dir, html=True), name="html_static")

# 初始化数据库和检查IPv6支持
init_database()

# 动态注册所有路由，避免循环依赖
def register_all_routes():
    """动态注册所有路由，避免启动时的循环导入问题"""
    logger.info("=" * 60)
    logger.info("开始注册所有API路由...")
    try:
        # 动态导入并注册聊天记录路由
        import importlib
        chat_records = importlib.import_module('chat_records')
        if hasattr(chat_records, 'register_chat_record_routes'):
            chat_records.register_chat_record_routes(app)
            logger.info("聊天记录路由注册成功")
        else:
            logger.error("聊天记录模块缺少register_chat_record_routes函数")
    except Exception as e:
        logger.error(f"注册聊天记录路由失败: {str(e)}")
    
    try:
        # 动态导入并注册语言学习路由
        import importlib
        logger.info("正在导入语言学习模块...")
        language_learning = importlib.import_module('language_learning')
        logger.info(f"语言学习模块导入成功，是否有register_language_learning_routes函数: {hasattr(language_learning, 'register_language_learning_routes')}")
        if hasattr(language_learning, 'register_language_learning_routes'):
            logger.info("开始调用register_language_learning_routes...")
            language_learning.register_language_learning_routes(app)
            logger.info("✓ 语言学习路由注册成功")
            
            # 验证路由是否已注册
            registered_routes = [r.path for r in app.routes if hasattr(r, 'path') and ('vocabulary' in r.path or 'progress' in r.path)]
            logger.info(f"已注册的语言学习相关路由: {registered_routes}")
        else:
            logger.error("✗ 语言学习模块缺少register_language_learning_routes函数")
    except Exception as e:
        logger.error(f"✗ 注册语言学习路由失败: {str(e)}", exc_info=True)
    
    logger.info("=" * 60)
    logger.info("所有API路由注册完成")

# 先注册所有API路由（在模块加载时执行）
logger.info("准备注册API路由...")
register_all_routes()
logger.info("API路由注册函数已调用")

# 为admin.html添加专用路由，确保可以直接访问
@app.get("/admin.html")
def get_admin_page():
    try:
        template_path = os.path.join(html_dir, "admin.html")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="管理员页面不存在")
        return FileResponse(template_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"访问管理员页面时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器错误")

# 为/html/admin.html路径添加路由，支持两种访问方式
@app.get("/html/admin.html")
def get_admin_page_html_prefix():
    """支持通过/html/admin.html路径访问管理员页面"""
    try:
        template_path = os.path.join(html_dir, "admin.html")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="管理员页面不存在")
        return FileResponse(template_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"通过/html/admin.html访问管理员页面时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器错误")

# 云盘页面路由保持不变，确保兼容性
@app.get("/cloud_disk.html")
def get_cloud_disk():
    try:
        template_path = os.path.join(html_dir, "cloud_disk.html")
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="页面不存在")
        return FileResponse(template_path)
    except HTTPException:
        raise
    except:
        raise HTTPException(status_code=500, detail="服务器错误")

# 注册路由器
from routers import user as user_router
app.include_router(user_router.router, prefix="/api/users", tags=["users"])

# 最后挂载静态文件服务（确保API路由优先级更高）
# 将/html路径前缀挂载为静态文件目录，支持通过/html/path访问
# 注意：html_dir已经在前面定义过，这里不需要重复定义
app.mount("/html", StaticFiles(directory=html_dir, html=True), name="html_static")

# 将根路径挂载为静态文件目录，支持直接访问文件
app.mount("/", StaticFiles(directory=html_dir, html=True), name="root_static")


# 单词记忆 Pydantic 模型
class WordCardCreate(BaseModel):
    term: str
    phonetic: Optional[str] = None
    part_of_speech: Optional[str] = None
    definition: Optional[str] = None
    context: Optional[str] = None

class WordCardUpdate(BaseModel):
    is_correct: bool

# 单词记忆路由
@app.get("/remenber.html")
async def get_remenber_page():
    return FileResponse(os.path.join(html_dir, "remenber.html"))

@app.post("/api/words/batch")
async def batch_create_words(
    words: List[WordCardCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = 0
    for w in words:
        # Check if exists
        exists = db.query(WordCard).filter_by(user_id=current_user.id, word=w.term).first()
        if not exists:
            new_word = WordCard(
                user_id=current_user.id,
                word=w.term,
                phonetic=w.phonetic,
                part_of_speech=w.part_of_speech,
                definition=w.definition,
                context=w.context
            )
            db.add(new_word)
            count += 1
    db.commit()
    return {"count": count}

@app.get("/api/words")
async def get_words(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    words = db.query(WordCard).filter_by(user_id=current_user.id).all()
    return [w.to_dict() for w in words]

@app.delete("/api/words/{word_id}")
async def delete_word(
    word_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    word = db.query(WordCard).filter_by(id=word_id, user_id=current_user.id).first()
    if word:
        db.delete(word)
        db.commit()
    return {"success": True}

@app.post("/api/words/{word_id}/rate")
async def rate_word(
    word_id: int,
    update: WordCardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    word = db.query(WordCard).filter_by(id=word_id, user_id=current_user.id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    now = datetime.now(UTC)
    
    if update.is_correct:
        if word.interval < 60000: # < 1 min
             word.interval = 10 * 60000 # 10 mins
        else:
             word.interval = int(word.interval * 2.2)
        word.next_review = now + timedelta(milliseconds=word.interval)
    else:
        word.interval = 10 * 1000 # 10 sec
        word.next_review = now + timedelta(milliseconds=10000)
        
    db.commit()
    return word.to_dict()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="::", port=5000, log_level="info")
