"""
语言学习模块 - Pydantic Schemas
包含所有与语言学习相关的数据验证模型
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


# 单词创建模型
class VocabularyWordCreate(BaseModel):
    word: str
    definition: Optional[str] = None
    part_of_speech: Optional[str] = None
    example: Optional[str] = None
    language: Optional[str] = 'en'  # 语言代码，默认英语


# 单词表创建模型
class VocabularyListCreate(BaseModel):
    name: str
    description: Optional[str] = None
    language: Optional[str] = 'en'  # 语言代码，默认英语
    words: List[VocabularyWordCreate]


# 单词表响应模型
class VocabularyListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    language: Optional[str] = 'en'  # 语言代码
    is_preset: bool
    word_count: int
    created_at: datetime


# 文章生成请求模型
class ArticleGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")  # 忽略额外字段，避免422错误
    
    vocabulary_list_id: Optional[int] = None
    selected_word_ids: Optional[List[int]] = None
    public_word_ids: Optional[List[int]] = None
    topic: Optional[str] = None
    difficulty_level: str = "intermediate"
    article_length: str = "medium"
    language: Optional[str] = 'en'  # 文章语言，默认英语
    custom_words: Optional[List[str]] = None  # 自定义单词列表（前端可能发送）
    manual_words: Optional[List[Dict[str, Any]]] = None  # 每个单词包含详细信息（word/definition/part_of_speech等）


# 用户进度更新模型
class UserProgressUpdate(BaseModel):
    word_id: int
    mastery_level: int
    is_difficult: bool = False


# 重组单词表请求模型
class ReorganizeVocabularyRequest(BaseModel):
    pass  # 可以添加特定字段如果需要

