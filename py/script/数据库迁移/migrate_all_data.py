#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据库迁移脚本（两步迁移模式）
第一步：将源数据库数据导出到文本文件
第二步：生成导入脚本，从文本文件导入到目标数据库

使用方法:
    导出模式:
        python migrate_all_data.py export --source-db <源数据库URL> --output-dir <输出目录>
    
    导入模式:
        python migrate_all_data.py import --target-db <目标数据库URL> --data-dir <数据目录>
    
    完整流程:
        1. python migrate_all_data.py export --source-db <源数据库URL> --output-dir ./migration_data
        2. python migrate_all_data.py import --target-db <目标数据库URL> --data-dir ./migration_data
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'py'))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

# 配置日志
def setup_logging():
    """设置日志配置"""
    log_dir = BASE_DIR / 'log'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'migrate_all_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# 定义表的迁移顺序（考虑外键依赖关系）
MIGRATION_ORDER = [
    # 第一层：基础表，无外键依赖
    'users',
    'categories',
    'vocabulary_lists',
    'public_vocabulary_words',
    'vocabulary_upload_tasks',
    
    # 第二层：依赖users表
    'admins',
    'verification_codes',
    'custom_ai_models',
    'notes',
    'user_folders',
    'user_files',
    'chat_sessions',
    'resources',
    'feedbacks',
    'user_learning_records',
    'generated_articles',
    
    # 第三层：依赖其他表
    'file_shares',  # 依赖 user_files, users
    'chat_records',  # 依赖 chat_sessions, users
    'collections',  # 依赖 users, resources
    'public_resources',  # 依赖 resources
    'vocabulary_words',  # 依赖 vocabulary_lists
    'user_word_progress',  # 依赖 vocabulary_words, users
    'article_used_words',  # 依赖 generated_articles, vocabulary_words
]

# 需要特殊处理的表（如自增ID需要重置）
TABLES_WITH_AUTO_INCREMENT = [
    'users', 'admins', 'verification_codes', 'custom_ai_models',
    'notes', 'user_folders', 'user_files', 'file_shares',
    'chat_sessions', 'chat_records', 'categories', 'resources',
    'collections', 'public_resources', 'feedbacks',
    'vocabulary_lists', 'vocabulary_words', 'user_word_progress',
    'public_vocabulary_words', 'user_learning_records',
    'generated_articles', 'article_used_words', 'vocabulary_upload_tasks'
]


