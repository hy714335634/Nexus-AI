"""
认证中间件

FastAPI 认证依赖注入
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .jwt_handler import verify_token

# HTTP Bearer 认证方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    获取当前用户
    
    从 Authorization header 或 cookie 中获取 token 并验证
    
    参数:
        request: FastAPI 请求对象
        credentials: HTTP Bearer 凭证
    
    返回:
        用户信息字典
    
    异常:
        HTTPException: 认证失败时抛出 401 错误
    """
    token = None
    
    # 优先从 Authorization header 获取
    if credentials:
        token = credentials.credentials
    
    # 其次从 cookie 获取
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证 token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"username": payload.get("sub")}


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    可选的用户认证
    
    不强制要求登录，返回用户信息或 None
    """
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None
