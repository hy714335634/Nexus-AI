"""
认证配置

简单的用户认证配置，支持从配置文件或环境变量读取
"""
import os
import hashlib
import secrets
from typing import Optional
from pydantic_settings import BaseSettings


def _load_auth_from_config() -> dict:
    """
    从配置文件加载认证信息
    
    返回:
        dict: 用户名到密码哈希的映射
    """
    try:
        # 导入配置加载器
        from nexus_utils.config_loader import get_config
        config = get_config()
        
        # 从配置文件读取认证信息
        nexus_config = config.config.get('nexus_ai', {})
        auth_config = nexus_config.get('auth', {})
        
        username = auth_config.get('user', 'admin')
        password = auth_config.get('password', 'nexus')
        
        # 返回用户名到密码哈希的映射
        return {
            username: hashlib.sha256(password.encode()).hexdigest()
        }
    except Exception:
        # 配置加载失败时使用默认值
        return {
            "admin": hashlib.sha256("nexus".encode()).hexdigest()
        }


class AuthSettings(BaseSettings):
    """认证配置"""
    
    # JWT 配置
    SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", secrets.token_hex(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # 用户账号 - 从配置文件加载，可通过环境变量覆盖
    # 配置文件路径: config/default_config.yaml -> nexus_ai.auth
    USERS: dict = {}

    
    class Config:
        env_prefix = "AUTH_"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从配置文件加载用户信息
        if not self.USERS:
            self.USERS = _load_auth_from_config()


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
