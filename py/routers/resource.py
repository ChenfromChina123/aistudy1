"""
资源路由
处理学习资源相关的API接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
import json

from database import get_db
from schemas.resource import (
    ResourceCreate, ResourceUpdate, ResourceResponse,
    ResourceSearchParams, CollectionCreate,
    CollectionResponse, PublicResourceResponse
)
from schemas.common import ResponseModel, PaginatedResponse
from services.resource_service import resource_service
# 暂时注释get_current_user导入，稍后实现
from models import User

# 创建路由实例
router = APIRouter()


@router.post("")
async def create_resource(
    title: str = Form(...),
    type: str = Form(...),
    content: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    创建学习资源
    - **title**: 资源标题
    - **type**: 资源类型
    - **content**: 资源内容
    - **description**: 资源描述（可选）
    - **tags**: 标签（可选，JSON格式字符串）
    - **file**: 附件文件（可选）
    """
    # 解析标签
    tags_list = []
    if tags:
        try:
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="标签格式错误"
            )
    
    # 构建资源数据
    resource_data = ResourceCreate(
        title=title,
        type=type,
        content=content,
        description=description,
        tags=tags_list
    )
    
    # 创建资源
    resource = resource_service.create_resource(db, resource_data, current_user.id, file)
    
    return ResponseModel(
        code=200,
        message="资源创建成功",
        data=resource.to_dict()
    )


