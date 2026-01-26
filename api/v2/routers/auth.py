"""
认证路由

处理登录、登出、用户信息等认证相关请求
"""
from fastapi import APIRouter, HTTPException, status, Response, Depends
from pydantic import BaseModel

from api.v2.auth.config import get_user, verify_password
from api.v2.auth.jwt_handler import create_access_token
from api.v2.auth.middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    """用户信息响应"""
    username: str
    authenticated: bool = True


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """
    用户登录
    
    验证用户名和密码，返回 JWT token
    """
    # 获取用户
    user = get_user(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # 验证密码
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # 生成 token
    access_token = create_access_token(data={"sub": user["username"]})
    
    # 设置 cookie (httponly, 更安全)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,  # 24 小时
        samesite="lax",
        secure=False,  # 生产环境应设为 True
    )
    
    return LoginResponse(
        success=True,
        access_token=access_token,
        username=user["username"]
    )


@router.post("/logout")
async def logout(response: Response):
    """
    用户登出
    
    清除认证 cookie
    """
    response.delete_cookie(key="access_token")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户信息
    
    需要认证
    """
    return UserResponse(username=current_user["username"])


@router.get("/check")
async def check_auth(current_user: dict = Depends(get_current_user)):
    """
    检查认证状态
    
    用于前端检查用户是否已登录
    """
    return {
        "authenticated": True,
        "username": current_user["username"]
    }
