"""
服务器端公共单词导入脚本
生成时间: 2025-11-11 12:04:00
单词数量: 981

使用说明:
1. 确保服务器上有 .env 文件，包含 DATABASE_URL 配置
2. 将此脚本和JSON数据文件放在项目根目录
3. 运行: python3 server_migration_script_20251111_120400.py
"""
import os
import json
import pymysql
from datetime import datetime
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

def get_db_connection():
    """从环境变量获取数据库连接"""
    # 加载环境变量
    load_dotenv()
    
    # 从环境变量获取数据库URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise Exception("未找到DATABASE_URL环境变量，请检查.env文件配置")
    
    print(f"[INFO] 使用数据库URL: {db_url.split('@')[0]}@***")
    
    # 解析数据库连接URL
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
    
    # 连接数据库
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4'
    )
    
    print("[OK] 数据库连接成功")
    return conn

def import_public_words(json_file_path):
    """导入公共单词到服务器数据库"""
    
    print("=" * 60)
    print("开始导入公共单词到服务器数据库")
    print("=" * 60)
    
    # 连接数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 读取JSON数据
        print(f"[INFO] 读取数据文件: {json_file_path}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        words = data['words']
        print(f"[INFO] 准备导入 {len(words)} 个单词")
        
        # 检查表是否存在
        cursor.execute("SHOW TABLES LIKE 'public_vocabulary_words'")
        if not cursor.fetchone():
            print("[WARNING] public_vocabulary_words 表不存在，请先创建表结构")
            return
        
        # 批量插入单词
        insert_sql = """
        INSERT INTO public_vocabulary_words 
        (word, language, definition, part_of_speech, example, tag, usage_count, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        definition = VALUES(definition),
        part_of_speech = VALUES(part_of_speech),
        example = VALUES(example),
        tag = VALUES(tag),
        usage_count = usage_count + VALUES(usage_count),
        updated_at = VALUES(updated_at)
        """
        
        imported_count = 0
        updated_count = 0
        
        for word in words:
            try:
                # 检查单词是否已存在
                cursor.execute(
                    "SELECT id FROM public_vocabulary_words WHERE word = %s AND language = %s",
                    (word['word'], word['language'])
                )
                exists = cursor.fetchone()
                
                cursor.execute(insert_sql, (
                    word['word'],
                    word['language'],
                    word['definition'],
                    word['part_of_speech'],
                    word['example'],
                    word['tag'],
                    word['usage_count'] or 0,
                    word['created_at'],
                    word['updated_at']
                ))
                
                if exists:
                    updated_count += 1
                else:
                    imported_count += 1
                
                total_processed = imported_count + updated_count
                if total_processed % 100 == 0:
                    print(f"[INFO] 已处理 {total_processed}/{len(words)} 个单词 (新增: {imported_count}, 更新: {updated_count})...")
                    
            except Exception as e:
                print(f"[ERROR] 处理单词失败: {word['word']} - {e}")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("导入完成!")
        print("=" * 60)
        print(f"总处理数量: {len(words)}")
        print(f"新增单词: {imported_count}")
        print(f"更新单词: {updated_count}")
        print(f"成功率: {((imported_count + updated_count) / len(words) * 100):.2f}%")
        
    except Exception as e:
        print(f"[ERROR] 导入过程出错: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
        print("[INFO] 数据库连接已关闭")

if __name__ == '__main__':
    # JSON数据文件路径
    json_file = 'public_words_data_20251111_120400.json'
    
    # 检查文件是否存在
    if not os.path.exists(json_file):
        print(f"[ERROR] 数据文件不存在: {json_file}")
        print("请确保将JSON数据文件放在脚本同一目录下")
        exit(1)
    
    # 检查环境变量
    if not os.getenv('DATABASE_URL'):
        print("[ERROR] 未找到DATABASE_URL环境变量")
        print("请确保.env文件存在且包含正确的数据库配置")
        print("示例: DATABASE_URL=mysql+pymysql://user:password@host:port/database")
        exit(1)
    
    try:
        import_public_words(json_file)
        print("\n[SUCCESS] 公共单词导入成功完成!")
    except Exception as e:
        print(f"\n[FAILED] 导入失败: {e}")
        exit(1)
