"""
反馈服务
处理用户反馈相关的业务逻辑
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from models import Feedback
from schemas.feedback import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse,
    FeedbackStatus, FeedbackType, FeedbackSearchParams
)
from services.user_service import user_service


class FeedbackService:
    """反馈服务类"""
    
    def get_feedback_by_id(self, db: Session, feedback_id: int) -> Optional[Feedback]:
        """根据ID获取反馈"""
        return db.query(Feedback).filter(Feedback.id == feedback_id).first()
    
    def create_feedback(
        self, 
        db: Session, 
        feedback_data: FeedbackCreate, 
        user_id: int
    ) -> Feedback:
        """创建新的反馈"""
        # 验证用户是否存在
        user = user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 创建反馈记录
        db_feedback = Feedback(
            user_id=user_id,
            type=feedback_data.type,
            title=feedback_data.title,
            content=feedback_data.content,
            status=FeedbackStatus.PENDING,
            contact_info=feedback_data.contact_info
        )
        
        db.add(db_feedback)
        db.commit()
        db.refresh(db_feedback)
        
        return db_feedback
    
    def update_feedback(
        self, 
        db: Session, 
        feedback_id: int, 
        feedback_update: FeedbackUpdate,
        user_id: int
    ) -> Feedback:
        """更新反馈"""
        # 获取反馈
        db_feedback = self.get_feedback_by_id(db, feedback_id)
        if not db_feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="反馈不存在"
            )
        
        # 检查权限
        is_admin = user_service.is_admin(db, user_id)
        is_owner = db_feedback.user_id == user_id
        
        if not is_admin and not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权更新该反馈"
            )
        
        # 准备更新数据
        update_data = feedback_update.model_dump(exclude_unset=True)
        
        # 非管理员只能更新反馈内容，不能更新状态
        if not is_admin and "status" in update_data:
            del update_data["status"]
        
        # 更新反馈信息
        update_data["updated_at"] = datetime.utcnow()
        for field, value in update_data.items():
            setattr(db_feedback, field, value)
        
        db.commit()
        db.refresh(db_feedback)
        
        return db_feedback
    
    def delete_feedback(
        self, 
        db: Session, 
        feedback_id: int, 
        user_id: int
    ) -> bool:
        """删除反馈"""
        # 获取反馈
        db_feedback = self.get_feedback_by_id(db, feedback_id)
        if not db_feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="反馈不存在"
            )
        
        # 检查权限
        if not user_service.is_admin(db, user_id) and db_feedback.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除该反馈"
            )
        
        # 删除反馈
        db.delete(db_feedback)
        db.commit()
        
        return True
    
    def get_user_feedbacks(
        self, 
        db: Session, 
        user_id: int,
        params: Optional[FeedbackSearchParams] = None,
        skip: int = 0, 
        limit: int = 20
    ) -> List[Feedback]:
        """获取用户的反馈列表"""
        query = db.query(Feedback).filter(Feedback.user_id == user_id)
        
        # 应用搜索参数
        if params:
            if params.type:
                query = query.filter(Feedback.type == params.type)
            
            if params.status:
                query = query.filter(Feedback.status == params.status)
            
            if params.keyword:
                search_pattern = f"%{params.keyword}%"
                query = query.filter(
                    (Feedback.title.ilike(search_pattern)) | 
                    (Feedback.content.ilike(search_pattern))
                )
            
            # 时间范围过滤
            if params.start_date:
                query = query.filter(Feedback.created_at >= params.start_date)
            
            if params.end_date:
                query = query.filter(Feedback.created_at <= params.end_date)
            
            # 排序
            order_field = getattr(Feedback, params.sort_by, Feedback.created_at)
            if params.order == "asc":
                query = query.order_by(order_field.asc())
            else:
                query = query.order_by(order_field.desc())
        else:
            # 默认按创建时间降序排序
            query = query.order_by(Feedback.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def get_all_feedbacks(
        self, 
        db: Session,
        params: Optional[FeedbackSearchParams] = None,
        skip: int = 0, 
        limit: int = 20
    ) -> List[Feedback]:
        """获取所有反馈（管理员）"""
        query = db.query(Feedback)
        
        # 应用搜索参数
        if params:
            if params.user_id:
                query = query.filter(Feedback.user_id == params.user_id)
            
            if params.type:
                query = query.filter(Feedback.type == params.type)
            
            if params.status:
                query = query.filter(Feedback.status == params.status)
            
            if params.keyword:
                search_pattern = f"%{params.keyword}%"
                query = query.filter(
                    (Feedback.title.ilike(search_pattern)) | 
                    (Feedback.content.ilike(search_pattern))
                )
            
            # 时间范围过滤
            if params.start_date:
                query = query.filter(Feedback.created_at >= params.start_date)
            
            if params.end_date:
                query = query.filter(Feedback.created_at <= params.end_date)
            
            # 排序
            order_field = getattr(Feedback, params.sort_by, Feedback.created_at)
            if params.order == "asc":
                query = query.order_by(order_field.asc())
            else:
                query = query.order_by(order_field.desc())
        else:
            # 默认按创建时间降序排序
            query = query.order_by(Feedback.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def respond_to_feedback(
        self, 
        db: Session, 
        feedback_id: int, 
        response_content: str, 
        user_id: int
    ) -> Feedback:
        """管理员回复反馈"""
        # 检查是否是管理员
        if not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以回复反馈"
            )
        
        # 获取反馈
        db_feedback = self.get_feedback_by_id(db, feedback_id)
        if not db_feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="反馈不存在"
            )
        
        # 更新反馈状态和回复内容
        db_feedback.status = FeedbackStatus.COMPLETED
        db_feedback.response = response_content
        db_feedback.updated_at = datetime.utcnow()
        db_feedback.response_by = user_id
        db_feedback.response_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_feedback)
        
        return db_feedback
    
    def get_feedback_statistics(
        self, 
        db: Session, 
        days: Optional[int] = 30
    ) -> Dict[str, Any]:
        """获取反馈统计信息"""
        # 计算起始日期
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 统计各类型的反馈数量
        type_counts = db.query(
            Feedback.type, 
            db.func.count(Feedback.id)
        ).filter(
            Feedback.created_at >= start_date
        ).group_by(Feedback.type).all()
        
        # 统计各状态的反馈数量
        status_counts = db.query(
            Feedback.status, 
            db.func.count(Feedback.id)
        ).filter(
            Feedback.created_at >= start_date
        ).group_by(Feedback.status).all()
        
        # 计算平均处理时间（从创建到完成）
        completed_feedbacks = db.query(Feedback).filter(
            Feedback.status == FeedbackStatus.COMPLETED,
            Feedback.created_at >= start_date,
            Feedback.response_at.isnot(None)
        ).all()
        
        avg_processing_time = 0
        if completed_feedbacks:
            total_time = sum(
                (feedback.response_at - feedback.created_at).total_seconds()
                for feedback in completed_feedbacks
                if feedback.response_at
            )
            avg_processing_time = total_time / len(completed_feedbacks) if completed_feedbacks else 0
        
        # 格式化统计结果
        return {
            "total_feedbacks": db.query(db.func.count(Feedback.id)).filter(
                Feedback.created_at >= start_date
            ).scalar(),
            "type_distribution": {item[0].value: item[1] for item in type_counts},
            "status_distribution": {item[0].value: item[1] for item in status_counts},
            "avg_processing_time_seconds": avg_processing_time,
            "avg_processing_time_hours": avg_processing_time / 3600,
            "time_period": f"过去{days}天"
        }
    
    def mark_feedback_as_read(
        self, 
        db: Session, 
        feedback_id: int, 
        user_id: int
    ) -> Feedback:
        """标记反馈为已读"""
        # 获取反馈
        db_feedback = self.get_feedback_by_id(db, feedback_id)
        if not db_feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="反馈不存在"
            )
        
        # 检查权限（只有管理员可以标记所有反馈为已读，用户只能标记自己的）
        is_admin = user_service.is_admin(db, user_id)
        if not is_admin and db_feedback.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权标记该反馈"
            )
        
        # 如果是管理员，标记为已处理
        if is_admin:
            db_feedback.is_read_by_admin = True
            # 可以选择同时更新状态
            if db_feedback.status == FeedbackStatus.PENDING:
                db_feedback.status = FeedbackStatus.IN_PROGRESS
        else:
            # 如果是用户，标记为已读
            db_feedback.is_read_by_user = True
        
        db_feedback.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_feedback)
        
        return db_feedback


# 创建全局的反馈服务实例
feedback_service = FeedbackService()