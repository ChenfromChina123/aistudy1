"""
语言学习模块 - 向后兼容入口
此文件保持向后兼容，同时从新的模块化结构导入模型和功能
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request, BackgroundTasks
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, func, or_, and_
from sqlalchemy.orm import relationship, Session
import json
from datetime import datetime, timedelta, UTC
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import os
import re
import uuid
import logging
from fastapi.responses import JSONResponse, StreamingResponse, Response
import asyncio
from enum import Enum

# 统一使用app框架下的配置
try:
    from app import get_db, Base, logger, verify_jwt
    logger.info("成功导入app框架配置")
except Exception as e:
    # 如果无法从app导入，则使用基本配置
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"无法从app导入配置: {str(e)}，使用基本配置")
    
    # 基本配置作为备选
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    
    Base = declarative_base()
    
    # 数据库配置
    DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:123456@localhost/ipv6_education')
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # JWT验证备选函数
    def verify_jwt(token):
        return {"sub": "1"}  # 假设用户ID为1

# 加载统一配置（用于读取API密钥等）
try:
    from config import settings as app_settings
except Exception:
    app_settings = None

# 尝试从模块化结构导入模型（向后兼容）
try:
    from models.language_learning import (
        VocabularyList, VocabularyWord, UserWordProgress, PublicVocabularyWord,
        UserLearningRecord, GeneratedArticle, ArticleUsedWord, VocabularyUploadTask
    )
    logger.info("从模块化结构导入数据库模型成功")
    _models_imported = True
except ImportError:
    # 如果导入失败，使用原有定义（向后兼容）
    logger.info("使用原有数据库模型定义")
    _models_imported = False

# 只有在导入失败时才定义模型类
if not _models_imported:
    # 数据库表定义 - 与app框架保持一致
    # 使用extend_existing=True防止重复定义表
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
        topic = Column(String(255), nullable=True)
        difficulty_level = Column(String(50), nullable=True)
        article_length = Column(String(50), nullable=True)
        original_text = Column(Text, nullable=False)
        translated_text = Column(Text, nullable=True)
        used_word_ids = Column(Text, nullable=True)  # JSON格式存储使用的单词ID列表
        created_at = Column(DateTime, default=datetime.now(UTC))
        
        # 关系
        vocabulary_list = relationship('VocabularyList')
        used_words = relationship('ArticleUsedWord', back_populates='article', cascade='all, delete-orphan')

    # 文章使用的单词模型
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

    # 单词表处理任务状态模型
    class VocabularyUploadTask(Base):
        __tablename__ = 'vocabulary_upload_tasks'
        __table_args__ = {'extend_existing': True}
        
        id = Column(Integer, primary_key=True, index=True)
        task_id = Column(String(100), unique=True, nullable=False, index=True)  # 任务ID
        user_id = Column(Integer, nullable=False)
        vocabulary_list_id = Column(Integer, ForeignKey('vocabulary_lists.id'), nullable=True)
        status = Column(String(50), default='pending')  # pending, processing, completed, failed
        progress = Column(Integer, default=0)  # 0-100 表示处理进度
        total_words = Column(Integer, default=0)  # 总单词数
        processed_words = Column(Integer, default=0)  # 已处理单词数
        message = Column(Text, nullable=True)  # 状态消息
        error_message = Column(Text, nullable=True)  # 错误消息
        created_at = Column(DateTime, default=datetime.now(UTC))
        updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
        
        # 关系
        vocabulary_list = relationship('VocabularyList')

# 尝试从模块化结构导入Schemas（向后兼容）
try:
    from schemas.language_learning import (
        VocabularyWordCreate, VocabularyListCreate, VocabularyListResponse,
        ArticleGenerationRequest, UserProgressUpdate
    )
    logger.info("从模块化结构导入Schemas成功")
except ImportError:
    # 如果导入失败，使用原有定义（向后兼容）
    logger.info("使用原有Schemas定义")
    # 数据模型类
    class VocabularyWordCreate(BaseModel):
        word: str
        definition: Optional[str] = None
        part_of_speech: Optional[str] = None
        example: Optional[str] = None
        language: Optional[str] = 'en'  # 语言代码，默认英语

    class VocabularyListCreate(BaseModel):
        name: str
        description: Optional[str] = None
        language: Optional[str] = 'en'  # 语言代码，默认英语
        words: List[VocabularyWordCreate]

    class VocabularyListResponse(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        
        id: int
        name: str
        description: Optional[str]
        language: Optional[str] = 'en'  # 语言代码
        is_preset: bool
        word_count: int
        created_at: datetime

    class ArticleGenerationRequest(BaseModel):
        model_config = ConfigDict(extra="allow")  # 允许额外字段，支持public_word_ids等
        
        vocabulary_list_id: Optional[int] = None
        selected_word_ids: Optional[List[int]] = None
        public_word_ids: Optional[List[int]] = None  # 系统词库（公共词库）单词ID列表
        topic: Optional[str] = None
        difficulty_level: str = "intermediate"
        article_length: str = "medium"
        language: Optional[str] = 'en'  # 文章语言，默认英语
        custom_words: Optional[List[str]] = None  # 自定义单词列表（前端可能发送）

    class UserProgressUpdate(BaseModel):
        word_id: int
        mastery_level: int
        is_difficult: bool = False

# 修改现有预设单词表数据，添加更多常用单词
def init_preset_vocabulary_lists(db: Session):
    """初始化预设单词表数据"""
    try:
        # 检查是否已存在预设单词表
        existing = db.query(func.count(VocabularyList.id)).filter(VocabularyList.is_preset == True).scalar()
        if existing > 0:
            logger.info(f"预设单词表已存在: {existing} 个")
            return
        
        logger.info("开始初始化预设单词表...")
        
        # 基础英语单词表 - 扩充版本
        basic_words = [
            {"word": "hello", "definition": "你好", "part_of_speech": "interjection", "example": "Hello, how are you?"},
            {"word": "good", "definition": "好的", "part_of_speech": "adjective", "example": "That's a good idea."},
            {"word": "time", "definition": "时间", "part_of_speech": "noun", "example": "What time is it?"},
            {"word": "day", "definition": "天，日", "part_of_speech": "noun", "example": "Have a nice day!"},
            {"word": "man", "definition": "男人", "part_of_speech": "noun", "example": "He is a good man."},
            {"word": "woman", "definition": "女人", "part_of_speech": "noun", "example": "She is a smart woman."},
            {"word": "world", "definition": "世界", "part_of_speech": "noun", "example": "The world is beautiful."},
            {"word": "work", "definition": "工作", "part_of_speech": "verb/noun", "example": "I go to work every day."},
            {"word": "study", "definition": "学习", "part_of_speech": "verb/noun", "example": "I study English every day."},
            {"word": "home", "definition": "家", "part_of_speech": "noun", "example": "I'm going home."},
            {"word": "book", "definition": "书", "part_of_speech": "noun", "example": "I like reading books."},
            {"word": "student", "definition": "学生", "part_of_speech": "noun", "example": "He is a university student."},
            {"word": "teacher", "definition": "教师", "part_of_speech": "noun", "example": "My teacher is very kind."},
            {"word": "language", "definition": "语言", "part_of_speech": "noun", "example": "English is an important language."},
            {"word": "computer", "definition": "电脑", "part_of_speech": "noun", "example": "I use my computer to study."},
            {"word": "friend", "definition": "朋友", "part_of_speech": "noun", "example": "He is my best friend."},
            {"word": "school", "definition": "学校", "part_of_speech": "noun", "example": "I go to school by bus."},
            {"word": "question", "definition": "问题", "part_of_speech": "noun", "example": "May I ask you a question?"},
            {"word": "answer", "definition": "回答", "part_of_speech": "noun/verb", "example": "Can you answer my question?"},
            {"word": "name", "definition": "名字", "part_of_speech": "noun", "example": "What is your name?"},
            {"word": "number", "definition": "数字", "part_of_speech": "noun", "example": "What's your phone number?"},
            {"word": "email", "definition": "电子邮件", "part_of_speech": "noun", "example": "Please send me an email."},
            {"word": "phone", "definition": "电话", "part_of_speech": "noun", "example": "I'll call you on the phone."},
            {"word": "address", "definition": "地址", "part_of_speech": "noun", "example": "What is your address?"},
            {"word": "food", "definition": "食物", "part_of_speech": "noun", "example": "I love Chinese food."},
            {"word": "apple", "definition": "苹果", "part_of_speech": "n.", "example": "I eat an apple every day."},
            {"word": "love", "definition": "爱", "part_of_speech": "v./n.", "example": "I love my family."},
        ]
        
        # 商务英语单词表 - 扩充版本
        business_words = [
            {"word": "meeting", "definition": "会议", "part_of_speech": "noun", "example": "We have a meeting tomorrow."},
            {"word": "project", "definition": "项目", "part_of_speech": "noun", "example": "I'm working on a new project."},
            {"word": "team", "definition": "团队", "part_of_speech": "noun", "example": "We're a great team."},
            {"word": "client", "definition": "客户", "part_of_speech": "noun", "example": "We need to meet our client."},
            {"word": "deadline", "definition": "截止日期", "part_of_speech": "noun", "example": "We must meet the deadline."},
            {"word": "report", "definition": "报告", "part_of_speech": "noun/verb", "example": "I need to write a report."},
            {"word": "budget", "definition": "预算", "part_of_speech": "noun", "example": "We have a tight budget."},
            {"word": "market", "definition": "市场", "part_of_speech": "noun", "example": "The market is growing."},
            {"word": "strategy", "definition": "策略", "part_of_speech": "noun", "example": "We need a new strategy."},
            {"word": "product", "definition": "产品", "part_of_speech": "noun", "example": "Our product is very popular."},
            {"word": "contract", "definition": "合同", "part_of_speech": "n.", "example": "We signed a contract."},
            {"word": "proposal", "definition": "提案", "part_of_speech": "n.", "example": "Let's discuss the proposal."},
        ]
        
        # 旅游英语单词表 - 扩充版本
        travel_words = [
            {"word": "airport", "definition": "机场", "part_of_speech": "noun", "example": "The airport is very busy."},
            {"word": "hotel", "definition": "酒店", "part_of_speech": "noun", "example": "We booked a hotel near the beach."},
            {"word": "ticket", "definition": "票", "part_of_speech": "noun", "example": "Do you have your ticket?"},
            {"word": "passport", "definition": "护照", "part_of_speech": "noun", "example": "Don't forget your passport."},
            {"word": "direction", "definition": "方向", "part_of_speech": "noun", "example": "Can you give me directions?"},
            {"word": "restaurant", "definition": "餐厅", "part_of_speech": "noun", "example": "Let's go to a restaurant."},
            {"word": "menu", "definition": "菜单", "part_of_speech": "noun", "example": "May I see the menu?"},
            {"word": "tourist", "definition": "游客", "part_of_speech": "noun", "example": "There are many tourists here."},
            {"word": "attraction", "definition": "景点", "part_of_speech": "noun", "example": "What's the main attraction here?"},
            {"word": "map", "definition": "地图", "part_of_speech": "noun", "example": "Do you have a map?"},
            {"word": "camera", "definition": "相机", "part_of_speech": "n.", "example": "I took many photos with my camera."},
            {"word": "luggage", "definition": "行李", "part_of_speech": "n.", "example": "My luggage is heavy."},
            {"word": "destination", "definition": "目的地", "part_of_speech": "n.", "example": "What's your destination?"},
        ]
        
        # 创建预设单词表
        lists_to_create = [
            {"name": "英语基础词汇", "description": "日常生活中最常用的基础英语单词", "words": basic_words},
            {"name": "商务英语词汇", "description": "工作和商务环境中常用的英语词汇", "words": business_words},
            {"name": "旅游英语词汇", "description": "旅游和出行中必备的英语词汇", "words": travel_words}
        ]
        
        for list_data in lists_to_create:
            # 创建单词表记录
            vocab_list = VocabularyList(
                name=list_data["name"],
                description=list_data["description"],
                is_preset=True,
                is_public=True,
                created_by=1  # 使用管理员用户ID
            )
            db.add(vocab_list)
            db.flush()  # 获取ID但不提交事务
            
            # 添加单词
            for word_data in list_data["words"]:
                vocabulary_word = VocabularyWord(
                    vocabulary_list_id=vocab_list.id,
                    word=word_data["word"],
                    definition=word_data["definition"],
                    part_of_speech=word_data["part_of_speech"],
                    example=word_data["example"]
                )
                db.add(vocabulary_word)
        
        db.commit()
        logger.info(f"成功创建 {len(lists_to_create)} 个预设单词表")
        
    except Exception as e:
        db.rollback()
        logger.error(f"初始化预设单词表失败: {str(e)}")

# 使用AI生成指定标签的单词列表并添加到公共单词库
def generate_preset_words_with_ai(db: Session, tag: str, count: int = 100, language: str = 'en'):
    """
    使用AI生成指定标签的单词列表并添加到公共单词库
    
    Args:
        db: 数据库会话
        tag: 标签（如：四级、六级、托福、雅思等）
        count: 要生成的单词数量
        language: 语言代码，默认'en'
    """
    from openai import OpenAI
    import os
    
    try:
        deepseek_api_key = (
            app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY else os.getenv("DEEPSEEK_API_KEY")
        )
        deepseek_api_key = deepseek_api_key.strip() if deepseek_api_key else None
        if not deepseek_api_key:
            logger.error("DeepSeek API密钥未设置，无法生成单词")
            return
        
        # 检查是否已存在该标签的单词
        existing_count = db.query(func.count(PublicVocabularyWord.id)).filter(
            PublicVocabularyWord.tag == tag,
            PublicVocabularyWord.language == language
        ).scalar()
        
        if existing_count >= count:
            logger.info(f"标签'{tag}'已有{existing_count}个单词，跳过生成")
            return
        
        remaining_count = count - existing_count
        logger.info(f"开始为标签'{tag}'生成{remaining_count}个单词...")
        
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        language_name = get_language_name(language)
        
        # 根据标签生成不同的提示词
        tag_descriptions = {
            "四级": "大学英语四级考试(CET-4)的核心词汇，难度适中，适合大学生学习",
            "六级": "大学英语六级考试(CET-6)的核心词汇，难度较高，适合有一定基础的学习者",
            "托福": "TOEFL考试的核心词汇，学术性强，适合准备出国留学的学生",
            "雅思": "IELTS考试的核心词汇，涵盖学术和日常场景，适合准备出国的人员",
            "考研": "研究生入学考试英语词汇，难度较高，适合准备考研的学生",
            "GRE": "GRE考试的核心词汇，学术难度高，适合准备申请研究生的人员",
            "SAT": "SAT考试的核心词汇，适合准备申请美国本科的学生",
        }
        
        tag_description = tag_descriptions.get(tag, f"{tag}相关的常用{language_name}单词")
        
        # 分批生成，每次生成100个单词，避免token限制
        batch_size = 100  # 每批生成100个单词
        total_added = 0
        batch_number = 0
        
        while total_added < remaining_count:
            batch_number += 1
            batch_target = min(batch_size, remaining_count - total_added)
            
            logger.info(f"第{batch_number}批：生成{batch_target}个单词（已完成{total_added}/{remaining_count}）")
            
            # 生成单词列表的提示词
            prompt = f"""
请生成{batch_target}个{language_name}单词，这些单词应该符合以下要求：
- 标签：{tag}
- 描述：{tag_description}
- 单词难度：根据标签选择合适难度的单词
- 单词类型：应该包含各种词性（名词、动词、形容词、副词等）
- 单词长度：建议4-15个字母，避免过短或过长的单词
- 单词频率：选择该标签下常见且重要的单词

请以JSON数组格式返回，每个对象包含以下字段：
1. word: 单词（小写）
2. definition: 准确的中文释义
3. part_of_speech: 词性（如noun、verb、adjective、adverb等，不要使用缩写）
4. example: 一个简单的英文例句

示例格式：
[
  {{"word": "example", "definition": "例子", "part_of_speech": "noun", "example": "This is a good example."}},
  {{"word": "demonstrate", "definition": "证明，展示", "part_of_speech": "verb", "example": "The experiment demonstrates the theory."}}
]

