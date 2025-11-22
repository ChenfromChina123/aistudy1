#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单数据库迁移工具
从 .env 文件读取配置，直接运行即可

使用方法：
    1. 确保 .env 文件中有 DATABASE_URL 配置
    2. 直接运行此脚本：python 简单迁移.py
    3. 选择导出或导入模式
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PY_DIR = BASE_DIR / 'py'
sys.path.insert(0, str(PY_DIR))
sys.path.insert(0, str(BASE_DIR))

# 加载环境变量
from dotenv import load_dotenv
ENV_FILE = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_FILE)

# 直接导入（因为脚本在 py/script/数据库迁移/ 目录下）
import importlib.util
spec = importlib.util.spec_from_file_location(
    "migrate_all_data",
    Path(__file__).parent / "migrate_all_data.py"
)
migrate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migrate_module)

DataExporter = migrate_module.DataExporter
DataImporter = migrate_module.DataImporter

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def get_database_url():
    """从环境变量或配置文件获取数据库URL"""
    # 先尝试从环境变量读取
    db_url = os.getenv('DATABASE_URL')
    
    # 如果没找到，尝试从 .env 文件读取
    if not db_url:
        env_file = BASE_DIR / '.env'
        if env_file.exists():
            print(f"正在从 .env 文件读取配置: {env_file}")
            # 重新加载
            load_dotenv(dotenv_path=env_file, override=True)
            db_url = os.getenv('DATABASE_URL')
    
    # 如果还是没找到，尝试从 config.py 读取默认值
    if not db_url:
        try:
            from config import settings
            db_url = settings.DATABASE_URL
            if db_url:
                print(f"使用 config.py 中的默认数据库配置")
        except Exception as e:
            pass
    
    # 如果还是没找到，使用默认值
    if not db_url:
        db_url = 'mysql+pymysql://root:123456@localhost:3306/ipv6_education'
        print(f"⚠️  未找到 DATABASE_URL，使用默认值")
        print(f"建议：在项目根目录创建 .env 文件并设置 DATABASE_URL")
    
    return db_url


def main():
    """主函数"""
    print("=" * 80)
    print("数据库迁移工具（简化版）")
    print("=" * 80)
    print()
    
    # 检查 .env 文件（可选，不是必需的）
    env_file = BASE_DIR / '.env'
    if not env_file.exists():
        print(f"提示: 未找到 .env 文件: {env_file}")
        print("将使用 config.py 中的默认配置或系统默认值")
        print("（可选）创建 .env 文件可自定义配置")
        print()
    
    # 获取数据库URL
    try:
        database_url = get_database_url()
        db_display = database_url.split('@')[-1] if '@' in database_url else database_url
        print(f"✓ 从 .env 文件读取数据库配置: {db_display}")
    except SystemExit:
        return
    except Exception as e:
        print(f"错误: 读取数据库配置失败: {str(e)}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 键退出...")
        return
    
    print()
    print("请选择操作模式:")
    print("1. 导出数据到文件（从数据库导出到 migration_data 目录）")
    print("2. 导入数据到数据库（从 migration_data 目录导入到数据库）")
    print("3. 退出")
    print()
    
    while True:
        choice = input("请输入选项 (1/2/3): ").strip()
        
        if choice == '1':
            # 导出模式
            export_data(database_url)
            break
        elif choice == '2':
            # 导入模式
            import_data(database_url)
            break
        elif choice == '3':
            print("退出程序")
            break
        else:
            print("无效选项，请输入 1、2 或 3")
    
    print()
    print("=" * 80)
    input("按 Enter 键退出...")


