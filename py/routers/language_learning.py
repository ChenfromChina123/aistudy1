"""
语言学习模块 - 路由定义
包含所有与语言学习相关的API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

# 导入依赖
try:
    from app import get_db, logger, verify_jwt
except ImportError:
    # 如果无法导入，使用基本配置
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    def get_db():
        raise NotImplementedError("需要配置数据库连接")

# 导入模型和schemas（支持相对导入和绝对导入）
try:
    from models.language_learning import (
        VocabularyList, VocabularyWord, UserWordProgress, PublicVocabularyWord,
        UserLearningRecord, GeneratedArticle, ArticleUsedWord, VocabularyUploadTask
    )
    from schemas.language_learning import (
        VocabularyWordCreate, VocabularyListCreate, ArticleGenerationRequest,
        UserProgressUpdate
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
    from schemas.language_learning import (
        VocabularyWordCreate, VocabularyListCreate, ArticleGenerationRequest,
        UserProgressUpdate
    )

# 创建路由器
router = APIRouter(prefix="/api", tags=["语言学习"])

# 路由定义将在这里添加
# 为了保持向后兼容，路由函数会从原 language_learning.py 导入
# 或者逐步迁移到 services 层