请确保：
1. 返回的单词不重复
2. 单词是该标签下的常见词汇
3. JSON格式正确，可以被直接解析
4. 返回的单词数量尽量接近{batch_target}个
5. 只返回JSON数组，不要添加任何其他文字说明
"""
            
            system_content = f"你是一位专业的{language_name}词汇专家，擅长根据考试标签生成合适难度的单词列表。请严格按照要求的JSON格式返回结果，只返回JSON数组，不要添加任何解释文字。"
            
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,  # 稍微提高温度以增加多样性
                    max_tokens=8000  # DeepSeek API最大支持8192，设置为8000确保安全
                )
                
                ai_content = response.choices[0].message.content.strip()
                logger.info(f"AI生成响应长度: {len(ai_content)} 字符")
                
                # 提取JSON数组 - 改进正则表达式，匹配可能的截断情况
                json_match = re.search(r'\[.*?\]', ai_content, re.DOTALL)
                if not json_match:
                    # 尝试查找不完整的JSON数组（可能被截断）
                    json_match = re.search(r'\[.*', ai_content, re.DOTALL)
                    if json_match:
                        # 尝试修复不完整的JSON
                        incomplete_json = json_match.group()
                        # 尝试找到最后一个完整的对象
                        last_complete = incomplete_json.rfind('}')
                        if last_complete > 0:
                            incomplete_json = incomplete_json[:last_complete + 1] + ']'
                            json_match = type('Match', (), {'group': lambda: incomplete_json})()
                            logger.warning("检测到JSON被截断，尝试修复...")
                
                if not json_match:
                    logger.error(f"第{batch_number}批：无法从AI响应中提取JSON数组")
                    logger.debug(f"AI响应内容（前500字符）: {ai_content[:500]}")
                    logger.debug(f"AI响应内容（后500字符）: {ai_content[-500:]}")
                    # 继续下一批，不直接返回
                    if batch_number >= 3:  # 如果连续3批都失败，停止
                        logger.error(f"连续3批生成失败，停止生成")
                        break
                    continue  # 跳到while循环的下一次迭代
                
                try:
                    words_list = json.loads(json_match.group())
                    logger.info(f"第{batch_number}批：AI生成了{len(words_list)}个单词")
                except json.JSONDecodeError as e:
                    logger.error(f"第{batch_number}批：JSON解析失败: {str(e)}")
                    logger.debug(f"JSON内容（前1000字符）: {json_match.group()[:1000]}")
                    if batch_number >= 3:
                        break
                    continue  # 跳到while循环的下一次迭代
                
                # 获取已存在的单词（检查所有相同语言的单词，避免唯一索引冲突）
                # 每次批次开始前都重新查询，确保获取最新的单词列表（包括上一批刚添加的）
                existing_words = set(
                    db.query(PublicVocabularyWord.word).filter(
                        PublicVocabularyWord.language == language
                    ).all()
                )
                existing_words = {w[0].lower() for w in existing_words}
                if batch_number == 1:
                    logger.info(f"已存在{len(existing_words)}个{language_name}单词（所有标签）")
                
                # 添加单词到数据库
                batch_added = 0
                batch_skipped = 0
                
                for word_data in words_list:
                    try:
                        if not word_data or not isinstance(word_data, dict):
                            continue
                        
                        word = word_data.get('word', '').strip().lower()
                        if not word or len(word) < 2:
                            continue
                        
                        # 检查是否已存在
                        if word in existing_words:
                            batch_skipped += 1
                            continue
                        
                        definition = word_data.get('definition', '').strip()
                        part_of_speech = word_data.get('part_of_speech', '').strip()
                        example = word_data.get('example', '').strip()
                        
                        if not definition or not part_of_speech:
                            logger.warning(f"单词'{word}'缺少必要信息，跳过")
                            continue
                        
                        # 创建公共单词记录
                        public_word = PublicVocabularyWord(
                            word=word,
                            language=language,
                            definition=definition,
                            part_of_speech=part_of_speech,
                            example=example,
                            tag=tag,
                            usage_count=0
                        )
                        db.add(public_word)
                        existing_words.add(word)  # 添加到已存在集合，避免本次批量添加中的重复
                        batch_added += 1
                        total_added += 1
                        
                    except Exception as e:
                        # 如果是唯一索引冲突，记录并跳过
                        if 'Duplicate' in str(e) or '1062' in str(e):
                            logger.debug(f"单词'{word_data.get('word', '')}'已存在（全局唯一索引），跳过")
                            existing_words.add(word)  # 添加到已存在集合
                            batch_skipped += 1
                        else:
                            logger.error(f"添加单词失败: {word_data}, 错误: {str(e)}")
                        # 回滚当前单词的添加，但保留在内存中的 existing_words 集合
                        try:
                            db.rollback()
                        except:
                            pass
                        continue
                
                # 每批提交一次，避免数据丢失
                try:
                    db.commit()
                    logger.info(f"第{batch_number}批：成功添加{batch_added}个单词，跳过{batch_skipped}个重复单词（累计：{total_added}/{remaining_count}）")
                except Exception as commit_error:
                    # 提交失败，回滚整个批次
                    db.rollback()
                    logger.warning(f"第{batch_number}批：提交失败，尝试逐个添加: {str(commit_error)}")
                    
                    # 重新查询已存在的单词（包括数据库中的和之前批次添加的）
                    existing_words = set(
                        db.query(PublicVocabularyWord.word).filter(
                            PublicVocabularyWord.language == language
                        ).all()
                    )
                    existing_words = {w[0].lower() for w in existing_words}
                    
                    # 重新处理这批单词，逐个添加并跳过重复的
                    batch_added = 0
                    batch_skipped = 0
                    for word_data in words_list:
                        if not word_data or not isinstance(word_data, dict):
                            continue
                        
                        word = word_data.get('word', '').strip().lower()
                        if not word or len(word) < 2:
                            continue
                        
                        # 检查是否已存在
                        if word in existing_words:
                            batch_skipped += 1
                            continue
                        
                        definition = word_data.get('definition', '').strip()
                        part_of_speech = word_data.get('part_of_speech', '').strip()
                        example = word_data.get('example', '').strip()
                        
                        if not definition or not part_of_speech:
                            continue
                        
                        try:
                            public_word = PublicVocabularyWord(
                                word=word,
                                language=language,
                                definition=definition,
                                part_of_speech=part_of_speech,
                                example=example,
                                tag=tag,
                                usage_count=0
                            )
                            db.add(public_word)
                            db.commit()  # 每个单词单独提交
                            existing_words.add(word)
                            batch_added += 1
                            total_added += 1
                        except Exception as e:
                            db.rollback()
                            if 'Duplicate' in str(e) or '1062' in str(e):
                                existing_words.add(word)
                                batch_skipped += 1
                            else:
                                logger.error(f"添加单词'{word}'失败: {str(e)}")
                    
                    logger.info(f"第{batch_number}批：重新处理后添加{batch_added}个单词，跳过{batch_skipped}个重复单词（累计：{total_added}/{remaining_count}）")
                
                # 如果这批没有添加任何单词，可能是重复太多，停止
                if batch_added == 0 and batch_skipped > 0:
                    logger.warning(f"第{batch_number}批：所有单词都重复，可能已达到目标数量")
                    break
                
                # 短暂延迟，避免API限流
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"第{batch_number}批：API调用失败: {str(e)}")
                db.rollback()  # 确保回滚事务
                if batch_number >= 3:
                    break
                continue
        
        logger.info(f"标签'{tag}'生成完成：总共添加{total_added}个单词（目标：{remaining_count}）")
        
    except json.JSONDecodeError as e:
        logger.error(f"解析AI返回的JSON失败: {str(e)}")
        logger.debug(f"AI响应内容: {ai_content[:1000] if 'ai_content' in locals() else 'N/A'}")
        db.rollback()
    except Exception as e:
        logger.error(f"生成预设单词失败（标签：{tag}）: {str(e)}", exc_info=True)
        db.rollback()

# 初始化所有标签的预设单词
def init_all_preset_words(db: Session):
    """初始化所有标签的预设单词"""
    tags = ["四级", "六级", "托福", "雅思", "考研", "GRE", "SAT"]
    word_counts = {
        "四级": 500,
        "六级": 500,
        "托福": 800,
        "雅思": 800,
        "考研": 600,
        "GRE": 1000,
        "SAT": 600,
    }
    
    logger.info("开始初始化所有标签的预设单词...")
    for tag in tags:
        count = word_counts.get(tag, 500)
        try:
            generate_preset_words_with_ai(db, tag, count, 'en')
            logger.info(f"标签'{tag}'的单词生成完成")
        except Exception as e:
            logger.error(f"标签'{tag}'的单词生成失败: {str(e)}")
            continue
    
    logger.info("所有标签的预设单词初始化完成")

# 辅助函数：获取当前用户 - 与app框架兼容版本
async def get_current_user(request: Any, db: Session) -> dict:
    """获取当前用户，返回用户信息字典而不是User对象
    支持从Authorization头或查询参数中获取token
    """
    token = None
    
    # 首先尝试从Authorization头获取
    auth_header = request.headers.get("Authorization")
    if auth_header:
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header
        logger.debug("从Authorization头获取token")
    
    # 如果头中没有token，尝试从查询参数获取
    if not token:
        try:
            # FastAPI的query_params是一个QueryParams对象，可以直接使用get方法
            if hasattr(request, 'query_params'):
                token = request.query_params.get("token")
                if token:
                    logger.debug("从查询参数获取token")
        except Exception as e:
            logger.warning(f"从查询参数获取token失败: {str(e)}")
    
    if not token:
        logger.error("未找到认证令牌（既不在Authorization头，也不在查询参数中）")
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    
    logger.debug(f"找到token，长度: {len(token)}，前10个字符: {token[:10]}...")
    
    try:
        payload = verify_jwt(token)
        
        # 检查是否有错误
        if not payload or (isinstance(payload, dict) and 'error' in payload):
            error_msg = payload.get('error', 'Token验证失败') if payload else 'Token验证失败'
            logger.error(f"JWT验证失败: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)
        
        # verify_jwt返回的是 {"user_id": ..., "username": ...}
        # 但JWT payload本身可能包含 "sub" 字段
        # 优先从返回的字典获取，如果失败则尝试从原始JWT payload获取
        user_id = payload.get("user_id") or payload.get("sub")
        
        # 如果还是没有，尝试直接解析JWT获取sub字段
        if not user_id:
            try:
                import jwt
                from config import settings
                decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"], options={"verify_signature": False})
                user_id = decoded.get("sub") or decoded.get("user_id")
            except:
                pass
        
        if not user_id:
            logger.error(f"JWT payload中没有用户ID，payload: {payload}")
            raise HTTPException(status_code=401, detail="无效的认证令牌")
        
        # 返回用户信息字典而不是User对象，确保ID是整数
        user_dict = {"id": int(user_id) if user_id else None}
        logger.info(f"获取当前用户成功: user_id={user_dict['id']}")
        return user_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户认证失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"用户认证失败: {str(e)}")

def check_vocabulary_permission(vocab_list: VocabularyList, current_user: dict) -> bool:
    """
    统一检查单词表访问权限
    返回True表示有权限，False表示无权限
    """
    # 预设单词表所有人都可以访问
    if vocab_list.is_preset:
        logger.debug(f"单词表{vocab_list.id}是预设单词表，允许访问")
        return True
    
    # 获取用户ID（可能是整数或字符串）
    user_id = current_user.get('id')
    if user_id is None:
        logger.warning(f"用户ID为空，拒绝访问单词表{vocab_list.id}")
        return False
    
    # 统一转换为整数进行比较（更可靠）
    try:
        created_by_int = int(vocab_list.created_by) if vocab_list.created_by is not None else None
        user_id_int = int(user_id) if user_id is not None else None
        
        has_permission = created_by_int == user_id_int
        if not has_permission:
            logger.debug(f"权限检查失败: 单词表{vocab_list.id}的创建者={created_by_int}, 当前用户={user_id_int}")
        return has_permission
    except (ValueError, TypeError) as e:
        logger.error(f"权限检查时类型转换失败: created_by={vocab_list.created_by}({type(vocab_list.created_by)}), user_id={user_id}({type(user_id)}), 错误: {str(e)}")
        # 降级到字符串比较
    created_by_str = str(vocab_list.created_by) if vocab_list.created_by is not None else None
    user_id_str = str(user_id) if user_id is not None else None
    return created_by_str == user_id_str

# API端点函数

# 语言代码到语言名称的映射
LANGUAGE_MAP = {
    'en': '英语',
    'zh': '中文',
    'ja': '日语',
    'ko': '韩语',
    'fr': '法语',
    'de': '德语',
    'es': '西班牙语',
    'it': '意大利语',
    'pt': '葡萄牙语',
    'ru': '俄语',
    'ar': '阿拉伯语',
    'th': '泰语',
    'vi': '越南语',
    'hi': '印地语',
    'tr': '土耳其语'
}

def get_language_name(language_code: str) -> str:
    """获取语言名称"""
    return LANGUAGE_MAP.get(language_code.lower(), language_code.upper())

def detect_language_from_text(text: str) -> str:
    """简单检测文本语言（基于字符集）"""
    if not text:
        return 'en'
    
    # 检测中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return 'zh'
    
    # 检测日文字符（平假名、片假名、汉字）
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', text):
        return 'ja'
    
    # 检测韩文字符
    if re.search(r'[\uac00-\ud7a3]', text):
        return 'ko'
    
    # 检测阿拉伯文字符
    if re.search(r'[\u0600-\u06ff]', text):
        return 'ar'
    
    # 检测俄语字符
    if re.search(r'[\u0400-\u04ff]', text):
        return 'ru'
    
    # 默认返回英语
    return 'en'

# 使用AI从原始内容提取单词列表（只返回单词，不做详细处理）
def extract_words_with_ai(text_content: str, language: str = 'en') -> list:
    """使用AI从原始文本内容中提取单词列表"""
    from openai import OpenAI
    import os
    
    try:
        deepseek_api_key = (
            app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY else os.getenv("DEEPSEEK_API_KEY")
        )
        deepseek_api_key = deepseek_api_key.strip() if deepseek_api_key else None
        if not deepseek_api_key:
            # 如果API密钥未设置，尝试从文本中简单提取单词
            words = re.findall(r'\b[a-zA-Z]+\b', text_content)
            return list(set([w.lower() for w in words if len(w) > 2]))
        
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        language_name = get_language_name(language)
        
        # 根据语言调整提示词
        if language == 'zh':
            word_description = "中文词语"
            example = '["词语1", "词语2", "词语3"]'
        elif language == 'ja':
            word_description = "日语单词（包括假名和汉字）"
            example = '["こんにちは", "ありがとう", "言葉"]'
        elif language == 'ko':
            word_description = "韩语单词"
            example = '["안녕", "감사", "단어"]'
        else:
            word_description = f"{language_name}单词"
            example = '["word1", "word2", "word3"]'
        
        prompt = f"""
请从以下文本内容中提取所有{language_name}单词，只返回单词列表。

文本内容：
{text_content[:5000]}  # 限制长度避免超出token限制

请以JSON数组格式返回所有提取的单词，例如：{example}
只返回单词，不要包含释义、词性等其他信息。
如果文本中没有有效的{language_name}单词，返回空数组[]。
"""
        
        system_content = f"你是一个专业的{language_name}单词提取工具，擅长从文本中提取{language_name}单词列表。请严格按照要求的JSON数组格式返回结果。"
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        ai_content = response.choices[0].message.content.strip()
        
        # 提取JSON数组
        json_match = re.search(r'\[.*?\]', ai_content, re.DOTALL)
        if json_match:
            words_list = json.loads(json_match.group())
            # 去重并转换为小写
            return list(set([str(w).lower().strip() for w in words_list if w and isinstance(w, str) and len(str(w).strip()) > 0]))
        else:
            # 如果无法提取JSON，尝试简单提取单词
            words = re.findall(r'\b[a-zA-Z]+\b', text_content)
            return list(set([w.lower() for w in words if len(w) > 2]))
            
    except Exception as e:
        logger.error(f"AI提取单词失败: {str(e)}")
        # 失败时使用正则表达式简单提取（根据语言使用不同的正则）
        if language == 'zh':
            # 提取中文词语（2-4个字符的词语）
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', text_content)
        elif language == 'ja':
            # 提取日语单词（假名和汉字）
            words = re.findall(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+', text_content)
        elif language == 'ko':
            # 提取韩语单词
            words = re.findall(r'[\uac00-\ud7a3]+', text_content)
        else:
            # 默认提取英语单词
            words = re.findall(r'\b[a-zA-Z]+\b', text_content)
            words = [w.lower() for w in words if len(w) > 2]
        return list(set(words))

# 使用AI处理单词信息的函数 - 支持批量处理和多语言
def process_words_with_ai(words_data: list, language: str = 'en') -> list:
    """批量使用DeepSeek API处理多个单词信息，减少API调用次数，支持多语言"""
    from openai import OpenAI
    import os
    
    try:
        deepseek_api_key = (
            app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY else os.getenv("DEEPSEEK_API_KEY")
        )
        deepseek_api_key = deepseek_api_key.strip() if deepseek_api_key else None
        deepseek_api_key = deepseek_api_key.strip() if deepseek_api_key else None
        deepseek_api_key = deepseek_api_key.strip() if deepseek_api_key else None
        if not deepseek_api_key:
            # 如果API密钥未设置，返回基础信息
            results = []
            for word_data in words_data:
                results.append({
                    "word": word_data["word"],
                    "definition": word_data["definition"] or "暂无解释",
                    "part_of_speech": word_data["part_of_speech"] or "未知",
                    "example": "",
                    "processed": False
                })
            return results
        
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        # 获取语言名称
        language_name = get_language_name(language)
        
        # 根据语言调整提示词
        if language == 'zh':
            definition_desc = "准确的中文释义"
            pos_desc = "标准的词性（如名词、动词、形容词等）"
            example_desc = "一个简单的中文例句"
            invalid_desc = "有效的词语"
        elif language == 'ja':
            definition_desc = "准确的中文释义"
            pos_desc = "标准的词性（如名词、动词、形容词等，使用日语术语）"
            example_desc = "一个简单的日语例句"
            invalid_desc = "有效的日语单词"
        elif language == 'ko':
            definition_desc = "准确的中文释义"
            pos_desc = "标准的词性（如名词、动词、形容词等，使用韩语术语）"
            example_desc = "一个简单的韩语例句"
            invalid_desc = "有效的韩语单词"
        else:
            definition_desc = "准确的中文释义"
            pos_desc = "标准的词性（如noun、verb、adjective等，不要使用缩写）"
            example_desc = f"一个简单的{language_name}例句"
            invalid_desc = f"有效的{language_name}单词"
        
        # 准备批量处理的提示词
        words_list_str = ""
        for i, word_data in enumerate(words_data):
            words_list_str += f"\n{i+1}. 单词: {word_data['word']}\n"
            words_list_str += f"   现有解释: {word_data['definition']}\n"
            words_list_str += f"   现有词性: {word_data['part_of_speech']}\n"
        
        prompt = f"""
请将以下多个{language_name}单词批量处理成标准格式，提供正确的释义和词性。

{words_list_str}

请以JSON数组格式返回所有单词的处理结果，每个对象确保包含以下字段：
1. word: 单词（保持原样）
2. definition: {definition_desc}
3. part_of_speech: {pos_desc}
4. example: {example_desc}

