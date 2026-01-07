"""
AI智能学习伴侣导师主程序入口
用于启动FastAPI应用服务器
"""
import uvicorn  
import sys
import os
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 从config.py导入配置
from config import settings

# 从app.py导入FastAPI应用
from app import app

# 确保所有必需的目录存在
settings.ensure_directories()

# 启动服务器
if __name__ == "__main__":
    try:
        # 获取主机和端口配置
        host = settings.HOST
        port = settings.PORT
        reload = settings.DEBUG  # 在调试模式下启用热重载
        
        logger.info(f"服务配置: 主机={host}, 端口={port}, 调试模式={reload}")
        logger.info(f"文档地址: http://{host}:{port}/docs")
        logger.info(f"API地址: http://{host}:{port}/api")
        
        # 启动UVicorn服务器
        logger.info(f"最大文件大小配置: {settings.MAX_FILE_SIZE / (1024 * 1024):.0f}MB")
        
        uvicorn.run(
            "app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            proxy_headers=True,
            forwarded_allow_ips="*",
            timeout_keep_alive=300,  # 增加 keep-alive 超时时间，支持大文件上传
            limit_concurrency=None,  # 不限制并发连接数
        )
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在优雅退出...")
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        sys.exit(1)