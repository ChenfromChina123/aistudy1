"""
公共单词迁移脚本
从当前数据库导出公共单词，检查重复项，保存到txt文件，并提供服务器上传功能
"""
import os
import json
import csv
import hashlib
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
import pymysql
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
import requests
from pathlib import Path

# 加载环境变量
load_dotenv()

class PublicWordsExporter:
    """公共单词导出器"""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化导出器
        
        Args:
            db_url: 数据库连接URL，如果为None则从环境变量获取
        """
        self.db_url = db_url or os.getenv('DATABASE_URL', 'mysql+pymysql://root:123456@localhost/ipv6_education')
        self.connection = None
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
        
    def connect_database(self):
        """连接数据库"""
        try:
            # 解析数据库连接URL
            if self.db_url.startswith('mysql+pymysql://'):
                db_url = self.db_url.replace('mysql+pymysql://', 'mysql://')
            else:
                db_url = self.db_url
            
            parsed = urlparse(db_url)
            
            # 提取连接参数并进行URL解码
            host = parsed.hostname or 'localhost'
            port = parsed.port or 3306
            user = unquote(parsed.username) if parsed.username else 'root'
            password = unquote(parsed.password) if parsed.password else ''
            database = parsed.path.lstrip('/') if parsed.path else 'ipv6_education'
            
            print(f"[INFO] 连接数据库: {host}:{port}/{database} (用户: {user})")
            
            # 连接数据库
            self.connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            print("[OK] 数据库连接成功")
            return True
            
        except Exception as e:
            print(f"[ERROR] 数据库连接失败: {e}")
            return False
    
    def export_public_words(self) -> List[Dict]:
        """
        从数据库导出所有公共单词
        
        Returns:
            List[Dict]: 公共单词列表
        """
        if not self.connection:
            raise Exception("数据库未连接")
        
        try:
            with self.connection.cursor() as cursor:
                # 查询所有公共单词
                sql = """
                SELECT 
                    id, word, language, definition, part_of_speech, 
                    example, tag, usage_count, created_at, updated_at
                FROM public_vocabulary_words 
                ORDER BY language, word
                """
                cursor.execute(sql)
                words = cursor.fetchall()
                
                print(f"[INFO] 从数据库导出了 {len(words)} 个公共单词")
                return words
                
        except Exception as e:
            print(f"[ERROR] 导出公共单词失败: {e}")
            raise
    
    def detect_duplicates(self, words: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        检测重复的单词
        
        Args:
            words: 单词列表
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (唯一单词列表, 重复单词列表)
        """
        print("\n[INFO] 开始检测重复单词...")
        
        # 使用 (word, language) 作为唯一键
        word_map = {}
        duplicates = []
        unique_words = []
        
        for word_data in words:
            key = (word_data['word'].lower().strip(), word_data['language'])
            
            if key in word_map:
                # 发现重复
                existing = word_map[key]
                duplicates.append({
                    'key': key,
                    'existing': existing,
                    'duplicate': word_data
                })
                print(f"[DUPLICATE] 发现重复: {word_data['word']} ({word_data['language']}) - ID: {existing['id']} vs {word_data['id']}")
            else:
                word_map[key] = word_data
                unique_words.append(word_data)
        
        print(f"[INFO] 检测完成: 唯一单词 {len(unique_words)} 个, 重复单词 {len(duplicates)} 个")
        return unique_words, duplicates
    
    def save_to_txt(self, words: List[Dict], duplicates: List[Dict], timestamp: str) -> Dict[str, str]:
        """
        保存数据到txt文件
        
        Args:
            words: 唯一单词列表
            duplicates: 重复单词列表
            timestamp: 时间戳
            
        Returns:
            Dict[str, str]: 生成的文件路径
        """
        files = {}
        
        # 保存唯一单词到CSV格式的txt文件
        unique_file = self.export_dir / f"public_words_unique_{timestamp}.txt"
        with open(unique_file, 'w', encoding='utf-8', newline='') as f:
            # 写入CSV头部
            f.write("id,word,language,definition,part_of_speech,example,tag,usage_count,created_at,updated_at\n")
            
            for word in words:
                # 处理可能包含逗号和引号的字段
                row = [
                    str(word['id']),
                    f'"{word["word"]}"',
                    word['language'],
                    f'"{(word["definition"] or "").replace(chr(34), chr(34)+chr(34))}"',  # 转义引号
                    f'"{word["part_of_speech"] or ""}"',
                    f'"{(word["example"] or "").replace(chr(34), chr(34)+chr(34))}"',  # 转义引号
                    f'"{word["tag"] or ""}"',
                    str(word['usage_count'] or 0),
                    str(word['created_at'] or ''),
                    str(word['updated_at'] or '')
                ]
                f.write(','.join(row) + '\n')
        
        files['unique'] = str(unique_file)
        print(f"[OK] 唯一单词已保存到: {unique_file}")
        
        # 保存重复单词信息
        if duplicates:
            duplicate_file = self.export_dir / f"public_words_duplicates_{timestamp}.txt"
            with open(duplicate_file, 'w', encoding='utf-8') as f:
                f.write("重复单词检测报告\n")
                f.write("=" * 50 + "\n")
                f.write(f"检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"重复项数量: {len(duplicates)}\n\n")
                
                for i, dup in enumerate(duplicates, 1):
                    f.write(f"{i}. 重复单词: {dup['key'][0]} ({dup['key'][1]})\n")
                    f.write(f"   现有记录 ID: {dup['existing']['id']}\n")
                    f.write(f"   重复记录 ID: {dup['duplicate']['id']}\n")
                    f.write(f"   现有定义: {dup['existing']['definition'][:100]}...\n")
                    f.write(f"   重复定义: {dup['duplicate']['definition'][:100]}...\n")
                    f.write("-" * 30 + "\n")
            
            files['duplicates'] = str(duplicate_file)
            print(f"[OK] 重复单词报告已保存到: {duplicate_file}")
        
        # 保存JSON格式（用于程序处理）
        json_file = self.export_dir / f"public_words_data_{timestamp}.json"
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_words': len(words),
            'duplicate_count': len(duplicates),
            'words': words,
            'duplicates': [
                {
                    'word': dup['key'][0],
                    'language': dup['key'][1],
                    'existing_id': dup['existing']['id'],
                    'duplicate_id': dup['duplicate']['id']
                }
                for dup in duplicates
            ]
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        files['json'] = str(json_file)
        print(f"[OK] JSON数据已保存到: {json_file}")
        
        return files
    
    def upload_to_server(self, file_path: str, server_url: str, api_key: Optional[str] = None) -> bool:
        """
        上传文件到服务器
        
        Args:
            file_path: 要上传的文件路径
            server_url: 服务器API地址
            api_key: API密钥（可选）
            
        Returns:
            bool: 上传是否成功
        """
        try:
            print(f"[INFO] 开始上传文件到服务器: {server_url}")
            
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    server_url,
                    files=files,
                    headers=headers,
                    timeout=300  # 5分钟超时
                )
            
            if response.status_code == 200:
                print(f"[OK] 文件上传成功")
                return True
            else:
                print(f"[ERROR] 文件上传失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 上传过程出错: {e}")
            return False
    
    def generate_migration_script(self, words: List[Dict], timestamp: str) -> str:
        """
        生成服务器端的迁移脚本
        
        Args:
            words: 单词列表
            timestamp: 时间戳
            
        Returns:
            str: 脚本文件路径
        """
        script_file = self.export_dir / f"server_migration_script_{timestamp}.py"
        
        script_content = f'''"""
服务器端公共单词导入脚本
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
单词数量: {len(words)}

使用说明:
1. 确保服务器上有 .env 文件，包含 DATABASE_URL 配置
2. 将此脚本和JSON数据文件放在项目根目录
3. 运行: python3 server_migration_script_{timestamp}.py
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
    
    print(f"[INFO] 使用数据库URL: {{db_url.split('@')[0]}}@***")
    
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
    
    print(f"[INFO] 连接参数: host={{host}}, port={{port}}, user={{user}}, database={{database}}")
    
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
        print(f"[INFO] 读取数据文件: {{json_file_path}}")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        words = data['words']
        print(f"[INFO] 准备导入 {{len(words)}} 个单词")
        
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
                    print(f"[INFO] 已处理 {{total_processed}}/{{len(words)}} 个单词 (新增: {{imported_count}}, 更新: {{updated_count}})...")
                    
            except Exception as e:
                print(f"[ERROR] 处理单词失败: {{word['word']}} - {{e}}")
        
        conn.commit()
        
        print("\\n" + "=" * 60)
        print("导入完成!")
        print("=" * 60)
        print(f"总处理数量: {{len(words)}}")
        print(f"新增单词: {{imported_count}}")
        print(f"更新单词: {{updated_count}}")
        print(f"成功率: {{((imported_count + updated_count) / len(words) * 100):.2f}}%")
        
    except Exception as e:
        print(f"[ERROR] 导入过程出错: {{e}}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
        print("[INFO] 数据库连接已关闭")

if __name__ == '__main__':
    # JSON数据文件路径
    json_file = 'public_words_data_{timestamp}.json'
    
    # 检查文件是否存在
    if not os.path.exists(json_file):
        print(f"[ERROR] 数据文件不存在: {{json_file}}")
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
        print("\\n[SUCCESS] 公共单词导入成功完成!")
    except Exception as e:
        print(f"\\n[FAILED] 导入失败: {{e}}")
        exit(1)
'''
        
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"[OK] 服务器迁移脚本已生成: {script_file}")
        return str(script_file)
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("[INFO] 数据库连接已关闭")


