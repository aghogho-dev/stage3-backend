from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    JWT_SECRET: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    DATABASE_URL: str


    @field_validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must start with 'postgresql+asyncpg://'")
        return v


    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore"
    )



settings = Settings()