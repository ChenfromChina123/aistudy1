#!/usr/bin/env python3
"""
数据库迁移脚本：创建 user_folders 表
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from pytz import UTC

# 获取项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入数据库配置
from py.app import Base, UserFolder, DATABASE_URL

def migrate():
    """执行迁移"""
    try:
        print("=" * 60)
        print("开始创建 user_folders 表...")
        print("=" * 60)
        
        # 创建数据库引擎
        engine = create_engine(DATABASE_URL)
        
        # 创建表
        print("\n1. 正在创建 user_folders 表...")
        Base.metadata.create_all(engine, tables=[Base.metadata.tables.get('user_folders')])
        
        print("✅ user_folders 表已成功创建！")
        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)
        
        # 验证表结构
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        if 'user_folders' in inspector.get_table_names():
            print("\n✅ 表验证成功")
            columns = inspector.get_columns('user_folders')
            print("\n表结构：")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
            
            # 检查约束
            constraints = inspector.get_unique_constraints('user_folders')
            if constraints:
                print("\n约束：")
                for constraint in constraints:
                    print(f"  - {constraint}")
        else:
            print("\n❌ 表创建失败，请检查数据库连接")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)