def main():
    """主函数"""
    print("=" * 60)
    print("公共单词迁移工具")
    print("=" * 60)
    
    # 创建导出器
    exporter = PublicWordsExporter()
    
    try:
        # 连接数据库
        if not exporter.connect_database():
            return
        
        # 导出公共单词
        print("\n[STEP 1] 导出公共单词...")
        words = exporter.export_public_words()
        
        if not words:
            print("[WARNING] 没有找到公共单词数据")
            return
        
        # 检测重复项
        print("\n[STEP 2] 检测重复单词...")
        unique_words, duplicates = exporter.detect_duplicates(words)
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存到文件
        print("\n[STEP 3] 保存数据到文件...")
        files = exporter.save_to_txt(unique_words, duplicates, timestamp)
        
        # 生成服务器迁移脚本
        print("\n[STEP 4] 生成服务器迁移脚本...")
        script_file = exporter.generate_migration_script(unique_words, timestamp)
        
        # 显示结果
        print("\n" + "=" * 60)
        print("迁移准备完成!")
        print("=" * 60)
        print(f"总单词数: {len(words)}")
        print(f"唯一单词: {len(unique_words)}")
        print(f"重复单词: {len(duplicates)}")
        print(f"\n生成的文件:")
        for file_type, file_path in files.items():
            print(f"  {file_type}: {file_path}")
        print(f"  migration_script: {script_file}")
        
        # 询问是否上传到服务器
        print("\n" + "-" * 40)
        upload_choice = input("是否要上传到服务器? (y/n): ").strip().lower()
        
        if upload_choice in ['y', 'yes']:
            server_url = input("请输入服务器API地址: ").strip()
            api_key = input("请输入API密钥 (可选，直接回车跳过): ").strip() or None
            
            if server_url:
                success = exporter.upload_to_server(files['json'], server_url, api_key)
                if success:
                    print("[OK] 文件已成功上传到服务器")
                else:
                    print("[ERROR] 文件上传失败")
        
        print("\n使用说明:")
        print("1. 将生成的JSON文件和迁移脚本复制到服务器")
        print("2. 在服务器上修改迁移脚本中的数据库配置")
        print("3. 运行迁移脚本导入数据")
        print("4. 如有重复项，请查看重复报告文件进行处理")
        
    except Exception as e:
        print(f"\n[ERROR] 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        exporter.close()


if __name__ == '__main__':
    main()
