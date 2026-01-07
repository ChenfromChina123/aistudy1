import pymysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接信息
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_NAME = 'ipv6_education'
DB_HOST = 'localhost'

def migrate_verification_code_table():
    """
    向verification_codes表添加缺失的字段
    """
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        # 检查并添加is_blocked字段
        cursor.execute("SHOW COLUMNS FROM verification_codes LIKE 'is_blocked'")
        result = cursor.fetchone()
        if not result:
            cursor.execute("ALTER TABLE verification_codes ADD COLUMN is_blocked BOOLEAN NOT NULL DEFAULT FALSE")
            print("✓ 已添加is_blocked字段")
        else:
            print("✓ is_blocked字段已存在")
        
        # 检查并添加blocked_until字段
        cursor.execute("SHOW COLUMNS FROM verification_codes LIKE 'blocked_until'")
        result = cursor.fetchone()
        if not result:
            cursor.execute("ALTER TABLE verification_codes ADD COLUMN blocked_until DATETIME NULL")
            print("✓ 已添加blocked_until字段")
        else:
            print("✓ blocked_until字段已存在")
        
        # 提交更改
        conn.commit()
        print("✓ 数据库迁移完成！")
        
    except pymysql.Error as err:
        print(f"✗ 数据库错误: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("开始数据库迁移...")
    migrate_verification_code_table()