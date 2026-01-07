"""
工具模块
包含JWT工具、邮件工具等
"""
from .jwt_utils import generate_jwt, verify_jwt
from .email_utils import (
    VerificationCodeGenerator,
    send_email,
    send_reset_email,
    send_reset_email_last  # 向后兼容
)

__all__ = [
    'generate_jwt',
    'verify_jwt',
    'VerificationCodeGenerator',
    'send_email',
    'send_reset_email',
    'send_reset_email_last',
]

