"""
数据库迁移脚本 - 为 files 表添加 folder_path 列
执行时间: 2025-11-11
目的: 支持云盘文件夹管理功能
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from urllib.parse import urlparse, unquote

# 加载环境变量
load_dotenv()

def get_db_connection():
    """获取数据库连接"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise Exception("未找到DATABASE_URL环境变量，请检查.env文件配置")
    
    print(f"[INFO] 使用数据库URL: {db_url.split('@')[0]}@***")
    
    # 处理不同格式的URL
    if db_url.startswith('mysql+pymysql://'):
        db_url = db_url.replace('mysql+pymysql://', 'mysql+pymysql://')
    
    engine = create_engine(db_url)
    return engine

def column_exists(inspector, table_name, column_name):
    """检查列是否存在"""
    if table_name not in inspector.get_table_names():
        return False
    
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_folder_path_column():
    """为 files 表添加 folder_path 列"""
    print("\n" + "="*60)
    print("开始数据库迁移：添加 folder_path 列")
    print("="*60)
    
    try:
        engine = get_db_connection()
        inspector = inspect(engine)
        
        # 检查表是否存在
        if 'files' not in inspector.get_table_names():
            print("[ERROR] 表 'files' 不存在")
            return False
        
        # 检查列是否已存在
        if column_exists(inspector, 'files', 'folder_path'):
            print("[INFO] 列 'folder_path' 已存在，无需添加")
            return True
        
        # 添加列
        with engine.connect() as connection:
            print("[INFO] 正在添加 folder_path 列...")
            
            # SQL语句
            sql = """
            ALTER TABLE files 
            ADD COLUMN folder_path VARCHAR(500) DEFAULT '/' NOT NULL 
            COMMENT '文件所在的文件夹路径，默认根目录'
            """
            
            connection.execute(text(sql))
            connection.commit()
            print("[OK] 列添加成功")
            
            # 创建索引
            print("[INFO] 正在创建索引...")
            try:
                index_sql = """
                CREATE INDEX idx_files_user_folder ON files(user_id, folder_path)
                """
                connection.execute(text(index_sql))
                connection.commit()
                print("[OK] 索引创建成功")
            except Exception as e:
                print(f"[WARNING] 索引创建失败（可能已存在）: {e}")
                connection.commit()
        
        print("\n[SUCCESS] 数据库迁移完成！")
        return True
        
    except Exception as e:
        print(f"[ERROR] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_migration():
    """验证迁移是否成功"""
    print("\n" + "="*60)
    print("验证迁移结果")
    print("="*60)
    
    try:
        engine = get_db_connection()
        inspector = inspect(engine)
        
        # 检查表结构
        if 'files' not in inspector.get_table_names():
            print("[ERROR] 表 'files' 不存在")
            return False
        
        columns = inspector.get_columns('files')
        print(f"\n[INFO] files 表现有列数: {len(columns)}")
        
        folder_path_exists = False
        for col in columns:
            col_name = col['name']
            col_type = str(col['type'])
            print(f"  - {col_name}: {col_type}")
            if col_name == 'folder_path':
                folder_path_exists = True
        
        if folder_path_exists:
            print("\n[SUCCESS] folder_path 列已成功添加！")
            return True
        else:
            print("\n[ERROR] folder_path 列不存在")
            return False
            
    except Exception as e:
        print(f"[ERROR] 验证失败: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("AI智能学习伴侣导师 - 数据库迁移工具")
    print("="*60)
    
    # 检查环境变量
    if not os.getenv('DATABASE_URL'):
        print("[ERROR] 未找到DATABASE_URL环境变量")
        print("请确保.env文件存在且包含正确的数据库配置")
        print("示例: DATABASE_URL=mysql+pymysql://user:password@host:3306/database")
        return False
    
    # 执行迁移
    success = add_folder_path_column()
    
    if success:
        # 验证结果
        verify_migration()
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