如果某个单词不是{invalid_desc}，请在该对象中返回null值。请确保返回的JSON格式正确，可以被直接解析。
"""
            
        # 增加max_tokens以容纳批量处理的结果
        max_tokens = min(4096, 500 * len(words_data))
        
        system_content = f"你是一位专业的{language_name}词典编辑，擅长批量提供准确的{language_name}单词释义、词性和例句。请严格按照要求的JSON格式返回结果。"
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 降低温度以获取更确定的结果
                max_tokens=max_tokens
            )
        
        ai_content = response.choices[0].message.content.strip()
        
        # 提取JSON数组部分
        json_match = re.search(r'\[.*\]', ai_content, re.DOTALL)
        if json_match:
            processed_data_list = json.loads(json_match.group())
            
            # 确保返回的结果与输入的单词数量匹配
            results = []
            for i, word_data in enumerate(words_data):
                if i < len(processed_data_list) and processed_data_list[i]:
                    processed_data = processed_data_list[i]
                    # 确保必需字段都有值，安全处理None值
                    definition = (processed_data.get("definition") or "").strip() if processed_data.get("definition") else ""
                    part_of_speech = (processed_data.get("part_of_speech") or "").strip() if processed_data.get("part_of_speech") else ""
                    
                    # 如果释义或词性为空，标记为未处理成功
                    if not definition or not part_of_speech:
                        results.append({
                            "word": word_data["word"],
                            "definition": definition or "暂无解释",
                            "part_of_speech": part_of_speech or "未知",
                            "example": (processed_data.get("example") or "").strip() if processed_data.get("example") else "",
                            "processed": False
                        })
                    else:
                        results.append({
                            "word": processed_data.get("word", word_data["word"]),
                            "definition": definition,
                            "part_of_speech": part_of_speech,
                            "example": (processed_data.get("example") or "").strip() if processed_data.get("example") else "",
                            "processed": True
                        })
                else:
                    # 如果某个单词没有返回结果或结果为null，使用原始信息
                    results.append({
                        "word": word_data["word"],
                        "definition": word_data["definition"] or "暂无解释",
                        "part_of_speech": word_data["part_of_speech"] or "未知",
                        "example": "",
                        "processed": False
                    })
            return results
        else:
            # 如果无法提取JSON数组，尝试提取多个单独的JSON对象
            json_objects = re.findall(r'\{[^}]*\}', ai_content)
            results = []
            for i, word_data in enumerate(words_data):
                if i < len(json_objects):
                    try:
                        processed_data = json.loads(json_objects[i])
                        # 确保必需字段都有值，安全处理None值
                        definition = (processed_data.get("definition") or "").strip() if processed_data.get("definition") else ""
                        part_of_speech = (processed_data.get("part_of_speech") or "").strip() if processed_data.get("part_of_speech") else ""
                        
                        # 如果释义或词性为空，标记为未处理成功
                        if not definition or not part_of_speech:
                            results.append({
                                "word": word_data["word"],
                                "definition": definition or "暂无解释",
                                "part_of_speech": part_of_speech or "未知",
                                "example": (processed_data.get("example") or "").strip() if processed_data.get("example") else "",
                                "processed": False
                            })
                        else:
                            results.append({
                                "word": processed_data.get("word", word_data["word"]),
                                "definition": definition,
                                "part_of_speech": part_of_speech,
                                "example": (processed_data.get("example") or "").strip() if processed_data.get("example") else "",
                                "processed": True
                            })
                    except:
                        results.append({
                            "word": word_data["word"],
                            "definition": word_data["definition"] or "暂无解释",
                            "part_of_speech": word_data["part_of_speech"] or "未知",
                            "example": "",
                            "processed": False
                        })
                else:
                    results.append({
                        "word": word_data["word"],
                        "definition": word_data["definition"] or "暂无解释",
                        "part_of_speech": word_data["part_of_speech"] or "未知",
                        "example": "",
                        "processed": False
                    })
            return results
    except Exception as e:
        logger.error(f"AI批量处理单词失败: {str(e)}", exc_info=True)

    # 失败时返回所有单词的原始信息
    results = []
    for word_data in words_data:
        # 安全处理可能为None的值
        word_text = word_data.get("word", "") or ""
        definition = word_data.get("definition") or "暂无解释"
        part_of_speech = word_data.get("part_of_speech") or "未知"
        
        results.append({
            "word": word_text,
            "definition": definition if definition else "暂无解释",
            "part_of_speech": part_of_speech if part_of_speech else "未知",
            "example": "",
            "processed": False
        })
    return results

# 保持向后兼容的单个单词处理函数
def process_word_with_ai(word: str, existing_definition: str = "", existing_pos: str = "") -> dict:
    """使用AI处理单个单词信息，内部调用批量处理函数"""
    result = process_words_with_ai([{
        "word": word,
        "definition": existing_definition,
        "part_of_speech": existing_pos
    }])
    return result[0] if result else {
        "word": word,
        "definition": existing_definition or "暂无解释",
        "part_of_speech": existing_pos or "未知",
        "example": "",
        "processed": False
    }

# 后台处理单词表任务
async def process_vocabulary_task(task_id: str, text_content: str, name: str, description: Optional[str], language: str, user_id: int, vocabulary_list_id: int):
    """后台处理单词表任务"""
    from app import SessionLocal
    db = SessionLocal()
    try:
        # 更新任务状态为处理中
        task = db.query(VocabularyUploadTask).filter(VocabularyUploadTask.task_id == task_id).first()
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return
        
        task.status = 'processing'
        task.message = '正在提取单词...'
        db.commit()
        
        # 步骤1：先用AI提取单词列表
        logger.info(f"任务 {task_id}: 开始使用AI提取单词列表...")
        extracted_words = extract_words_with_ai(text_content)
        logger.info(f"任务 {task_id}: AI提取到 {len(extracted_words)} 个单词")
        
        # 如果AI提取失败或提取的单词很少，尝试解析文件格式
        if len(extracted_words) < 3:
            logger.info(f"任务 {task_id}: AI提取的单词较少，尝试解析文件格式...")
            words_from_file = []
            # 简单提取单词（假设每行一个单词）
            lines = text_content.split('\n')
            for line in lines:
                if line.strip():
                    word = line.strip().split('\t')[0].split(',')[0].strip()
                    if word:
                        words_from_file.append(word.lower().strip())
            extracted_words = list(set(extracted_words + words_from_file))
            logger.info(f"任务 {task_id}: 合并后共有 {len(extracted_words)} 个单词")
        
        if not extracted_words:
            task.status = 'failed'
            task.error_message = "未能从文件中提取到有效的英语单词"
            db.commit()
            return
        
        # 更新任务：设置总单词数
        task.total_words = len(extracted_words)
        task.processed_words = 0
        task.progress = 0
        task.message = f'共提取到 {len(extracted_words)} 个单词，开始处理...'
        db.commit()
        
        # 步骤2：与总表配对（按语言匹配）
        logger.info(f"任务 {task_id}: 开始与总表配对（语言: {language}）...")
        # 对于非英语，不强制转小写（某些语言大小写敏感）
        if language == 'en':
            all_words_lower = [w.lower() for w in extracted_words]
            existing_public_words = db.query(PublicVocabularyWord).filter(
                PublicVocabularyWord.language == language,
                func.lower(PublicVocabularyWord.word).in_(all_words_lower)
            ).all()
        else:
            # 对于其他语言，直接匹配
            existing_public_words = db.query(PublicVocabularyWord).filter(
                PublicVocabularyWord.language == language,
                PublicVocabularyWord.word.in_(extracted_words)
            ).all()
        
        # 创建匹配映射（根据语言决定是否转小写）
        if language == 'en':
            public_word_map = {pw.word.lower(): pw for pw in existing_public_words}
            found_words = []
            words_to_process = []
            for word in extracted_words:
                word_lower = word.lower()
                if word_lower in public_word_map:
                    found_words.append((word, public_word_map[word_lower]))
                else:
                    words_to_process.append(word)
        else:
            public_word_map = {pw.word: pw for pw in existing_public_words}
            found_words = []
            words_to_process = []
            for word in extracted_words:
                if word in public_word_map:
                    found_words.append((word, public_word_map[word]))
                else:
                    words_to_process.append(word)
        
        logger.info(f"任务 {task_id}: 总表配对完成: 找到 {len(found_words)} 个，需要AI处理 {len(words_to_process)} 个")
        
        # 步骤3：立即保存找到的单词
        public_words_reused = 0
        for word, public_word in found_words:
            vocabulary_word = VocabularyWord(
                vocabulary_list_id=vocabulary_list_id,
                word=public_word.word,
                definition=public_word.definition,
                part_of_speech=public_word.part_of_speech,
                example=public_word.example,
                language=language
            )
            db.add(vocabulary_word)
            public_word.usage_count += 1
            public_words_reused += 1
        
        db.commit()
        logger.info(f"任务 {task_id}: 已保存 {public_words_reused} 个从总表找到的单词")
        
        # 更新进度
        task.processed_words = public_words_reused
        task.progress = int((public_words_reused / task.total_words) * 100) if task.total_words > 0 else 0
        task.message = f'已匹配 {public_words_reused} 个单词，正在处理剩余 {len(words_to_process)} 个...'
        db.commit()
        
        # 步骤4：分批处理未找到的单词
        words_processed_with_ai = 0
        batch_size = 20
        
        for batch_start in range(0, len(words_to_process), batch_size):
            batch_words = words_to_process[batch_start:batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(words_to_process) + batch_size - 1) // batch_size
            
            logger.info(f"任务 {task_id}: 处理批次 {batch_num}/{total_batches}: {len(batch_words)} 个单词")
            
            task.message = f'正在处理批次 {batch_num}/{total_batches}...'
            db.commit()
            
            # 准备批量处理的单词数据
            batch_words_data = [{"word": w, "definition": "", "part_of_speech": "", "example": ""} for w in batch_words]
            
            # 使用AI处理这一批单词（传入语言参数）
            processed_batch = process_words_with_ai(batch_words_data, language=language)
            
            # 立即保存这一批处理完的单词
            for processed_word in processed_batch:
                # 检查是否处理成功，并且必需字段都有值
                word_text = (processed_word.get("word") or "").strip()
                definition_raw = processed_word.get("definition")
                part_of_speech_raw = processed_word.get("part_of_speech")
                
                # 安全处理None值
                definition = (definition_raw or "").strip() if definition_raw else ""
                part_of_speech = (part_of_speech_raw or "").strip() if part_of_speech_raw else ""
                
                # 只有单词、释义和词性都有值时才保存
                if (processed_word.get("processed", False) and 
                    word_text and 
                    definition and 
                    part_of_speech):
                    
                    # 保存到公共单词库（包含语言信息）
                    new_public_word = PublicVocabularyWord(
                        word=word_text,
                        language=language,
                        definition=definition.strip(),
                        part_of_speech=part_of_speech.strip(),
                        example=(processed_word.get("example") or "").strip(),
                        usage_count=1
                    )
                    db.add(new_public_word)
                    
                    # 添加到用户的单词表中（包含语言信息）
                    vocabulary_word = VocabularyWord(
                        vocabulary_list_id=vocabulary_list_id,
                        word=word_text,
                        definition=definition.strip(),
                        part_of_speech=part_of_speech.strip(),
                        example=(processed_word.get("example") or "").strip(),
                        language=language
                    )
                    db.add(vocabulary_word)
                    words_processed_with_ai += 1
                else:
                    # 记录处理失败的单词（安全处理字符串）
                    def safe_str(value, max_len=30):
                        if value is None:
                            return 'None'
                        try:
                            str_val = str(value)
                            return str_val[:max_len] + '...' if len(str_val) > max_len else str_val
                        except:
                            return f'<{type(value).__name__}>'
                    
                    logger.warning(f"任务 {task_id}: 单词 '{word_text}' 处理不完整，跳过保存。processed={processed_word.get('processed')}, definition={safe_str(definition)}, part_of_speech={safe_str(part_of_speech, 20)}")
            
            # 每处理完一批就提交一次
            db.commit()
            
            # 更新进度
            task.processed_words = public_words_reused + words_processed_with_ai
            task.progress = int((task.processed_words / task.total_words) * 100) if task.total_words > 0 else 0
            task.message = f'已处理 {task.processed_words}/{task.total_words} 个单词 ({task.progress}%)'
            db.commit()
            
            logger.info(f"任务 {task_id}: 批次 {batch_num} 处理完成并已保存")
        
        # 任务完成
        task.status = 'completed'
        task.progress = 100
        task.message = f'处理完成！共处理 {task.total_words} 个单词，其中 {public_words_reused} 个来自总表，{words_processed_with_ai} 个由AI处理'
        db.commit()
        
        logger.info(f"任务 {task_id}: 处理完成！总单词数={task.total_words}, 复用={public_words_reused}, AI处理={words_processed_with_ai}")
        
    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {str(e)}", exc_info=True)
        task = db.query(VocabularyUploadTask).filter(VocabularyUploadTask.task_id == task_id).first()
        if task:
            task.status = 'failed'
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()

# 上传单词表 - 异步版本
async def upload_vocabulary_file(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...), name: str = Form(...), description: Optional[str] = Form(None), language: str = Form('en'), db: Session = Depends(get_db)):
    # 正确获取当前用户
    current_user = await get_current_user(request, db)
    try:
        # 验证语言代码
        if language not in LANGUAGE_MAP:
            language = 'en'  # 默认使用英语
            logger.warning(f"未知的语言代码，使用默认语言: en")
        
        # 记录接收到的文件信息以调试
        logger.info(f"接收到上传文件: {file.filename}, 名称: {name}, 语言: {language}")
        
        # 验证必要参数
        if not name or name.strip() == '':
            # 返回标准的422错误格式
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body", "name"], "msg": "单词表名称不能为空", "type": "value_error"}]
            )
        
        # 检查文件类型
        if not file.filename or not file.filename.endswith(('.txt', '.csv')):
            raise HTTPException(status_code=400, detail="只支持TXT和CSV格式的文件")
        
        # 读取文件内容
        content = await file.read()
        
        # 验证文件大小
        if len(content) == 0:
            # 返回标准的422错误格式
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body", "file"], "msg": "上传的文件内容不能为空", "type": "value_error"}]
            )
        
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # 返回标准的422错误格式
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body", "file"], "msg": "文件编码错误，请确保使用UTF-8编码", "type": "value_error"}]
            )
        
        # 创建单词表
        user_id_for_creation = int(current_user['id']) if current_user['id'] else None
        logger.info(f"创建单词表: 名称={name}, 用户ID={user_id_for_creation}")
        
        vocabulary_list = VocabularyList(
            name=name,
            description=description,
            language=language,
            is_preset=False,
            is_public=False,
            created_by=user_id_for_creation
        )
        db.add(vocabulary_list)
        db.flush()  # 获取ID但不提交事务
        logger.info(f"单词表创建成功: ID={vocabulary_list.id}, 语言: {language}")
        
        # 创建任务记录
        task_id = str(uuid.uuid4())
        task = VocabularyUploadTask(
            task_id=task_id,
            user_id=user_id_for_creation,
                vocabulary_list_id=vocabulary_list.id,
            status='pending',
            progress=0,
            message='任务已创建，等待处理...'
            )
        db.add(task)
        db.commit()
        
        # 将处理任务添加到后台任务
        background_tasks.add_task(
            process_vocabulary_task,
            task_id=task_id,
            text_content=text_content,
            name=name,
            description=description,
            language=language,
            user_id=user_id_for_creation,
            vocabulary_list_id=vocabulary_list.id
        )
        
        logger.info(f"单词表上传任务已创建: task_id={task_id}, vocabulary_list_id={vocabulary_list.id}")
        
        # 立即返回任务信息
        return {
            "task_id": task_id,
            "vocabulary_list_id": vocabulary_list.id,
            "status": "pending",
            "message": "单词表上传任务已创建，正在后台处理...",
            "progress": 0
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"上传单词表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

# 获取单词表列表
async def get_vocabulary_lists(request: Request, preset: Optional[bool] = Query(None, alias="preset"), language: Optional[str] = Query(None, alias="language"), db: Session = Depends(get_db)):
    # 手动获取当前用户
    current_user = await get_current_user(request, db)
    try:
        # 获取用户ID，确保类型一致
        user_id = int(current_user['id']) if current_user['id'] else None
        logger.info(f"查询用户单词表，用户ID: {user_id}, 类型: {type(user_id)}, preset参数: {preset}")
        
        query = db.query(VocabularyList)
        from sqlalchemy import or_, and_
        
        # 根据preset参数过滤
        if preset is True:
            # 只返回预设单词表
            query = query.filter(VocabularyList.is_preset == True)
            logger.info(f"查询条件: is_preset=True (只返回预设单词表)")
        elif preset is False:
            # 只返回用户自己创建的非预设单词表
            # 先查询所有非预设单词表，用于调试
            all_non_preset = db.query(VocabularyList).filter(VocabularyList.is_preset == False).all()
            logger.info(f"数据库中所有非预设单词表数量: {len(all_non_preset)}")
            if all_non_preset:
                for v in all_non_preset:
                    logger.info(f"单词表ID={v.id}, 名称={v.name}, created_by={v.created_by} (类型: {type(v.created_by)}), 当前用户ID={user_id} (类型: {type(user_id)})")
            
            query = query.filter(
                and_(
                    VocabularyList.is_preset == False,
                    VocabularyList.created_by == user_id
                )
            )
            logger.info(f"查询条件: is_preset=False 且 created_by={user_id} (只返回用户自己的单词表)")
        else:
            # 返回预设单词表或用户创建的单词表
            query = query.filter(
                or_(
                    VocabularyList.is_preset == True,
                    VocabularyList.created_by == user_id
                )
            )
            logger.info(f"查询条件: is_preset=True 或 created_by={user_id} (返回预设和用户自己的单词表)")
        
        # 按语言过滤（如果指定）
        if language:
            if language not in LANGUAGE_MAP:
                logger.warning(f"未知的语言代码: {language}，忽略语言过滤")
            else:
                query = query.filter(VocabularyList.language == language)
                logger.info(f"添加语言过滤: language={language}")
        
        lists = query.all()
        logger.info(f"查询到 {len(lists)} 个单词表")
        
        # 获取每个单词表的单词数量
        result = []
        for vocab_list in lists:
            result.append({
                "id": vocab_list.id,
                "name": vocab_list.name,
                "description": vocab_list.description,
                "language": getattr(vocab_list, 'language', 'en') or 'en',
                "is_preset": vocab_list.is_preset,
                "word_count": len(vocab_list.words),
                "created_at": vocab_list.created_at.isoformat() if vocab_list.created_at else None
            })
        
        logger.info(f"返回 {len(result)} 个单词表给用户")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取单词表列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取单词表失败: {str(e)}")

# 获取单词表详情
async def get_vocabulary_list(vocabulary_list_id: int, request: Request, db: Session = Depends(get_db)):
    # 手动获取当前用户
    current_user = await get_current_user(request, db)
    try:
        # 查询单词表
        vocab_list = db.query(VocabularyList).filter(VocabularyList.id == vocabulary_list_id).first()
        
        if not vocab_list:
            raise HTTPException(status_code=404, detail="单词表不存在")
        
        # 检查权限（使用统一权限检查函数）
        logger.info(f"检查单词表{vocabulary_list_id}的访问权限: is_preset={vocab_list.is_preset}, created_by={vocab_list.created_by}, current_user_id={current_user.get('id')}")
        if not check_vocabulary_permission(vocab_list, current_user):
            logger.warning(f"用户{current_user.get('id')}无权访问单词表{vocabulary_list_id} (创建者: {vocab_list.created_by}, 预设: {vocab_list.is_preset})")
            raise HTTPException(status_code=403, detail="无权访问此单词表")
        
        # 获取用户历史选择过的单词ID（从生成的文章记录中）
        user_id = int(current_user['id'])
        user_selected_word_ids = set()
        
        # 查询用户之前生成文章时选择的单词
        try:
            user_articles = db.query(GeneratedArticle).filter(
                GeneratedArticle.user_id == user_id,
                GeneratedArticle.vocabulary_list_id == vocabulary_list_id
            ).all()
            
            for article in user_articles:
                if article.used_word_ids:
                    try:
                        used_ids = json.loads(article.used_word_ids)
                        if isinstance(used_ids, list):
                            user_selected_word_ids.update(used_ids)
                    except:
                        pass
            
            logger.info(f"用户 {user_id} 在单词表 {vocabulary_list_id} 中历史选择过的单词ID: {list(user_selected_word_ids)[:10]}... (共{len(user_selected_word_ids)}个)")
        except Exception as e:
            logger.warning(f"获取用户历史选择单词失败: {str(e)}")
        
        # 获取单词列表并排序：历史选择过的单词放到最后
        words = []
        unselected_words = []  # 未选择过的单词
        selected_words = []    # 选择过的单词（放到最后）
        
        for word in vocab_list.words:
            # 检查是否需要增强单词信息
            word_info = {
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example
            }
            
            # 根据是否选择过进行分类
            if word.id in user_selected_word_ids:
                selected_words.append(word_info)
            else:
                unselected_words.append(word_info)
        
        # 合并：未选择的在前，选择过的在后
        words = unselected_words + selected_words
        logger.info(f"单词排序完成: 未选择 {len(unselected_words)} 个，已选择 {len(selected_words)} 个")
        
        return {
            "id": vocab_list.id,
            "name": vocab_list.name,
            "description": vocab_list.description,
            "is_preset": vocab_list.is_preset,
            "words": words
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取单词表详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取单词表失败: {str(e)}")

# AI增强的单词详细解释
async def get_enhanced_word_info(word_id: int, request: Request, db: Session = Depends(get_db)):
    # 手动获取当前用户
    current_user = await get_current_user(request, db)
    try:
        # 获取单词基础信息
        word = db.query(VocabularyWord).filter(VocabularyWord.id == word_id).first()
        if not word:
            raise HTTPException(status_code=404, detail="单词不存在")
        
        # 准备调用DeepSeek API
        from openai import OpenAI
        import os
        
        deepseek_api_key = (
            app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY else os.getenv("DEEPSEEK_API_KEY")
        )
        if not deepseek_api_key:
            # 如果API密钥未设置，返回基础信息
            return {
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example,
                "enhanced": False,
                "message": "AI增强功能暂不可用"
            }
        
        try:
            client = OpenAI(
                api_key=deepseek_api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            # 准备提示词
            prompt = f"""
请为以下英语单词提供详细的解释和学习辅助信息：

单词: {word.word}
词性: {word.part_of_speech or '未知'}
现有解释: {word.definition or '暂无'}
现有例句: {word.example or '暂无'}

请提供：
1. 详细的中英文解释
2. 2-3个实用例句（英文+中文翻译）
3. 记忆技巧或联想方法（帮助记忆这个单词）
4. 常见搭配
5. 同义词和反义词

