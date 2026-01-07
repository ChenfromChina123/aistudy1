"""
清理公共词库中格式不符的单词记录（独立脚本版本）
删除单词字段包含非英文字符的记录
不依赖app框架，避免模型冲突
"""
import re
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 创建独立的Base
Base = declarative_base()

# 定义简化的PublicVocabularyWord模型（仅用于清理）
class PublicVocabularyWord(Base):
    __tablename__ = 'public_vocabulary_words'
    
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(100), nullable=False, index=True)
    language = Column(String(10), default='en', nullable=False, index=True)
    definition = Column(Text, nullable=False)
    part_of_speech = Column(String(50), nullable=False)
    example = Column(Text, nullable=True)
    tag = Column(String(50), nullable=True, index=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

def is_valid_english_word(word: str) -> bool:
    """
    检查单词是否只包含英文字母、连字符和空格
    
    Args:
        word: 待检查的单词
        
    Returns:
        bool: True表示符合规范，False表示不符合
    """
    if not word:
        return False
    
    # 允许英文字母、连字符、撇号、空格
    # 例如：hello, self-control, don't, ice cream
    pattern = r'^[a-zA-Z\-\'\s]+$'
    return bool(re.match(pattern, word.strip()))

def get_db_connection():
    """
    创建数据库连接
    """
    # 数据库连接配置
    DATABASE_URL = "mysql+pymysql://root:123456@localhost/ipv6_education"
    
    # 创建引擎
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    
    # 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine

def clean_public_words():
    """
    清理公共词库中的不规范数据
    """
    print("=" * 60)
    print("开始清理公共词库数据...")
    print("=" * 60)
    
    # 创建数据库连接
    session, engine = get_db_connection()
    
    try:
        # 查询所有公共词库记录
        all_words = session.query(PublicVocabularyWord).all()
        total_count = len(all_words)
        print(f"\n总记录数: {total_count}")
        
        if total_count == 0:
            print("公共词库为空，无需清理")
            return
        
        # 统计无效记录
        invalid_words = []
        for word_obj in all_words:
            if not is_valid_english_word(word_obj.word):
                invalid_words.append(word_obj)
        
        invalid_count = len(invalid_words)
        print(f"发现不符合规范的记录数: {invalid_count}")
        
        if invalid_count == 0:
            print("\n✅ 所有记录格式正确，无需清理")
            return
        
        # 显示前10个不规范的记录作为示例
        print("\n不规范记录示例（前10个）:")
        print("-" * 60)
        for i, word_obj in enumerate(invalid_words[:10], 1):
            print(f"{i}. ID: {word_obj.id}, 单词: '{word_obj.word}', 语言: {word_obj.language}")
        
        if invalid_count > 10:
            print(f"... 还有 {invalid_count - 10} 条不规范记录")
        
        # 询问用户是否继续
        print("\n" + "=" * 60)
        confirm = input(f"是否删除这 {invalid_count} 条不规范记录? (yes/no): ").strip().lower()
        
        if confirm not in ['yes', 'y']:
            print("操作已取消")
            return
        
        # 删除不规范记录
        print("\n开始删除不规范记录...")
        deleted_count = 0
        
        for word_obj in invalid_words:
            try:
                session.delete(word_obj)
                deleted_count += 1
                if deleted_count % 100 == 0:
                    print(f"已删除 {deleted_count}/{invalid_count} 条记录...")
            except Exception as e:
                print(f"删除记录 ID {word_obj.id} 失败: {str(e)}")
        
        # 提交更改
        session.commit()
        
        # 统计清理结果
        remaining_count = session.query(PublicVocabularyWord).count()
        
        print("\n" + "=" * 60)
        print("清理完成！")
        print("=" * 60)
        print(f"原始记录数: {total_count}")
        print(f"删除记录数: {deleted_count}")
        print(f"剩余记录数: {remaining_count}")
        print(f"清理率: {(deleted_count/total_count*100):.2f}%")
        
    except Exception as e:
        print(f"\n❌ 清理过程出错: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

def show_statistics():
    """
    显示公共词库统计信息
    """
    print("\n" + "=" * 60)
    print("公共词库统计信息")
    print("=" * 60)
    
    # 创建数据库连接
    session, engine = get_db_connection()
    
    try:
        from sqlalchemy import func
        
        # 按语言统计
        language_stats = session.query(
            PublicVocabularyWord.language,
            func.count(PublicVocabularyWord.id).label('count')
        ).group_by(PublicVocabularyWord.language).all()
        
        print("\n按语言分类:")
        for lang, count in language_stats:
            print(f"  {lang}: {count} 个单词")
        
        # 总数
        total = session.query(PublicVocabularyWord).count()
        print(f"\n总计: {total} 个单词")
        
        # 检查无效记录
        all_words = session.query(PublicVocabularyWord).all()
        invalid_count = sum(1 for w in all_words if not is_valid_english_word(w.word))
        valid_count = total - invalid_count
        
        print(f"\n数据质量:")
        print(f"  ✅ 格式正确: {valid_count} ({valid_count/total*100:.2f}%)")
        print(f"  ❌ 格式错误: {invalid_count} ({invalid_count/total*100:.2f}%)")
        
    except Exception as e:
        print(f"\n❌ 统计过程出错: {str(e)}")
    finally:
        session.close()
        engine.dispose()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='清理公共词库中格式不符的单词')
    parser.add_argument('--stats', action='store_true', help='仅显示统计信息，不执行清理')
    parser.add_argument('--force', action='store_true', help='强制执行清理，不询问确认')
    
    args = parser.parse_args()
    
    if args.stats:
        show_statistics()
    else:
        if args.force:
            # 如果强制执行，修改clean_public_words函数跳过确认
            import builtins
            original_input = builtins.input
            builtins.input = lambda _: 'yes'
            try:
                clean_public_words()
            finally:
                builtins.input = original_input
        else:
            clean_public_words()
        
        # 清理后显示统计
        show_statistics()

