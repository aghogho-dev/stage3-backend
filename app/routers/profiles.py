import json

from fastapi import Request, APIRouter, File, UploadFile, Query, Depends, Response, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from ..database import get_db
from ..models import Profile
from ..services.export_service import generate_profile_csv
from ..services.external_api import get_enriched_data
from ..parser import parse_natural_language
from ..core.security import get_current_user
from ..core.dependencies import verify_api_version, check_admin

from ..utils import limiter, generate_normalized_cache_key
from ..services.ingestion import stream_csv_ingestion
from ..core.redis import get_redis

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])


@router.get("/search", dependencies=[Depends(verify_api_version)])
@limiter.limit("60/minute")
async def search_profiles(
    request: Request,
    q: Optional[str] = Query(None), 
    page: int = Query(1, ge=1), 
    limit: int = Query(10, ge=1, le=50), 
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)):
    
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Missing query parameter")

    interpreted_filters = parse_natural_language(q)
    
    if not interpreted_filters:
        raise HTTPException(status_code=400, detail="Unable to interpret query")
    
    cache_context = {
        **interpreted_filters,
        "page": page,
        "limit": limit
    }
    cache_key = generate_normalized_cache_key(cache_context)


    redis = get_redis()
    cached_result = redis.get(cache_key)

    if cached_result:
        return Response(content=cached_result, media_type="application/json")
    
    result = await get_profiles(
        **interpreted_filters, 
        page=page, 
        limit=limit, 
        db=db, 
        user=user,
        request=request
    )

    redis.setex(cache_key, value=json.dumps(result), ex=300)

    return result


@router.get("/", dependencies=[Depends(verify_api_version)])
@limiter.limit("60/minute")
async def get_profiles(
    request: Request,
    gender: Optional[str] = None,
    age_group: Optional[str] = None,
    country_id: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    min_gender_probability: Optional[float] = None,
    min_country_probability: Optional[float] = None,
    sort_by: str = "created_at",
    order: str = "asc",
    format: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)):

    
    if sort_by not in ["age", "created_at", "gender_probability"]:
        raise HTTPException(status_code=400, detail="Invalid sort parameter")

   
    stmt = select(Profile)
    filters = []
    if gender: filters.append(Profile.gender == gender.lower())
    if age_group: filters.append(Profile.age_group == age_group.lower())
    if country_id: filters.append(Profile.country_id == country_id.upper())
    if min_age is not None: filters.append(Profile.age >= min_age)
    if max_age is not None: filters.append(Profile.age <= max_age)
    if min_gender_probability: filters.append(Profile.gender_probability >= min_gender_probability)
    if min_country_probability: filters.append(Profile.country_probability >= min_country_probability)
    
    if filters: stmt = stmt.where(and_(*filters))

    
    if format == "csv":
        result = await db.execute(stmt)
        profiles = result.scalars().all()
        csv_content = generate_profile_csv(profiles)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=profiles_{datetime.now().timestamp()}.csv"}
        )

    
    sort_attr = getattr(Profile, sort_by)
    stmt = stmt.order_by(sort_attr.desc() if order == "desc" else sort_attr.asc())
    
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    data = result.scalars().all()

 
    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": {
            "self": f"/api/profiles?page={page}&limit={limit}",
            "next": f"/api/profiles?page={page+1}&limit={limit}" if page < total_pages else None,
            "prev": f"/api/profiles?page={page-1}&limit={limit}" if page > 1 else None
        },
        "data": data
    }

@router.get("/upload", dependencies=[Depends(verify_api_version)])
@limiter.limit("5/minute")
async def upload_csv(request: Request, file: UploadFile = File(...), db: AsyncSession=Depends(get_db)):
    content = await file.read()
    return await stream_csv_ingestion(content, db)



@router.post("/", dependencies=[Depends(verify_api_version)], status_code=201)
@limiter.limit("60/minute")
async def create_profile(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user=Depends(check_admin)):

    name = payload.get("name")

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    enriched_data = await get_enriched_data(name)

    new_profile = Profile(
        name=name,
        gender=enriched_data["gender"],
        gender_probability=enriched_data["gender_probability"],
        age=enriched_data["age"],
        age_group=enriched_data["age_group"],
        country_id=enriched_data["country_id"],
        country_probability=enriched_data["country_probability"]
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    return {
        "status": "success", 
        "data": new_profile,
        "message": "Profile created successfully"
        }