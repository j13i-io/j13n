from datetime import datetime
from typing import Generic, TypeVar, Optional, AsyncGenerator
from sqlalchemy import DateTime, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel, ConfigDict
from .config import DatabaseSettings

# Type variables for generic types
I = TypeVar('I')  # ID type
U = TypeVar('U')  # User type

# Create metadata with naming convention
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)

class BaseDto(BaseModel, Generic[I, U]):
    """Base Pydantic model for DTOs."""
    id: Optional[I] = None
    created_at: Optional[datetime] = None
    created_by: Optional[U] = None

    model_config = ConfigDict(from_attributes=True)

class BaseUpdatableDto(BaseDto[I, U]):
    """Base Pydantic model for updatable DTOs."""
    updated_at: Optional[datetime] = None
    updated_by: Optional[U] = None

class Base(DeclarativeBase):
    """Base SQLAlchemy model."""
    metadata = metadata

    id: Mapped[I] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow(), nullable=False)
    created_by: Mapped[Optional[U]] = mapped_column(nullable=True)

class BaseUpdatable(Base):
    """Base SQLAlchemy model for updatable entities."""
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by: Mapped[Optional[U]] = mapped_column(nullable=True)

class Database:
    """Database connection manager."""
    def __init__(self, settings: DatabaseSettings):
        self.settings = settings
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            echo=settings.DB_ECHO,
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        async with self.async_session() as session:
            yield session

    async def init_models(self):
        """Initialize database models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """Close database connection."""
        await self.engine.dispose()