class DataExporter:
    """数据导出器"""
    
    def __init__(self, source_db_url: str, output_dir: Path):
        """
        初始化导出器
        
        Args:
            source_db_url: 源数据库连接URL
            output_dir: 输出目录
        """
        self.source_db_url = source_db_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建数据库引擎
        self.source_engine = create_engine(source_db_url, pool_pre_ping=True)
        self.source_session = sessionmaker(bind=self.source_engine)
        
        # 统计信息
        self.stats = {
            'total_tables': 0,
            'exported_tables': 0,
            'failed_tables': [],
            'total_records': 0,
            'exported_records': 0
        }
        
        # 元数据文件
        self.metadata_file = self.output_dir / 'migration_metadata.json'
    
    def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.source_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ 源数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return False
    
    def get_table_names(self, engine) -> List[str]:
        """获取数据库中的所有表名"""
        inspector = inspect(engine)
        return inspector.get_table_names()
    
    def get_table_columns(self, engine, table_name: str) -> List[str]:
        """获取表的列名"""
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        return [col['name'] for col in columns]
    
    def get_table_row_count(self, session: Session, table_name: str) -> int:
        """获取表的记录数"""
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
            return result.scalar() or 0
        except Exception as e:
            logger.warning(f"获取表 {table_name} 记录数失败: {str(e)}")
            return 0
    
    def escape_sql_value(self, value: Any) -> str:
        """转义SQL值"""
        if value is None:
            return 'NULL'
        elif isinstance(value, datetime):
            return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
        elif isinstance(value, str):
            # 转义单引号和反斜杠
            escaped = value.replace('\\', '\\\\').replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return '1' if value else '0'
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            # 其他类型转为字符串
            escaped = str(value).replace('\\', '\\\\').replace("'", "''")
            return f"'{escaped}'"
    
    def export_table(self, table_name: str, batch_size: int = 1000) -> Dict[str, Any]:
        """
        导出单个表的数据到SQL文件
        
        Args:
            table_name: 表名
            batch_size: 批量处理大小
            
        Returns:
            导出结果统计
        """
        result = {
            'table': table_name,
            'source_count': 0,
            'exported_count': 0,
            'success': False
        }
        
        source_session = self.source_session()
        sql_file = self.output_dir / f"{table_name}.sql"
        
        try:
            # 检查表是否存在
            source_tables = self.get_table_names(self.source_engine)
            if table_name not in source_tables:
                logger.warning(f"表 {table_name} 在源数据库中不存在，跳过")
                result['success'] = True
                return result
            
            # 获取源表记录数
            result['source_count'] = self.get_table_row_count(source_session, table_name)
            
            if result['source_count'] == 0:
                logger.info(f"表 {table_name} 无数据，跳过")
                result['success'] = True
                # 创建空文件
                sql_file.write_text(f"-- 表 {table_name} 无数据\n", encoding='utf-8')
                return result
            
            logger.info(f"开始导出表 {table_name}，记录数: {result['source_count']}")
            
            # 获取表的列名
            columns = self.get_table_columns(self.source_engine, table_name)
            columns_str = ', '.join([f"`{col}`" for col in columns])
            
            # 打开SQL文件
            with open(sql_file, 'w', encoding='utf-8') as f:
                # 写入文件头
                f.write(f"-- 表 {table_name} 数据导出\n")
                f.write(f"-- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- 总记录数: {result['source_count']}\n")
                f.write(f"-- 列: {', '.join(columns)}\n\n")
                f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")
                
                # 分批导出数据
                offset = 0
                while offset < result['source_count']:
                    try:
                        # 从源数据库读取数据
                        query = f"SELECT {columns_str} FROM `{table_name}` LIMIT {batch_size} OFFSET {offset}"
                        source_result = source_session.execute(text(query))
                        rows = source_result.fetchall()
                        
                        if not rows:
                            break
                        
                        # 写入INSERT语句
                        for row in rows:
                            values_list = []
                            for i, col in enumerate(columns):
                                val = row[i]
                                values_list.append(self.escape_sql_value(val))
                            
                            values_str = ', '.join(values_list)
                            insert_sql = f"INSERT IGNORE INTO `{table_name}` ({columns_str}) VALUES ({values_str});\n"
                            f.write(insert_sql)
                            result['exported_count'] += 1
                        
                        if result['exported_count'] % 1000 == 0:
                            logger.info(f"  已导出 {result['exported_count']}/{result['source_count']} 条记录")
                        
                        offset += batch_size
                        
                    except Exception as e:
                        logger.error(f"导出表 {table_name} 批次失败 (offset={offset}): {str(e)}")
                        offset += batch_size
                        continue
                
                # 写入文件尾
                f.write("\nSET FOREIGN_KEY_CHECKS = 1;\n")
                
                # 如果是自增表，添加重置自增ID的语句
                if table_name in TABLES_WITH_AUTO_INCREMENT:
                    f.write(f"\n-- 重置自增ID\n")
                    f.write(f"SELECT @max_id := MAX(id) FROM `{table_name}`;\n")
                    f.write(f"SET @max_id = IFNULL(@max_id, 0);\n")
                    f.write(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = @max_id + 1;\n")
            
            result['success'] = True
            logger.info(f"✓ 表 {table_name} 导出完成: {result['exported_count']} 条记录 -> {sql_file}")
            
        except Exception as e:
            logger.error(f"导出表 {table_name} 失败: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
        
        finally:
            source_session.close()
        
        return result
    
    def export_all(self, tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        导出所有表的数据
        
        Args:
            tables: 要导出的表列表，如果为None则导出所有表
            
        Returns:
            导出结果统计
        """
        logger.info("=" * 80)
        logger.info("开始数据导出")
        logger.info(f"源数据库: {self.source_db_url.split('@')[-1] if '@' in self.source_db_url else 'N/A'}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info("=" * 80)
        
        # 检查连接
        if not self.check_connection():
            return self.stats
        
        # 确定要导出的表
        if tables is None:
            source_tables = self.get_table_names(self.source_engine)
            # 只导出在迁移顺序中的表
            tables = [t for t in MIGRATION_ORDER if t in source_tables]
            # 添加其他未在顺序中的表
            other_tables = [t for t in source_tables if t not in MIGRATION_ORDER]
            tables.extend(other_tables)
        
        self.stats['total_tables'] = len(tables)
        
        logger.info(f"将导出 {len(tables)} 个表")
        logger.info(f"导出顺序: {', '.join(tables)}")
        logger.info("-" * 80)
        
        # 按顺序导出每个表
        exported_tables_info = []
        for i, table_name in enumerate(tables, 1):
            logger.info(f"\n[{i}/{len(tables)}] 导出表: {table_name}")
            result = self.export_table(table_name)
            
            # 更新统计
            if result['success']:
                self.stats['exported_tables'] += 1
                self.stats['exported_records'] += result['exported_count']
            else:
                self.stats['failed_tables'].append({
                    'table': table_name,
                    'error': result.get('error', 'Unknown error')
                })
            
            self.stats['total_records'] += result['source_count']
            exported_tables_info.append({
                'table': table_name,
                'source_count': result['source_count'],
                'exported_count': result['exported_count'],
                'file': f"{table_name}.sql"
            })
        
        # 保存元数据
        metadata = {
            'export_time': datetime.now().isoformat(),
            'source_database': self.source_db_url.split('@')[-1] if '@' in self.source_db_url else 'N/A',
            'tables': exported_tables_info,
            'stats': {
                'total_tables': self.stats['total_tables'],
                'exported_tables': self.stats['exported_tables'],
                'total_records': self.stats['total_records'],
                'exported_records': self.stats['exported_records']
            }
        }
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 打印导出摘要
        self.print_summary()
        
        return self.stats
    
    def print_summary(self):
        """打印导出摘要"""
        logger.info("\n" + "=" * 80)
        logger.info("导出摘要")
        logger.info("=" * 80)
        logger.info(f"总表数: {self.stats['total_tables']}")
        logger.info(f"成功导出: {self.stats['exported_tables']}")
        logger.info(f"失败表数: {len(self.stats['failed_tables'])}")
        logger.info(f"总记录数: {self.stats['total_records']}")
        logger.info(f"成功导出记录数: {self.stats['exported_records']}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info(f"元数据文件: {self.metadata_file}")
        
        if self.stats['failed_tables']:
            logger.info("\n失败的表:")
            for failed in self.stats['failed_tables']:
                logger.info(f"  - {failed['table']}: {failed['error']}")
        
        logger.info("=" * 80)


class DataImporter:
    """数据导入器"""
    
    def __init__(self, target_db_url: str, data_dir: Path):
        """
        初始化导入器
        
        Args:
            target_db_url: 目标数据库连接URL
            data_dir: 数据文件目录
        """
        self.target_db_url = target_db_url
        self.data_dir = Path(data_dir)
        
        if not self.data_dir.exists():
            raise ValueError(f"数据目录不存在: {self.data_dir}")
        
        # 创建数据库引擎
        self.target_engine = create_engine(target_db_url, pool_pre_ping=True)
        self.target_session = sessionmaker(bind=self.target_engine)
        
        # 统计信息
        self.stats = {
            'total_tables': 0,
            'imported_tables': 0,
            'failed_tables': [],
            'total_records': 0,
            'imported_records': 0,
            'failed_records': 0
        }
        
        # 元数据文件
        self.metadata_file = self.data_dir / 'migration_metadata.json'
    
    def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ 目标数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return False
    
    def load_metadata(self) -> Optional[Dict]:
        """加载元数据"""
        if not self.metadata_file.exists():
            logger.warning("元数据文件不存在，将尝试导入所有SQL文件")
            return None
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载元数据失败: {str(e)}")
            return None
    
    def import_table(self, table_name: str, sql_file: Path) -> Dict[str, Any]:
        """
        从SQL文件导入单个表的数据
        
        Args:
            table_name: 表名
            sql_file: SQL文件路径
            
        Returns:
            导入结果统计
        """
        result = {
            'table': table_name,
            'imported_count': 0,
            'failed_count': 0,
            'success': False
        }
        
        target_session = self.target_session()
        
        try:
            if not sql_file.exists():
                logger.warning(f"SQL文件不存在: {sql_file}")
                result['success'] = True
                return result
            
            logger.info(f"开始导入表 {table_name}，文件: {sql_file}")
            
            # 读取SQL文件内容
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 检查文件是否为空：去除注释和空白后，检查是否有实际的SQL语句
            # 将SQL内容按行分割，过滤掉注释行和空行
            lines = [line.strip() for line in sql_content.split('\n') 
                    if line.strip() and not line.strip().startswith('--')]
            actual_sql = '\n'.join(lines)
            
            if not actual_sql.strip():
                logger.info(f"表 {table_name} SQL文件为空，跳过")
                result['success'] = True
                return result
            
            # 禁用外键检查
            target_session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            target_session.commit()
            
            # 执行SQL语句
            # 改进的SQL语句分割：按分号分割，但跳过字符串中的分号
            statements = []
            current_stmt = ""
            in_string = False
            string_char = None
            i = 0
            
            while i < len(sql_content):
                char = sql_content[i]
                
                # 检查是否进入或退出字符串
                if char in ("'", '"') and (i == 0 or sql_content[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                current_stmt += char
                
                # 如果遇到分号且不在字符串中，则是一个完整的语句
                if char == ';' and not in_string:
                    stmt = current_stmt.strip()
                    if stmt and not stmt.startswith('--'):
                        # 移除末尾的分号
                        stmt = stmt.rstrip(';').strip()
                        if stmt:
                            statements.append(stmt)
                    current_stmt = ""
                
                i += 1
            
            # 处理最后一个语句（如果没有以分号结尾）
            if current_stmt.strip() and not current_stmt.strip().startswith('--'):
                stmt = current_stmt.strip().rstrip(';').strip()
                if stmt:
                    statements.append(stmt)
            
            # 执行SQL语句
            for stmt in statements:
                try:
                    if not stmt:
                        continue
                    
                    # 跳过重置自增ID的语句（这些语句语法有问题，应该在所有数据导入后统一执行）
                    if 'AUTO_INCREMENT' in stmt.upper() or 'SELECT @max_id' in stmt.upper() or 'SET @max_id' in stmt.upper():
                        continue
                    
                    # 跳过SET FOREIGN_KEY_CHECKS（已经在前面统一处理）
                    if 'FOREIGN_KEY_CHECKS' in stmt.upper():
                        continue
                    
                    target_session.execute(text(stmt))
                    if 'INSERT' in stmt.upper():
                        result['imported_count'] += 1
                except Exception as e:
                    error_msg = str(e)
                    # 对于某些错误，给出更详细的提示
                    if "doesn't exist" in error_msg:
                        logger.warning(f"执行SQL语句失败（表或列不存在）: {error_msg[:200]}")
                    elif "Unknown column" in error_msg:
                        logger.warning(f"执行SQL语句失败（列不存在）: {error_msg[:200]}")
                    else:
                        logger.warning(f"执行SQL语句失败: {error_msg[:200]}")
                    result['failed_count'] += 1
                    continue
            
            # 提交事务
            target_session.commit()
            
            # 启用外键检查
            target_session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            target_session.commit()
            
            result['success'] = True
            logger.info(f"✓ 表 {table_name} 导入完成: {result['imported_count']} 条记录")
            
        except Exception as e:
            logger.error(f"导入表 {table_name} 失败: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
            target_session.rollback()
        
        finally:
            target_session.close()
        
        return result
    
    def import_all(self, tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        导入所有表的数据
        
        Args:
            tables: 要导入的表列表，如果为None则导入所有表
            
        Returns:
            导入结果统计
        """
        logger.info("=" * 80)
        logger.info("开始数据导入")
        logger.info(f"目标数据库: {self.target_db_url.split('@')[-1] if '@' in self.target_db_url else 'N/A'}")
        logger.info(f"数据目录: {self.data_dir}")
        logger.info("=" * 80)
        
        # 检查连接
        if not self.check_connection():
            return self.stats
        
        # 加载元数据
        metadata = self.load_metadata()
        
        # 确定要导入的表
        if tables is None:
            if metadata and 'tables' in metadata:
                # 从元数据获取表列表
                tables = [t['table'] for t in metadata['tables']]
            else:
                # 从目录中查找所有SQL文件
                sql_files = list(self.data_dir.glob('*.sql'))
                tables = [f.stem for f in sql_files if f.name != 'migration_metadata.json']
                # 按迁移顺序排序
                ordered_tables = [t for t in MIGRATION_ORDER if t in tables]
                other_tables = [t for t in tables if t not in MIGRATION_ORDER]
                tables = ordered_tables + other_tables
        
        self.stats['total_tables'] = len(tables)
        
        logger.info(f"将导入 {len(tables)} 个表")
        logger.info(f"导入顺序: {', '.join(tables)}")
        logger.info("-" * 80)
        
        # 按顺序导入每个表
        for i, table_name in enumerate(tables, 1):
            logger.info(f"\n[{i}/{len(tables)}] 导入表: {table_name}")
            sql_file = self.data_dir / f"{table_name}.sql"
            result = self.import_table(table_name, sql_file)
            
            # 更新统计
            if result['success']:
                self.stats['imported_tables'] += 1
                self.stats['imported_records'] += result['imported_count']
            else:
                self.stats['failed_tables'].append({
                    'table': table_name,
                    'error': result.get('error', 'Unknown error')
                })
            
            self.stats['failed_records'] += result['failed_count']
            self.stats['total_records'] += result['imported_count'] + result['failed_count']
        
        # 打印导入摘要
        self.print_summary()
        
        return self.stats
    
    def print_summary(self):
        """打印导入摘要"""
        logger.info("\n" + "=" * 80)
        logger.info("导入摘要")
        logger.info("=" * 80)
        logger.info(f"总表数: {self.stats['total_tables']}")
        logger.info(f"成功导入: {self.stats['imported_tables']}")
        logger.info(f"失败表数: {len(self.stats['failed_tables'])}")
        logger.info(f"总记录数: {self.stats['total_records']}")
        logger.info(f"成功导入记录数: {self.stats['imported_records']}")
        logger.info(f"失败记录数: {self.stats['failed_records']}")
        
        if self.stats['failed_tables']:
            logger.info("\n失败的表:")
            for failed in self.stats['failed_tables']:
                logger.info(f"  - {failed['table']}: {failed['error']}")
        
        logger.info("=" * 80)


def generate_import_script(data_dir: Path, target_db_url: str, output_script: Path):
    """生成导入脚本"""
    script_content = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
自动生成的数据库导入脚本
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据目录: {data_dir}
目标数据库: {target_db_url.split('@')[-1] if '@' in target_db_url else 'N/A'}
\"\"\"

import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'py'))

from script.数据库迁移.migrate_all_data import DataImporter

if __name__ == "__main__":
    data_dir = Path(r"{data_dir}")
    target_db_url = r"{target_db_url}"
    
    importer = DataImporter(target_db_url, data_dir)
    importer.import_all()
    print("\\n✓ 数据导入完成！")
"""
    
    output_script.write_text(script_content, encoding='utf-8')
    # 在Unix系统上添加执行权限
    if os.name != 'nt':
        os.chmod(output_script, 0o755)
    
    logger.info(f"✓ 导入脚本已生成: {output_script}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据库迁移脚本（两步模式）')
    subparsers = parser.add_subparsers(dest='mode', help='迁移模式')
    
    # 导出模式
    export_parser = subparsers.add_parser('export', help='导出数据到文件')
    export_parser.add_argument(
        '--source-db',
        type=str,
        required=True,
        help='源数据库连接URL'
    )
    export_parser.add_argument(
        '--output-dir',
        type=str,
        default='./migration_data',
        help='输出目录（默认: ./migration_data）'
    )
    export_parser.add_argument(
        '--tables',
        type=str,
        nargs='+',
        help='要导出的表列表（可选）'
    )
    export_parser.add_argument(
        '--generate-script',
        action='store_true',
        help='生成导入脚本'
    )
    export_parser.add_argument(
        '--target-db',
        type=str,
        help='目标数据库URL（用于生成导入脚本）'
    )
    
    # 导入模式
    import_parser = subparsers.add_parser('import', help='从文件导入数据')
    import_parser.add_argument(
        '--target-db',
        type=str,
        required=True,
        help='目标数据库连接URL'
    )
    import_parser.add_argument(
        '--data-dir',
        type=str,
        required=True,
        help='数据文件目录'
    )
    import_parser.add_argument(
        '--tables',
        type=str,
        nargs='+',
        help='要导入的表列表（可选）'
    )
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.mode == 'export':
            # 导出模式
            output_dir = Path(args.output_dir)
            exporter = DataExporter(args.source_db, output_dir)
            exporter.export_all(tables=args.tables)
            
            # 如果指定了生成脚本
            if args.generate_script and args.target_db:
                script_file = output_dir / 'import_data.py'
                generate_import_script(output_dir, args.target_db, script_file)
                logger.info(f"\n✓ 导出完成！")
                logger.info(f"数据文件目录: {output_dir}")
                logger.info(f"导入脚本: {script_file}")
                logger.info(f"\n下一步: 运行导入脚本或使用以下命令:")
                logger.info(f"python py/script/数据库迁移/migrate_all_data.py import --target-db \"{args.target_db}\" --data-dir \"{output_dir}\"")
            else:
                logger.info(f"\n✓ 导出完成！")
                logger.info(f"数据文件目录: {output_dir}")
                logger.info(f"\n下一步: 使用以下命令导入数据:")
                logger.info(f"python py/script/数据库迁移/migrate_all_data.py import --target-db \"<目标数据库URL>\" --data-dir \"{output_dir}\"")
        
        elif args.mode == 'import':
            # 导入模式
            data_dir = Path(args.data_dir)
            importer = DataImporter(args.target_db, data_dir)
            importer.import_all(tables=args.tables)
            logger.info("\n✓ 数据导入完成！")
    
    except KeyboardInterrupt:
        logger.warning("\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n操作过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
