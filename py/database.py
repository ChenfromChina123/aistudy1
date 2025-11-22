"""数据库初始化模块"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

from config import settings

logger = logging.getLogger(__name__)

# 使用统一配置
DATABASE_URL = settings.DATABASE_URL
logger.info(f"使用数据库URL: {DATABASE_URL}")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 连接池预检查
    pool_size=10,        # 连接池大小
    max_overflow=20      # 最大溢出连接数
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_user_favorites_if_needed():
    """初始化用户收藏表（如果需要）"""
    try:
        # 确保所有表都已创建
        Base.metadata.create_all(bind=engine)
        logger.info("用户收藏表检查完成")
    except Exception as e:
        logger.error(f"初始化用户收藏表时出错: {str(e)}")


def init_db():
    """初始化数据库，创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建/检查完成")
    except Exception as e:
        logger.error(f"创建数据库表时出错: {str(e)}")
        raise