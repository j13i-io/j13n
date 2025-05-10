from typing import Optional
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "app"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    @property
    def DATABASE_URL(self) -> str:
        """Get the database URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_prefix = ""
        case_sensitive = True