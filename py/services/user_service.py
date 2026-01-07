"""
用户服务
处理用户管理相关的业务逻辑
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from models import User, Admin
from schemas.user import UserCreate, UserUpdate, UserResponse
from services.auth_service import auth_service


class UserService:
    """用户服务类"""
    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()
    
    def get_users(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """获取用户列表"""
        query = db.query(User)
        
        # 过滤激活状态
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        # 搜索关键词（用户名或邮箱）
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (User.username.ilike(search_pattern)) | (User.email.ilike(search_pattern))
            )
        
        # 分页并按创建时间降序排列
        return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_user_count(self, db: Session, is_active: Optional[bool] = None) -> int:
        """获取用户总数"""
        query = db.query(User)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        return query.count()
    
    def create_user(self, db: Session, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查邮箱是否已存在
        existing_user = self.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该邮箱已被注册"
            )
        
        # 检查用户名是否已存在
        existing_user = self.get_user_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该用户名已被使用"
            )
        
        # 创建用户
        hashed_password = auth_service.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            is_active=True
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    def update_user(self, db: Session, user_id: int, user_update: UserUpdate) -> User:
        """更新用户信息"""
        # 获取用户
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 准备更新数据
        update_data = user_update.model_dump(exclude_unset=True)
        
        # 如果要更新邮箱，检查是否已存在
        if "email" in update_data and update_data["email"] != user.email:
            existing_user = self.get_user_by_email(db, update_data["email"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该邮箱已被其他用户使用"
                )
        
        # 如果要更新用户名，检查是否已存在
        if "username" in update_data and update_data["username"] != user.username:
            existing_user = self.get_user_by_username(db, update_data["username"])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该用户名已被使用"
                )
        
        # 如果要更新密码，进行哈希处理
        if "password" in update_data:
            update_data["password_hash"] = auth_service.get_password_hash(update_data.pop("password"))
        
        # 更新用户信息
        update_data["updated_at"] = datetime.utcnow()
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return user
    
    def deactivate_user(self, db: Session, user_id: int) -> User:
        """禁用用户"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已被禁用"
            )
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return user
    
    def activate_user(self, db: Session, user_id: int) -> User:
        """启用用户"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已被启用"
            )
        
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return user
    
    def delete_user(self, db: Session, user_id: int) -> bool:
        """删除用户（软删除）"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 软删除：禁用用户
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.commit()
        
        return True
    
    def get_user_stats(self, db: Session, user_id: int) -> Dict[str, Any]:
        """获取用户统计信息"""
        user = self.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 导入相关模型以避免循环导入
        from models import ChatSession, Resource, UserFile, Collection, Feedback
        
        # 获取统计数据
        chat_count = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        ).count()
        
        resource_count = db.query(Resource).filter(Resource.user_id == user_id).count()
        file_count = db.query(UserFile).filter(UserFile.user_id == user_id).count()
        collection_count = db.query(Collection).filter(Collection.user_id == user_id).count()
        feedback_count = db.query(Feedback).filter(Feedback.user_id == user_id).count()
        
        return {
            "user_id": user_id,
            "username": user.username,
            "total_chats": chat_count,
            "total_resources": resource_count,
            "total_files": file_count,
            "total_collections": collection_count,
            "total_feedbacks": feedback_count,
            "member_since": user.created_at,
            "last_login": user.last_login,
            "is_active": user.is_active
        }
    
    def is_admin(self, db: Session, user_id: int) -> bool:
        """检查用户是否为管理员"""
        admin = db.query(Admin).filter(Admin.user_id == user_id).first()
        return admin is not None
    
    def is_superadmin(self, db: Session, user_id: int) -> bool:
        """检查用户是否为超级管理员"""
        admin = db.query(Admin).filter(Admin.user_id == user_id).first()
        return admin is not None and admin.is_superadmin


# 创建全局的用户服务实例
user_service = UserService()