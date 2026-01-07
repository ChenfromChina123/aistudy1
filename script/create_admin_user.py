#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建系统管理员用户脚本
基于FastAPI框架，与主应用模型保持一致
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, UTC
import os
import logging
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 数据库配置 - 与主应用保持一致
DATABASE_URL = os.getenv('DATABASE_URL') or 'mysql+pymysql://root:123456@localhost/ipv6_education'
logger.info(f"使用数据库URL: {DATABASE_URL}")

# 初始化SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 定义User模型 - 与主应用完全一致
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    def set_password(self, password: str):
        """设置用户密码（哈希加密）"""
        if len(password) < 6 or len(password) > 20:
            raise ValueError("密码长度需在6-20字符之间")
        self.password_hash = generate_password_hash(password)
    
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

# 定义Admin模型 - 与主应用完全一致
class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, comment='用户ID')
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    created_at = Column(DateTime, default=datetime.now(UTC), comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), comment='更新时间')
    
    # 建立与用户的关联
    user = relationship('User', backref='admin_role')

# 创建或更新管理员用户的函数
def create_or_update_admin():
    # 创建所有数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建/检查完成")
    
    db = SessionLocal()
    try:
        # 检查是否已存在admin用户
        existing_user = db.query(User).filter_by(username='admin').first()
        
        if existing_user:
            # 更新现有管理员用户的密码和邮箱
            existing_user.set_password('admin123')
            existing_user.email = 'admin@example.com'
            existing_user.updated_at = datetime.now(UTC)
            db.commit()
            logger.info('管理员用户 "admin" 密码已重置！')
            user_id = existing_user.id
        else:
            # 创建新的管理员用户
            admin_user = User(
                username='admin',
                email='admin@example.com',
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            
            # 设置密码为'admin'
            admin_user.set_password('admin')
            
            # 添加到数据库并提交
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            user_id = admin_user.id
            logger.info('管理员用户 "admin" 创建成功！')
        
        # 检查管理员角色是否存在
        existing_admin = db.query(Admin).filter_by(user_id=user_id).first()
        
        if not existing_admin:
            # 创建管理员角色记录
            admin_role = Admin(
                user_id=user_id,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            db.add(admin_role)
            db.commit()
            logger.info(f'为用户ID {user_id} 创建管理员角色成功！')
        else:
            # 确保管理员角色处于激活状态
            if not existing_admin.is_active:
                existing_admin.is_active = True
                existing_admin.updated_at = datetime.now(UTC)
                db.commit()
                logger.info(f'管理员角色已激活')
        
        # 输出成功信息
        print('=' * 60)
        print('管理员用户创建/更新成功！')
        print('用户名: admin')
        print('密码: admin')
        print('邮箱: admin@example.com')
        print('=' * 60)
        print('注意：请在首次登录后立即修改默认密码以提高安全性！')
        
    except ValueError as e:
        db.rollback()
        logger.error(f"密码设置错误: {str(e)}")
        print(f"错误: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"创建管理员用户时发生错误: {str(e)}")
        print(f"创建管理员失败: {str(e)}")
    finally:
        db.close()
        logger.info("数据库会话已关闭")

# 执行创建或更新管理员用户的函数
if __name__ == '__main__':
    logger.info("开始创建/更新管理员用户...")
    create_or_update_admin()
    logger.info("管理员创建/更新脚本执行完成")

# 注意事项：
# 1. 此脚本使用与主应用相同的数据库模型和配置
# 2. 会同时创建/更新用户表和管理员角色表
# 3. 生产环境中请务必修改默认密码
# 4. 确保数据库连接配置正确
# 5. 如果遇到权限问题，请检查数据库用户权限