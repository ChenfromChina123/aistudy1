"""
数据库迁移执行脚本
用于创建custom_ai_models表
"""
import pymysql
from config import settings
import sys

def parse_database_url(url: str):
    """解析数据库URL"""
    # mysql+pymysql://user:password@host/database
    parts = url.replace('mysql+pymysql://', '').split('@')
    user_pass = parts[0].split(':')
    host_db = parts[1].split('/')
    
    return {
        'user': user_pass[0],
        'password': user_pass[1],
        'host': host_db[0],
        'database': host_db[1]
    }

def run_migration():
    """执行数据库迁移"""
    # 解析数据库连接信息
    db_info = parse_database_url(settings.DATABASE_URL)
    
    print(f"连接到数据库: {db_info['database']} @ {db_info['host']}")
    
    # 读取SQL文件
    sql_file = 'py/migrations/add_custom_ai_models_table.sql'
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 连接数据库
    connection = pymysql.connect(
        host=db_info['host'],
        user=db_info['user'],
        password=db_info['password'],
        database=db_info['database'],
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # 执行SQL
            print("正在创建custom_ai_models表...")
            cursor.execute(sql_content)
            connection.commit()
            print("✓ 表创建成功！")
            
            # 验证表是否存在
            cursor.execute("SHOW TABLES LIKE 'custom_ai_models'")
            result = cursor.fetchone()
            if result:
                print("✓ 验证成功：custom_ai_models表已存在")
                
                # 显示表结构
                cursor.execute("DESC custom_ai_models")
                columns = cursor.fetchall()
                print("\n表结构:")
                for col in columns:
                    print(f"  {col[0]}: {col[1]}")
            else:
                print("✗ 验证失败：表未创建")
                sys.exit(1)
                
    except pymysql.Error as e:
        print(f"✗ 迁移失败: {e}")
        connection.rollback()
        sys.exit(1)
    finally:
        connection.close()
    
    print("\n数据库迁移完成！")

if __name__ == '__main__':
    run_migration()

