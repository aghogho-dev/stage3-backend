from fastapi import Header, HTTPException, Depends
from .security import get_current_user

async def verify_api_version(x_api_version: str = Header(None)):
    if x_api_version != "1":
        raise HTTPException(400, "API version header required")

def check_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")
    return user