@router.get("")
async def get_resources(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    type: Optional[str] = Query(None, description="资源类型"),
    tags: Optional[str] = Query(None, description="标签（多个标签用逗号分隔）"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="最低评分"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取资源列表
    支持关键词搜索、类型筛选、标签筛选等
    """
    # 解析标签
    tags_list = []
    if tags:
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    # 构建搜索参数
    search_params = ResourceSearchParams(
        keyword=keyword,
        type=type,
        tags=tags_list,
        min_rating=min_rating,
        is_public=is_public,
        sort_by=sort_by,
        order=order
    )
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取用户ID（如果已登录）
    user_id = None  # 暂时设置为None，稍后实现用户认证
    
    # 获取资源列表
    resources = resource_service.get_resources(db, search_params, skip, page_size, user_id)
    
    # 获取总数
    total = resource_service.get_resources_count(db, search_params, user_id)
    
    return ResponseModel(
        code=200,
        message="获取资源列表成功",
        data={
            "items": [resource.to_dict() for resource in resources],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    )


@router.get("/my")
async def get_my_resources(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    type: Optional[str] = Query(None, description="资源类型"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取当前用户的资源列表
    """
    # 构建搜索参数
    search_params = ResourceSearchParams(
        keyword=keyword,
        type=type,
        is_public=is_public,
        sort_by=sort_by,
        order=order,
        # user_id=current_user.id  # 暂时注释，稍后实现
    )
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取资源列表
    resources = resource_service.get_resources(db, search_params, skip, page_size, None)
    
    # 获取总数
    total = resource_service.get_resources_count(db, search_params, None)
    
    return ResponseModel(
        code=200,
        message="获取我的资源列表成功",
        data={
            "items": [resource.to_dict() for resource in resources],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    )


@router.get("/{resource_id}")
async def get_resource(
    resource_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    根据ID获取资源详情
    """
    # 获取用户ID（如果已登录）
    user_id = current_user.id if current_user else None
    
    # 获取资源
    resource = resource_service.get_resource_by_id(db, resource_id, user_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="资源不存在"
        )
    
    # 检查访问权限
    if resource.is_private and resource.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该私有资源"
        )
    
    return ResponseModel(
        code=200,
        message="获取资源成功",
        data=resource.to_dict()
    )


@router.put("/{resource_id}")
async def update_resource(
    resource_id: int,
    resource_update: ResourceUpdate,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    更新资源
    - **title**: 资源标题（可选）
    - **type**: 资源类型（可选）
    - **content**: 资源内容（可选）
    - **description**: 资源描述（可选）
    - **tags**: 标签（可选）
    - **is_public**: 是否公开（可选）
    """
    # 更新资源
    updated_resource = resource_service.update_resource(db, resource_id, resource_update, None)
    
    return ResponseModel(
        code=200,
        message="资源更新成功",
        data=updated_resource.to_dict()
    )


@router.delete("/{resource_id}")
async def delete_resource(
    resource_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    删除资源
    """
    # 删除资源
    resource_service.delete_resource(db, resource_id, None)
    
    return ResponseModel(
        code=200,
        message="资源删除成功"
    )


@router.post("/{resource_id}/collect")
async def collect_resource(
    resource_id: int,
    collection_data: Optional[CollectionCreate] = None,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    收藏资源
    - **note**: 收藏备注（可选）
    """
    # 如果没有提供收藏数据，创建默认数据
    if not collection_data:
        collection_data = CollectionCreate()
    
    # 收藏资源
    collection = resource_service.collect_resource(db, resource_id, collection_data, None)
    
    return ResponseModel(
        code=200,
        message="收藏成功",
        data=collection.to_dict()
    )


@router.delete("/{resource_id}/collect")
async def uncollect_resource(
    resource_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    取消收藏
    """
    # 取消收藏
    resource_service.uncollect_resource(db, resource_id, None)
    
    return ResponseModel(
        code=200,
        message="取消收藏成功"
    )


@router.get("/my/collections")
async def get_my_collections(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    type: Optional[str] = Query(None, description="资源类型"),
    sort_by: str = Query("collected_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取我的收藏列表
    """
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取收藏列表
    collections = resource_service.get_user_collections(
        db, None, keyword, type, sort_by, order, skip, page_size
    )
    
    # 获取总数
    total = resource_service.get_user_collections_count(
        db, None, keyword, type
    )
    
    return ResponseModel(
        code=200,
        message="获取收藏列表成功",
        data={
            "items": [collection.to_dict() for collection in collections],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    )


@router.post("/{resource_id}/like")
async def like_resource(
    resource_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    点赞资源
    """
    # 点赞资源
    liked = resource_service.like_resource(db, resource_id, None)
    
    if liked:
        return ResponseModel(
            code=200,
            message="点赞成功"
        )
    else:
        return ResponseModel(
            code=200,
            message="已取消点赞"
        )


@router.post("/{resource_id}/rate")
async def rate_resource(
    resource_id: int,
    rating: float = Query(..., ge=1, le=5, description="评分：1-5星"),
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    评分资源
    - **rating**: 评分（1-5星）
    """
    # 评分资源
    resource_service.rate_resource(db, resource_id, None, rating)
    
    return ResponseModel(
        code=200,
        message="评分成功"
    )


@router.post("/{resource_id}/publish")
async def publish_resource(
    resource_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    发布资源到公共库
    """
    # 发布资源
    public_resource = resource_service.publish_resource(db, resource_id, None)
    
    return ResponseModel(
        code=200,
        message="资源发布成功",
        data=public_resource.to_dict()
    )


@router.get("/public/hot")
async def get_hot_resources(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    获取热门资源
    根据浏览量、点赞数等综合排序
    """
    resources = resource_service.get_hot_resources(db, limit)
    
    return ResponseModel(
        code=200,
        message="获取热门资源成功",
        data=[resource.to_dict() for resource in resources]
    )


@router.get("/public/latest")
async def get_latest_resources(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    获取最新发布的资源
    """
    resources = resource_service.get_latest_resources(db, limit)
    
    return ResponseModel(
        code=200,
        message="获取最新资源成功",
        data=[resource.to_dict() for resource in resources]
    )


@router.get("/tags/popular")
async def get_popular_tags(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_db)
):
    """
    获取热门标签
    """
    tags = resource_service.get_popular_tags(db, limit)
    
    return ResponseModel(
        code=200,
        message="获取热门标签成功",
        data=tags
    )