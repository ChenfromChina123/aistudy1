#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库文件路径更新脚本
用于将数据库中的文件路径从原来的相对路径更新为新的 /root/files 绝对路径
"""

import os
import logging
import sqlite3
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'update_database_paths_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'app.db')
logger.info(f"数据库路径: {DB_PATH}")

# 路径映射配置
PATH_MAPPINGS = [
    # 将相对路径 'uploads/' 更新为绝对路径 '/root/files/uploads/'
    ('uploads/', '/root/files/uploads/'),
    # 将相对路径 'cloud_disk/' 更新为绝对路径 '/root/files/cloud_disk/'
    ('cloud_disk/', '/root/files/cloud_disk/'),
]

def connect_db():
    """连接到SQLite数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 允许通过列名访问
        logger.info("成功连接到数据库")
        return conn
    except Exception as e:
        logger.error(f"连接数据库失败: {str(e)}")
        return None

def get_tables_and_columns(conn):
    """获取数据库中所有表及其列信息"""
    try:
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        table_columns = {}
        
        # 对每个表获取列信息
        for table in tables:
            table_name = table[0]
            # 跳过SQLite系统表
            if table_name.startswith('sqlite_'):
                continue
            
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]  # col[1] 是列名
            
            # 只保留可能包含文件路径的列（基于常见列名）
            path_columns = [col for col in column_names 
                          if any(keyword in col.lower() 
                                for keyword in ['path', 'file', 'url', 'save'])]
            
            if path_columns:
                table_columns[table_name] = path_columns
        
        return table_columns
    except Exception as e:
        logger.error(f"获取表和列信息失败: {str(e)}")
        return {}

def update_table_paths(conn, table_name, columns):
    """更新指定表中指定列的路径"""
    try:
        cursor = conn.cursor()
        total_updated = 0
        
        for column in columns:
            # 获取当前列中有数据的记录
            cursor.execute(f"SELECT id, {column} FROM {table_name} WHERE {column} IS NOT NULL AND {column} != ''")
            records = cursor.fetchall()
            
            for record in records:
                record_id = record['id']
                current_path = record[column]
                new_path = current_path
                
                # 应用所有路径映射
                for old_path, new_abs_path in PATH_MAPPINGS:
                    if old_path in new_path:
                        new_path = new_path.replace(old_path, new_abs_path)
                        logger.info(f"表 {table_name} 记录 {record_id} 列 {column}: {current_path} -> {new_path}")
                
                # 如果路径发生了变化，更新数据库
                if new_path != current_path:
                    cursor.execute(
                        f"UPDATE {table_name} SET {column} = ? WHERE id = ?",
                        (new_path, record_id)
                    )
                    total_updated += 1
        
        # 提交更改
        conn.commit()
        return total_updated
    except Exception as e:
        logger.error(f"更新表 {table_name} 的路径失败: {str(e)}")
        conn.rollback()
        return 0

def create_backup():
    """创建数据库备份"""
    try:
        backup_path = os.path.join(
            BASE_DIR,
            'instance',
            f'app_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        )
        
        if os.path.exists(DB_PATH):
            import shutil
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"数据库备份已创建: {backup_path}")
            return backup_path
        else:
            logger.warning("数据库文件不存在，无法创建备份")
            return None
    except Exception as e:
        logger.error(f"创建数据库备份失败: {str(e)}")
        return None

def main():
    """主函数"""
    logger.info("开始更新数据库文件路径...")
    
    # 创建数据库备份
    backup_path = create_backup()
    if not backup_path:
        logger.warning("没有创建备份，但将继续更新过程")
    
    # 连接数据库
    conn = connect_db()
    if not conn:
        logger.error("无法连接到数据库，退出程序")
        return
    
    try:
        # 获取可能包含文件路径的表和列
        table_columns = get_tables_and_columns(conn)
        
        if not table_columns:
            logger.warning("未找到可能包含文件路径的表或列")
        else:
            logger.info(f"找到以下可能包含文件路径的表和列:")
            for table, columns in table_columns.items():
                logger.info(f"  - 表 {table}: {', '.join(columns)}")
            
            # 确认是否继续
            confirmation = input("\n是否继续更新这些表中的文件路径？(y/N): ")
            if confirmation.lower() != 'y':
                logger.info("用户取消了更新操作")
                return
            
            # 更新每个表中的路径
            total_updates = 0
            for table_name, columns in table_columns.items():
                logger.info(f"\n更新表 {table_name}...")
                updates = update_table_paths(conn, table_name, columns)
                total_updates += updates
                logger.info(f"表 {table_name} 更新完成，更新了 {updates} 条记录")
            
            logger.info(f"\n总更新记录数: {total_updates}")
            
        # 提供额外的SQL查询示例
        logger.info("\n" + "="*80)
        logger.info("如果需要手动执行特定更新，可以使用以下SQL命令:")
        for old_path, new_path in PATH_MAPPINGS:
            logger.info(f"UPDATE 表名 SET 列名 = REPLACE(列名, '{old_path}', '{new_path}');")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
    finally:
        if conn:
            conn.close()
            logger.info("数据库连接已关闭")
    
    logger.info("数据库文件路径更新脚本执行完成！")

if __name__ == "__main__":
    main()