def select_directory(title="选择文件夹", initial_dir=None):
    """通过命令行输入文件夹路径"""
    print()
    print(f"{title}")
    if initial_dir:
        print(f"默认路径: {initial_dir}")
    
    while True:
        folder_path = input("请输入文件夹路径（直接回车使用默认路径）: ").strip()
        
        if not folder_path:
            # 使用默认路径
            if initial_dir:
                folder_path = str(initial_dir)
            else:
                print("未提供路径且无默认路径，请重新输入")
                continue
        
        # 转换为Path对象
        folder_path_obj = Path(folder_path)
        
        # 检查路径是否存在
        if not folder_path_obj.exists():
            print(f"错误: 路径不存在: {folder_path}")
            retry = input("是否重新输入？(y/n，默认y): ").strip().lower()
            if retry == '' or retry == 'y':
                continue
            else:
                return None
        elif not folder_path_obj.is_dir():
            print(f"错误: 路径不是文件夹: {folder_path}")
            retry = input("是否重新输入？(y/n，默认y): ").strip().lower()
            if retry == '' or retry == 'y':
                continue
            else:
                return None
        else:
            # 路径有效
            return folder_path_obj.resolve()


def export_data(source_db_url: str):
    """导出数据"""
    print()
    print("=" * 80)
    print("导出数据模式")
    print("=" * 80)
    
    # 默认输出目录
    default_output_dir = BASE_DIR / 'migration_data'
    
    print(f"源数据库: {source_db_url.split('@')[-1] if '@' in source_db_url else 'N/A'}")
    print(f"默认输出目录: {default_output_dir}")
    print()
    
    # 询问是否使用默认路径
    use_default = input("是否使用默认路径？(y/n，默认y): ").strip().lower()
    
    if use_default == '' or use_default == 'y':
        # 使用默认路径
        output_dir = default_output_dir
        print(f"使用默认路径: {output_dir}")
    else:
        # 通过命令行输入路径
        output_dir = select_directory(
            title="选择导出数据保存的文件夹",
            initial_dir=BASE_DIR
        )
        
        if not output_dir:
            print("未选择文件夹，已取消导出")
            return
        
        print(f"已选择路径: {output_dir}")
    
    print()
    confirm = input("确认开始导出？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消导出")
        return
    
    try:
        exporter = DataExporter(source_db_url, output_dir)
        exporter.export_all()
        print()
        print("=" * 80)
        print("✓ 导出完成！")
        print(f"数据文件保存在: {output_dir}")
        print("=" * 80)
    except Exception as e:
        print(f"导出失败: {str(e)}")
        import traceback
        traceback.print_exc()


def import_data(target_db_url: str):
    """导入数据"""
    print()
    print("=" * 80)
    print("导入数据模式")
    print("=" * 80)
    
    # 默认数据目录
    default_data_dir = BASE_DIR / 'migration_data'
    
    print(f"目标数据库: {target_db_url.split('@')[-1] if '@' in target_db_url else 'N/A'}")
    print(f"默认数据目录: {default_data_dir}")
    print()
    
    # 询问是否使用默认路径
    use_default = input("是否使用默认路径？(y/n，默认y): ").strip().lower()
    
    if use_default == '' or use_default == 'y':
        # 使用默认路径
        data_dir = default_data_dir
        print(f"使用默认路径: {data_dir}")
    else:
        # 通过命令行输入路径
        data_dir = select_directory(
            title="选择包含SQL文件的数据文件夹",
            initial_dir=BASE_DIR
        )
        
        if not data_dir:
            print("未选择文件夹，已取消导入")
            return
        
        print(f"已选择路径: {data_dir}")
    
    if not data_dir.exists():
        print(f"错误: 数据目录不存在: {data_dir}")
        print("请先执行导出操作或检查路径是否正确")
        return
    
    print(f"数据目录: {data_dir}")
    print()
    
    # 检查是否有SQL文件
    sql_files = list(data_dir.glob('*.sql'))
    if not sql_files:
        print("警告: 数据目录中没有找到SQL文件")
        confirm = input("是否继续？(y/n): ").strip().lower()
        if confirm != 'y':
            return
    else:
        print(f"找到 {len(sql_files)} 个SQL文件")
    
    print()
    confirm = input("确认开始导入？这将覆盖目标数据库中的数据！(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消导入")
        return
    
    try:
        importer = DataImporter(target_db_url, data_dir)
        importer.import_all()
        print()
        print("=" * 80)
        print("✓ 导入完成！")
        print("=" * 80)
    except Exception as e:
        print(f"导入失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 键退出...")

