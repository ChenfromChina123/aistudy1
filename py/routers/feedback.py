"""
反馈路由
处理用户反馈相关的API接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from schemas.feedback import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse,
    FeedbackType, FeedbackStatus, FeedbackSearchParams
)
from schemas.common import ResponseModel, PaginatedResponse
from services.feedback_service import feedback_service
# from services.auth_service import get_current_user  # 暂时注释，稍后实现
from services.user_service import user_service
from models import User

# 创建路由实例
router = APIRouter()


@router.post("")
async def create_feedback(
    feedback_data: FeedbackCreate,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    提交反馈
    - **type**: 反馈类型 (bug/suggestion/question/other)
    - **title**: 反馈标题
    - **content**: 反馈内容
    - **contact_info**: 联系方式（可选）
    """
    # 创建反馈
    feedback = feedback_service.create_feedback(db, feedback_data, None)  # 暂时使用None代替用户ID
    
    return {
        "status": "success",
        "message": "反馈提交成功",
        "data": feedback.to_dict()
    }


@router.get("")
async def get_my_feedbacks(
    type: Optional[FeedbackType] = Query(None, description="反馈类型"),
    status: Optional[FeedbackStatus] = Query(None, description="反馈状态"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取我的反馈列表
    """
    # 构建搜索参数
    search_params = FeedbackSearchParams(
        type=type,
        status=status,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order
    )
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取反馈列表
    feedbacks = feedback_service.get_user_feedbacks(
        db, None, search_params, skip, page_size  # 暂时使用None代替用户ID
    )
    
    # 获取总数（这里简化处理，实际应该单独查询总数）
    total_feedbacks = len(feedback_service.get_user_feedbacks(db, None, search_params))  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="获取反馈列表成功",
        data={
            "items": [feedback.to_dict() for feedback in feedbacks],
            "total": total_feedbacks,
            "page": page,
            "page_size": page_size,
            "pages": (total_feedbacks + page_size - 1) // page_size
        }
    )


@router.get("/{feedback_id}")
async def get_feedback(
    feedback_id: int,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取反馈详情
    """
    # 获取反馈
    feedback = feedback_service.get_feedback_by_id(db, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="反馈不存在"
        )
    
    # 检查权限（只有管理员或用户本人可以访问）
    # is_admin = user_service.is_admin(db, current_user.id)  # 暂时注释管理员检查，稍后实现
    # if not is_admin and feedback.user_id != current_user.id:  # 暂时注释权限检查，稍后实现
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该反馈"
        )
    
    # 如果是用户访问自己的反馈且有回复，标记为已读
    # if feedback.user_id == current_user.id and feedback.response and not feedback.is_read_by_user:  # 暂时注释已读标记，稍后实现
        feedback.is_read_by_user = True
        feedback.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(feedback)
    
    return ResponseModel(
        code=200,
        message="获取反馈详情成功",
        data=feedback.to_dict()
    )


@router.put("/{feedback_id}")
async def update_feedback(
    feedback_id: int,
    feedback_update: FeedbackUpdate,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    更新反馈
    普通用户只能更新未回复的反馈内容
    - **content**: 反馈内容（可选）
    """
    # 更新反馈
    updated_feedback = feedback_service.update_feedback(
        db, feedback_id, feedback_update, None  # 暂时使用None代替用户ID
    )
    
    return ResponseModel(
        code=200,
        message="反馈更新成功",
        data=updated_feedback.to_dict()
    )


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    删除反馈
    """
    # 删除反馈
    feedback_service.delete_feedback(db, feedback_id, None)  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="反馈删除成功"
    )


@router.post("/{feedback_id}/read")
async def mark_feedback_as_read(
    feedback_id: int,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    标记反馈为已读
    """
    # 标记为已读
    updated_feedback = feedback_service.mark_feedback_as_read(db, feedback_id, None)  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="标记已读成功",
        data=updated_feedback.to_dict()
    )


# 管理员接口
@router.get("/admin/all")
async def get_all_feedbacks(
    user_id: Optional[int] = Query(None, description="用户ID"),
    type: Optional[FeedbackType] = Query(None, description="反馈类型"),
    status: Optional[FeedbackStatus] = Query(None, description="反馈状态"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    is_read_by_admin: Optional[bool] = Query(None, description="是否已被管理员阅读"),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取所有反馈（管理员）
    需要管理员权限
    """
    # # 检查管理员权限（暂时注释，稍后实现）
    # if not user_service.is_admin(db, current_user.id):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="需要管理员权限"
    #     )
    
    # 构建搜索参数
    search_params = FeedbackSearchParams(
        user_id=user_id,
        type=type,
        status=status,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order
    )
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取反馈列表
    feedbacks = feedback_service.get_all_feedbacks(db, search_params, skip, page_size)
    
    # 如果需要筛选已读/未读
    if is_read_by_admin is not None:
        feedbacks = [f for f in feedbacks if f.is_read_by_admin == is_read_by_admin]
    
    # 获取总数（这里简化处理，实际应该单独查询总数）
    total_feedbacks = len(feedback_service.get_all_feedbacks(db, search_params))
    if is_read_by_admin is not None:
        total_feedbacks = sum(1 for f in feedback_service.get_all_feedbacks(db, search_params) 
                             if f.is_read_by_admin == is_read_by_admin)
    
    return ResponseModel(
        code=200,
        message="获取反馈列表成功",
        data={
            "items": [feedback.to_dict() for feedback in feedbacks],
            "total": total_feedbacks,
            "page": page,
            "page_size": page_size,
            "pages": (total_feedbacks + page_size - 1) // page_size
        }
    )


@router.post("/{feedback_id}/respond")
async def respond_to_feedback(
    feedback_id: int,
    response_content: str,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    回复反馈（管理员）
    需要管理员权限
    - **response_content**: 回复内容
    """
    # # 检查管理员权限（暂时注释，稍后实现）
    # if not user_service.is_admin(db, current_user.id):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="需要管理员权限"
    #     )
    
    # 回复反馈
    updated_feedback = feedback_service.respond_to_feedback(
        db, feedback_id, response_content, None  # 暂时使用None代替用户ID
    )
    
    return ResponseModel(
        code=200,
        message="回复反馈成功",
        data=updated_feedback.to_dict()
    )


@router.get("/admin/stats")
async def get_feedback_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取反馈统计信息（管理员）
    需要管理员权限
    """
    # # 检查管理员权限（暂时注释，稍后实现）
    # if not user_service.is_admin(db, current_user.id):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="需要管理员权限"
    #     )
    
    # 获取统计信息
    stats = feedback_service.get_feedback_statistics(db, days)
    
    return ResponseModel(
        code=200,
        message="获取统计信息成功",
        data=stats
    )


@router.get("/admin/unread-count")
async def get_unread_feedback_count(
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取未读反馈数量（管理员）
    需要管理员权限
    """
    # # 检查管理员权限（暂时注释，稍后实现）
    # if not user_service.is_admin(db, current_user.id):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="需要管理员权限"
    #     )
    
    # 计算未读反馈数量
    from sqlalchemy import func
    unread_count = db.query(func.count(Feedback.id)).filter(
        Feedback.is_read_by_admin == False,
        Feedback.status == FeedbackStatus.PENDING
    ).scalar()
    
    return ResponseModel(
        code=200,
        message="获取未读数量成功",
        data={
            "unread_count": unread_count
        }
    )