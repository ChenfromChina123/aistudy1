"""
语言学习模块 - 数据库模型
包含所有与语言学习相关的数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

# 从app框架导入Base
try:
    from app import Base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


# 单词表模型
class VocabularyList(Base):
    __tablename__ = "vocabulary_lists"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    language = Column(String(10), default='en', nullable=False, index=True)  # 语言代码：en, zh, ja, ko, fr, de, es等
    is_preset = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    created_by = Column(Integer)  # 普通整数列，与app框架保持一致
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # 关系
    words = relationship('VocabularyWord', back_populates='vocabulary_list', cascade='all, delete-orphan')


# 单词模型
class VocabularyWord(Base):
    __tablename__ = 'vocabulary_words'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    vocabulary_list_id = Column(Integer, ForeignKey('vocabulary_lists.id'), nullable=False)
    word = Column(String(100), nullable=False, index=True)
    definition = Column(Text, nullable=True)
    part_of_speech = Column(String(50), nullable=True)
    example = Column(Text, nullable=True)
    language = Column(String(10), default='en', nullable=False, index=True)  # 语言代码
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    # 关系
    vocabulary_list = relationship('VocabularyList', back_populates='words')
    user_progress = relationship('UserWordProgress', back_populates='word', cascade='all, delete-orphan')


# 用户单词进度模型
class UserWordProgress(Base):
    __tablename__ = 'user_word_progress'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # 不使用外键约束，与app框架保持一致
    word_id = Column(Integer, ForeignKey('vocabulary_words.id'), nullable=False)
    mastery_level = Column(Integer, default=0)  # 0-5 表示掌握程度
    last_reviewed = Column(DateTime, nullable=True)
    next_review_date = Column(DateTime, nullable=True)
    review_count = Column(Integer, default=0)
    is_difficult = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # 关系
    word = relationship('VocabularyWord', back_populates='user_progress')


# 公共单词库模型
class PublicVocabularyWord(Base):
    __tablename__ = 'public_vocabulary_words'
    __table_args__ = (
        {'extend_existing': True},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(100), nullable=False, index=True)  # 移除unique约束，因为不同语言的单词可能相同
    language = Column(String(10), default='en', nullable=False, index=True)  # 语言代码
    definition = Column(Text, nullable=False)  # 经过AI处理的标准释义
    part_of_speech = Column(String(50), nullable=False)  # 经过AI处理的标准词性
    example = Column(Text, nullable=True)  # 示例句子
    tag = Column(String(50), nullable=True, index=True)  # 标签：四级、六级、托福、雅思等
    usage_count = Column(Integer, default=0)  # 被使用的次数
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))


# 用户学习记录模型
class UserLearningRecord(Base):
    __tablename__ = 'user_learning_records'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # 不使用外键约束，与app框架保持一致
    activity_type = Column(String(50), nullable=False)  # vocabulary_review, article_reading 等
    activity_details = Column(Text, nullable=True)  # JSON格式的活动详情
    duration = Column(Integer, nullable=True)  # 持续时间（秒）
    created_at = Column(DateTime, default=datetime.now(UTC))


# AI生成文章模型
class GeneratedArticle(Base):
    __tablename__ = 'generated_articles'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # 不使用外键约束，与app框架保持一致
    vocabulary_list_id = Column(Integer, ForeignKey('vocabulary_lists.id'), nullable=True)
    topic = Column(String(255), nullable=True)  # 文章主题
    difficulty_level = Column(String(50), nullable=True)  # 难度级别
    article_length = Column(String(50), nullable=True)  # 文章长度
    original_text = Column(Text, nullable=False)  # 文章原文
    translated_text = Column(Text, nullable=True)  # 文章翻译
    used_word_ids = Column(Text, nullable=True)  # JSON格式存储使用的单词ID列表
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    # 关系
    vocabulary_list = relationship('VocabularyList')
    used_words = relationship('ArticleUsedWord', back_populates='article', cascade='all, delete-orphan')


# 文章使用单词关联模型
class ArticleUsedWord(Base):
    __tablename__ = 'article_used_words'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('generated_articles.id'), nullable=False)
    word_id = Column(Integer, ForeignKey('vocabulary_words.id'), nullable=False)
    word_text = Column(String(100), nullable=False)  # 单词文本（冗余字段，便于查询）
    occurrence_count = Column(Integer, default=1)  # 在文章中出现的次数
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    # 关系
    article = relationship('GeneratedArticle', back_populates='used_words')
    word = relationship('VocabularyWord')


# 词汇上传任务模型
class VocabularyUploadTask(Base):
    __tablename__ = 'vocabulary_upload_tasks'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)  # 任务唯一标识
    vocabulary_list_id = Column(Integer, nullable=True)  # 关联的单词表ID
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    progress = Column(Integer, default=0)  # 进度百分比 0-100
    total_words = Column(Integer, default=0)  # 总单词数
    processed_words = Column(Integer, default=0)  # 已处理单词数
    message = Column(Text, nullable=True)  # 状态消息
    error_message = Column(Text, nullable=True)  # 错误消息
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

