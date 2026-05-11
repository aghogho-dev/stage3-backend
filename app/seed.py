import json
import asyncio 
from sqlalchemy.dialects.postgresql import insert 
from .database import SessionLocal 
from .models import Profile


async def seed():
    with open("seed_profiles.json", "r") as f:
        data = json.load(f)

    async with SessionLocal() as session:
        for p in data["profiles"]:
            stmt = insert(Profile).values(**p).on_conflict_do_nothing(
                index_elements=["name"]
            )
            await session.execute(stmt)
        await session.commit()
    print("Database seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())