请使用清晰的结构和格式回答。
            """
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位专业的英语语言教师，擅长解释单词并提供有效的学习辅助。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            enhanced_content = response.choices[0].message.content.strip()
            
            # 记录学习活动（UserLearningRecord.user_id是Integer类型）
            user_id = int(current_user['id'])
            learning_record = UserLearningRecord(
                user_id=user_id,
                activity_type="word_enhancement",
                activity_details=json.dumps({"word_id": word.id, "word": word.word})
            )
            db.add(learning_record)
            db.commit()
            
            return {
                "id": word.id,
                "word": word.word,
                "enhanced_content": enhanced_content,
                "enhanced": True
            }
        except Exception as api_error:
            logger.error(f"单词增强API调用失败: {str(api_error)}")
            # 降级：返回基础信息
            return {
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example,
                "enhanced": False,
                "message": "AI增强失败，返回基础信息"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取单词增强信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取单词增强信息失败: {str(e)}")

# 生成文章
async def generate_article(article_request: ArticleGenerationRequest, request: Request, db: Session = Depends(get_db)):
    # 直接调用get_current_user获取当前用户
    try:
        current_user = await get_current_user(request, db)
    except Exception as auth_error:
        logger.error(f"获取用户信息失败: {str(auth_error)}")
        raise HTTPException(status_code=401, detail="用户认证失败")
    
    try:
        logger.info(f"生成文章请求: vocabulary_list_id={article_request.vocabulary_list_id}, "
                   f"selected_word_ids={article_request.selected_word_ids}, "
                   f"topic={article_request.topic}, "
                   f"difficulty_level={article_request.difficulty_level}, "
                   f"article_length={article_request.article_length}, "
                   f"custom_words={article_request.custom_words}")
        
        # 获取语言设置（从请求或单词表）
        language = article_request.language or 'en'
        
        # 验证必需字段 - topic可以是None或空字符串，如果是这样则使用默认主题
        topic = (article_request.topic or "").strip()
        if not topic:
            language_name = get_language_name(language)
            topic = f"{language_name}学习"  # 默认主题
            logger.info(f"文章主题为空，使用默认主题: {topic}")
        # 获取单词表（如果指定）
        vocabulary_words = []
        public_vocabulary_words = []  # 系统词库（公共词库）单词
        custom_words_list = []  # 自定义单词（仅文本）
        
        # 获取系统词库和自定义单词（从请求模型中获取）
        public_word_ids = article_request.public_word_ids or []
        custom_words = article_request.custom_words or []
        
        # 处理用户单词表
        if article_request.vocabulary_list_id:
            vocab_list = db.query(VocabularyList).filter(VocabularyList.id == article_request.vocabulary_list_id).first()
            if not vocab_list:
                raise HTTPException(status_code=404, detail="单词表不存在")
            
            # 从单词表获取语言（如果请求中没有指定）
            if not article_request.language:
                language = vocab_list.language or 'en'
            
            # 检查权限（使用统一权限检查函数）
            if not check_vocabulary_permission(vocab_list, current_user):
                raise HTTPException(status_code=403, detail="无权访问此单词表")
            
            # 如果指定了selected_word_ids，则只使用选中的单词
            if article_request.selected_word_ids:
                # 从单词表中筛选选中的单词
                vocabulary_words = [word for word in vocab_list.words if word.id in article_request.selected_word_ids]
                # 验证所有请求的单词ID是否都存在
                if len(vocabulary_words) != len(article_request.selected_word_ids):
                    raise HTTPException(status_code=400, detail="部分请求的单词ID不存在")
            else:
                # 否则使用整个单词表的单词
                vocabulary_words = vocab_list.words
        
        # 处理系统词库（公共词库）
        if public_word_ids and len(public_word_ids) > 0:
            public_words = db.query(PublicVocabularyWord).filter(
                PublicVocabularyWord.id.in_(public_word_ids)
            ).all()
            if public_words:
                public_vocabulary_words = public_words
                logger.info(f"使用系统词库单词: {len(public_vocabulary_words)} 个")
        
        # 处理自定义单词
        if custom_words and len(custom_words) > 0:
            custom_words_list = [w.strip() for w in custom_words if w and w.strip()]
            logger.info(f"使用自定义单词: {len(custom_words_list)} 个")
        
        # 调用DeepSeek API生成文章
        from openai import OpenAI
        import os
        import json
        
        # 从统一配置/环境变量获取API密钥
        deepseek_api_key = (
            app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY else os.getenv("DEEPSEEK_API_KEY")
        )
        if not deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY环境变量未设置")
        
        # 准备单词列表（合并所有来源的单词）
        all_words_for_prompt = []
        if vocabulary_words:
            all_words_for_prompt.extend([word.word for word in vocabulary_words])
        if public_vocabulary_words:
            all_words_for_prompt.extend([word.word for word in public_vocabulary_words])
        if custom_words_list:
            all_words_for_prompt.extend(custom_words_list)
        
        word_list = ", ".join(all_words_for_prompt) if all_words_for_prompt else "无需特定单词"
        
        # 难度级别映射
        difficulty_mapping = {
            "四级": "大学英语四级水平，词汇量约4000-5000，使用基础语法结构，句子简单明了",
            "六级": "大学英语六级水平，词汇量约5500-6500，语法结构稍微复杂，包含更多连接词",
            "托福": "托福水平，词汇量约8000-10000，句式多样，逻辑结构清晰，适合学术环境",
            "雅思": "雅思水平，词汇量约7000-9000，表达流畅自然，使用多样化句式和地道表达",
            "商务英语": "商务英语水平，使用专业商务术语和表达，语气正式但清晰，适合职场环境",
            "初级": "初级水平，使用简单词汇和基本语法，句子结构单一",
            "中级": "中级水平，词汇量适中，语法结构稍微复杂",
            "高级": "高级水平，词汇丰富，句式复杂，逻辑结构严密"
        }
        
        difficulty_description = difficulty_mapping.get(article_request.difficulty_level, "中级水平")
        
        # 根据语言调整提示词
        language_name = get_language_name(language)
        
        if language == 'en':
            original_desc = "英语原文"
            translation_desc = "中文翻译"
        elif language == 'zh':
            original_desc = "中文原文"
            translation_desc = "英文翻译"
        else:
            original_desc = f"{language_name}原文"
            translation_desc = "中文翻译"
        
        # 准备提示词
        prompt = f"""
请基于以下要求生成一篇{language_name}文章，并提供中文翻译：

主题：{topic}
难度级别：{difficulty_description}
文章长度：{article_request.article_length}，建议300-500词
需要包含的单词：{word_list}

请确保：
1. 文章语法完全正确，逻辑清晰，上下文连贯
2. 严格遵循指定的难度级别特征，包括词汇复杂度和句子结构
3. 将所有指定的单词自然、合理地融入文章中，避免生硬堆砌
4. 文章应有明确的主题和中心思想，段落之间过渡自然
5. 内容有实质性内容，避免空洞无物

**重要：必须严格按照以下格式输出，使用三个连字符（---）分隔原文和翻译：**

{original_desc}段落1
{original_desc}段落2
{original_desc}段落3
---
{translation_desc}段落1
{translation_desc}段落2
{translation_desc}段落3

请严格按照上述格式输出，不要添加任何额外的说明或标记。
        """
        
        try:
            client = OpenAI(
                api_key=deepseek_api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            system_content = f"你是一位专业的{language_name}写作教师，擅长根据指定的单词和主题生成高质量的学习文章。请严格按照要求的格式输出，确保文章质量高、语法正确、逻辑清晰。"
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            # 解析AI生成的内容
            ai_content = response.choices[0].message.content.strip()
            logger.info(f"AI返回的原始内容长度: {len(ai_content)} 字符")
            
            original_text = ""
            translated_text = ""
            
            # 尝试多种方式解析内容
            if "---" in ai_content:
                # 使用三个连字符分隔
                parts = ai_content.split("---", 1)  # 只分割第一次出现
                original_text = parts[0].strip()
                translated_text = parts[1].strip() if len(parts) > 1 else ""
            elif "---\n" in ai_content or "\n---" in ai_content:
                # 分隔符前后有换行符
                parts = re.split(r'\n\s*---\s*\n', ai_content, 1)
                original_text = parts[0].strip()
                translated_text = parts[1].strip() if len(parts) > 1 else ""
            elif "中文翻译" in ai_content or "翻译：" in ai_content:
                # 尝试通过关键词分割
                match = re.search(r'(中文翻译|翻译：)[：:\s]*\n?(.*)', ai_content, re.DOTALL)
                if match:
                    # 找到"中文翻译"标记，之前的是英文，之后的是中文
                    split_pos = match.start()
                    original_text = ai_content[:split_pos].strip()
                    translated_text = match.group(2).strip() if match.group(2) else ""
                else:
                    # 如果匹配失败，尝试简单的中英文识别
                    lines = ai_content.split('\n')
                    chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]+')
                    split_idx = -1
                    for i, line in enumerate(lines):
                        chinese_count = len(chinese_char_pattern.findall(line))
                        if chinese_count > len(line) * 0.3:  # 如果一行超过30%是中文字符
                            split_idx = i
                            break
                    if split_idx > 0:
                        original_text = '\n'.join(lines[:split_idx]).strip()
                        translated_text = '\n'.join(lines[split_idx:]).strip()
                    else:
                        original_text = ai_content
                        translated_text = ""
            else:
                # 最后尝试：通过中文字符分布来识别
                chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]+')
                lines = ai_content.split('\n')
                
                # 找到第一个包含大量中文的行
                split_idx = -1
                for i, line in enumerate(lines):
                    if line.strip():
                        chinese_ratio = len(chinese_char_pattern.findall(line)) / max(len(line), 1)
                        if chinese_ratio > 0.3:  # 超过30%是中文字符
                            split_idx = i
                            break
                
                if split_idx > 0:
                    original_text = '\n'.join(lines[:split_idx]).strip()
                    translated_text = '\n'.join(lines[split_idx:]).strip()
                else:
                    # 如果还是无法识别，使用整个内容作为英文
                    original_text = ai_content
                    translated_text = ""
                    logger.warning("AI生成的内容格式不符合预期，无法识别中英文部分，已保存原始内容")
            
            # 验证解析结果
            if not original_text:
                original_text = ai_content
                logger.warning("未能解析出英文原文，使用完整内容")
            
            if not translated_text:
                logger.warning("未能解析出中文翻译，翻译部分为空")
                # 可以选择是否使用AI再次翻译，但会增加延迟
                # 暂时留空，前端可以提示用户
                
            logger.info(f"解析结果 - 英文长度: {len(original_text)}, 中文长度: {len(translated_text)}")
        
        except Exception as api_error:
            logger.error(f"DeepSeek API调用失败: {str(api_error)}")
            # 降级策略：使用默认文章
            original_text = """
In our modern world, technology has become an integral part of our daily lives. We rely on it for communication, work, education, and entertainment. 
The rapid development of artificial intelligence is transforming various industries and creating new opportunities for innovation. 
However, with these advancements come challenges related to privacy, security, and ethical considerations. 
It is important for us to use technology responsibly and ensure that it benefits humanity as a whole. 
By balancing innovation with careful consideration, we can create a future where technology enhances our lives while preserving our values and well-being.
        """.strip()
        
            translated_text = """
