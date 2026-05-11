import json
import asyncio
from sqlalchemy.dialects.postgresql import insert
from .database import SessionLocal, engine
from .models import Base, Profile

async def seed():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        with open("seed_profiles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: seed_profiles.json not found.")
        return

    profiles_list = data.get("profiles", [])
    print(f"Starting seed of {len(profiles_list)} records...")

    async with SessionLocal() as session:
        chunk_size = 100 
        
        for i in range(0, len(profiles_list), chunk_size):
            batch = profiles_list[i : i + chunk_size]
            
            cleaned_batch = []
            for p in batch:
                # We map only the keys that exist in your Profile model
                # Note: 'country_name' is ignored as it's not in your model
                cleaned_batch.append({
                    "name": p.get("name"),
                    "gender": p.get("gender"),
                    "gender_probability": p.get("gender_probability"),
                    "age": p.get("age"),
                    "age_group": p.get("age_group"),
                    "country_id": p.get("country_id"),
                    "country_probability": p.get("country_probability")
                })

            # Idempotency: Use 'name' as the conflict target
            stmt = insert(Profile).values(cleaned_batch).on_conflict_do_nothing(
                index_elements=["name"]
            )
            
            await session.execute(stmt)
            # CRITICAL: Commit each chunk to clear WAL logs and avoid "No space left"
            await session.commit()
            
    print("Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed())


# async def seed():
#     with open("seed_profiles.json", "r") as f:
#         data = json.load(f)

#     async with SessionLocal() as session:
#         for p in data["profiles"]:
#             stmt = insert(Profile).values(**p).on_conflict_do_nothing(
#                 index_elements=["name"]
#             )
#             await session.execute(stmt)
#         await session.commit()
#     print("Database seeded successfully.")


# if __name__ == "__main__":
#     asyncio.run(seed())