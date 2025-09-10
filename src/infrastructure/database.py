"""
EasyPay Payment Gateway - Database Infrastructure
"""
import os
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.core.exceptions import DatabaseError

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://easypay:password@localhost:5432/easypay")
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    echo=os.getenv("DEBUG", "false").lower() == "true"
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create base class for models
Base = declarative_base()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        DatabaseError: If session creation fails
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Database session error: {str(e)}")
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize database connection and create tables.
    
    Raises:
        DatabaseError: If database initialization fails
    """
    try:
        # Test connection
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Log successful initialization
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Database initialized successfully")
        
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database: {str(e)}")


async def close_database() -> None:
    """
    Close database connections.
    
    Raises:
        DatabaseError: If database closure fails
    """
    try:
        await async_engine.dispose()
        
        # Log successful closure
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        raise DatabaseError(f"Failed to close database connections: {str(e)}")
