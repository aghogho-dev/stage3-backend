import os 
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession 
from sqlalchemy.orm import sessionmaker, declarative_base 
from .core.config import settings

print("Initializing database connection...")
print("DATABASE_URL:", settings.get_async_database_url())
print("**************************************************************")

engine = create_async_engine(
    settings.get_async_database_url(),
    echo=False,
    pool_pre_ping=True,
    connect_args={"timeout": 30}
)

SessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session