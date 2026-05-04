from datetime import datetime, timedelta, timezone
from uuid import UUID  
from jose import jwt, JWTError 
from fastapi import Depends, HTTPException, Request, status 
from sqlalchemy import select 
from .config import settings
from ..database import get_db 
from ..models import User 
import os 
from dotenv import load_dotenv

load_dotenv()

def create_tokens(user_id):
   
    user_id_str = str(user_id)
    now = datetime.now(timezone.utc)
    
    access = jwt.encode(
        {
            "sub": user_id_str,
            "type": "access",
            "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        },
        settings.JWT_SECRET, 
        algorithm=settings.ALGORITHM
    )

    refresh = jwt.encode(
        {
            "sub": user_id_str,
            "type": "refresh",
            "exp": now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        },
        settings.JWT_SECRET,
        algorithm=settings.ALGORITHM
    )

    return access, refresh

async def get_current_user(
    request: Request, # Changed from 'security' to 'Request' to access cookies
    db=Depends(get_db)
):
    # Check for token in Cookies (Requirement for Web Portal)
    token = request.cookies.get("access_token")
    
    # Fallback to Authorization Header (Requirement for CLI)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Authentication required"
        )

    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
        
        token_sub = payload.get("sub")
        if not token_sub:
            raise HTTPException(401, "Invalid token payload")

        # Convert string from JWT back into a UUID object
        try:
            user_id = UUID(token_sub)
        except (ValueError, AttributeError):
            raise HTTPException(401, "Invalid user identifier format")

    except JWTError:
        # If token is expired, return 401 so CLI/Web can trigger /auth/refresh
        raise HTTPException(401, "Token expired or invalid")

    # Check User System Requirements (is_active status)
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    # Requirement: If is_active is false, 403 Forbidden
    if not user:
        raise HTTPException(401, "User not found")
    
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account disabled")
    
    return user