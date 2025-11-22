#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件迁移脚本
用于将原来路径的文件转移到新路径 /root/files 下
"""

import os
import shutil
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migrate_files_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 定义迁移路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger.info(f"项目基础目录: {BASE_DIR}")

# 源路径和目标路径映射
MIGRATION_PATHS = {
    'uploads': {
        'source': os.path.join(BASE_DIR, 'uploads'),
        'destination': '/root/files/uploads'
    },
    'cloud_disk': {
        'source': os.path.join(BASE_DIR, 'cloud_disk'),
        'destination': '/root/files/cloud_disk'
    }
}

# 同时也处理py目录下的uploads文件夹（如果存在）
PY_UPLOADS_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if os.path.exists(PY_UPLOADS_SOURCE):
    MIGRATION_PATHS['py_uploads'] = {
        'source': PY_UPLOADS_SOURCE,
        'destination': '/root/files/uploads'
    }

def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建"""
    try:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"确保目录存在: {directory}")
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {directory}: {str(e)}")
        return False

def copy_file(source_file, destination_file):
    """复制单个文件"""
    try:
        # 确保目标目录存在
        os.makedirs(os.path.dirname(destination_file), exist_ok=True)
        
        # 复制文件
        shutil.copy2(source_file, destination_file)
        logger.info(f"成功复制文件: {source_file} -> {destination_file}")
        return True
    except Exception as e:
        logger.error(f"复制文件失败 {source_file} -> {destination_file}: {str(e)}")
        return False

def migrate_directory(source_dir, destination_dir):
    """迁移整个目录"""
    if not os.path.exists(source_dir):
        logger.warning(f"源目录不存在: {source_dir}")
        return 0, 0
    
    if not ensure_directory_exists(destination_dir):
        return 0, 0
    
    total_files = 0
    copied_files = 0
    
    try:
        # 遍历源目录
        for root, dirs, files in os.walk(source_dir):
            # 计算相对路径
            relative_path = os.path.relpath(root, source_dir)
            if relative_path == '.':
                relative_path = ''
            
            # 创建目标子目录
            target_dir = os.path.join(destination_dir, relative_path)
            if not ensure_directory_exists(target_dir):
                continue
            
            # 复制文件
            for file in files:
                total_files += 1
                source_file = os.path.join(root, file)
                destination_file = os.path.join(target_dir, file)
                
                # 检查目标文件是否已存在
                if os.path.exists(destination_file):
                    # 比较文件大小
                    if os.path.getsize(source_file) == os.path.getsize(destination_file):
                        logger.info(f"文件已存在且大小相同，跳过: {destination_file}")
                        copied_files += 1  # 算作已复制
                        continue
                    else:
                        logger.warning(f"文件已存在但大小不同，将覆盖: {destination_file}")
                
                if copy_file(source_file, destination_file):
                    copied_files += 1
    
    except Exception as e:
        logger.error(f"迁移目录时发生错误 {source_dir}: {str(e)}")
    
    return total_files, copied_files

def update_database_references():
    """提示用户数据库引用更新注意事项"""
    logger.warning("="*80)
    logger.warning("注意: 数据库中的文件路径引用可能需要更新！")
    logger.warning("如果数据库中存储了文件的完整路径，需要执行SQL更新操作。")
    logger.warning("例如:")
    logger.warning("UPDATE files SET save_path = REPLACE(save_path, 'uploads/', '/root/files/uploads/');")
    logger.warning("UPDATE files SET save_path = REPLACE(save_path, 'cloud_disk/', '/root/files/cloud_disk/');")
    logger.warning("请根据实际数据库结构调整SQL语句。")
    logger.warning("="*80)

def main():
    """主函数"""
    logger.info("开始文件迁移...")
    logger.info(f"迁移配置: {MIGRATION_PATHS}")
    
    total_all_files = 0
    copied_all_files = 0
    
    # 执行迁移
    for path_type, paths in MIGRATION_PATHS.items():
        logger.info(f"\n开始迁移 {path_type}...")
        logger.info(f"源路径: {paths['source']}")
        logger.info(f"目标路径: {paths['destination']}")
        
        total_files, copied_files = migrate_directory(paths['source'], paths['destination'])
        total_all_files += total_files
        copied_all_files += copied_files
        
        logger.info(f"{path_type} 迁移完成 - 总计: {total_files}, 成功: {copied_files}")
    
    # 显示迁移摘要
    logger.info("\n" + "="*80)
    logger.info(f"文件迁移摘要:")
    logger.info(f"总文件数: {total_all_files}")
    logger.info(f"成功迁移: {copied_all_files}")
    logger.info(f"迁移成功率: {copied_all_files/total_all_files*100:.2f}%" if total_all_files > 0 else "无文件需要迁移")
    logger.info("="*80)
    
    # 提示数据库更新
    update_database_references()
    
    # 提示权限设置
    logger.info("\n请确保设置正确的目录权限:")
    logger.info("sudo chown -R <app_user>:<app_group> /root/files")
    logger.info("sudo chmod -R 755 /root/files")
    logger.info("其中 <app_user> 是运行应用的用户")
    
    logger.info("\n文件迁移脚本执行完成！")

if __name__ == "__main__":
    main()