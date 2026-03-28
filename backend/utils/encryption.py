"""
密码加密工具模块
使用 Fernet 加密算法（AES-128-CBC）对密码进行加密存储
"""

import os
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from typing import Optional


def get_encryption_key() -> str:
    """
    获取加密密钥
    优先从环境变量获取，若未设置则生成一个临时密钥（生产环境不推荐）
    """
    key = os.environ.get('ENCRYPTION_KEY')
    if key:
        return key

    # 开发环境生成临时密钥（生产环境必须通过环境变量设置）
    temp_key = Fernet.generate_key().decode()
    print(f"WARNING: Using temporary encryption key (for development only): {temp_key}")
    print("Please set ENCRYPTION_KEY environment variable in production")
    return temp_key


def encrypt_password(password: str) -> str:
    """
    加密密码
    """
    if not password:
        return ""

    try:
        key = get_encryption_key()
        fernet = Fernet(key.encode())
        encrypted = fernet.encrypt(password.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        raise Exception(f"Password encryption failed: {str(e)}")


def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码
    """
    if not encrypted_password:
        return ""

    try:
        key = get_encryption_key()
        fernet = Fernet(key.encode())
        decrypted = fernet.decrypt(encrypted_password.encode('utf-8'))
        return decrypted.decode('utf-8')
    except InvalidToken:
        raise Exception("Invalid encryption token")
    except Exception as e:
        raise Exception(f"Password decryption failed: {str(e)}")