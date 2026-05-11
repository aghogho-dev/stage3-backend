import os 
from sqlalchemy import text
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

async def init_optimization():
    """
    Applies performance indexes and idempotency constraints.
    """
    optimization_queries = [
        # Query Performance: Indexes for low-hundreds ms targets
        "CREATE INDEX IF NOT EXISTS idx_profiles_gender ON profiles(gender)",
        "CREATE INDEX IF NOT EXISTS idx_profiles_country_id ON profiles(country_id)",
        "CREATE INDEX IF NOT EXISTS idx_profiles_age ON profiles(age)",
        "CREATE INDEX IF NOT EXISTS idx_profiles_search_composite ON profiles(gender, country_id, age)",
        
        # Idempotency Required for CSV ingestion logic
        "ALTER TABLE profiles ADD CONSTRAINT unique_name UNIQUE (name)"
    ]
    
    async with engine.begin() as conn:
        # Handle Indexes (CREATE INDEX IF NOT EXISTS is already idempotent)
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_profiles_gender ON profiles(gender)",
            "CREATE INDEX IF NOT EXISTS idx_profiles_country_id ON profiles(country_id)",
            "CREATE INDEX IF NOT EXISTS idx_profiles_age ON profiles(age)",
            "CREATE INDEX IF NOT EXISTS idx_profiles_search_composite ON profiles(gender, country_id, age)"
        ]
        for idx in indexes:
            await conn.execute(text(idx))

        # Handle the Unique Constraint with a check
        check_constraint = text("""
            SELECT count(*) FROM pg_constraint WHERE conname = 'unique_name'
        """)
        result = await conn.execute(check_constraint)
        if result.scalar() == 0:
            try:
                await conn.execute(text("ALTER TABLE profiles ADD CONSTRAINT unique_name UNIQUE (name)"))
                print("Optimization: Unique constraint 'unique_name' created.")
            except Exception as e:
                print(f"Optimization Note: Could not add constraint: {e}")
        else:
            print("Optimization: Unique constraint 'unique_name' already exists. Skipping.")


async def get_db():
    async with SessionLocal() as session:
        yield session