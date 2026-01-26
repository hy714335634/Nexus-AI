"""
JWT Token 处理

生成和验证 JWT Token
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt

from .config import auth_settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    参数:
        data: 要编码的数据
        expires_delta: 过期时间增量
    
    返回:
        JWT token 字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=auth_settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, auth_settings.SECRET_KEY, algorithm=auth_settings.ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    验证令牌
    
    参数:
        token: JWT token 字符串
    
    返回:
        解码后的数据，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, auth_settings.SECRET_KEY, algorithms=[auth_settings.ALGORITHM])
        return payload
    except JWTError:
        return None
