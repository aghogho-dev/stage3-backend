from datetime import datetime, timedelta, timezone
from uuid import UUID  
from jose import jwt, JWTError 
from fastapi import Depends, HTTPException, status 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
from sqlalchemy import select 
from .config import settings
from ..database import get_db 
from ..models import User 
import os 
from dotenv import load_dotenv

load_dotenv()


security = HTTPBearer()


def create_tokens(user_id):
    # Ensure user_id is serialized as a string for the JWT payload
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
    cred: HTTPAuthorizationCredentials=Depends(security),
    db=Depends(get_db)):
    try:
        payload = jwt.decode(
            cred.credentials, 
            settings.JWT_SECRET,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
        
        token_sub = payload.get("sub")
        if not token_sub:
            raise HTTPException(401, "Invalid token payload")

        # Convert the string from the JWT back into a UUID object
        try:
            user_id = UUID(token_sub)
        except (ValueError, AttributeError):
            raise HTTPException(401, "Invalid user identifier format")

    except JWTError:
        raise HTTPException(401, "Authentication required")

    # SQLAlchemy now receives a UUID object, preventing the .hex attribute error
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(403, "User account disabled")
    
    return user











# from datetime import datetime, timedelta, timezone
# from jose import jwt, JWTError 
# from fastapi import Depends, HTTPException, status 
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
# from sqlalchemy import select 
# from .config import settings
# from ..database import get_db 
# from ..models import User 
# import os 
# from dotenv import load_dotenv

# load_dotenv()


# security = HTTPBearer()


# def create_tokens(user_id: str):
#     now = datetime.now(timezone.utc)
#     access = jwt.encode(
#         {
#             "sub": user_id,
#             "type": "access",
#             "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#         },
#         settings.JWT_SECRET, 
#         algorithm=settings.ALGORITHM
#     )

#     refresh = jwt.encode(
#         {
#             "sub": user_id,
#             "type": "refresh",
#             "exp": now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
#         },
#         settings.JWT_SECRET,
#         algorithm=settings.ALGORITHM
#     )

#     return access, refresh


# async def get_current_user(
#     cred: HTTPAuthorizationCredentials=Depends(security),
#     db=Depends(get_db)):
#     try:
#         payload = jwt.decode(
#             cred.credentials, 
#             settings.JWT_SECRET,
#             algorithms=[settings.ALGORITHM]
#         )

#         if payload.get("type") != "access":
#             raise HTTPException(401, "Invalid token type")
#         user_id = payload.get("sub")
#     except JWTError:
#         raise HTTPException(401, "Authentication required")

#     result = await db.execute(
#         select(User).where(User.id == user_id)
#     )
#     user = result.scalar_one_or_none()
#     if not user or not user.is_active:
#         raise HTTPException(403, "User account disabled")
    
#     return user
