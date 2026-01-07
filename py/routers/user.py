"""
用户路由
处理用户管理相关的API接口
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse, Response
import os
import uuid
import json
from pathlib import Path
from PIL import Image
import io
from datetime import datetime

from database import get_db
from schemas.user import (
    UserResponse, UserUpdate
)
from schemas.common import ResponseModel
from services.user_service import user_service
from services.auth_service import auth_service
from models import User

# 创建路由实例
router = APIRouter()

# 头像配置
AVATAR_DIR = Path(__file__).parent.parent / "avatars"
AVATAR_MAX_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
AVATAR_SIZE = (200, 200)  # 头像压缩尺寸


@router.post("/avatar/upload")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上传用户头像
    - **file**: 头像图片文件（支持 JPG、PNG、GIF、WebP格式）
    - 自动压缩为 200x200 像素
    - 最大文件大小：5MB
    """
    # 获取当前用户（使用app.py中的get_current_user）
    from app import get_current_user
    current_user = await get_current_user(request, db)
    user_id = current_user.id
    
    # 验证文件类型
    if file.content_type not in AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型。支持的类型：{', '.join(AVATAR_ALLOWED_TYPES)}"
        )
    
    # 读取文件内容
    content = await file.read()
    
    # 验证文件大小
    if len(content) > AVATAR_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大{AVATAR_MAX_SIZE / 1024 / 1024}MB）"
        )
    
    try:
        # 打开图片
        image = Image.open(io.BytesIO(content))
        
        # 转换为RGB模式（处理PNG透明背景）
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 裁剪为正方形（取中心部分）
        width, height = image.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        image = image.crop((left, top, right, bottom))
        
        # 调整大小
        image = image.resize(AVATAR_SIZE, Image.Resampling.LANCZOS)
        
        # 生成唯一文件名
        file_extension = ".jpg"  # 统一保存为JPG格式
        filename = f"{user_id}_{uuid.uuid4().hex}{file_extension}"
        filepath = AVATAR_DIR / filename
        
        # 确保目录存在
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存图片
        image.save(filepath, "JPEG", quality=85, optimize=True)
        
        # 更新用户头像字段
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 删除旧头像文件（如果存在）
        if user.avatar:
            old_filename = user.avatar.split('/')[-1]
            old_filepath = AVATAR_DIR / old_filename
            if old_filepath.exists():
                old_filepath.unlink()
        
        # 更新数据库
        avatar_url = f"/api/users/avatar/{filename}"
        user.avatar = avatar_url
        db.commit()
        
        return ResponseModel(
            code=200,
            message="头像上传成功",
            data={
                "avatar_url": avatar_url,
                "filename": filename
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"头像处理失败：{str(e)}"
        )


@router.get("/avatar/{filename}")
async def get_avatar(filename: str):
    """
    获取用户头像
    - **filename**: 头像文件名
    """
    filepath = AVATAR_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="头像文件不存在"
        )
    
    return FileResponse(filepath, media_type="image/jpeg")


