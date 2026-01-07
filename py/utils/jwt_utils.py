"""
JWT工具模块
用于生成和验证JWT Token
"""
import jwt
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from config import settings


def generate_jwt(user_id: int, username: str) -> str:
    """
    生成JWT Token
    
    Args:
        user_id: 用户ID
        username: 用户名
        
    Returns:
        JWT Token字符串
    """
    current_time = datetime.now(UTC)
    
    payload = {
        "sub": str(user_id),  # 用户唯一ID（字符串格式）
        "username": username,
        "user_id": user_id,  # 额外存储用户ID（数字格式）
        "iat": current_time,  # 生成时间（UTC时区）
        "exp": current_time + timedelta(seconds=settings.JWT_EXPIRE_SECONDS)  # 过期时间
    }
    
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    验证JWT Token并返回用户信息
    
    Args:
        token: JWT Token字符串
        
    Returns:
        用户信息字典，如果验证失败返回None或包含error的字典
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username")
        }
    
    except jwt.ExpiredSignatureError:
        return {"error": "Token已过期"}
    except jwt.InvalidSignatureError:
        return {"error": "Token签名无效（可能被篡改）"}
    except jwt.InvalidTokenError:
        return {"error": "Token格式错误"}
    except Exception as e:
        return {"error": f"验证失败: {str(e)}"}


# 测试代码
if __name__ == "__main__":
    try:
        # 生成token
        token = generate_jwt(1, "test_user")
        print("生成的Token:", token)
        
        # 验证刚刚生成的token
        verify_result = verify_jwt(token)
        print("验证结果:", verify_result)
        
    except Exception as e:
        print("发生错误:", str(e))

