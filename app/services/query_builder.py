from sqlalchemy import select, and_, func 
from ..models import Profile 


def build_profile_query(filters: dict):
    stmt = select(Profile)
    clauses = []

    if filters.get("gender"): clauses.append(Profile.gender == filters["gender"].lower())
    if filters.get("age_group"): clauses.append(Profile.age_group == filters["age_group"].lower())
    if filters.get("country_id"): clauses.append(Profile.country_id == filters["country_id"].upper())
    if filters.get("min_age"): clauses.append(Profile.age >= filters["min_age"])
    if filters.get("max_age"): clauses.append(Profile.age <= filters["max_age"])

    if clauses: stmt = stmt.where(and_(*clauses))
    
    sort_by = filters.get("sort_by", "created_at")
    order = filters.get("order", "asc")
    attr = getattr(Profile, sort_by, Profile.created_at)
    stmt = stmt.order_by(attr.desc() if order == "desc" else attr.asc())
    
    return stmt

