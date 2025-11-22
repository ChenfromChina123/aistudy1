"""
项目配置管理模块
统一管理所有配置项，从环境变量读取
"""
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_FILE)


class Settings:
    """应用配置类"""
    
    # ============ 数据库配置 ============
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:123456@localhost/ipv6_education'
    )
    
    # ============ JWT配置 ============
    JWT_SECRET_KEY: str = os.getenv(
        'JWT_SECRET_KEY',
        'default_development_key_change_in_production'
    )
    JWT_EXPIRE_SECONDS: int = int(os.getenv('JWT_EXPIRE_SECONDS', '7200'))  # 2小时
    
    # ============ AI模型配置 ============
    DEEPSEEK_API_KEY: Optional[str] = os.getenv('DEEPSEEK_API_KEY')
    DOUBAO_KEY: Optional[str] = os.getenv('DOUBAO_KEY')
    DOUBAO_BASEURL: str = os.getenv(
        'DOUBAO_BASEURL',
        'https://api.doubao.com/v1'
    )
    MAX_TOKEN: int = int(os.getenv('MAX_TOKEN', '4096'))
    
    # ============ 文件配置 ============
    # 使用项目根目录的相对路径
    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = BASE_DIR / 'uploads'
    CLOUD_DISK_DIR: Path = BASE_DIR / 'cloud_disk'
    # 支持环境变量配置，默认500MB（适合视频文件）
    MAX_FILE_SIZE: int = int(os.getenv('MAX_FILE_SIZE', str(500 * 1024 * 1024)))  # 500MB
    NOTES_FOLDER_NAME: str = 'notes'
    
    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = {
        # 图片
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp',
        # 文本文件
        'txt', 'md', 'csv', 'json', 'xml', 'html', 'css', 'js',
        # 文档
        'doc', 'docx', 'pdf', 'rtf',
        # 表格
        'xls', 'xlsx',
        # 演示文稿
        'ppt', 'pptx',
        # 视频
        'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv',
        # 压缩包
        'zip', 'rar', '7z', 'tar', 'gz'
    }
    
    # ============ 邮件配置 ============
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.qq.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SENDER_EMAIL: Optional[str] = os.getenv('SENDER_EMAIL', '3301767269@qq.com')
    SENDER_PASSWORD: Optional[str] = os.getenv('SENDER_PASSWORD', 'dinasyxqstbodbej')
    USE_SSL: bool = os.getenv('USE_SSL', 'False').lower() == 'true'
    
    # ============ 服务器配置 ============
    HOST: str = os.getenv('HOST', '::')
    PORT: int = int(os.getenv('PORT', '5000'))
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    RELOAD: bool = os.getenv('RELOAD', 'True').lower() == 'true'
    
    # ============ 应用配置 ============
    APP_NAME: str = 'AI智能学习导师'
    APP_VERSION: str = '8.1'
    APP_DESCRIPTION: str = '基于IPv6的AI智能学习助手'
    
    # ============ 验证码配置 ============
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 5
    
    # ============ 消息常量 ============
    USER_SENDER: int = 1
    AI_SENDER: int = 2
    
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.CLOUD_DISK_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls) -> list:
        """
        验证配置是否完整
        返回缺失的配置项列表
        """
        missing = []
        
        if not cls.DEEPSEEK_API_KEY and not cls.DOUBAO_KEY:
            missing.append('至少需要配置一个AI模型的API密钥 (DEEPSEEK_API_KEY 或 DOUBAO_KEY)')
        
        if cls.JWT_SECRET_KEY == 'default_development_key_change_in_production':
            missing.append('警告: 使用默认JWT密钥，生产环境请更改 JWT_SECRET_KEY')
        
        return missing
    
    @classmethod
    def get_upload_dir_for_user(cls, user_id: int) -> Path:
        """获取指定用户的上传目录"""
        user_dir = cls.UPLOAD_DIR / f'user_{user_id}'
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    @classmethod
    def get_cloud_disk_dir_for_user(cls, user_id: int) -> Path:
        """获取指定用户的云盘目录"""
        user_dir = cls.CLOUD_DISK_DIR / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    @classmethod
    def get_notes_dir_for_user(cls, user_id: int) -> Path:
        """获取指定用户的笔记目录"""
        user_dir = cls.get_cloud_disk_dir_for_user(user_id)
        notes_dir = user_dir / cls.NOTES_FOLDER_NAME
        notes_dir.mkdir(parents=True, exist_ok=True)
        return notes_dir


# 创建全局配置实例
settings = Settings()

# 确保目录存在
settings.ensure_directories()

# 验证配置
if __name__ == '__main__':
    missing_configs = settings.validate()
    if missing_configs:
        print("配置验证警告:")
        for config in missing_configs:
            print(f"  - {config}")
    else:
        print("配置验证通过 ✓")

