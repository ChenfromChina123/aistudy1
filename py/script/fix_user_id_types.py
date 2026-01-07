#!/usr/bin/env python3
"""
修复数据库中的user_id类型不一致问题
检查并修复UserWordProgress和UserLearningRecord表中的user_id字段
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from py.app import SessionLocal, engine
from sqlalchemy import text
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_user_id_types():
    """修复user_id类型不一致问题"""
    db = SessionLocal()
    try:
        logger.info("开始检查数据库中的user_id类型...")
        
        # 检查UserWordProgress表
        # 注意：在SQLite中，如果字段是INTEGER类型，存储的应该是整数
        # 但如果有字符串类型的值，我们需要检查并修复
        
        # 获取所有user_id值并检查类型
        result = db.execute(text("""
            SELECT DISTINCT user_id, typeof(user_id) as type_name
            FROM user_word_progress
            LIMIT 100
        """))
        
        user_ids = result.fetchall()
        logger.info(f"找到 {len(user_ids)} 个不同的user_id值")
        
        # 检查是否有字符串类型的user_id
        string_user_ids = []
        for row in user_ids:
            user_id = row[0]
            type_name = row[1] if len(row) > 1 else None
            # 尝试转换为整数，如果失败说明是字符串
            try:
                int(user_id)
            except (ValueError, TypeError):
                string_user_ids.append(user_id)
                logger.warning(f"发现字符串类型的user_id: {user_id} (类型: {type_name})")
        
        if string_user_ids:
            logger.info(f"发现 {len(string_user_ids)} 个字符串类型的user_id，开始修复...")
            for user_id_str in string_user_ids:
                try:
                    user_id_int = int(user_id_str)
                    # 更新为整数类型
                    db.execute(text("""
                        UPDATE user_word_progress
                        SET user_id = :user_id_int
                        WHERE user_id = :user_id_str
                    """), {"user_id_int": user_id_int, "user_id_str": user_id_str})
                    logger.info(f"已修复 user_id: {user_id_str} -> {user_id_int}")
                except (ValueError, TypeError) as e:
                    logger.error(f"无法转换 user_id {user_id_str}: {str(e)}")
            
            db.commit()
            logger.info("UserWordProgress表修复完成")
        else:
            logger.info("UserWordProgress表中的user_id类型正常，无需修复")
        
        # 检查UserLearningRecord表
        result = db.execute(text("""
            SELECT DISTINCT user_id, typeof(user_id) as type_name
            FROM user_learning_records
            LIMIT 100
        """))
        
        user_ids = result.fetchall()
        logger.info(f"UserLearningRecord表找到 {len(user_ids)} 个不同的user_id值")
        
        string_user_ids = []
        for row in user_ids:
            user_id = row[0]
            try:
                int(user_id)
            except (ValueError, TypeError):
                string_user_ids.append(user_id)
                logger.warning(f"发现字符串类型的user_id: {user_id}")
        
        if string_user_ids:
            logger.info(f"发现 {len(string_user_ids)} 个字符串类型的user_id，开始修复...")
            for user_id_str in string_user_ids:
                try:
                    user_id_int = int(user_id_str)
                    db.execute(text("""
                        UPDATE user_learning_records
                        SET user_id = :user_id_int
                        WHERE user_id = :user_id_str
                    """), {"user_id_int": user_id_int, "user_id_str": user_id_str})
                    logger.info(f"已修复 user_id: {user_id_str} -> {user_id_int}")
                except (ValueError, TypeError) as e:
                    logger.error(f"无法转换 user_id {user_id_str}: {str(e)}")
            
            db.commit()
            logger.info("UserLearningRecord表修复完成")
        else:
            logger.info("UserLearningRecord表中的user_id类型正常，无需修复")
        
        logger.info("数据修复完成！")
        
    except Exception as e:
        logger.error(f"数据修复失败: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("修复数据库中的user_id类型不一致问题")
    print("=" * 60)
    print()
    
    fix_user_id_types()
    
    print("\n修复完成！请重启服务器并刷新浏览器页面。")

