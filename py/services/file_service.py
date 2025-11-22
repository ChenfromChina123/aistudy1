"""
文件服务
处理文件上传、下载和分享等业务逻辑
"""
from typing import Optional, List, Dict, Any, BinaryIO
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
import os
import shutil
import uuid
import secrets
from datetime import datetime, timedelta
import mimetypes

from models import UserFile, FileShare
from schemas.file import (
    UserFileUpload, UserFileUpdate, UserFileResponse,
    FileShareCreate, FileShareResponse, FileSearchParams
)
from config import settings
from services.user_service import user_service


class FileService:
    """文件服务类"""
    
    def __init__(self):
        # 确保上传目录存在
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    def get_file_by_id(self, db: Session, file_id: int) -> Optional[UserFile]:
        """根据ID获取文件"""
        return db.query(UserFile).filter(UserFile.id == file_id).first()
    
    def get_file_by_path(self, file_path: str) -> Optional[UserFile]:
        """根据文件路径获取文件信息"""
        # 注意：这个方法需要在事务中调用
        from database import SessionLocal
        db = SessionLocal()
        try:
            return db.query(UserFile).filter(UserFile.file_path == file_path).first()
        finally:
            db.close()
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """生成唯一的文件名"""
        # 获取文件扩展名
        ext = os.path.splitext(original_filename)[1]
        # 生成唯一文件名
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{unique_id}{ext}"
    
    def save_upload_file(self, upload_file: UploadFile, user_id: int) -> Dict[str, Any]:
        """保存上传的文件到磁盘"""
        # 验证文件大小
        file_size = 0
        contents = upload_file.file.read()
        file_size = len(contents)
        upload_file.file.seek(0)  # 重置文件指针
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超过限制，最大允许 {settings.MAX_FILE_SIZE // (1024 * 1024)}MB"
            )
        
        # 验证文件类型
        content_type = upload_file.content_type or mimetypes.guess_type(upload_file.filename)[0]
        if content_type and not self.is_allowed_file_type(content_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支持的文件类型"
            )
        
        # 生成唯一文件名
        unique_filename = self.generate_unique_filename(upload_file.filename)
        
        # 创建用户目录
        user_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(user_dir, unique_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        # 生成相对路径（存储到数据库）
        relative_path = os.path.join(str(user_id), unique_filename)
        
        return {
            "filename": upload_file.filename,
            "content_type": content_type,
            "file_size": file_size,
            "file_path": relative_path,
            "absolute_path": file_path
        }
    
    def is_allowed_file_type(self, content_type: str) -> bool:
        """检查文件类型是否允许"""
        # 允许的文件类型列表
        allowed_types = settings.ALLOWED_FILE_TYPES
        
        # 如果没有限制，则允许所有类型
        if not allowed_types:
            return True
        
        # 检查是否在允许的类型中
        for allowed_type in allowed_types:
            # 支持通配符，如 "image/*"
            if allowed_type.endswith("/*"):
                base_type = allowed_type[:-2]
                if content_type.startswith(base_type):
                    return True
            elif content_type == allowed_type:
                return True
        
        return False
    
    def upload_file(
        self, 
        db: Session, 
        upload_file: UploadFile, 
        file_data: UserFileUpload, 
        user_id: int
    ) -> UserFile:
        """上传文件"""
        try:
            # 保存文件到磁盘
            file_info = self.save_upload_file(upload_file, user_id)
            
            # 创建文件记录
            db_file = UserFile(
                user_id=user_id,
                filename=file_info["filename"],
                content_type=file_info["content_type"],
                file_size=file_info["file_size"],
                file_path=file_info["file_path"],
                description=file_data.description,
                is_private=file_data.is_private
            )
            
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            
            return db_file
            
        except HTTPException:
            raise
        except Exception as e:
            # 如果数据库操作失败，删除已上传的文件
            if "absolute_path" in locals() and os.path.exists(local_file_info["absolute_path"]):
                os.remove(local_file_info["absolute_path"])
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件上传失败"
            )
    
    def update_file(
        self, 
        db: Session, 
        file_id: int, 
        file_update: UserFileUpdate, 
        user_id: int
    ) -> UserFile:
        """更新文件信息"""
        # 获取文件
        db_file = self.get_file_by_id(db, file_id)
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 检查权限
        if db_file.user_id != user_id and not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改该文件"
            )
        
        # 准备更新数据
        update_data = file_update.model_dump(exclude_unset=True)
        
        # 更新文件信息
        update_data["updated_at"] = datetime.utcnow()
        for field, value in update_data.items():
            setattr(db_file, field, value)
        
        db.commit()
        db.refresh(db_file)
        
        return db_file
    
    def delete_file(self, db: Session, file_id: int, user_id: int) -> bool:
        """删除文件"""
        # 获取文件
        db_file = self.get_file_by_id(db, file_id)
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 检查权限
        if db_file.user_id != user_id and not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除该文件"
            )
        
        # 获取文件的绝对路径
        absolute_path = os.path.join(settings.UPLOAD_DIR, db_file.file_path)
        
        # 删除文件记录
        db.delete(db_file)
        
        # 删除相关的分享记录
        db.query(FileShare).filter(FileShare.file_id == file_id).delete()
        
        db.commit()
        
        # 删除磁盘上的文件
        if os.path.exists(absolute_path):
            try:
                os.remove(absolute_path)
            except Exception:
                # 文件删除失败不影响数据库操作
                pass
        
        return True
    
    def get_user_files(
        self, 
        db: Session, 
        user_id: int,
        params: Optional[FileSearchParams] = None,
        skip: int = 0, 
        limit: int = 20
    ) -> List[UserFile]:
        """获取用户的文件列表"""
        query = db.query(UserFile).filter(UserFile.user_id == user_id)
        
        # 应用搜索参数
        if params:
            if params.keyword:
                search_pattern = f"%{params.keyword}%"
                query = query.filter(
                    (UserFile.filename.ilike(search_pattern)) | 
                    (UserFile.description.ilike(search_pattern))
                )
            
            if params.content_type:
                query = query.filter(UserFile.content_type == params.content_type)
            
            if params.min_size is not None:
                query = query.filter(UserFile.file_size >= params.min_size)
            
            if params.max_size is not None:
                query = query.filter(UserFile.file_size <= params.max_size)
            
            if params.is_private is not None:
                query = query.filter(UserFile.is_private == params.is_private)
            
            # 排序
            order_field = getattr(UserFile, params.sort_by, UserFile.created_at)
            if params.order == "asc":
                query = query.order_by(order_field.asc())
            else:
                query = query.order_by(order_field.desc())
        else:
            # 默认按创建时间降序排序
            query = query.order_by(UserFile.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def share_file(
        self, 
        db: Session, 
        share_data: FileShareCreate, 
        user_id: int
    ) -> FileShare:
        """分享文件"""
        # 检查文件是否存在且属于该用户
        db_file = self.get_file_by_id(db, share_data.file_id)
        if not db_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        if db_file.user_id != user_id and not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权分享该文件"
            )
        
        # 生成访问码
        access_code = secrets.token_urlsafe(16)
        
        # 创建分享记录
        db_share = FileShare(
            file_id=share_data.file_id,
            user_id=user_id,
            share_type=share_data.share_type,
            access_code=access_code,
            password=share_data.password,
            expires_at=share_data.expires_at,
            max_downloads=share_data.max_downloads,
            current_downloads=0,
            is_active=True
        )
        
        db.add(db_share)
        db.commit()
        db.refresh(db_share)
        
        # 生成分享链接
        share_link = f"/api/files/share/{access_code}"
        db_share.share_link = share_link
        db.commit()
        
        return db_share
    
    def get_share_by_access_code(
        self, 
        db: Session, 
        access_code: str
    ) -> Optional[FileShare]:
        """根据访问码获取分享信息"""
        return db.query(FileShare).filter(
            FileShare.access_code == access_code,
            FileShare.is_active == True
        ).first()
    
    def verify_share_access(
        self, 
        db: Session, 
        access_code: str, 
        password: Optional[str] = None
    ) -> UserFile:
        """验证分享访问权限"""
        # 获取分享记录
        share = self.get_share_by_access_code(db, access_code)
        if not share:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分享链接不存在或已失效"
            )
        
        # 检查是否过期
        if share.expires_at and datetime.utcnow() > share.expires_at:
            share.is_active = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="分享链接已过期"
            )
        
        # 检查下载次数限制
        if share.max_downloads and share.current_downloads >= share.max_downloads:
            share.is_active = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="分享链接已达到最大下载次数"
            )
        
        # 验证密码
        if share.share_type == "password":
            if not password or password != share.password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="密码错误"
                )
        
        # 获取文件
        db_file = self.get_file_by_id(db, share.file_id)
        if not db_file:
            # 如果文件不存在，禁用分享
            share.is_active = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分享的文件不存在"
            )
        
        # 增加下载次数
        share.current_downloads += 1
        db.commit()
        
        return db_file
    
    def revoke_share(self, db: Session, share_id: int, user_id: int) -> bool:
        """撤销文件分享"""
        # 获取分享记录
        share = db.query(FileShare).filter(FileShare.id == share_id).first()
        if not share:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分享记录不存在"
            )
        
        # 检查权限
        if share.user_id != user_id and not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权撤销该分享"
            )
        
        # 禁用分享
        share.is_active = False
        db.commit()
        
        return True


# 创建全局的文件服务实例
file_service = FileService()