在我们现代世界中，技术已成为我们日常生活不可或缺的一部分。我们依靠它进行沟通、工作、教育和娱乐。
人工智能的快速发展正在改变各个行业，并为创新创造新的机会。
然而，随着这些进步，也带来了与隐私、安全和伦理考虑相关的挑战。
对我们来说，负责任地使用技术并确保它造福整个人类是很重要的。
通过平衡创新与谨慎考虑，我们可以创造一个技术提升我们生活同时保留我们价值观和福祉的未来。
        """.strip()
        
        # 提取文章中使用的单词（从原文中提取，匹配所有来源的单词）
        used_words_info = []  # 存储所有使用的单词信息（用于返回）
        used_word_ids = []  # 仅用于用户单词表的ID（用于数据库保存）
        
        # 将原文转换为小写用于匹配
        original_text_lower = original_text.lower()
        # 提取所有单词（去除标点符号）
        import string
        words_in_article = re.findall(r'\b[a-zA-Z]+\b', original_text_lower)
        
        # 匹配用户单词表中的单词
        if vocabulary_words:
            for vocab_word in vocabulary_words:
                word_lower = vocab_word.word.lower()
                # 统计单词在文章中出现的次数
                count = words_in_article.count(word_lower)
                if count > 0:
                    used_words_info.append({
                        'id': vocab_word.id,
                        'word': vocab_word.word,
                        'definition': vocab_word.definition or '',
                        'part_of_speech': vocab_word.part_of_speech or '',
                        'example': vocab_word.example or '',
                        'occurrence_count': count,
                        'source': 'vocabulary_list'
                    })
                    used_word_ids.append(vocab_word.id)
        
        # 匹配系统词库（公共词库）中的单词
        public_word_ids_used = []  # 记录实际使用的系统词库单词ID
        if public_vocabulary_words:
            for public_word in public_vocabulary_words:
                word_lower = public_word.word.lower()
                # 统计单词在文章中出现的次数
                count = words_in_article.count(word_lower)
                if count > 0:
                    # 使用特殊ID格式：'public_' + str(public_word.id)，避免与用户单词表ID冲突
                    used_words_info.append({
                        'id': f'public_{public_word.id}',  # 使用字符串ID格式，前端可以识别
                        'word': public_word.word,
                        'definition': public_word.definition or '',
                        'part_of_speech': public_word.part_of_speech or '',
                        'example': public_word.example or '',
                        'occurrence_count': count,
                        'source': 'public_vocabulary',
                        'public_word_id': public_word.id  # 保存原始ID用于数据库存储
                    })
                    public_word_ids_used.append(public_word.id)
        
        # 匹配自定义单词
        if custom_words_list:
            for custom_word_text in custom_words_list:
                if not custom_word_text or not custom_word_text.strip():
                    continue
                word_lower = custom_word_text.strip().lower()
                # 统计单词在文章中出现的次数
                count = words_in_article.count(word_lower)
                if count > 0:
                    # 检查是否已经在used_words_info中（避免重复）
                    already_added = any(item['word'].lower() == word_lower for item in used_words_info)
                    if not already_added:
                        used_words_info.append({
                            'id': None,  # 自定义单词没有ID
                            'word': custom_word_text.strip(),
                            'definition': '',
                            'part_of_speech': '',
                            'example': '',
                            'occurrence_count': count,
                            'source': 'custom'
                        })
        
        # 保存生成的文章
        # 记录所有使用的单词信息（包括用户单词表、系统词库、自定义单词）
        # 格式：{"vocabulary_word_ids": [1,2,3], "public_word_ids": [10,20,30], "custom_words": ["word1", "word2"], "total_count": 5}
        custom_words_used = [w['word'] for w in used_words_info if w.get('source') == 'custom']
        all_used_words_metadata = {
            "vocabulary_word_ids": used_word_ids,
            "public_word_ids": public_word_ids_used,  # 直接使用记录的系统词库单词ID
            "custom_words": custom_words_used,
            "total_count": len(used_words_info)
        }
        
        generated_article = GeneratedArticle(
            user_id=int(current_user["id"]),
            vocabulary_list_id=article_request.vocabulary_list_id,
            topic=topic,
            difficulty_level=article_request.difficulty_level,
            article_length=article_request.article_length,
            original_text=original_text,
            translated_text=translated_text,
            used_word_ids=json.dumps(all_used_words_metadata, ensure_ascii=False)
        )
        db.add(generated_article)
        db.flush()  # 获取ID但不提交
        
        # 保存文章中使用的单词（仅保存用户单词表中的单词，因为ArticleUsedWord需要word_id）
        for word_info in used_words_info:
            # 只保存有word_id的单词（即来自用户单词表的单词）
            if word_info.get('id') and word_info.get('source') == 'vocabulary_list':
                word_id = word_info['id']
                article_used_word = ArticleUsedWord(
                    article_id=generated_article.id,
                    word_id=word_id,
                    word_text=word_info['word'],
                    occurrence_count=word_info['occurrence_count']
                )
                db.add(article_used_word)
                
                # 更新单词的学习进度（记录用户阅读了包含该单词的文章）
                user_id_int = int(current_user['id'])
                progress = db.query(UserWordProgress).filter(
                    UserWordProgress.user_id == user_id_int,
                    UserWordProgress.word_id == word_id
                ).first()
                
                if not progress:
                    progress = UserWordProgress(
                        user_id=user_id_int,
                        word_id=word_id,
                        mastery_level=1,  # 初始掌握程度
                        review_count=1,
                        last_reviewed=datetime.now(UTC)
                    )
                    db.add(progress)
                else:
                    # 增加复习次数，更新最后复习时间
                    progress.review_count += 1
                    progress.last_reviewed = datetime.now(UTC)
                    # 如果阅读文章，稍微提升掌握程度（但不超过当前值+1）
                    if progress.mastery_level < 5:
                        progress.mastery_level = min(progress.mastery_level + 1, 5)
        
        db.commit()
        db.refresh(generated_article)
        
        logger.info(f"文章生成并保存成功: ID={generated_article.id}, 使用单词数={len(used_word_ids)}")
        
        # 解析文章为段落
        paragraphs = []
        original_paragraphs = original_text.split('\n')
        translated_paragraphs = translated_text.split('\n')
        
        for i in range(len(original_paragraphs)):
            if i < len(translated_paragraphs):
                paragraphs.append({
                    "original": original_paragraphs[i],
                    "translated": translated_paragraphs[i]
                })
        
        # 记录学习活动
        learning_record = UserLearningRecord(
            user_id=int(current_user["id"]),
            activity_type="article_generation",
            activity_details=json.dumps({
                "article_id": generated_article.id,
                "vocabulary_list_id": article_request.vocabulary_list_id,
                "topic": topic,
                "used_words_count": len(used_word_ids)
            })
        )
        db.add(learning_record)
        db.commit()
        
        # 准备返回的使用的单词信息（格式化）
        formatted_used_words = []
        for word_info in used_words_info:
            formatted_used_words.append({
                "id": word_info.get('id'),
                "word": word_info.get('word', ''),
                "definition": word_info.get('definition', ''),
                "part_of_speech": word_info.get('part_of_speech', ''),
                "example": word_info.get('example', ''),
                "occurrence_count": word_info.get('occurrence_count', 0)
            })
        
        return {
            "id": generated_article.id,
            "paragraphs": paragraphs,
            "topic": topic,
            "difficulty_level": article_request.difficulty_level,
            "article_length": article_request.article_length,
            "used_words": formatted_used_words,
            "used_words_count": len(formatted_used_words)
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        # 处理API密钥等配置错误
        logger.error(f"配置错误: {str(e)}")
        raise HTTPException(status_code=400, detail=f"配置错误: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"生成文章失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成文章失败: {str(e)}")

# 获取用户生成的文章列表
async def get_user_articles(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """获取当前用户生成的文章列表"""
    try:
        current_user = await get_current_user(request, db)
        user_id = int(current_user['id'])
        
        # 查询用户生成的文章
        query = db.query(GeneratedArticle).filter(GeneratedArticle.user_id == user_id)
        total = query.count()
        
        # 按创建时间降序排序
        articles = query.order_by(GeneratedArticle.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        
        # 格式化返回数据
        from datetime import timezone, timedelta
        china_tz = timezone(timedelta(hours=8))
        articles_list = []
        for article in articles:
            # 解析使用的单词ID
            used_word_ids = json.loads(article.used_word_ids) if article.used_word_ids else []
            
            # 将UTC时间转换为中国时区（UTC+8）
            created_at_china = None
            if article.created_at:
                if article.created_at.tzinfo is None:
                    created_at_utc = article.created_at.replace(tzinfo=UTC)
                else:
                    created_at_utc = article.created_at
                created_at_china = created_at_utc.astimezone(china_tz).isoformat()
            
            articles_list.append({
                "id": article.id,
                "topic": article.topic,
                "difficulty_level": article.difficulty_level,
                "article_length": article.article_length,
                "vocabulary_list_id": article.vocabulary_list_id,
                "vocabulary_list_name": article.vocabulary_list.name if article.vocabulary_list else None,
                "used_words_count": len(used_word_ids),
                "original_text_preview": article.original_text[:200] + "..." if len(article.original_text) > 200 else article.original_text,
                "created_at": created_at_china
            })
        
        return {
            "articles": articles_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文章列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文章列表失败: {str(e)}")

# 获取文章详情（包括使用的单词）
async def get_article_detail(article_id: int, request: Request, db: Session = Depends(get_db)):
    """获取文章详情，包括完整内容和使用的单词"""
    try:
        current_user = await get_current_user(request, db)
        user_id = int(current_user['id'])
        
        # 查询文章
        article = db.query(GeneratedArticle).filter(
            GeneratedArticle.id == article_id,
            GeneratedArticle.user_id == user_id
        ).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在或无权限访问")
        
        # 获取使用的单词
        used_words = db.query(ArticleUsedWord).filter(
            ArticleUsedWord.article_id == article_id
        ).join(VocabularyWord).all()
        
        # 格式化使用的单词信息
        used_words_info = []
        for used_word in used_words:
            word = used_word.word
            used_words_info.append({
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example,
                "occurrence_count": used_word.occurrence_count
            })
        
        # 解析文章为段落
        paragraphs = []
        original_paragraphs = article.original_text.split('\n')
        translated_paragraphs = article.translated_text.split('\n') if article.translated_text else []
        
        for i in range(len(original_paragraphs)):
            if i < len(translated_paragraphs):
                paragraphs.append({
                    "original": original_paragraphs[i],
                    "translated": translated_paragraphs[i]
                })
            else:
                paragraphs.append({
                    "original": original_paragraphs[i],
                    "translated": ""
                })
        
        # 将UTC时间转换为中国时区（UTC+8）
        from datetime import timezone, timedelta
        china_tz = timezone(timedelta(hours=8))
        created_at_china = None
        if article.created_at:
            if article.created_at.tzinfo is None:
                # 如果没有时区信息，假设是UTC
                created_at_utc = article.created_at.replace(tzinfo=UTC)
            else:
                created_at_utc = article.created_at
            # 转换为中国时区
            created_at_china = created_at_utc.astimezone(china_tz).isoformat()
        
        return {
            "id": article.id,
            "topic": article.topic,
            "difficulty_level": article.difficulty_level,
            "article_length": article.article_length,
            "vocabulary_list_id": article.vocabulary_list_id,
            "vocabulary_list_name": article.vocabulary_list.name if article.vocabulary_list else None,
            "paragraphs": paragraphs,
            "original_text": article.original_text,
            "translated_text": article.translated_text,
            "used_words": used_words_info,
            "used_words_count": len(used_words_info),
            "created_at": created_at_china
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文章详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文章详情失败: {str(e)}")

# 下载文章为PDF
async def download_article_pdf(article_id: int, request: Request, db: Session = Depends(get_db)):
    """下载文章为PDF格式"""
    try:
        current_user = await get_current_user(request, db)
        user_id = int(current_user['id'])
        
        # 查询文章
        article = db.query(GeneratedArticle).filter(
            GeneratedArticle.id == article_id,
            GeneratedArticle.user_id == user_id
        ).first()
        
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在或无权限访问")
        
        # 获取使用的单词（包括用户单词表和系统词库）
        used_words_info = []
        
        # 1. 从ArticleUsedWord表获取用户单词表的单词
        used_words = db.query(ArticleUsedWord).filter(
            ArticleUsedWord.article_id == article_id
        ).join(VocabularyWord).all()
        
        for used_word in used_words:
            word = used_word.word
            used_words_info.append({
                "word": word.word,
                "definition": word.definition or '',
                "part_of_speech": word.part_of_speech or '',
                "example": word.example or '',
            })
        
        # 2. 从used_word_ids JSON字段解析系统词库单词（如果存在）
        if article.used_word_ids:
            try:
                used_word_ids_data = json.loads(article.used_word_ids)
                # 检查是否是新的元数据格式
                if isinstance(used_word_ids_data, dict):
                    public_word_ids = used_word_ids_data.get('public_word_ids', [])
                elif isinstance(used_word_ids_data, list):
                    # 旧格式，只包含用户单词表ID，不需要处理
                    public_word_ids = []
                else:
                    public_word_ids = []
                
                # 查询系统词库单词
                if public_word_ids:
                    public_words = db.query(PublicVocabularyWord).filter(
                        PublicVocabularyWord.id.in_(public_word_ids)
                    ).all()
                    for public_word in public_words:
                        used_words_info.append({
                            "word": public_word.word,
                            "definition": public_word.definition or '',
                            "part_of_speech": public_word.part_of_speech or '',
                            "example": public_word.example or '',
                        })
            except Exception as e:
                logger.warning(f"解析used_word_ids失败: {str(e)}")
        
        # 解析文章为段落
        paragraphs = []
        original_paragraphs = article.original_text.split('\n')
        translated_paragraphs = article.translated_text.split('\n') if article.translated_text else []
        
        for i in range(len(original_paragraphs)):
            if i < len(translated_paragraphs):
                paragraphs.append({
                    "original": original_paragraphs[i],
                    "translated": translated_paragraphs[i]
                })
            else:
                paragraphs.append({
                    "original": original_paragraphs[i],
                    "translated": ""
                })
        
        # 生成PDF（使用reportlab）
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib import colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from io import BytesIO
            import html
            import platform
            
            # 注册中文字体
            chinese_font_name = 'Helvetica'  # 默认字体
            try:
                # 尝试注册Windows系统字体
                if platform.system() == 'Windows':
                    # 尝试注册微软雅黑（优先）
                    font_paths = [
                        ('C:/Windows/Fonts/msyh.ttc', 0),  # 微软雅黑，索引0
                        ('C:/Windows/Fonts/msyh.ttc', 1),  # 微软雅黑，索引1（粗体）
                        ('C:/Windows/Fonts/simhei.ttf', None),  # 黑体
                        ('C:/Windows/Fonts/simsun.ttc', 0),  # 宋体，索引0
                    ]
                    chinese_font_registered = False
                    for font_path, font_index in font_paths:
                        if os.path.exists(font_path):
                            try:
                                if font_path.endswith('.ttc'):
                                    # TTC文件需要指定字体索引
                                    if font_index is not None:
                                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=font_index))
                                    else:
                                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                                else:
                                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                                
                                # 验证字体是否成功注册
                                registered_fonts = pdfmetrics.getRegisteredFontNames()
                                if 'ChineseFont' in registered_fonts:
                                    chinese_font_registered = True
                                    chinese_font_name = 'ChineseFont'
                                    logger.info(f"✓ 成功注册中文字体: {font_path} (索引: {font_index})")
                                    logger.info(f"  已注册的字体列表: {registered_fonts}")
                                    break
                                else:
                                    logger.warning(f"字体注册后未出现在注册列表中: {font_path}")
                            except Exception as e:
                                logger.warning(f"注册字体失败 {font_path} (索引: {font_index}): {str(e)}", exc_info=True)
                                continue
                    
                    if not chinese_font_registered:
                        logger.error("✗ 未找到可用的中文字体，中文将无法正确显示！")
                        logger.info(f"当前已注册的字体: {pdfmetrics.getRegisteredFontNames()}")
                else:
                    # Linux/Mac系统，尝试查找系统字体
                    font_paths = [
                        '/System/Library/Fonts/PingFang.ttc',  # macOS
                        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux - 文泉驿微米黑
                        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',  # Linux - 文泉驿正黑
                        '/usr/share/fonts/truetype/arphic/ukai.ttc',  # Linux - AR PL UKai
                        '/usr/share/fonts/truetype/arphic/uming.ttc',  # Linux - AR PL UMing
                        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux - DejaVu (不支持中文，但作为备选)
                        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Linux - Liberation
                        # 尝试查找其他常见字体目录
                        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Linux - Noto Sans CJK
                        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',  # Linux - Noto Sans CJK (备选路径)
                    ]
                    chinese_font_registered = False
                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            try:
                                if font_path.endswith('.ttc'):
                                    # TTC文件需要指定字体索引
                                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path, subfontIndex=0))
                                else:
                                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                                
                                registered_fonts = pdfmetrics.getRegisteredFontNames()
                                if 'ChineseFont' in registered_fonts:
                                    chinese_font_name = 'ChineseFont'
                                    chinese_font_registered = True
                                    logger.info(f"✓ 成功注册中文字体: {font_path}")
                                    break
                            except Exception as e:
                                logger.warning(f"注册字体失败 {font_path}: {str(e)}")
                                continue
                    
                    if not chinese_font_registered:
                        logger.error("✗ 未找到可用的中文字体，中文将无法正确显示！")
                        logger.info(f"当前已注册的字体: {pdfmetrics.getRegisteredFontNames()}")
                        logger.info("建议在Linux系统上安装中文字体，例如：")
                        logger.info("  sudo apt-get install fonts-wqy-microhei fonts-wqy-zenhei")
                        logger.info("  或 sudo yum install wqy-microhei-fonts wqy-zenhei-fonts")
            except Exception as e:
                logger.error(f"注册中文字体时出错: {str(e)}", exc_info=True)
            
            # 最终检查并记录使用的字体
            if chinese_font_name == 'ChineseFont':
                logger.info(f"PDF生成将使用中文字体: {chinese_font_name}")
            else:
                logger.error(f"PDF生成将使用默认字体: {chinese_font_name} (中文可能无法正确显示！)")
            
            # 创建PDF缓冲区
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                  leftMargin=20*mm, rightMargin=20*mm,
                                  topMargin=20*mm, bottomMargin=20*mm)
            
            # 创建样式（使用支持中文的字体）
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=chinese_font_name,
                fontSize=18,
                textColor=colors.HexColor('#3498db'),
                alignment=1,  # 居中
                spaceAfter=20
            )
            
            meta_style = ParagraphStyle(
                'CustomMeta',
                parent=styles['Normal'],
                fontName=chinese_font_name,
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                alignment=1,  # 居中
                spaceAfter=20
            )
            
            para_style = ParagraphStyle(
                'CustomPara',
                parent=styles['Normal'],
                fontName=chinese_font_name,
                fontSize=11,
                leading=18,
                spaceAfter=15
            )
            
            trans_style = ParagraphStyle(
                'CustomTrans',
                parent=styles['Normal'],
                fontName=chinese_font_name,
                fontSize=10,
                leading=16,
                textColor=colors.HexColor('#666666'),
                leftIndent=15,
                spaceAfter=20
            )
            
            # 构建PDF内容
            story = []
            
            # 标题（确保使用中文字体）
            title = article.topic or '生成的文章'
            logger.info(f"PDF生成 - 标题: {title[:50]}...")
            logger.info(f"PDF生成 - 使用字体: {chinese_font_name}")
            story.append(Paragraph(html.escape(title), title_style))
            story.append(Spacer(1, 10))
            
            # 元信息 - 将UTC时间转换为中国时区显示
            from datetime import timezone, timedelta
            china_tz = timezone(timedelta(hours=8))
            created_at_str = '未知'
            if article.created_at:
                if article.created_at.tzinfo is None:
                    created_at_utc = article.created_at.replace(tzinfo=UTC)
                else:
                    created_at_utc = article.created_at
                created_at_china = created_at_utc.astimezone(china_tz)
                created_at_str = created_at_china.strftime('%Y-%m-%d %H:%M:%S')
            meta_text = f"难度: {article.difficulty_level or '未知'} | 长度: {article.article_length or '未知'} | 使用单词: {len(used_words_info)} 个 | 生成时间: {created_at_str}"
            story.append(Paragraph(html.escape(meta_text), meta_style))
            story.append(Spacer(1, 20))
            
            # 提取使用的单词列表（用于标记）
            used_words_list = [word_info['word'].lower() for word_info in used_words_info]
            logger.info(f"PDF生成 - 需要标记的单词: {used_words_list}")
            
            # 定义标记单词的函数
            def highlight_words_in_text(text, words_to_highlight):
                """
                在文本中标记指定的单词，使用黄色背景高亮
                返回包含HTML标记的文本（reportlab兼容格式）
                """
                if not words_to_highlight or not text:
                    return html.escape(text)
                
                # 转义HTML特殊字符
                escaped_text = html.escape(text)
                
                # 对每个单词进行标记（不区分大小写，但保持原文大小写）
                # 使用有序集合避免重复标记
                marked_positions = []  # 存储已标记的位置，避免重叠
                
                for word in words_to_highlight:
                    if not word:
                        continue
                    # 使用正则表达式匹配单词边界，不区分大小写
                    # \b 确保单词边界，避免部分匹配
                    pattern = r'\b(' + re.escape(word) + r')\b'
                    
                    # 找到所有匹配位置
                    for match in re.finditer(pattern, escaped_text, flags=re.IGNORECASE):
                        start, end = match.span()
                        # 检查是否与已标记的位置重叠
                        overlap = False
                        for marked_start, marked_end in marked_positions:
                            if not (end <= marked_start or start >= marked_end):
                                overlap = True
                                break
                        if not overlap:
                            marked_positions.append((start, end))
                
                # 从后往前替换，避免位置偏移问题
                marked_positions.sort(reverse=True)
                marked_text = escaped_text
                for start, end in marked_positions:
                    matched_word = marked_text[start:end]
                    # reportlab的Paragraph支持<font>标签，但backColor属性可能不支持
                    # 尝试使用背景色标记（黄色背景 #fff176，与前端保持一致）
                    # 如果backColor不支持，reportlab会忽略该属性，但不会报错
                    highlighted = f'<font color="#000000" backColor="#fff176">{matched_word}</font>'
                    # 备选方案：如果背景色不支持，使用橙色文字+粗体+下划线
                    # highlighted = f'<b><u><font color="#d97706">{matched_word}</font></u></b>'
                    marked_text = marked_text[:start] + highlighted + marked_text[end:]
                
                return marked_text
            
            # 文章段落
            logger.info(f"PDF生成 - 段落数量: {len(paragraphs)}")
            for i, para in enumerate(paragraphs):
                if para['original']:
                    # 原文（标记使用的单词）
                    original_text = highlight_words_in_text(para['original'], used_words_list)
                    if i == 0:
                        logger.info(f"PDF生成 - 第一段原文(前100字符): {para['original'][:100]}")
                    story.append(Paragraph(original_text, para_style))
                    story.append(Spacer(1, 8))
                    
                    # 译文（不需要标记）
                    if para['translated']:
                        if i == 0:
                            logger.info(f"PDF生成 - 第一段译文(前100字符): {para['translated'][:100]}")
                        story.append(Paragraph(html.escape(para['translated']), trans_style))
                        story.append(Spacer(1, 15))
            
            # 单词列表
            if used_words_info:
                story.append(Spacer(1, 20))
                # 使用支持中文的样式
                word_list_heading_style = ParagraphStyle(
                    'WordListHeading',
                    parent=styles['Heading2'],
                    fontName=chinese_font_name,
                    fontSize=14,
                    spaceAfter=10
                )
                story.append(Paragraph('<b>使用的单词列表</b>', word_list_heading_style))
                story.append(Spacer(1, 10))
                
                # 创建表格样式（用于表格单元格）
                table_cell_style = ParagraphStyle(
                    'TableCell',
                    parent=styles['Normal'],
                    fontName=chinese_font_name,
                    fontSize=8,
                    leading=10,
                    leftPadding=5,
                    rightPadding=5,
                    topPadding=3,
                    bottomPadding=3
                )
                
                # 创建表格标题样式
                table_header_style = ParagraphStyle(
                    'TableHeader',
                    parent=styles['Normal'],
                    fontName=chinese_font_name,
                    fontSize=9,
                    leading=12,
                    leftPadding=5,
                    rightPadding=5,
                    topPadding=5,
                    bottomPadding=5,
                    textColor=colors.HexColor('#2c3e50')
                )
                
                # 创建表格数据，使用Paragraph对象以支持中文
                table_data = [[
                    Paragraph('<b>单词</b>', table_header_style),
                    Paragraph('<b>词性</b>', table_header_style),
                    Paragraph('<b>释义</b>', table_header_style),
                    Paragraph('<b>例句</b>', table_header_style)
                ]]
                for word_info in used_words_info:
                    table_data.append([
                        Paragraph(html.escape(str(word_info.get('word', ''))), table_cell_style),
                        Paragraph(html.escape(str(word_info.get('part_of_speech', ''))), table_cell_style),
                        Paragraph(html.escape(str(word_info.get('definition', ''))), table_cell_style),
                        Paragraph(html.escape(str(word_info.get('example', ''))), table_cell_style)
                    ])
                
                # 创建表格，使用支持中文的字体
                table = Table(table_data, colWidths=[40*mm, 25*mm, 60*mm, 50*mm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#eeeeee')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]))
                
                story.append(table)
            
            # 构建PDF
            doc.build(story)
            
            # 获取PDF数据
            buffer.seek(0)
            pdf_data = buffer.read()
            buffer.close()
            
            # 生成文件名（使用用户设置的主题）
            # 确保使用文章主题作为文件名，优先使用article.topic，其次从文章内容提取
            user_topic = article.topic
            
            # 如果数据库中的主题为空，尝试从文章内容提取第一句话作为主题
            if not user_topic or user_topic.strip() == '':
                # 尝试从文章原始文本提取第一句话作为主题
                original_text = article.original_text or ''
                if original_text:
                    # 提取第一个句号、问号或感叹号之前的内容作为主题
                    match = re.match(r'^(.*?[。.!?])', original_text)
                    if match:
                        user_topic = match.group(1).strip()
                    else:
                        # 如果没有标点符号，使用前30个字符
                        user_topic = original_text[:30].strip()
                
                # 如果还是没有主题，使用默认值
                if not user_topic or user_topic.strip() == '':
                    user_topic = '生成的文章'
            
            logger.info(f"PDF文件名生成 - 使用的主题: {user_topic}")
            
            # 清理标题中的特殊字符，保留中文、英文、数字和常用符号
            safe_title = user_topic.strip()
            # 替换不安全的字符，但保留中文、日文、韩文等
            safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', safe_title)  # 只替换文件系统不安全的字符
            safe_title = re.sub(r'\s+', '_', safe_title)  # 多个空格替换为单个下划线
            safe_title = safe_title.strip('_')  # 去除首尾下划线
            
            # 限制文件名长度（避免过长）
            if len(safe_title) > 50:
                safe_title = safe_title[:50]
            
            # 如果标题为空或只有特殊字符，使用默认名称
            if not safe_title or len(safe_title.strip('_')) == 0:
                safe_title = '生成的文章'
                logger.warning("PDF文件名生成 - 主题为空，使用默认名称")
            
            logger.info(f"PDF文件名生成 - 清理后的主题: {safe_title}")
            
            # 生成文件名：主题_日期.pdf
            date_str = article.created_at.strftime('%Y-%m-%d') if article.created_at else 'unknown'
            filename = f"{safe_title}_{date_str}.pdf"
            logger.info(f"PDF文件名生成 - 最终文件名: {filename}")
            
            # 对文件名进行URL编码，解决中文文件名问题
            from urllib.parse import quote
            # RFC 5987格式要求：对文件名进行百分号编码
            # 特别注意：对于RFC 5987，我们需要编码所有非ASCII字符和特殊字符
            encoded_filename = quote(filename, safe='')
            logger.info(f"PDF文件名生成 - URL编码后的文件名: {encoded_filename}")
            
            # 生成ASCII安全的备用文件名（用于不支持RFC 5987的旧浏览器）
            # 直接使用文章ID作为基础，确保文件名稳定且唯一
            ascii_title_safe = f"article_{article.id}"
            logger.info(f"PDF文件名生成 - 使用文章ID作为基础文件名: {ascii_title_safe}")
            
            # 尝试从标题中提取ASCII字符（如果有），避免文件名过于单调
            title_ascii_part = re.sub(r'[^\x00-\x7F]', '', safe_title)  # 移除非ASCII字符
            title_ascii_part = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title_ascii_part)
            title_ascii_part = re.sub(r'\s+', '_', title_ascii_part).strip('_')
            
            # 如果标题中包含可用的ASCII部分，则添加到文件名中
            if title_ascii_part and len(title_ascii_part.strip()) > 0:
                # 限制长度，避免文件名过长
                title_ascii_part = title_ascii_part[:20]  # 限制标题部分长度
                ascii_title_safe = f"{title_ascii_part}_{article.id}"
                logger.info(f"PDF文件名生成 - 结合标题ASCII部分和文章ID: {ascii_title_safe}")
            
            # 生成最终的ASCII备用文件名
            ascii_filename = f"{ascii_title_safe}_{date_str}.pdf"
            logger.info(f"PDF文件名生成 - ASCII备用文件名: {ascii_filename}")
            
            # 返回PDF响应，使用正确的RFC 5987格式支持UTF-8文件名
            # 对于Linux服务器，使用更简单的文件名格式，避免编码问题
            # 生成简洁的文件名：article_文章ID_日期.pdf
            simple_filename = f"article_{article.id}_{date_str}.pdf"
            logger.info(f"PDF文件名生成 - 简化文件名: {simple_filename}")
            
            # 如果标题包含中文，尝试生成中文文件名（使用UTF-8编码）
            if safe_title and any('\u4e00' <= char <= '\u9fff' for char in safe_title):
                # 包含中文，使用UTF-8编码的文件名
                try:
                    # 使用RFC 5987格式
                    encoded_title = quote(safe_title.encode('utf-8'), safe='')
                    utf8_filename = f"{safe_title}_{date_str}.pdf"
                    encoded_utf8_filename = quote(utf8_filename.encode('utf-8'), safe='')
                    content_disposition = f'attachment; filename="{simple_filename}"; filename*=UTF-8\'\'{encoded_utf8_filename}'
                except Exception as e:
                    logger.warning(f"UTF-8文件名编码失败，使用ASCII文件名: {str(e)}")
                    content_disposition = f'attachment; filename="{simple_filename}"'
            else:
                # 不包含中文，直接使用ASCII文件名
                content_disposition = f'attachment; filename="{simple_filename}"'
            
            logger.info(f"PDF文件名生成 - Content-Disposition: {content_disposition[:200]}")
            
            # 设置响应头
            headers = {
                'Content-Disposition': content_disposition,
                'Content-Type': 'application/pdf; charset=utf-8'
            }
            logger.info("PDF文件名生成 - Content-Disposition header设置成功")
            
            return Response(
                content=pdf_data,
                media_type='application/pdf',
                headers=headers
            )
            
        except ImportError:
            # 如果没有安装reportlab，返回错误
            logger.error("reportlab库未安装，无法生成PDF")
            raise HTTPException(
                status_code=500, 
                detail="PDF生成功能需要安装reportlab库，请联系管理员"
            )
        except Exception as e:
            logger.error(f"生成PDF失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"生成PDF失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文章PDF失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载文章PDF失败: {str(e)}")

# 更新用户单词学习进度
async def update_word_progress(progress_data: List[UserProgressUpdate], request: Request, db: Session = Depends(get_db)):
    try:
        current_user = await get_current_user(request, db)
        updated_words = []
        
        for item in progress_data:
            # 检查单词是否存在
            word = db.query(VocabularyWord).filter(VocabularyWord.id == item.word_id).first()
            if not word:
                continue
            
            # 确保user_id是整数类型（UserWordProgress.user_id是Integer类型）
            user_id = int(current_user['id'])
            
            # 查找或创建进度记录
            progress = db.query(UserWordProgress).filter(
                UserWordProgress.user_id == user_id,
                UserWordProgress.word_id == item.word_id
            ).first()
            
            if not progress:
                progress = UserWordProgress(
                    user_id=user_id,
                    word_id=item.word_id
                )
                db.add(progress)
            
            # 更新进度
            progress.mastery_level = item.mastery_level
            progress.is_difficult = item.is_difficult
            progress.review_count += 1
            progress.last_reviewed = datetime.now(UTC)
            
            # 计算下次复习时间（基于艾宾浩斯记忆曲线）
            intervals = [0, 1, 2, 4, 7, 15, 30]  # 天数间隔
            review_index = min(progress.review_count, len(intervals) - 1)
            days_to_next_review = intervals[review_index]
            progress.next_review_date = datetime.now(UTC) + timedelta(days=days_to_next_review)
            
            updated_words.append(word.word)
        
        db.commit()
        
        return {
            "updated_count": len(updated_words),
            "updated_words": updated_words,
            "message": "学习进度更新成功"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新学习进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

# 更新单个单词状态（已知/未知）
async def update_word_status(request: Request, db: Session = Depends(get_db)):
    """更新单词学习状态，支持多种请求格式"""
    try:
        current_user = await get_current_user(request, db)
        
        # 从请求体获取数据
        try:
            body = await request.json()
        except:
            body = {}
        
        # 支持多种字段名称（兼容不同的前端调用方式）
        word_id = None
        word_text = None
        is_known = None
        
        # 尝试从不同字段获取word_id
        if 'word_id' in body:
            word_id = int(body['word_id'])
        elif 'wordId' in body:
            word_id = int(body['wordId'])
        elif 'id' in body:
            word_id = int(body['id'])
        
        # 如果没有word_id，尝试通过单词文本查找
        if not word_id:
            word_text = body.get('word') or body.get('word_text')
            if word_text:
                # 通过单词文本查找word_id
                word = db.query(VocabularyWord).filter(VocabularyWord.word == word_text).first()
                if word:
                    word_id = word.id
                else:
                    raise HTTPException(status_code=404, detail=f"单词 '{word_text}' 不存在")
            else:
                raise HTTPException(status_code=400, detail="缺少word_id或word参数")
        
        # 获取is_known状态（支持多种字段名）
        if 'is_known' in body:
            is_known = bool(body['is_known'])
        elif 'is_remembered' in body:
            is_known = bool(body['is_remembered'])
        elif 'status' in body:
            # status可能是"known", "unknown", "mastered"等
            status = body['status']
            is_known = status in ['known', 'mastered', 'remembered', True]
        else:
            raise HTTPException(status_code=400, detail="缺少is_known、is_remembered或status参数")
        
        # 检查单词是否存在
        word = db.query(VocabularyWord).filter(VocabularyWord.id == word_id).first()
        if not word:
            raise HTTPException(status_code=404, detail="单词不存在")
        
        # 确保user_id是整数类型
        user_id = int(current_user['id'])
        
        # 查找或创建进度记录
        progress = db.query(UserWordProgress).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.word_id == word_id
        ).first()
        
        if not progress:
            progress = UserWordProgress(
                user_id=user_id,
                word_id=word_id
            )
            db.add(progress)
        
        # 更新进度
        progress.mastery_level = 5 if is_known else 1
        progress.is_difficult = not is_known
        progress.review_count += 1
        progress.last_reviewed = datetime.now(UTC)
        
        # 计算下次复习时间
        intervals = [0, 1, 2, 4, 7, 15, 30]  # 天数间隔
        review_index = min(progress.review_count, len(intervals) - 1)
        days_to_next_review = intervals[review_index] if is_known else 0
        progress.next_review_date = datetime.now(UTC) + timedelta(days=days_to_next_review)
        
        db.commit()
        
        return {
            "word": word.word,
            "is_known": is_known,
            "message": f"单词已标记为{'已知' if is_known else '未知'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新单词状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

# 保存单词表
async def save_vocabulary_list(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = await get_current_user(request, db)
        logger.info(f"开始保存单词表，用户ID: {current_user['id']}")
        
        # 手动解析请求体，避免FastAPI自动验证
        data = await request.json()
        
        # 基本数据获取
        vocabulary = data.get('vocabulary', [])
        vocabulary_id = data.get('vocabulary_id')
        
        logger.info(f"单词表包含 {len(vocabulary)} 个单词")
        
        # 简单验证
        if not vocabulary or not isinstance(vocabulary, list):
            raise HTTPException(status_code=400, detail="单词表内容不能为空且必须为数组格式")
        
        # 过滤空单词
        valid_vocabulary = []
        for i, word_data in enumerate(vocabulary):
            if isinstance(word_data, dict) and word_data.get('word'):
                valid_vocabulary.append(word_data)
            else:
                logger.warning(f"跳过无效的单词数据: {word_data}")
        
        if not valid_vocabulary:
            raise HTTPException(status_code=400, detail="没有有效的单词数据")
        
        # 处理单词表ID
        if vocabulary_id:
            try:
                vocab_id_int = int(vocabulary_id)
                # 查找现有单词表
                vocab_list = db.query(VocabularyList).filter(
                    VocabularyList.id == vocab_id_int,
                    VocabularyList.created_by == int(current_user['id'])
                ).first()
                
                if not vocab_list:
                    raise HTTPException(status_code=404, detail="单词表不存在或无权限访问")
                
                # 删除现有单词
                db.query(VocabularyWord).filter(
                    VocabularyWord.vocabulary_list_id == vocab_id_int
                ).delete()
                
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="单词表ID格式错误")
        else:
            # 创建新单词表
            vocab_list = VocabularyList(
                name="自定义单词表",
                description="用户自定义单词表",
                is_preset=False,
                is_public=False,
                created_by=int(current_user['id']) if current_user['id'] else None
            )
            db.add(vocab_list)
            db.flush()
        
        # 添加有效单词
        for word_data in valid_vocabulary:
            vocabulary_word = VocabularyWord(
                vocabulary_list_id=vocab_list.id,
                word=word_data.get('word', '').strip(),
                definition=word_data.get('definition', '').strip(),
                part_of_speech=word_data.get('partOfSpeech', word_data.get('part_of_speech', '')).strip(),
                example=word_data.get('example', '').strip()
            )
            db.add(vocabulary_word)
        
        # 提交事务
        db.commit()
        db.refresh(vocab_list)
        
        logger.info(f"单词表保存成功，ID: {vocab_list.id}")
        return {
            "id": vocab_list.id,
            "name": vocab_list.name,
            "word_count": len(valid_vocabulary),
            "message": "单词表保存成功"
        }
        
    except HTTPException:
        raise
    except json.JSONDecodeError:
        logger.error("请求体不是有效的JSON格式")
        raise HTTPException(status_code=400, detail="请求数据格式错误，请检查JSON格式")
    except Exception as e:
        db.rollback()
        logger.error(f"保存单词表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

# 请求模型
class ReorganizeVocabularyRequest(BaseModel):
    word_ids: Optional[List[int]] = None  # 如果为空，则整理所有缺少信息的单词

# 使用AI批量整理单词表
async def reorganize_vocabulary_with_ai(
    vocabulary_list_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    使用AI批量整理单词表中的单词
    如果请求体中的word_ids为空，则整理所有缺少释义或词性的单词
    """
    try:
        current_user = await get_current_user(request, db)
        # 从请求体获取word_ids
        word_ids = None
        try:
            body = await request.json()
            if body and isinstance(body, dict):
                word_ids = body.get('word_ids')
        except:
            # 如果请求体为空或不是JSON，word_ids保持为None（整理所有）
            pass
        # 查询单词表
        vocab_list = db.query(VocabularyList).filter(
            VocabularyList.id == vocabulary_list_id
        ).first()
        
        if not vocab_list:
            raise HTTPException(status_code=404, detail="单词表不存在")
        
        # 检查权限（使用统一权限检查函数）
        if not check_vocabulary_permission(vocab_list, current_user):
            logger.warning(f"权限检查失败: created_by={vocab_list.created_by}, user_id={current_user.get('id')}, vocab_id={vocabulary_list_id}")
            raise HTTPException(status_code=403, detail="无权访问此单词表")
        
        # 获取需要整理的单词
        if word_ids:
            # 整理指定的单词
            words_query = db.query(VocabularyWord).filter(
                VocabularyWord.vocabulary_list_id == vocabulary_list_id,
                VocabularyWord.id.in_(word_ids)
            )
        else:
            # 整理所有缺少释义或词性的单词
            words_query = db.query(VocabularyWord).filter(
                VocabularyWord.vocabulary_list_id == vocabulary_list_id,
                (
                    (VocabularyWord.definition == None) |
                    (VocabularyWord.definition == "") |
                    (VocabularyWord.part_of_speech == None) |
                    (VocabularyWord.part_of_speech == "") |
                    (VocabularyWord.definition == "暂无解释") |
                    (VocabularyWord.part_of_speech == "未知")
                )
            )
        
        words_to_process = words_query.all()
        
        if not words_to_process:
            return {
                "message": "没有需要整理的单词",
                "processed_count": 0,
                "total_count": 0
            }
        
        # 准备AI处理的数据（按索引一一对应，避免同形词/大小写导致的映射失败）
        words_data = [{
            "word": w.word,
            "definition": (w.definition or ""),
            "part_of_speech": (w.part_of_speech or "")
        } for w in words_to_process]
        
        # 分批调用AI处理，避免一次请求过大导致耗时或失败
        logger.info(f"开始使用AI整理 {len(words_data)} 个单词")
        # 缺少密钥时给出显式提示（process_words_with_ai 会容错返回 processed=False）
        try:
            deepseek_key_set = bool(
                app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY else os.getenv("DEEPSEEK_API_KEY")
            )
        except Exception:
            deepseek_key_set = False

        BATCH_SIZE = 20
        processed_words: list = []
        total = len(words_data)
        for start in range(0, total, BATCH_SIZE):
            end = min(start + BATCH_SIZE, total)
            sub = words_data[start:end]
            logger.info(f"AI整理批次: {start+1}-{end}/{total}")
            sub_result = process_words_with_ai(sub)
            processed_words.extend(sub_result)
        
        # 更新数据库（按序更新，保证与输入一一对应）
        processed_count = 0
        failed_count = 0
        pair_count = min(len(words_to_process), len(processed_words))

        for i in range(pair_count):
            word = words_to_process[i]
            processed_word = processed_words[i] or {}

            if processed_word.get("processed", False):
                # 清洗字符串，避免空白覆盖
                new_def = (processed_word.get("definition") or "").strip()
                new_pos = (processed_word.get("part_of_speech") or "").strip()
                new_exm = (processed_word.get("example") or "").strip()

                if new_def:
                    word.definition = new_def
                if new_pos:
                    word.part_of_speech = new_pos
                if new_exm:
                    word.example = new_exm
                processed_count += 1
            else:
                failed_count += 1

        # 如果AI返回数量少于待处理数量，其余视为失败
        if len(words_to_process) > pair_count:
            failed_count += (len(words_to_process) - pair_count)
        
        # 提交事务
        db.commit()
        
        logger.info(f"AI整理完成: 成功 {processed_count} 个，失败 {failed_count} 个")

        # 构造更友好的反馈信息
        result: Dict[str, Any] = {
            "message": "单词整理完成",
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total_count": len(words_to_process)
        }

        if processed_count == 0:
            # 给出明显原因提示，便于前端直接展示
            if not deepseek_key_set:
                result["reason"] = "未配置 DEEPSEEK_API_KEY，已跳过AI处理"
            else:
                result["reason"] = "AI未返回可用结果，可能是网络/配额/返回格式问题"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"AI整理单词表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"整理失败: {str(e)}")

