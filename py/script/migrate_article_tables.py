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

def migrate_article_tables():
    """
    向generated_articles表添加used_word_ids字段，并创建article_used_words表
    """
    try:
        # 连接数据库
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        print("开始迁移文章相关表...")
        
        # 1. 检查并添加used_word_ids字段到generated_articles表
        cursor.execute("SHOW COLUMNS FROM generated_articles LIKE 'used_word_ids'")
        result = cursor.fetchone()
        if not result:
            cursor.execute("ALTER TABLE generated_articles ADD COLUMN used_word_ids TEXT NULL")
            print("[OK] 已添加used_word_ids字段到generated_articles表")
        else:
            print("[OK] used_word_ids字段已存在")
        
        # 2. 检查并创建article_used_words表
        cursor.execute("SHOW TABLES LIKE 'article_used_words'")
        result = cursor.fetchone()
        if not result:
            cursor.execute("""
                CREATE TABLE article_used_words (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    article_id INT NOT NULL,
                    word_id INT NOT NULL,
                    word_text VARCHAR(100) NOT NULL,
                    occurrence_count INT NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (article_id) REFERENCES generated_articles(id) ON DELETE CASCADE,
                    FOREIGN KEY (word_id) REFERENCES vocabulary_words(id) ON DELETE CASCADE,
                    INDEX idx_article_id (article_id),
                    INDEX idx_word_id (word_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("[OK] 已创建article_used_words表")
        else:
            print("[OK] article_used_words表已存在")
        
        # 提交更改
        conn.commit()
        print("[OK] 数据库迁移完成！")
        
    except pymysql.Error as err:
        print(f"[ERROR] 数据库错误: {err}")
        if 'conn' in locals():
            conn.rollback()
        raise
    except Exception as e:
        print(f"[ERROR] 发生错误: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("开始迁移文章相关数据库表...")
    print("=" * 60)
    migrate_article_tables()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)