@router.delete("/avatar")
async def delete_avatar(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    删除用户头像
    """
    # 获取当前用户
    from app import get_current_user
    current_user = await get_current_user(request, db)
    user_id = current_user.id
    
    # 获取用户信息
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 删除头像文件
    if user.avatar:
        filename = user.avatar.split('/')[-1]
        filepath = AVATAR_DIR / filename
        if filepath.exists():
            filepath.unlink()
        
        # 更新数据库
        user.avatar = None
        db.commit()
        
        return ResponseModel(
            code=200,
            message="头像删除成功"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未设置头像"
        )


@router.get("/me")
async def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取当前登录用户信息
    需要在请求头中提供有效的访问令牌
    """
    from app import get_current_user
    current_user = await get_current_user(request, db)
    user_id = current_user.id
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return ResponseModel(
        code=200,
        message="获取用户信息成功",
        data=user.to_dict()
    )


@router.put("/me")
async def update_current_user(
    user_update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    - **username**: 用户名（可选）
    - **email**: 邮箱（可选）
    - **avatar**: 头像URL（可选）
    """
    from app import get_current_user
    current_user = await get_current_user(request, db)
    user_id = current_user.id
    
    # 更新用户信息
    updated_user = user_service.update_user(db, user_id, user_update, user_id)
    
    return ResponseModel(
        code=200,
        message="用户信息更新成功",
        data=updated_user.to_dict()
    )


@router.put("/profile")
async def update_user_profile(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    更新用户基本信息（仅用户名，邮箱不可修改）
    """
    from app import get_current_user
    current_user = await get_current_user(request, db)
    user_id = current_user.id
    
    # 从请求体获取数据
    body = await request.json()
    username = body.get('username')
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证用户名
    if username:
        if len(username) < 3 or len(username) > 80:
            raise HTTPException(status_code=400, detail="用户名长度必须在3-80个字符之间")
        # 检查用户名是否已被使用
        existing_user = db.query(User).filter(User.username == username, User.id != user_id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已被使用")
        user.username = username
    else:
        # 如果没有提供用户名，则返回提示信息
        raise HTTPException(status_code=400, detail="请提供有效的用户名")
    
    db.commit()
    db.refresh(user)
    
    return ResponseModel(
        code=200,
        message="用户名更新成功",
        data=user.to_dict()
    )


@router.post("/change-password")
async def change_password(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    修改用户密码
    - **old_password**: 当前密码
    - **new_password**: 新密码
    """
    from app import get_current_user
    current_user = await get_current_user(request, db)
    user_id = current_user.id
    
    # 从请求体获取数据
    body = await request.json()
    old_password = body.get('old_password')
    new_password = body.get('new_password')
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="请提供当前密码和新密码")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证当前密码
    from werkzeug.security import check_password_hash, generate_password_hash
    if not check_password_hash(user.password_hash, old_password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    
    # 验证新密码
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度至少需要6位")
    
    # 更新密码
    user.password_hash = generate_password_hash(new_password)
    db.commit()
    
    return ResponseModel(
        code=200,
        message="密码修改成功",
        data=None
    )


@router.get("/export")
async def export_user_data(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    导出用户所有数据
    包括：用户信息、聊天记录、学习记录等
    """
    from app import get_current_user
    import json
    from fastapi.responses import Response
    
    current_user = await get_current_user(request, db)
    user_id = current_user.id
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 收集用户数据
    export_data = {
        "user_info": user.to_dict(),
        "export_date": str(datetime.now()),
        # 可以添加更多数据导出
        # "chat_history": ...,
        # "learning_progress": ...,
    }
    
    # 转换为JSON
    json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
    
    # 返回JSON文件
    return Response(
        content=json_data,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=user_data_{user_id}.json"
        }
    )


@router.get("/me/profile")
async def get_user_profile(
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取用户详细资料（包含统计信息）
    """
    # 获取用户基本信息
    user_dict = current_user.to_dict()
    
    # 获取统计信息
    stats = user_service.get_user_stats(db, current_user.id)
    
    # 合并数据
    profile_data = {
        **user_dict,
        "stats": stats
    }
    
    return ResponseModel(
        code=200,
        message="获取用户资料成功",
        data=profile_data
    )


@router.get("/me/stats")
async def get_current_user_stats(
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取当前用户的统计信息
    """
    stats = user_service.get_user_stats(db, current_user.id)
    
    return ResponseModel(
        code=200,
        message="获取用户统计信息成功",
        data=stats
    )


@router.get("/{user_id}")
async def get_user_by_id(
    user_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    根据ID获取用户信息
    只有管理员或用户本人可以访问详细信息
    """
    # 获取用户
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 检查权限（只有管理员或用户本人可以访问）
    if not user_service.is_admin(db, current_user.id) and current_user.id != user_id:
        # 非管理员只能看到公开信息
        user_dict = user.to_dict()
        # 移除敏感信息
        private_fields = ["email", "phone", "created_at", "updated_at", "last_login_at"]
        for field in private_fields:
            user_dict.pop(field, None)
        
        return ResponseModel(
            code=200,
            message="获取用户公开信息成功",
            data=user_dict
        )
    
    # 管理员或用户本人可以看到所有信息
    return ResponseModel(
        code=200,
        message="获取用户信息成功",
        data=user.to_dict()
    )


# 管理员接口
@router.get("")
async def get_users(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    is_active: Optional[bool] = Query(None, description="用户状态"),
    is_admin: Optional[bool] = Query(None, description="是否管理员"),
    email_verified: Optional[bool] = Query(None, description="邮箱是否已验证"),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取用户列表（管理员）
    需要管理员权限
    """
    # 检查管理员权限
    if not user_service.is_admin(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    # 构建搜索参数
    search_params = UserSearchParams(
        keyword=keyword,
        is_active=is_active,
        is_admin=is_admin,
        email_verified=email_verified,
        sort_by=sort_by,
        order=order
    )
    
    # 计算偏移量
    skip = (page - 1) * page_size
    
    # 获取用户列表
    users = user_service.get_users(db, search_params, skip, page_size)
    
    # 获取总数
    total = user_service.get_users_count(db, search_params)
    
    return ResponseModel(
        code=200,
        message="获取用户列表成功",
        data={
            "items": [user.to_dict() for user in users],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    )


@router.put("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    更新用户状态（管理员）
    启用或禁用用户账号
    """
    # 检查管理员权限
    if not user_service.is_admin(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    # 不允许禁用自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己的账号"
        )
    
    # 更新用户状态
    updated_user = user_service.update_user_status(db, user_id, is_active)
    
    return ResponseModel(
        code=200,
        message="用户状态更新成功",
        data=updated_user.to_dict()
    )


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    is_admin: bool,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    更新用户角色（管理员）
    设置或取消管理员权限
    """
    # 检查管理员权限
    if not user_service.is_admin(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    # 更新用户角色
    updated_user = user_service.update_user_role(db, user_id, is_admin)
    
    return ResponseModel(
        code=200,
        message="用户角色更新成功",
        data=updated_user.to_dict()
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    删除用户（管理员）
    注意：此操作不可逆
    """
    # 检查管理员权限
    if not user_service.is_admin(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    # 不允许删除自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号"
        )
    
    # 删除用户
    user_service.delete_user(db, user_id)
    
    return ResponseModel(
        code=200,
        message="用户删除成功"
    )


@router.get("/admin/stats")
async def get_admin_stats(
    # 暂时移除get_current_user依赖，稍后实现
    db: Session = Depends(get_db)
):
    """
    获取管理员统计信息
    需要管理员权限
    """
    # 检查管理员权限
    if not user_service.is_admin(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    # 获取统计信息
    stats = user_service.get_admin_stats(db)
    
    return ResponseModel(
        code=200,
        message="获取统计信息成功",
        data=stats
    )