# 获取下一个复习会话
async def get_next_review_session(
    request: Request, 
    vocabulary_id: Optional[int] = Query(None, description="单词表ID，如果提供则只返回该单词表的单词"),
    limit: Optional[int] = Query(None, description="限制返回的单词数量"),
    review_type: Optional[str] = Query(None, description="复习类型：'reviewed'已复习，'unreviewed'未复习，None全部"),
    db: Session = Depends(get_db)
):
    try:
        current_user = await get_current_user(request, db)
        today = datetime.now(UTC)
        
        # 确保user_id是整数类型
        user_id = int(current_user['id'])
        
        # 构建基础查询
        base_query = db.query(VocabularyWord, UserWordProgress).join(
            UserWordProgress, VocabularyWord.id == UserWordProgress.word_id
        ).filter(
            UserWordProgress.user_id == user_id
        )
        
        # 如果指定了单词表ID，只查询该单词表的单词
        if vocabulary_id:
            # 验证单词表权限
            vocab_list = db.query(VocabularyList).filter(
                VocabularyList.id == vocabulary_id
            ).first()
            
            if not vocab_list:
                raise HTTPException(status_code=404, detail="单词表不存在")
            
            # 检查权限：用户创建的单词表或公开的预设单词表
            if not vocab_list.is_preset and str(vocab_list.created_by) != str(current_user['id']):
                raise HTTPException(status_code=403, detail="无权访问该单词表")
            
            # 过滤该单词表的单词
            base_query = base_query.filter(
                VocabularyWord.vocabulary_list_id == vocabulary_id
            )
        
        # 根据复习类型过滤单词
        if review_type == 'reviewed':
            # 只返回已复习过的单词（review_count > 0）
            review_words = base_query.filter(
                UserWordProgress.review_count > 0
            ).order_by(UserWordProgress.last_reviewed.desc()).all()
        elif review_type == 'unreviewed':
            # 查询未复习过的单词：包括已创建进度但未复习的，以及从未学习过的单词
            # 首先查询已创建进度但未复习的单词
            unreviewed_with_progress = base_query.filter(
                (UserWordProgress.review_count == 0) | (UserWordProgress.last_reviewed.is_(None))
            ).all()
            
            # 查询从未学习过的单词（需要单独查询，因为UserWordProgress记录不存在）
            user_word_ids = db.query(UserWordProgress.word_id).filter(
                UserWordProgress.user_id == str(current_user['id'])
            ).subquery()
            
            unreviewed_query = db.query(VocabularyWord).filter(
                ~VocabularyWord.id.in_(user_word_ids)
            )
            
            # 如果指定了单词表ID，只查询该单词表的单词
            if vocabulary_id:
                unreviewed_query = unreviewed_query.filter(
                    VocabularyWord.vocabulary_list_id == vocabulary_id
                )
            
            unreviewed_words = unreviewed_query.all()
            
            # 合并结果：对于从未学习过的单词，创建临时进度记录用于显示
            review_words = list(unreviewed_with_progress)
            for word in unreviewed_words:
                # 创建临时进度对象用于返回，但不保存到数据库
                temp_progress = type('TempProgress', (), {
                    'mastery_level': 0,
                    'is_difficult': False,
                    'review_count': 0,
                    'last_reviewed': None
                })()
                review_words.append((word, temp_progress))
        else:
            # 默认：先尝试获取今天需要复习的单词
            review_words = base_query.filter(
            UserWordProgress.next_review_date <= today
        ).order_by(UserWordProgress.next_review_date).all()
        
        # 如果没有需要复习的单词，且不是选择"未复习"类型，获取一些未学习过的单词
        if not review_words and review_type != 'unreviewed':
            # 查询用户未学习过的单词
            user_word_ids = db.query(UserWordProgress.word_id).filter(
                UserWordProgress.user_id == str(current_user['id'])
            ).subquery()
            
            # 构建新单词查询
            new_words_query = db.query(VocabularyWord).filter(
                ~VocabularyWord.id.in_(user_word_ids)
            )
            
            # 如果指定了单词表ID，只查询该单词表的新单词
            if vocabulary_id:
                new_words_query = new_words_query.filter(
                    VocabularyWord.vocabulary_list_id == vocabulary_id
                )
            
            # 限制数量
            limit_count = limit if limit else 20
            new_words = new_words_query.limit(limit_count).all()
            
            # 确保user_id是整数类型
            user_id = int(current_user['id'])
            
            # 为这些单词创建初始进度记录
            for word in new_words:
                progress = UserWordProgress(
                    user_id=user_id,
                    word_id=word.id,
                    mastery_level=0,
                    is_difficult=False,
                    review_count=0,
                    last_reviewed=None,
                    next_review_date=today
                )
                db.add(progress)
            
            db.commit()
            
            # 重新查询包含进度信息的单词
            review_words = db.query(VocabularyWord, UserWordProgress).join(
                UserWordProgress, VocabularyWord.id == UserWordProgress.word_id
            ).filter(
                UserWordProgress.user_id == user_id,
                UserWordProgress.word_id.in_([w.id for w in new_words])
            ).all()
        
        # 如果指定了limit，限制返回数量
        if limit and len(review_words) > limit:
            review_words = review_words[:limit]
        
        # 格式化返回数据
        words = []
        for word, progress in review_words:
            words.append({
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example,
                "mastery_level": progress.mastery_level,
                "is_difficult": progress.is_difficult,
                "review_count": progress.review_count,
                "last_reviewed": progress.last_reviewed
            })
        
        return {
            "session_id": str(uuid.uuid4()),
            "total_words": len(words),
            "words": words,
            "created_at": today
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取复习会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取复习会话失败: {str(e)}")

# 获取用户学习进度统计
async def get_learning_stats(request: Request, db: Session = Depends(get_db)):
    # 手动获取当前用户
    current_user = await get_current_user(request, db)
    try:
        # 确保user_id是整数类型（UserWordProgress.user_id是Integer类型）
        user_id = int(current_user['id'])
        
        # 统计已学习的单词数
        total_words = db.query(func.count(UserWordProgress.id)).filter(
            UserWordProgress.user_id == user_id
        ).scalar() or 0
        
        # 统计掌握的单词数（掌握度>=3）
        mastered_words = db.query(func.count(UserWordProgress.id)).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.mastery_level >= 3
        ).scalar() or 0
        
        # 统计学习中的单词数（掌握度1-2）
        learning_words = db.query(func.count(UserWordProgress.id)).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.mastery_level >= 1,
            UserWordProgress.mastery_level <= 2
        ).scalar() or 0
        
        # 统计未掌握的单词数（掌握度=0）
        unmastered_words = db.query(func.count(UserWordProgress.id)).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.mastery_level == 0
        ).scalar() or 0
        
        # 统计疑难单词数
        difficult_words = db.query(func.count(UserWordProgress.id)).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.is_difficult == True
        ).scalar() or 0
        
        # 计算学习天数（user_id已在上面定义）
        first_record = db.query(UserLearningRecord).filter(
            UserLearningRecord.user_id == user_id
        ).order_by(UserLearningRecord.created_at).first()
        
        learning_days = 0
        if first_record:
            # 检查数据库中的时间是否有时区信息
            if hasattr(first_record.created_at, 'tzinfo') and first_record.created_at.tzinfo is not None:
                # 如果有时区信息，使用带时区的当前时间
                delta = datetime.now(UTC) - first_record.created_at
            else:
                # 如果没有时区信息，使用不带时区的当前时间
                delta = datetime.now() - first_record.created_at
            learning_days = delta.days + 1
        
        # 计算总学习时长（秒）
        total_duration = db.query(func.sum(UserLearningRecord.duration)).filter(
            UserLearningRecord.user_id == user_id,
            UserLearningRecord.duration.isnot(None)
        ).scalar() or 0
        
        # 转换为小时和分钟
        hours = total_duration // 3600
        minutes = (total_duration % 3600) // 60
        duration_str = f"{hours}h {minutes}m"
        
        # 获取总学习分钟数（前端需要）
        total_time_minutes = (total_duration // 60) if total_duration > 0 else 0
        
        # 计算真实的每日学习单词量（过去7天）
        from datetime import timedelta
        daily_words_data = [0] * 7
        daily_words_labels = []
        
        # 获取过去7天的日期标签
        today = datetime.now(UTC).date()
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            if i == 0:
                daily_words_labels.append("今天")
            elif i == 1:
                daily_words_labels.append("昨天")
            else:
                # 使用星期几
                weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                daily_words_labels.append(weekdays[date.weekday()])
            
            # 统计该日期学习的单词数（通过UserWordProgress的created_at或last_reviewed）
            day_start = datetime.combine(date, datetime.min.time()).replace(tzinfo=UTC)
            day_end = datetime.combine(date, datetime.max.time()).replace(tzinfo=UTC)
            
            # 统计该日期创建或复习的单词数
            words_count = db.query(func.count(func.distinct(UserWordProgress.word_id))).filter(
                UserWordProgress.user_id == user_id,
                or_(
                    and_(UserWordProgress.created_at >= day_start, UserWordProgress.created_at <= day_end),
                    and_(UserWordProgress.last_reviewed >= day_start, UserWordProgress.last_reviewed <= day_end)
                )
            ).scalar() or 0
            
            daily_words_data[6 - i] = words_count
        
        daily_words = {
            "labels": daily_words_labels,
            "data": daily_words_data
        }
        
        # 计算真实的每周学习趋势（过去6周或从开始学习）
        weekly_trend_data = []
        weekly_trend_labels = []
        
        if first_record:
            # 计算从第一次学习到现在的周数
            start_date = first_record.created_at.date()
            end_date = datetime.now(UTC).date()
            weeks_diff = (end_date - start_date).days // 7 + 1
            
            # 限制最多显示12周
            weeks_to_show = min(weeks_diff, 12)
            
            # 如果不足6周，显示所有周；否则显示最近6周
            if weeks_to_show <= 6:
                weeks_to_show = weeks_to_show
            else:
                weeks_to_show = 6
            
            cumulative_words = 0
            for week in range(weeks_to_show):
                week_start_date = start_date + timedelta(weeks=week)
                week_end_date = min(start_date + timedelta(weeks=week + 1) - timedelta(days=1), end_date)
                
                week_start = datetime.combine(week_start_date, datetime.min.time()).replace(tzinfo=UTC)
                week_end = datetime.combine(week_end_date, datetime.max.time()).replace(tzinfo=UTC)
                
                # 统计该周学习的单词数
                week_words = db.query(func.count(func.distinct(UserWordProgress.word_id))).filter(
                    UserWordProgress.user_id == user_id,
                    or_(
                        and_(UserWordProgress.created_at >= week_start, UserWordProgress.created_at <= week_end),
                        and_(UserWordProgress.last_reviewed >= week_start, UserWordProgress.last_reviewed <= week_end)
                    )
                ).scalar() or 0
                
                cumulative_words += week_words
                weekly_trend_data.append(cumulative_words)
                weekly_trend_labels.append(f"第{week + 1}周")
        else:
            # 如果没有学习记录，返回空数据
            weekly_trend_data = [0]
            weekly_trend_labels = ["第1周"]
        
        weekly_trend = {
            "labels": weekly_trend_labels,
            "data": weekly_trend_data
        }
        
        # 返回完整的数据结构，包含前端所需的所有字段
        return {
            "total_words": total_words,
            "mastered_words": mastered_words,
            "mastery_rate": round((mastered_words / total_words * 100) if total_words > 0 else 0, 1),
            "difficult_words": difficult_words,
            "learning_days": learning_days,
            "total_duration": duration_str,
            "total_time_minutes": total_time_minutes,
            "learning_words": learning_words,
            "unmastered_words": unmastered_words,
            "daily_words": daily_words,
            "weekly_trend": weekly_trend
        }
        
    except Exception as e:
        logger.error(f"获取学习统计失败: {str(e)}")
        # 返回默认数据，避免前端完全无法工作
        return {
            "total_words": 0,
            "mastered_words": 0,
            "mastery_rate": 0,
            "difficult_words": 0,
            "learning_days": 0,
            "total_duration": "0h 0m",
            "total_time_minutes": 0,
            "learning_words": 0,
            "unmastered_words": 0,
            "daily_words": {
                "labels": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                "data": [45, 63, 78, 52, 91, 105, 68]
            },
            "weekly_trend": {
                "labels": ["第1周", "第2周", "第3周", "第4周", "第5周", "第6周"],
                "data": [250, 480, 690, 850, 1020, 1254]
            }
        }

# 获取待复习单词
async def get_words_for_review(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = await get_current_user(request, db)
        # 查询今天需要复习的单词
        # 确保user_id是整数类型
        user_id = int(current_user['id'])
        today = datetime.now(UTC)
        words = db.query(VocabularyWord, UserWordProgress).join(
            UserWordProgress, VocabularyWord.id == UserWordProgress.word_id
        ).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.next_review_date <= today
        ).order_by(UserWordProgress.next_review_date).all()
        
        # 格式化返回数据
        review_words = []
        for word, progress in words:
            review_words.append({
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example,
                "mastery_level": progress.mastery_level,
                "is_difficult": progress.is_difficult,
                "review_count": progress.review_count
            })
        
        return {
            "count": len(review_words),
            "words": review_words
        }
        
    except Exception as e:
        logger.error(f"获取复习单词失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取复习单词失败: {str(e)}")

# 获取疑难单词
async def get_difficult_words(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = await get_current_user(request, db)
        # 确保user_id是整数类型
        user_id = int(current_user['id'])
        
        # 查询标记为疑难的单词
        words = db.query(VocabularyWord, UserWordProgress).join(
            UserWordProgress, VocabularyWord.id == UserWordProgress.word_id
        ).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.is_difficult == True
        ).all()
        
        # 格式化返回数据
        difficult_words = []
        for word, progress in words:
            difficult_words.append({
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example,
                "mastery_level": progress.mastery_level,
                "review_count": progress.review_count,
                "last_reviewed": progress.last_reviewed
            })
        
        return {
            "count": len(difficult_words),
            "words": difficult_words
        }
        
    except Exception as e:
        logger.error(f"获取疑难单词失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取疑难单词失败: {str(e)}")

# 获取疑难单词（兼容前端接口）
async def get_difficult_words_compat(request: Request, db: Session = Depends(get_db)):
    # 直接调用现有的get_difficult_words函数
    result = await get_difficult_words(request=request, db=db)
    return result

# 获取用户已复习的单词列表
async def get_reviewed_words(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词（单词或释义）"),
    vocabulary_id: Optional[int] = Query(None, description="单词表ID过滤"),
    sort_by: Optional[str] = Query("last_reviewed", description="排序字段：last_reviewed, review_count, mastery_level, word"),
    order: Optional[str] = Query("desc", description="排序方向：asc, desc"),
    db: Session = Depends(get_db)
):
    """
    获取用户已复习的单词列表（支持分页、搜索、排序）
    """
    try:
        current_user = await get_current_user(request, db)
        # 确保user_id是整数类型
        user_id = int(current_user['id'])
        
        # 基础查询：已复习的单词（review_count > 0）
        base_query = db.query(VocabularyWord, UserWordProgress).join(
            UserWordProgress, VocabularyWord.id == UserWordProgress.word_id
        ).filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.review_count > 0
        )
        
        # 单词表过滤
        if vocabulary_id:
            base_query = base_query.filter(VocabularyWord.vocabulary_list_id == vocabulary_id)
        
        # 搜索过滤
        if search:
            search_term = f"%{search}%"
            base_query = base_query.filter(
                or_(
                    VocabularyWord.word.like(search_term),
                    VocabularyWord.definition.like(search_term)
                )
            )
        
        # 排序
        if sort_by == "last_reviewed":
            order_by = UserWordProgress.last_reviewed.desc() if order == "desc" else UserWordProgress.last_reviewed.asc()
        elif sort_by == "review_count":
            order_by = UserWordProgress.review_count.desc() if order == "desc" else UserWordProgress.review_count.asc()
        elif sort_by == "mastery_level":
            order_by = UserWordProgress.mastery_level.desc() if order == "desc" else UserWordProgress.mastery_level.asc()
        elif sort_by == "word":
            order_by = VocabularyWord.word.asc() if order == "asc" else VocabularyWord.word.desc()
        else:
            order_by = UserWordProgress.last_reviewed.desc()
        
        base_query = base_query.order_by(order_by)
        
        # 获取总数
        total_count = base_query.count()
        
        # 分页
        offset = (page - 1) * page_size
        words_data = base_query.offset(offset).limit(page_size).all()
        
        # 格式化返回数据
        words = []
        for word, progress in words_data:
            words.append({
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "part_of_speech": word.part_of_speech,
                "example": word.example,
                "pronunciation": getattr(word, 'pronunciation', None),
                "mastery_level": progress.mastery_level,
                "is_difficult": progress.is_difficult,
                "review_count": progress.review_count,
                "last_reviewed": progress.last_reviewed.isoformat() if progress.last_reviewed else None,
                "next_review_date": progress.next_review_date.isoformat() if progress.next_review_date else None,
                "vocabulary_list_id": word.vocabulary_list_id,
                "vocabulary_list_name": None  # 可以后续关联查询
            })
        
        # 获取单词表名称（如果需要）
        if words:
            vocab_ids = list(set([w["vocabulary_list_id"] for w in words if w["vocabulary_list_id"]]))
            if vocab_ids:
                vocab_lists = db.query(VocabularyList).filter(VocabularyList.id.in_(vocab_ids)).all()
                vocab_dict = {v.id: v.name for v in vocab_lists}
                for w in words:
                    if w["vocabulary_list_id"] in vocab_dict:
                        w["vocabulary_list_name"] = vocab_dict[w["vocabulary_list_id"]]
        
        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "words": words
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取已复习单词列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取已复习单词列表失败: {str(e)}")

