"""
认证配置

简单的用户认证配置，支持从环境变量或配置文件读取
"""
import os
import hashlib
import secrets
from typing import Optional
from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    """认证配置"""
    
    # JWT 配置
    SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", secrets.token_hex(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # 预设用户账号 - 可通过环境变量覆盖
    # 格式: username:password_hash (SHA256)
    # 默认账号: admin / nexus
    USERS: dict = {
        "admin": hashlib.sha256("nexus".encode()).hexdigest()
    }

    
    class Config:
        env_prefix = "AUTH_"


auth_settings = AuthSettings()


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return get_password_hash(plain_password) == hashed_password


def get_user(username: str) -> Optional[dict]:
    """获取用户信息"""
    if username in auth_settings.USERS:
        return {
            "username": username,
            "password_hash": auth_settings.USERS[username]
        }
    return None
