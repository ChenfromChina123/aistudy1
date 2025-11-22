"""
语言学习模块 - 业务逻辑服务层
包含所有与语言学习相关的业务逻辑函数
"""
import os
import re
import json
import uuid
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

# 导入模型（支持相对导入和绝对导入）
try:
    from models.language_learning import (
        VocabularyList, VocabularyWord, UserWordProgress, PublicVocabularyWord,
        UserLearningRecord, GeneratedArticle, ArticleUsedWord, VocabularyUploadTask
    )
except ImportError:
    # 如果相对导入失败，尝试从上级目录导入
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.language_learning import (
        VocabularyList, VocabularyWord, UserWordProgress, PublicVocabularyWord,
        UserLearningRecord, GeneratedArticle, ArticleUsedWord, VocabularyUploadTask
    )

# 导入schemas
try:
    from schemas.language_learning import (
        VocabularyWordCreate, VocabularyListCreate, ArticleGenerationRequest,
        UserProgressUpdate
    )
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from schemas.language_learning import (
        VocabularyWordCreate, VocabularyListCreate, ArticleGenerationRequest,
        UserProgressUpdate
    )

# 导入配置和工具
try:
    from config import settings as app_settings
except ImportError:
    app_settings = None

try:
    from app import logger, verify_jwt
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# 获取DeepSeek API密钥
def get_deepseek_client():
    """获取DeepSeek API客户端"""
    deepseek_api_key = (
        app_settings.DEEPSEEK_API_KEY if app_settings and app_settings.DEEPSEEK_API_KEY 
        else os.getenv("DEEPSEEK_API_KEY", "")
    ).strip()
    
    if not deepseek_api_key or not OpenAI:
        return None
    
    return OpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com/v1"
    )

# 语言名称映射
def get_language_name(language_code: str) -> str:
    """获取语言名称"""
    language_names = {
        'en': '英语',
        'zh': '中文',
        'ja': '日语',
        'ko': '韩语',
        'fr': '法语',
        'de': '德语',
        'es': '西班牙语'
    }
    return language_names.get(language_code, language_code)

# 语言检测
def detect_language_from_text(text: str) -> str:
    """从文本检测语言"""
    # 检测中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return 'zh'
    
    # 检测日文字符
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return 'ja'
    
    # 检测韩文字符
    if re.search(r'[\uac00-\ud7a3]', text):
        return 'ko'
    
    # 默认英语
    return 'en'

# 验证单词有效性
def is_valid_word(word_text: str) -> bool:
    """检查单词是否有效（不是注释、句子或中文）"""
    if not word_text or len(word_text.strip()) == 0:
        return False
    
    word = word_text.strip()
    
    # 检查是否包含中文括号（注释标记）
    if '【' in word or '】' in word:
        return False
    
    # 检查是否包含中文字符
    if re.search(r'[\u4e00-\u9fff]', word):
        return False
    
    # 检查是否有过多空格（可能是句子）
    if word.count(' ') > 2:
        return False
    
    # 检查是否以句号、问号、感叹号结尾（可能是句子，除非是很短的缩写）
    if len(word) > 3 and word[-1] in ['.', '?', '!']:
        return False
    
    # 检查长度是否合理（单词通常不超过50个字符）
    if len(word) > 50:
        return False
    
    # 检查是否包含常见的中文标点
    chinese_punctuation = ['，', '。', '？', '！', '；', '：', '、']
    if any(p in word for p in chinese_punctuation):
        return False
    
    return True

# 其他业务逻辑函数将逐步迁移到这里
# 由于代码量很大，我会分步骤进行迁移