# 完成复习会话
async def complete_review_session(session_id: str, review_data: Dict[str, Any], request: Request, db: Session = Depends(get_db)):
    try:
        current_user = await get_current_user(request, db)
        # 获取复习数据
        reviewed_words = review_data.get('words', [])
        duration = review_data.get('duration', 0)
        
        # 更新单词进度
        updated_words = []
        for word_data in reviewed_words:
            word_id = word_data.get('id')
            mastery_level = word_data.get('mastery_level', 0)
            is_difficult = word_data.get('is_difficult', False)
            
            if word_id is not None:
                # 确保user_id是整数类型
                user_id = int(current_user['id'])
                
                # 查找或创建进度记录
                progress = db.query(UserWordProgress).filter(
                    UserWordProgress.user_id == user_id,
                    UserWordProgress.word_id == word_id
                ).first()
                
                if progress:
                    # 更新进度
                    progress.mastery_level = mastery_level
                    progress.is_difficult = is_difficult
                    progress.review_count += 1
                    progress.last_reviewed = datetime.now(UTC)
                    
                    # 计算下次复习时间（基于艾宾浩斯记忆曲线）
                    intervals = [0, 1, 2, 4, 7, 15, 30]  # 天数间隔
                    review_index = min(progress.review_count, len(intervals) - 1)
                    days_to_next_review = intervals[review_index]
                    progress.next_review_date = datetime.now(UTC) + timedelta(days=days_to_next_review)
                    
                    updated_words.append(word_id)
        
        # 记录学习活动（UserLearningRecord.user_id是Integer类型）
        # 注意：user_id已在上面循环中定义，但这里需要确保使用正确的类型
        review_user_id = int(current_user['id'])
        learning_record = UserLearningRecord(
            user_id=review_user_id,
            activity_type="vocabulary_review",
            activity_details=json.dumps({
                "session_id": session_id,
                "reviewed_words": updated_words,
                "duration": duration
            }),
            duration=duration
        )
        db.add(learning_record)
        db.commit()
        
        return {
            "session_id": session_id,
            "updated_words": len(updated_words),
            "duration": duration,
            "message": "复习会话完成并记录成功"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"完成复习会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"完成复习会话失败: {str(e)}")

# 初始化预设单词表
def init_preset_vocabulary_lists(db: Session):
    """初始化预设单词表数据"""
    try:
        # 检查是否已存在预设单词表
        existing = db.query(func.count(VocabularyList.id)).filter(VocabularyList.is_preset == True).scalar()
        if existing > 0:
            logger.info(f"预设单词表已存在: {existing} 个")
            return
        
        # 基础英语单词表
        basic_words = [
            {"word": "apple", "definition": "苹果", "part_of_speech": "n.", "example": "I eat an apple every day."},
            {"word": "book", "definition": "书", "part_of_speech": "n.", "example": "This is my favorite book."},
            {"word": "computer", "definition": "电脑", "part_of_speech": "n.", "example": "I use a computer for work."},
            {"word": "friend", "definition": "朋友", "part_of_speech": "n.", "example": "He is my best friend."},
            {"word": "home", "definition": "家", "part_of_speech": "n.", "example": "I want to go home."},
            {"word": "study", "definition": "学习", "part_of_speech": "v.", "example": "I study English every day."},
            {"word": "work", "definition": "工作", "part_of_speech": "v./n.", "example": "I work in an office."},
            {"word": "love", "definition": "爱", "part_of_speech": "v./n.", "example": "I love my family."},
            {"word": "time", "definition": "时间", "part_of_speech": "n.", "example": "What time is it?"},
            {"word": "day", "definition": "天", "part_of_speech": "n.", "example": "Today is a good day."}
        ]
        
        # 旅游英语单词表
        travel_words = [
            {"word": "airport", "definition": "机场", "part_of_speech": "n.", "example": "We arrived at the airport early."},
            {"word": "hotel", "definition": "酒店", "part_of_speech": "n.", "example": "We stayed at a nice hotel."},
            {"word": "ticket", "definition": "票", "part_of_speech": "n.", "example": "I bought a plane ticket."},
            {"word": "tour", "definition": "旅游", "part_of_speech": "n./v.", "example": "We took a tour of the city."},
            {"word": "restaurant", "definition": "餐厅", "part_of_speech": "n.", "example": "Let's go to that new restaurant."},
            {"word": "map", "definition": "地图", "part_of_speech": "n.", "example": "I need a map to find my way."},
            {"word": "camera", "definition": "相机", "part_of_speech": "n.", "example": "I took many photos with my camera."},
            {"word": "luggage", "definition": "行李", "part_of_speech": "n.", "example": "My luggage is heavy."},
            {"word": "passport", "definition": "护照", "part_of_speech": "n.", "example": "Don't forget your passport!"},
            {"word": "destination", "definition": "目的地", "part_of_speech": "n.", "example": "What's your destination?"}
        ]
        
        # 商务英语单词表
        business_words = [
            {"word": "meeting", "definition": "会议", "part_of_speech": "n.", "example": "We have a meeting tomorrow."},
            {"word": "project", "definition": "项目", "part_of_speech": "n.", "example": "He is working on a new project."},
            {"word": "report", "definition": "报告", "part_of_speech": "n./v.", "example": "I need to write a report."},
            {"word": "deadline", "definition": "截止日期", "part_of_speech": "n.", "example": "We have to meet the deadline."},
            {"word": "budget", "definition": "预算", "part_of_speech": "n.", "example": "We need to stay within the budget."},
            {"word": "client", "definition": "客户", "part_of_speech": "n.", "example": "The client is very important."},
            {"word": "contract", "definition": "合同", "part_of_speech": "n.", "example": "We signed a contract."},
            {"word": "proposal", "definition": "提案", "part_of_speech": "n.", "example": "Let's discuss the proposal."},
            {"word": "team", "definition": "团队", "part_of_speech": "n.", "example": "We are a great team."},
            {"word": "strategy", "definition": "策略", "part_of_speech": "n.", "example": "We need a new strategy."}
        ]
        
        # 创建预设单词表
        lists_to_create = [
            {"name": "基础英语单词", "description": "适合初学者的常用英语单词", "words": basic_words},
            {"name": "旅游英语词汇", "description": "旅游出行必备英语词汇", "words": travel_words},
            {"name": "商务英语常用词", "description": "职场商务场景常用英语单词", "words": business_words}
        ]
        
        for list_data in lists_to_create:
            vocab_list = VocabularyList(
                name=list_data["name"],
                description=list_data["description"],
                is_preset=True,
                is_public=True
            )
            db.add(vocab_list)
            db.flush()
            
            for word_data in list_data["words"]:
                word = VocabularyWord(
                    vocabulary_list_id=vocab_list.id,
                    word=word_data["word"],
                    definition=word_data["definition"],
                    part_of_speech=word_data["part_of_speech"],
                    example=word_data["example"]
                )
                db.add(word)
        
        db.commit()
        logger.info(f"成功创建 {len(lists_to_create)} 个预设单词表")
        
    except Exception as e:
        db.rollback()
        logger.error(f"初始化预设单词表失败: {str(e)}")

# 查询单词表上传任务状态
async def get_upload_task_status(task_id: str, request: Request, db: Session = Depends(get_db)):
    """查询单词表上传任务状态"""
    try:
        # 获取当前用户（可选，用于验证权限）
        current_user = await get_current_user(request, db)
        user_id = current_user.get('id')
        
        # 查询任务
        task = db.query(VocabularyUploadTask).filter(VocabularyUploadTask.task_id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 验证权限：只能查看自己的任务
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权访问此任务")
        
        return {
            "task_id": task.task_id,
            "vocabulary_list_id": task.vocabulary_list_id,
            "status": task.status,
            "progress": task.progress,
            "total_words": task.total_words,
            "processed_words": task.processed_words,
            "message": task.message,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

# 注册API端点到FastAPI应用 - 与app框架完全兼容
async def delete_vocabulary_list(vocabulary_list_id: int, request: Request, db: Session = Depends(get_db)):
    """删除用户单词表 - 使用统一的认证方式"""
    try:
        # 获取当前用户
        current_user = await get_current_user(request, db)
        user_id_int = current_user.get('id')
        
        if not user_id_int:
            logger.error("删除单词表失败: 用户未登录")
            return {"status": "error", "message": "用户未登录"}
        
        # 转换ID为整数
        list_id = int(vocabulary_list_id)
        
        logger.info(f"尝试删除单词表ID: {list_id}, 用户ID: {user_id_int}")
        
        # 先查找单词表是否存在并属于当前用户
        vocabulary_list = db.query(VocabularyList).filter(
            VocabularyList.id == list_id
        ).first()
        
        if not vocabulary_list:
            logger.warning(f"单词表不存在: ID={list_id}")
            return {"status": "error", "message": "单词表不存在"}
        
        # 检查权限（使用统一权限检查函数）
        # 构建current_user字典用于权限检查
        current_user_dict = {"id": user_id_int}
        if not check_vocabulary_permission(vocabulary_list, current_user_dict):
            logger.warning(f"权限不足: 用户{user_id_int}尝试删除单词表{list_id}(所有者:{vocabulary_list.created_by})")
            return {"status": "error", "message": "无权限删除该单词表"}
        
        if vocabulary_list.is_preset:
            logger.warning(f"无法删除预设单词表: {list_id}")
            return {"status": "error", "message": "无法删除预设单词表"}
        
        # 先删除相关单词
        word_count = db.query(VocabularyWord).filter(VocabularyWord.vocabulary_list_id == list_id).delete()
        logger.info(f"删除了{word_count}个相关单词")
        
        # 删除单词表
        result = db.query(VocabularyList).filter(
            VocabularyList.id == list_id
        ).delete()
        
        db.commit()
        
        if result > 0:
            logger.info(f"单词表{list_id}删除成功")
            return {"status": "success", "message": "删除成功"}
        else:
            logger.error(f"单词表{list_id}删除失败: 记录不存在或权限不足")
            return {"status": "error", "message": "删除失败: 记录不存在或权限不足"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"删除单词表时发生错误: {str(e)}")
        return {"status": "error", "message": f"删除失败: {str(e)}"}

def migrate_database_tables():
    """迁移数据库表，添加新字段"""
    try:
        from app import engine
        from sqlalchemy import text
        
        # 使用begin()来确保事务正确提交
        with engine.begin() as conn:
            # 检查并添加 generated_articles 表的 used_word_ids 列
            try:
                conn.execute(text("SELECT used_word_ids FROM generated_articles LIMIT 1"))
                logger.info("generated_articles.used_word_ids 列已存在")
            except Exception:
                logger.info("正在添加 generated_articles.used_word_ids 列...")
                conn.execute(text("ALTER TABLE generated_articles ADD COLUMN used_word_ids TEXT NULL"))
                logger.info("成功添加 generated_articles.used_word_ids 列")
            
            # 检查并添加语言字段到各个表
            # vocabulary_lists 表
            try:
                conn.execute(text("SELECT language FROM vocabulary_lists LIMIT 1"))
                logger.info("vocabulary_lists.language 列已存在")
            except Exception:
                logger.info("正在添加 vocabulary_lists.language 列...")
                conn.execute(text("ALTER TABLE vocabulary_lists ADD COLUMN language VARCHAR(10) DEFAULT 'en' NOT NULL"))
                logger.info("成功添加 vocabulary_lists.language 列")
            
            # public_vocabulary_words 表的 tag 字段
            try:
                conn.execute(text("SELECT tag FROM public_vocabulary_words LIMIT 1"))
                logger.info("public_vocabulary_words.tag 列已存在")
            except Exception:
                logger.info("正在添加 public_vocabulary_words.tag 列...")
                conn.execute(text("ALTER TABLE public_vocabulary_words ADD COLUMN tag VARCHAR(50) NULL"))
                # 添加索引以提高查询性能
                try:
                    conn.execute(text("CREATE INDEX idx_public_vocab_tag ON public_vocabulary_words(tag)"))
                    logger.info("成功添加 public_vocabulary_words.tag 列和索引")
                except Exception as e:
                    logger.warning(f"添加tag索引失败（可能已存在）: {str(e)}")
                    logger.info("成功添加 public_vocabulary_words.tag 列")
            
            # vocabulary_words 表
            try:
                conn.execute(text("SELECT language FROM vocabulary_words LIMIT 1"))
                logger.info("vocabulary_words.language 列已存在")
            except Exception:
                logger.info("正在添加 vocabulary_words.language 列...")
                conn.execute(text("ALTER TABLE vocabulary_words ADD COLUMN language VARCHAR(10) DEFAULT 'en' NOT NULL"))
                logger.info("成功添加 vocabulary_words.language 列")
            
            # public_vocabulary_words 表
            try:
                conn.execute(text("SELECT language FROM public_vocabulary_words LIMIT 1"))
                logger.info("public_vocabulary_words.language 列已存在")
            except Exception:
                logger.info("正在添加 public_vocabulary_words.language 列...")
                # 先检查是否有unique约束，如果有需要删除
                try:
                    conn.execute(text("ALTER TABLE public_vocabulary_words DROP INDEX word"))
                except:
                    pass
                conn.execute(text("ALTER TABLE public_vocabulary_words ADD COLUMN language VARCHAR(10) DEFAULT 'en' NOT NULL"))
                # 添加索引
                try:
                    conn.execute(text("CREATE INDEX idx_public_word_lang ON public_vocabulary_words(word, language)"))
                except:
                    pass
                logger.info("成功添加 public_vocabulary_words.language 列")
            
            # 检查 article_used_words 表是否存在
            try:
                conn.execute(text("SELECT COUNT(*) FROM article_used_words LIMIT 1"))
                logger.info("article_used_words 表已存在")
            except Exception:
                logger.info("正在创建 article_used_words 表...")
                ArticleUsedWord.__table__.create(bind=engine, checkfirst=True)
                logger.info("成功创建 article_used_words 表")
                
    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}", exc_info=True)

def check_and_complete_missing_words(db: Session):
    """检查并补全缺少释义和词性的单词"""
    try:
        # 查询所有缺少释义或词性的单词（包括公共单词库和用户单词表）
        # 检查公共单词库
        incomplete_public_words = db.query(PublicVocabularyWord).filter(
            or_(
                PublicVocabularyWord.definition == None,
                PublicVocabularyWord.definition == "",
                PublicVocabularyWord.definition == "暂无解释",
                PublicVocabularyWord.part_of_speech == None,
                PublicVocabularyWord.part_of_speech == "",
                PublicVocabularyWord.part_of_speech == "未知"
            )
        ).limit(50).all()  # 每次最多处理50个，避免启动时间过长
        
        # 检查用户单词表中的单词
        incomplete_user_words = db.query(VocabularyWord).filter(
            or_(
                VocabularyWord.definition == None,
                VocabularyWord.definition == "",
                VocabularyWord.definition == "暂无解释",
                VocabularyWord.part_of_speech == None,
                VocabularyWord.part_of_speech == "",
                VocabularyWord.part_of_speech == "未知"
            )
        ).limit(50).all()
        
        total_incomplete = len(incomplete_public_words) + len(incomplete_user_words)
        
        if total_incomplete == 0:
            logger.info("所有单词信息完整，无需补全")
            return
        
        logger.info(f"发现 {total_incomplete} 个缺少信息的单词，开始自动补全...")
        
        # 合并所有需要处理的单词
        all_words_to_process = []
        
        # 处理公共单词库
        for word in incomplete_public_words:
            all_words_to_process.append({
                "word": word,
                "type": "public",
                "word_text": word.word
            })
        
        # 处理用户单词表
        for word in incomplete_user_words:
            all_words_to_process.append({
                "word": word,
                "type": "user",
                "word_text": word.word
            })
        
        # 准备批量处理的数据
        words_data = [{
            "word": item["word_text"],
            "definition": item["word"].definition or "",
            "part_of_speech": item["word"].part_of_speech or ""
        } for item in all_words_to_process]
        
        # 分批调用AI处理
        batch_size = 20
        processed_count = 0
        
        for i in range(0, len(words_data), batch_size):
            batch = words_data[i:i + batch_size]
            batch_items = all_words_to_process[i:i + batch_size]
            
            logger.info(f"处理批次 {i // batch_size + 1}: {len(batch)} 个单词")
            
            # 调用AI处理
            processed_results = process_words_with_ai(batch)
            
            # 更新数据库
            for j, result in enumerate(processed_results):
                if j < len(batch_items):
                    item = batch_items[j]
                    word_obj = item["word"]
                    
                    if result.get("processed", False):
                        definition = result.get("definition", "").strip()
                        part_of_speech = result.get("part_of_speech", "").strip()
                        
                        if definition and part_of_speech:
                            # 更新单词信息
                            word_obj.definition = definition
                            word_obj.part_of_speech = part_of_speech
                            if result.get("example"):
                                word_obj.example = result.get("example", "").strip()
                            
                            processed_count += 1
            
            # 每处理完一批就提交一次
            db.commit()
            logger.info(f"批次 {i // batch_size + 1} 处理完成，已更新 {processed_count} 个单词")
        
        logger.info(f"单词补全完成！共处理 {len(words_data)} 个单词，成功更新 {processed_count} 个")
        
    except Exception as e:
        logger.error(f"自动补全单词信息失败: {str(e)}", exc_info=True)
        # 不抛出异常，避免影响应用启动

def register_language_learning_routes(app):
    """注册语言学习相关的所有API端点到FastAPI应用"""
    logger.info("开始注册语言学习模块路由...")
    
    # 首先创建数据库表（使用engine而不是get_db，避免依赖问题）
    try:
        from app import engine
        Base.metadata.create_all(bind=engine)
        logger.info("语言学习模块数据库表创建/检查完成")
        
        # 执行数据库迁移（添加新字段）
        migrate_database_tables()
    except Exception as e:
        logger.warning(f"创建数据库表失败（将稍后重试）: {str(e)}")
    
    # 初始化预设单词表 - 使用app框架的数据库会话（可选，不阻止路由注册）
    try:
        from app import SessionLocal
        db = SessionLocal()
        try:
            init_preset_vocabulary_lists(db)
            logger.info("预设单词表初始化完成")
            
            # 检查并补全缺少信息的单词（在后台异步执行，不阻塞启动）
            import threading
            def async_complete_words():
                try:
                    db_local = SessionLocal()
                    try:
                        check_and_complete_missing_words(db_local)
                    finally:
                        db_local.close()
                except Exception as e:
                    logger.error(f"后台补全单词失败: {str(e)}")
            
            # 在后台线程中执行，不阻塞应用启动
            thread = threading.Thread(target=async_complete_words, daemon=True)
            thread.start()
            logger.info("已启动后台任务：自动补全缺少信息的单词")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"预设单词表初始化失败（不影响路由注册）: {str(e)}")
    
    # 单词表管理
    app.post("/api/vocabulary/upload", response_model=Dict[str, Any])(upload_vocabulary_file)
    app.get("/api/vocabulary/upload/task/{task_id}", response_model=Dict[str, Any])(get_upload_task_status)
    app.get("/api/vocabulary/lists")(get_vocabulary_lists)
    app.get("/api/vocabulary/lists/{vocabulary_list_id}", response_model=Dict[str, Any])(get_vocabulary_list)
    # 使用简单路径参数，避免类型验证问题
    app.delete("/api/vocabulary/lists/{vocabulary_list_id}")(delete_vocabulary_list)
    # 单词增强功能
    app.get("/api/vocabulary/word/{word_id}/enhanced", response_model=Dict[str, Any])(get_enhanced_word_info)
    
    # 文章生成
    app.post("/api/articles/generate", response_model=Dict[str, Any])(generate_article)
    
    # AI生成主题建议
    async def generate_topic_suggestions(request: Request, db: Session = Depends(get_db)):
        """基于选中的单词生成5个主题建议"""
        try:
            current_user = await get_current_user(request, db)
            data = await request.json()
            
            # 支持两种方式：1) selected_word_ids (用户单词表的ID)  2) words (单词文本列表，来自系统词库或自定义单词)
            selected_word_ids = data.get("selected_word_ids", [])
            words_text_list = data.get("words", [])
            
            word_list = None
            
            # 方式1：如果提供了selected_word_ids，从数据库查询单词
            if selected_word_ids and len(selected_word_ids) > 0:
                words = db.query(VocabularyWord).filter(VocabularyWord.id.in_(selected_word_ids)).all()
                if words:
                    word_list = ", ".join([word.word for word in words])
            
            # 方式2：如果提供了words文本列表，直接使用
            if not word_list and words_text_list and len(words_text_list) > 0:
                # 过滤掉空字符串
                valid_words = [w.strip() for w in words_text_list if w and w.strip()]
                if valid_words:
                    word_list = ", ".join(valid_words)
            
            if not word_list:
                logger.warning(f"生成主题建议失败：未找到有效的单词数据。selected_word_ids={selected_word_ids}, words={words_text_list}")
                return {"topics": []}
            
            # 调用AI生成主题建议
            from openai import OpenAI
            import os
            
            deepseek_api_key = (
                app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY else os.getenv("DEEPSEEK_API_KEY")
            )
            if not deepseek_api_key:
                return {"topics": []}
            
            client = OpenAI(
                api_key=deepseek_api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
            prompt = f"""
基于以下英语单词，生成5个适合写文章的主题建议。每个主题应该：
1. 简洁明了（2-8个字）
2. 与这些单词相关
3. 适合用于写作练习
4. 主题多样，涵盖不同领域（如科技、生活、教育、文化、商业等）

单词列表：{word_list}

请以JSON数组格式返回5个主题，例如：
["科技与创新", "日常生活", "教育发展", "文化交流", "商业趋势"]

只返回JSON数组，不要其他说明文字。
"""
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的写作助手，擅长根据单词生成合适的文章主题。请只返回JSON数组格式的主题列表。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            ai_content = response.choices[0].message.content.strip()
            
            # 提取JSON数组
            import json
            import re
            json_match = re.search(r'\[.*\]', ai_content, re.DOTALL)
            if json_match:
                topics = json.loads(json_match.group())
                # 确保返回5个主题，如果不够则补充
                while len(topics) < 5:
                    topics.append(f"主题{len(topics) + 1}")
                return {"topics": topics[:5]}
            else:
                # 如果解析失败，返回默认主题
                return {"topics": ["科技与创新", "日常生活", "教育发展", "文化交流", "商业趋势"]}
                
        except Exception as e:
            logger.error(f"生成主题建议失败: {str(e)}", exc_info=True)
            return {"topics": []}
    
    app.post("/api/articles/generate-topics", response_model=Dict[str, Any])(generate_topic_suggestions)
    app.get("/api/articles", response_model=Dict[str, Any])(get_user_articles)
    app.get("/api/articles/{article_id}", response_model=Dict[str, Any])(get_article_detail)
    app.get("/api/articles/{article_id}/download/pdf")(download_article_pdf)
    
    # 学习进度
    app.post("/api/progress/update", response_model=Dict[str, Any])(update_word_progress)
    app.get("/api/progress/stats")(get_learning_stats)
    
    # 获取按掌握程度分类的单词列表
    async def get_words_by_mastery(
        request: Request,
        mastery_type: str = Query(..., description="掌握类型：mastered(已掌握), learning(学习中), unmastered(未掌握)"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(50, ge=1, le=200, description="每页数量"),
        db: Session = Depends(get_db)
    ):
        """根据掌握程度获取单词列表"""
        try:
            current_user = await get_current_user(request, db)
            user_id = int(current_user['id'])
            
            # 构建查询
            base_query = db.query(VocabularyWord, UserWordProgress).join(
                UserWordProgress, VocabularyWord.id == UserWordProgress.word_id
            ).filter(
                UserWordProgress.user_id == user_id
            )
            
            # 根据类型过滤
            if mastery_type == "mastered":
                # 已掌握：mastery_level >= 3
                base_query = base_query.filter(UserWordProgress.mastery_level >= 3)
            elif mastery_type == "learning":
                # 学习中：mastery_level >= 1 and mastery_level <= 2
                base_query = base_query.filter(
                    UserWordProgress.mastery_level >= 1,
                    UserWordProgress.mastery_level <= 2
                )
            elif mastery_type == "unmastered":
                # 未掌握：mastery_level == 0
                base_query = base_query.filter(UserWordProgress.mastery_level == 0)
            else:
                raise HTTPException(status_code=400, detail="无效的掌握类型")
            
            # 计算总数
            total = base_query.count()
            
            # 分页
            offset = (page - 1) * page_size
            words_data = base_query.order_by(
                UserWordProgress.mastery_level.desc(),
                VocabularyWord.word.asc()
            ).offset(offset).limit(page_size).all()
            
            # 格式化返回数据
            words = []
            for word, progress in words_data:
                words.append({
                    "id": word.id,
                    "word": word.word,
                    "definition": word.definition,
                    "part_of_speech": word.part_of_speech,
                    "example": word.example,
                    "mastery_level": progress.mastery_level,
                    "review_count": progress.review_count,
                    "last_reviewed": progress.last_reviewed.isoformat() if progress.last_reviewed else None
                })
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "words": words
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取单词列表失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"获取单词列表失败: {str(e)}")
    
    app.get("/api/progress/words-by-mastery")(get_words_by_mastery)
    
    # 记录学习时长
    async def record_learning_duration(request: Request, db: Session = Depends(get_db)):
        """记录用户在学习页面的停留时间"""
        try:
            current_user = await get_current_user(request, db)
            user_id = int(current_user['id'])
            
            data = await request.json()
            duration = data.get("duration", 0)  # 停留时间（秒）
            activity_type = data.get("activity_type", "page_view")  # 活动类型
            
            if duration <= 0:
                return {"message": "时长无效", "success": False}
            
            # 记录学习活动
            learning_record = UserLearningRecord(
                user_id=user_id,
                activity_type=activity_type,
                activity_details=json.dumps({"page": "language_learning"}),
                duration=duration
            )
            db.add(learning_record)
            db.commit()
            
            logger.info(f"用户 {user_id} 学习时长已记录: {duration} 秒")
            return {"message": "学习时长已记录", "success": True}
            
        except Exception as e:
            logger.error(f"记录学习时长失败: {str(e)}", exc_info=True)
            db.rollback()
            raise HTTPException(status_code=500, detail=f"记录学习时长失败: {str(e)}")
    
    app.post("/api/progress/record-duration", response_model=Dict[str, Any])(record_learning_duration)
    app.post("/api/progress/words", response_model=Dict[str, Any])(update_word_status)
    
    # 单词复习
    app.get("/api/review/words", response_model=Dict[str, Any])(get_words_for_review)
    app.get("/api/review/difficult", response_model=Dict[str, Any])(get_difficult_words)
    app.get("/api/review/difficult-words", response_model=Dict[str, Any])(get_difficult_words_compat)
    app.get("/api/review/next-session", response_model=Dict[str, Any])(get_next_review_session)
    app.post("/api/review/complete/{session_id}", response_model=Dict[str, Any])(complete_review_session)
    app.get("/api/review/reviewed-words", response_model=Dict[str, Any])(get_reviewed_words)
    
    # 单词表管理扩展
    app.post("/api/vocabulary/save", response_model=Dict[str, Any])(save_vocabulary_list)
    
    # 批量AI整理单词表
    async def reorganize_endpoint(vocabulary_list_id: int, request: Request, db: Session = Depends(get_db)):
        return await reorganize_vocabulary_with_ai(vocabulary_list_id, request, db)
    
    app.post("/api/vocabulary/{vocabulary_list_id}/reorganize", response_model=Dict[str, Any])(reorganize_endpoint)
    
    # 公共词库（系统词库）
    async def get_public_words(
        request: Request,
        language: str = Query('en', description="语言代码"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=200, description="每页数量"),
        search: Optional[str] = Query(None, description="搜索关键词"),
        db: Session = Depends(get_db)
    ):
        """获取公共词库（系统词库）单词列表"""
        try:
            # 验证用户（可选，公共词库可以不需要登录）
            # current_user = await get_current_user(request, db)
            
            # 构建查询
            query = db.query(PublicVocabularyWord).filter(
                PublicVocabularyWord.language == language
            )
            
            # 搜索关键词
            if search and search.strip():
                search_pattern = f"%{search.strip()}%"
                query = query.filter(
                    or_(
                        PublicVocabularyWord.word.ilike(search_pattern),
                        PublicVocabularyWord.definition.ilike(search_pattern),
                        PublicVocabularyWord.example.ilike(search_pattern)
                    )
                )
            
            # 计算总数
            total = query.count()
            
            # 分页
            offset = (page - 1) * page_size
            words_data = query.order_by(
                PublicVocabularyWord.usage_count.desc(),
                PublicVocabularyWord.word.asc()
            ).offset(offset).limit(page_size).all()
            
            # 格式化返回数据
            items = []
            for word in words_data:
                items.append({
                    "id": word.id,
                    "word": word.word,
                    "language": word.language,
                    "definition": word.definition,
                    "part_of_speech": word.part_of_speech,
                    "example": word.example,
                    "tag": word.tag,
                    "usage_count": word.usage_count,
                    "created_at": word.created_at.isoformat() if word.created_at else None,
                    "updated_at": word.updated_at.isoformat() if word.updated_at else None
                })
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
                "items": items
            }
            
        except Exception as e:
            logger.error(f"获取公共词库失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"获取公共词库失败: {str(e)}")
    
    app.get("/api/public-words", response_model=Dict[str, Any])(get_public_words)
    
    logger.info("语言学习相关API端点注册完成")