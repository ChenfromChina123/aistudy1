"""
数据库迁移脚本：为users表添加avatar字段
"""
import pymysql
import os
from config import settings
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

def migrate_add_avatar_field():
    """添加avatar字段到users表"""
    try:
        # 加载环境变量
        load_dotenv()
        
        # 从环境变量或配置获取数据库URL
        db_url = os.getenv('DATABASE_URL') or settings.DATABASE_URL
        
        print("=" * 60)
        print("开始数据库迁移：添加avatar字段")
        print("=" * 60)
        print(f"[INFO] 使用数据库URL: {db_url.split('@')[0]}@***")  # 隐藏密码部分
        
        # 解析数据库连接URL
        # 格式: mysql+pymysql://user:password@host:port/database
        if db_url.startswith('mysql+pymysql://'):
            db_url = db_url.replace('mysql+pymysql://', 'mysql://')
        
        parsed = urlparse(db_url)
        
        # 提取连接参数并进行URL解码
        host = parsed.hostname or 'localhost'
        port = parsed.port or 3306
        user = unquote(parsed.username) if parsed.username else 'root'
        password = unquote(parsed.password) if parsed.password else ''
        database = parsed.path.lstrip('/') if parsed.path else 'ipv6_education'
        
        print(f"[INFO] 连接参数: host={host}, port={port}, user={user}, database={database}")
        print(f"[DEBUG] 原始密码字段: {parsed.password}")
        print(f"[DEBUG] 解码后密码长度: {len(password) if password else 0}")
        
        # 连接数据库
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        print("[OK] 数据库连接成功")
        
        # 获取数据库名（用于检查字段）
        database_name = database
        
        # 检查avatar字段是否已存在
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'avatar'
        """, (database_name,))
        
        result = cursor.fetchone()
        
        if result[0] > 0:
            print("[INFO] avatar字段已存在，跳过迁移")
        else:
            # 添加avatar字段
            print("[INFO] 正在添加avatar字段...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN avatar VARCHAR(255) NULL 
                COMMENT '用户头像URL/路径' 
                AFTER password_hash
            """)
            print("[OK] avatar字段添加成功")
        
        # 提交更改
        conn.commit()
        print("[OK] 数据库迁移完成！")
        
    except pymysql.Error as err:
        print(f"[ERROR] 数据库错误: {err}")
        print(f"[ERROR] 错误代码: {err.args[0] if err.args else 'Unknown'}")
        if 'conn' in locals():
            conn.rollback()
        raise
    except Exception as e:
        print(f"[ERROR] 发生错误: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
            print("[INFO] 数据库游标已关闭")
        if 'conn' in locals():
            conn.close()
            print("[INFO] 数据库连接已关闭")

def print_usage():
    """打印使用说明"""
    print("=" * 60)
    print("用户头像功能 - 数据库迁移")
    print("=" * 60)
    print()
    print("此脚本将为users表添加avatar字段")
    print()
    print("环境变量配置:")
    print("  DATABASE_URL - 数据库连接URL")
    print("  格式: mysql+pymysql://user:password@host:port/database")
    print()
    print("示例:")
    print("  export DATABASE_URL='mysql+pymysql://root:123456@localhost/ipv6_education'")
    print("  python migrate_add_avatar.py")
    print()

if __name__ == "__main__":
    print_usage()
    
    # 检查环境变量
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("[WARNING] 未设置DATABASE_URL环境变量，将使用config.py中的默认配置")
        print()
    
    try:
        migrate_add_avatar_field()
        print()
        print("=" * 60)
        print("✓ 迁移成功完成！")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ 迁移失败: {e}")
        print("=" * 60)
        print()
        print("故障排除建议:")
        print("1. 检查数据库连接参数是否正确")
        print("2. 确保数据库服务正在运行")
        print("3. 验证用户权限是否足够")
        print("4. 检查数据库是否存在")
        exit(1)

