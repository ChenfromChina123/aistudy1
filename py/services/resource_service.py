"""
资源服务
处理学习资源相关的业务逻辑
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime
import json

from models import Resource, Collection, PublicResource
from schemas.resource import (
    ResourceCreate, ResourceUpdate, ResourceResponse,
    CollectionCreate, CollectionResponse,
    PublicResourceCreate, PublicResourceUpdate, ResourceSearchParams
)
from services.user_service import user_service


class ResourceService:
    """资源服务类"""
    
    def get_resource_by_id(self, db: Session, resource_id: int) -> Optional[Resource]:
        """根据ID获取资源"""
        return db.query(Resource).filter(Resource.id == resource_id).first()
    
    def create_resource(self, db: Session, resource_data: ResourceCreate, user_id: int) -> Resource:
        """创建资源"""
        # 创建资源对象
        db_resource = Resource(
            **resource_data.model_dump(),
            user_id=user_id,
            # 将标签列表转换为JSON字符串存储
            tags=json.dumps(resource_data.tags) if resource_data.tags else "[]"
        )
        
        db.add(db_resource)
        db.commit()
        db.refresh(db_resource)
        
        return db_resource
    
    def update_resource(
        self, 
        db: Session, 
        resource_id: int, 
        resource_update: ResourceUpdate, 
        user_id: int
    ) -> Resource:
        """更新资源"""
        # 获取资源
        resource = self.get_resource_by_id(db, resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="资源不存在"
            )
        
        # 检查权限
        if resource.user_id != user_id and not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改该资源"
            )
        
        # 准备更新数据
        update_data = resource_update.model_dump(exclude_unset=True)
        
        # 处理标签
        if "tags" in update_data:
            update_data["tags"] = json.dumps(update_data["tags"])
        
        # 更新资源信息
        update_data["updated_at"] = datetime.utcnow()
        for field, value in update_data.items():
            setattr(resource, field, value)
        
        db.commit()
        db.refresh(resource)
        
        return resource
    
    def delete_resource(self, db: Session, resource_id: int, user_id: int) -> bool:
        """删除资源"""
        # 获取资源
        resource = self.get_resource_by_id(db, resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="资源不存在"
            )
        
        # 检查权限
        if resource.user_id != user_id and not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除该资源"
            )
        
        # 删除相关的收藏记录
        db.query(Collection).filter(Collection.resource_id == resource_id).delete()
        
        # 删除相关的公共资源记录
        db.query(PublicResource).filter(PublicResource.resource_id == resource_id).delete()
        
        # 删除资源
        db.delete(resource)
        db.commit()
        
        return True
    
    def get_resources(
        self, 
        db: Session, 
        params: ResourceSearchParams,
        skip: int = 0, 
        limit: int = 20,
        user_id: Optional[int] = None
    ) -> List[Resource]:
        """搜索资源"""
        query = db.query(Resource)
        
        # 搜索关键词
        if params.keyword:
            search_pattern = f"%{params.keyword}%"
            query = query.filter(
                (Resource.title.ilike(search_pattern)) | 
                (Resource.description.ilike(search_pattern)) |
                (Resource.content.ilike(search_pattern))
            )
        
        # 资源类型过滤
        if params.type:
            query = query.filter(Resource.type == params.type)
        
        # 用户ID过滤
        if params.user_id:
            query = query.filter(Resource.user_id == params.user_id)
        
        # 公开/私有过滤
        if params.is_public is not None:
            if params.is_public:
                query = query.filter(Resource.is_private == False)
            else:
                query = query.filter(Resource.is_private == True)
        
        # 标签过滤（可选，这里简化处理）
        if params.tags:
            # 实际应用中可能需要更复杂的JSON查询
            pass
        
        # 排序
        order_field = getattr(Resource, params.sort_by, Resource.created_at)
        if params.order == "asc":
            query = query.order_by(order_field.asc())
        else:
            query = query.order_by(order_field.desc())
        
        # 分页
        return query.offset(skip).limit(limit).all()
    
    def get_user_resources(
        self, 
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Resource]:
        """获取用户的资源"""
        return db.query(Resource).filter(
            Resource.user_id == user_id
        ).order_by(Resource.created_at.desc()).offset(skip).limit(limit).all()
    
    def increment_view_count(self, db: Session, resource_id: int) -> None:
        """增加资源查看次数"""
        resource = self.get_resource_by_id(db, resource_id)
        if resource:
            resource.views += 1
            db.commit()
    
    def toggle_like(self, db: Session, resource_id: int, user_id: int) -> Dict[str, Any]:
        """点赞/取消点赞资源"""
        from models import Like
        
        # 检查资源是否存在
        resource = self.get_resource_by_id(db, resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="资源不存在"
            )
        
        # 检查是否已点赞
        existing_like = db.query(Like).filter(
            Like.resource_id == resource_id,
            Like.user_id == user_id
        ).first()
        
        if existing_like:
            # 取消点赞
            db.delete(existing_like)
            resource.likes = max(0, resource.likes - 1)
            is_liked = False
        else:
            # 添加点赞
            new_like = Like(resource_id=resource_id, user_id=user_id)
            db.add(new_like)
            resource.likes += 1
            is_liked = True
        
        db.commit()
        
        return {
            "is_liked": is_liked,
            "total_likes": resource.likes
        }
    
    def create_collection(
        self, 
        db: Session, 
        collection_data: CollectionCreate, 
        user_id: int
    ) -> Collection:
        """收藏资源"""
        # 检查资源是否存在
        resource = self.get_resource_by_id(db, collection_data.resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="资源不存在"
            )
        
        # 检查是否已收藏
        existing_collection = db.query(Collection).filter(
            Collection.resource_id == collection_data.resource_id,
            Collection.user_id == user_id
        ).first()
        
        if existing_collection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已经收藏过该资源"
            )
        
        # 创建收藏记录
        db_collection = Collection(
            **collection_data.model_dump(),
            user_id=user_id
        )
        
        db.add(db_collection)
        db.commit()
        db.refresh(db_collection)
        
        return db_collection
    
    def remove_collection(
        self, 
        db: Session, 
        collection_id: int, 
        user_id: int
    ) -> bool:
        """取消收藏"""
        # 获取收藏记录
        collection = db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="收藏记录不存在"
            )
        
        # 检查权限
        if collection.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作该收藏记录"
            )
        
        # 删除收藏
        db.delete(collection)
        db.commit()
        
        return True
    
    def get_user_collections(
        self, 
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Collection]:
        """获取用户的收藏"""
        return db.query(Collection).filter(
            Collection.user_id == user_id
        ).order_by(Collection.created_at.desc()).offset(skip).limit(limit).all()
    
    def publish_to_public(
        self, 
        db: Session, 
        publish_data: PublicResourceCreate, 
        user_id: int
    ) -> PublicResource:
        """发布资源到公共区域"""
        # 检查资源是否存在且属于该用户
        resource = self.get_resource_by_id(db, publish_data.resource_id)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="资源不存在"
            )
        
        if resource.user_id != user_id and not user_service.is_admin(db, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权发布该资源"
            )
        
        # 检查是否已发布
        existing_public = db.query(PublicResource).filter(
            PublicResource.resource_id == publish_data.resource_id
        ).first()
        
        if existing_public:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该资源已发布到公共区域"
            )
        
        # 创建公共资源记录
        db_public_resource = PublicResource(
            **publish_data.model_dump(),
            status="pending"  # 默认为待审核状态
        )
        
        db.add(db_public_resource)
        db.commit()
        db.refresh(db_public_resource)
        
        return db_public_resource
    
    def get_public_resources(
        self, 
        db: Session, 
        category: Optional[str] = None,
        recommended: Optional[bool] = None,
        skip: int = 0, 
        limit: int = 20
    ) -> List[PublicResource]:
        """获取公共资源"""
        query = db.query(PublicResource).filter(PublicResource.status == "approved")
        
        if category:
            query = query.filter(PublicResource.category == category)
        
        if recommended is not None:
            query = query.filter(PublicResource.recommended == recommended)
        
        return query.order_by(PublicResource.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_resources_count(self, db: Session, params: ResourceSearchParams, user_id: Optional[int] = None) -> int:
        """获取符合条件的资源总数"""
        query = db.query(Resource)
        
        # 搜索关键词
        if params.keyword:
            search_pattern = f"%{params.keyword}%"
            query = query.filter(
                (Resource.title.ilike(search_pattern)) | 
                (Resource.description.ilike(search_pattern)) |
                (Resource.content.ilike(search_pattern))
            )
        
        # 资源类型过滤
        if params.type:
            query = query.filter(Resource.type == params.type)
        
        # 用户ID过滤
        if params.user_id:
            query = query.filter(Resource.user_id == params.user_id)
        
        # 公开/私有过滤
        if params.is_public is not None:
            if params.is_public:
                query = query.filter(Resource.is_private == False)
            else:
                query = query.filter(Resource.is_private == True)
        
        # 标签过滤（可选，这里简化处理）
        if params.tags:
            # 实际应用中可能需要更复杂的JSON查询
            pass
        
        return query.count()


# 创建全局的资源服务实例
resource_service = ResourceService()