"""
邮件工具模块
用于发送邮件和生成验证码
"""
import smtplib
import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from config import settings


class VerificationCodeGenerator:
    """验证码生成与验证工具类"""
    
    @staticmethod
    def generate_6digit_code() -> str:
        """
        生成6位数字验证码
        
        Returns:
            6位数字验证码字符串
        """
        code = random.randint(100000, 999999)
        return str(code)
    
    @staticmethod
    def generate_mixed_code() -> str:
        """
        生成包含数字和字母的6位混合验证码
        
        Returns:
            6位混合验证码字符串
        """
        characters = string.digits + string.ascii_letters
        code = ''.join(random.choice(characters) for _ in range(6))
        return code
    
    @staticmethod
    def is_valid(code: str, stored_code: Dict[str, Any], expiration_minutes: int = 5) -> bool:
        """
        验证验证码是否有效
        
        Args:
            code: 用户输入的验证码
            stored_code: 存储的验证码信息字典，包含'code'和'expiration_time'
            expiration_minutes: 过期时间（分钟），默认5分钟
            
        Returns:
            验证码是否有效
        """
        if code != stored_code.get('code'):
            return False
        
        current_time = datetime.now()
        expiration_time = stored_code.get('expiration_time')
        
        if not expiration_time:
            return False
        
        if current_time > expiration_time:
            return False
        
        return True


def send_email(
    sender_email: str,
    sender_password: str,
    receiver_email: str,
    subject: str,
    message: str,
    smtp_server: str,
    smtp_port: int,
    attachments: Optional[List[str]] = None,
    use_ssl: bool = False
) -> bool:
    """
    发送电子邮件的函数
    
    Args:
        sender_email: 发送者邮箱
        sender_password: 发送者密码或授权码
        receiver_email: 接收者邮箱
        subject: 邮件主题
        message: 邮件内容
        smtp_server: SMTP服务器地址
        smtp_port: SMTP服务器端口
        attachments: 附件文件路径列表（可选）
        use_ssl: 是否使用SSL（可选）
        
    Returns:
        发送是否成功
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        # 处理附件
        if attachments:
            for file_path in attachments:
                if os.path.isfile(file_path):
                    part = MIMEBase('application', 'octet-stream')
                    with open(file_path, 'rb') as file:
                        part.set_payload(file.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(file_path)
                    part.add_header('Content-Disposition', f"attachment; filename= {filename}")
                    msg.attach(part)
                else:
                    print(f"警告: 附件文件不存在 - {file_path}")
        
        # 建立连接（增加10秒超时，避免无限等待）
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()  # 启用TLS加密
        
        # 登录发送
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("邮件发送成功！")
        return True
    
    except smtplib.SMTPAuthenticationError:
        print("❌ 邮件发送失败: 用户名或授权码错误（请检查QQ邮箱授权码是否有效）")
        return False
    except smtplib.SMTPConnectError:
        print("❌ 邮件发送失败: 无法连接SMTP服务器（检查域名、端口或网络）")
        return False
    except smtplib.SMTPServerDisconnected:
        print("❌ 邮件发送失败: 服务器意外断开连接（可能是网络波动或服务器限制）")
        return False
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")
        return False


def send_reset_email(aim_email: str) -> Optional[Dict[str, Any]]:
    """
    发送密码重置邮件
    
    Args:
        aim_email: 目标邮箱地址
        
    Returns:
        存储的验证码信息字典，如果发送失败返回None
    """
    # 1. 生成6位验证码
    verification_code = VerificationCodeGenerator.generate_6digit_code()
    
    # 2. 存储验证码信息
    stored_data = {
        'email': aim_email,
        'code': verification_code,
        'expiration_time': datetime.now() + timedelta(
            minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES
        )
    }
    
    # 3. 使用配置中的邮件设置
    sender_email = settings.SENDER_EMAIL
    sender_password = settings.SENDER_PASSWORD
    smtp_server = settings.SMTP_SERVER
    smtp_port = settings.SMTP_PORT
    use_ssl = settings.USE_SSL
    
    if not sender_email or not sender_password:
        print("❌ 邮件配置未设置，请检查环境变量")
        return None
    
    # 4. 邮件内容
    subject = "【AI智能学习伴侣】密码重置验证码"
    message = (
        f"您的密码重置验证码是：{verification_code}\n\n"
        f"该验证码{settings.VERIFICATION_CODE_EXPIRE_MINUTES}分钟内有效，请勿泄露给他人。\n"
        "若未发起此操作，请忽略此邮件。"
    )
    
    # 5. 发送邮件
    res = send_email(
        sender_email=sender_email,
        sender_password=sender_password,
        receiver_email=aim_email,
        subject=subject,
        message=message,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        attachments=None,
        use_ssl=use_ssl
    )
    
    # 6. 返回结果
    if res:
        print(f"✅ 验证码 {verification_code} 已发送至 {aim_email}")
        return stored_data
    else:
        print(f"❌ 向 {aim_email} 发送验证码失败")
        return None


# 向后兼容：保持旧函数名
send_reset_email_last = send_reset_email


# 测试代码
if __name__ == "__main__":
    # 测试发送（替换为真实收件人邮箱）
    test_email = "test@example.com"
    result = send_reset_email(test_email)
    
    # 验证结果
    if result:
        print(f"\n存储的验证码信息：")
        print(f"邮箱：{result['email']}")
        print(f"验证码：{result['code']}")
        print(f"过期时间：{result['expiration_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n❌ 测试发送失败，请检查配置后重试")

