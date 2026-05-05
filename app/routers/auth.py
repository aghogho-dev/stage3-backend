from urllib import response

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy import select, delete 
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from ..core.config import settings 
from ..core.security import create_tokens,get_current_user
from ..database import get_db 
from ..models import User, RefreshToken, LogoutRequest 
import httpx 

from ..utils import limiter

from fastapi.responses import RedirectResponse



router = APIRouter(prefix="/auth", tags=["Auth"])



async def process_github_auth(code: str, db: AsyncSession):
    """
    Consolidated logic for exchanging GitHub code for internal JWTs.
    """
    async with httpx.AsyncClient() as client:
        
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            params={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_res.json()
        gh_access_token = token_data.get("access_token")

        if not gh_access_token:
            raise HTTPException(
                status_code=401,
                detail="Failed to retrieve Github access token"
            )

        
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {gh_access_token}"},
        )
        gh_user = user_res.json()
        github_id = str(gh_user.get("id"))

        
        query = select(User).where(User.github_id == github_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                github_id=github_id,
                username=gh_user.get("login"),
                email=gh_user.get("email"),
                role="analyst"
            )
            db.add(user)
            await db.flush()

        
        internal_user_id = str(user.id)
        access_token, refresh_token = create_tokens(internal_user_id)
        db.add(RefreshToken(token=refresh_token, user_id=user.id))

        await db.commit()
        await db.refresh(user)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": internal_user_id,
                "username": user.username,
                "role": user.role
            }
        }

@router.get("/github")
@limiter.limit("10/minute")
async def github_login(request:Request, state: str = None):
    """
    Step 1: Redirect user to GitHub's OAuth page.
    """
    scope = "read:user user:email"
    
    github_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"scope={scope}&"
        f"state={state if state else 'web'}"
    )
    return RedirectResponse(url=github_url)


@router.get("/github/callback")
@limiter.limit("10/minute")
async def callback(
    request: Request, 
    response: Response,
    code: str, 
    state: str = None, 
    db: AsyncSession = Depends(get_db)):
    auth_data = await process_github_auth(code, db)

    if state == "cli":
        access = auth_data["access_token"]
        refresh = auth_data["refresh_token"]

        return RedirectResponse(
            url=f"http://localhost:8000/callback?access_token={access}&refresh_token={refresh}"
        )
    
    web_redirect = RedirectResponse(url="http://localhost:5173/")
    
    web_redirect.set_cookie(
        key="access_token",
        value=auth_data["access_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=180
    )

    web_redirect.set_cookie(
        key="refresh_token",
        value=auth_data["refresh_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=300
    )
    return web_redirect  


@router.post("/token")
@limiter.limit("10/minute")
async def exchange_token(request: Request, body: dict, db: AsyncSession = Depends(get_db)):
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Code is required")
    return await process_github_auth(code, db)



@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh_access_token(request: Request, refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token expired or tampered")


    stmt = select(RefreshToken).where(RefreshToken.token == refresh_token)
    result = await db.execute(stmt)
    token_record = result.scalar_one_or_none()
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Refresh token revoked or already used")
    
    await db.execute(delete(RefreshToken).where(RefreshToken.token == refresh_token))
    
    new_access, new_refresh = create_tokens(str(user_id))
    
    db.add(RefreshToken(token=new_refresh, user_id=token_record.user_id))
    
    await db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }



# @router.post("/logout")
# @limiter.limit("10/minute")
# async def logout(request: Request, body: LogoutRequest, db: AsyncSession = Depends(get_db)):
    
#     stmt = delete(RefreshToken).where(RefreshToken.token == body.refresh_token)
#     result = await db.execute(stmt)
    
#     if result.rowcount == 0:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, 
#             detail="Invalid or already invalidated refresh token"
#         )
    
#     await db.commit()

#     return {
#         "status": "success",
#         "message": "Logged out successfully. Refresh token invalidated."
#     }

@router.post("/logout")
@limiter.limit("10/minute")
async def logout(request: Request, response: Response):
    response.delete_cookie(key="access_token", httponly=True, secure=True, samesite="none")
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="none")
    return {"message": "Logged out"}


@router.get("/whoami")
@limiter.limit("10/minute")
async def whoami(request: Request, current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active
    }