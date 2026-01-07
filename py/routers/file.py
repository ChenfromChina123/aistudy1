"""
文件路由
处理文件上传、下载和分享相关的API接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import json

from database import get_db
from schemas.file import (
    UserFileUpload, UserFileUpdate, UserFileResponse,
    FileShareCreate, FileShareResponse, FileSearchParams
)
from schemas.common import ResponseModel, PaginatedResponse
from services.file_service import file_service
# from services.auth_service import get_current_user  # 暂时注释，稍后实现
from models import User
from config import settings

# 创建路由实例
router = APIRouter()


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    is_private: bool = Form(True),
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    上传文件
    - **file**: 要上传的文件
    - **description**: 文件描述（可选）
    - **is_private**: 是否私有文件（默认：是）
    """
    # 构建文件上传数据
    file_data = UserFileUpload(
        description=description,
        is_private=is_private
    )
    
    # 上传文件
    uploaded_file = file_service.upload_file(db, file, file_data, None)  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="文件上传成功",
        data=uploaded_file.to_dict()
    )


@router.get("")
async def get_my_files(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    content_type: Optional[str] = Query(None, description="文件类型"),
    min_size: Optional[int] = Query(None, ge=0, description="最小文件大小（字节）"),
    max_size: Optional[int] = Query(None, ge=0, description="最大文件大小（字节）"),
    is_private: Optional[bool] = Query(None, description="是否私有文件"),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取我的文件列表
    """
    # 构建搜索参数
    search_params = FileSearchParams(
        keyword=keyword,
        content_type=content_type,
        min_size=min_size,
        max_size=max_size,
        is_private=is_private,
        sort_by=sort_by,
        order=order
    )
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取文件列表
    files = file_service.get_user_files(db, None, search_params, skip, page_size)  # 暂时使用None代替用户ID
    
    # 获取总数（这里简化处理，实际应该单独查询总数）
    total_files = len(file_service.get_user_files(db, None, search_params))  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="获取文件列表成功",
        data={
            "items": [file.to_dict() for file in files],
            "total": total_files,
            "page": page,
            "page_size": page_size,
            "pages": (total_files + page_size - 1) // page_size
        }
    )


@router.get("/{file_id}")
async def get_file_info(
    file_id: int,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取文件信息
    """
    # 获取文件
    file = file_service.get_file_by_id(db, file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 检查权限
    # if file.user_id != current_user.id:  # 暂时注释权限检查，稍后实现
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该文件"
        )
    
    return ResponseModel(
        code=200,
        message="获取文件信息成功",
        data=file.to_dict()
    )


@router.put("/{file_id}")
async def update_file_info(
    file_id: int,
    file_update: UserFileUpdate,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    更新文件信息
    - **description**: 文件描述（可选）
    - **is_private**: 是否私有文件（可选）
    """
    # 更新文件信息
    updated_file = file_service.update_file(db, file_id, file_update, None)  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="文件信息更新成功",
        data=updated_file.to_dict()
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    删除文件
    """
    # 删除文件
    file_service.delete_file(db, file_id, None)  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="文件删除成功"
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    下载文件
    """
    # 获取文件
    file = file_service.get_file_by_id(db, file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 检查权限
    # if file.user_id != current_user.id:  # 暂时注释权限检查，稍后实现
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权下载该文件"
        )
    
    # 构建文件的绝对路径
    file_path = os.path.join(settings.UPLOAD_DIR, file.file_path)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 返回文件响应
    return FileResponse(
        path=file_path,
        filename=file.filename,
        media_type=file.content_type or "application/octet-stream"
    )


@router.post("/{file_id}/share")
async def share_file(
    file_id: int,
    share_data: FileShareCreate,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    分享文件
    - **share_type**: 分享类型 (public/password)
    - **password**: 分享密码（当share_type为password时必需）
    - **expires_at**: 过期时间（可选）
    - **max_downloads**: 最大下载次数（可选）
    """
    # 创建分享
    share = file_service.share_file(db, share_data, None)  # 暂时使用None代替用户ID
    
    # 生成完整的分享链接
    full_share_link = f"{settings.BASE_URL}{share.share_link}"
    
    # 更新返回数据
    share_dict = share.to_dict()
    share_dict["share_link"] = full_share_link
    
    return ResponseModel(
        code=200,
        message="文件分享成功",
        data=share_dict
    )


@router.get("/share/list")
async def get_my_shares(
    file_id: Optional[int] = Query(None, description="文件ID"),
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取我的分享列表
    """
    from sqlalchemy import and_
    
    # 查询分享记录
    query = db.query(FileShare).filter(
        # FileShare.user_id == current_user.id,  # 暂时注释用户过滤，稍后实现
        FileShare.is_active == True
    )
    
    if file_id:
        query = query.filter(FileShare.file_id == file_id)
    
    shares = query.order_by(FileShare.created_at.desc()).all()
    
    # 生成完整的分享链接
    shares_data = []
    for share in shares:
        share_dict = share.to_dict()
        share_dict["share_link"] = f"{settings.BASE_URL}{share.share_link}"
        shares_data.append(share_dict)
    
    return ResponseModel(
        code=200,
        message="获取分享列表成功",
        data=shares_data
    )


@router.delete("/share/{share_id}")
async def revoke_share(
    share_id: int,
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    撤销文件分享
    """
    # 撤销分享
    file_service.revoke_share(db, share_id, None)  # 暂时使用None代替用户ID
    
    return ResponseModel(
        code=200,
        message="分享撤销成功"
    )


# 公开的文件分享接口
@router.post("/share/{access_code}/verify")
async def verify_file_share(
    access_code: str,
    password: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    验证文件分享访问权限
    用于预览文件信息或检查密码是否正确
    """
    # 验证分享访问权限
    file = file_service.verify_share_access(db, access_code, password)
    
    return ResponseModel(
        code=200,
        message="验证成功",
        data=file.to_dict()
    )


@router.get("/share/{access_code}/download")
async def download_shared_file(
    access_code: str,
    password: Optional[str] = Query(None, description="分享密码"),
    db: Session = Depends(get_db)
):
    """
    下载分享的文件
    公开接口，不需要登录，但需要有效的分享码和密码（如果设置了的话）
    """
    # 验证分享访问权限
    file = file_service.verify_share_access(db, access_code, password)
    
    # 构建文件的绝对路径
    file_path = os.path.join(settings.UPLOAD_DIR, file.file_path)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在"
        )
    
    # 返回文件响应
    return FileResponse(
        path=file_path,
        filename=file.filename,
        media_type=file.content_type or "application/octet-stream"
    )


@router.get("/stats/summary")
async def get_file_stats(
    # current_user: User = Depends(get_current_user),  # 暂时注释，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取文件统计信息
    - 总文件数
    - 已用存储空间
    - 各类型文件数量
    """
    from sqlalchemy import func
    
    # 获取总文件数
    total_files = db.query(func.count(UserFile.id)).filter(
        # UserFile.user_id == current_user.id  # 暂时注释用户过滤，稍后实现
        True
    ).scalar()
    
    # 获取已用存储空间
    used_space = db.query(func.sum(UserFile.file_size)).filter(
        # UserFile.user_id == current_user.id  # 暂时注释用户过滤，稍后实现
        True
    ).scalar() or 0
    
    # 获取各类型文件数量
    type_counts = db.query(
        UserFile.content_type,
        func.count(UserFile.id)
    ).filter(
        # UserFile.user_id == current_user.id  # 暂时注释用户过滤，稍后实现
        True
    ).group_by(UserFile.content_type).all()
    
    type_distribution = {}
    for content_type, count in type_counts:
        type_distribution[content_type or "unknown"] = count
    
    return ResponseModel(
        code=200,
        message="获取文件统计信息成功",
        data={
            "total_files": total_files,
            "used_space_bytes": used_space,
            "used_space_mb": round(used_space / (1024 * 1024), 2),
            "type_distribution": type_distribution
        }
    )