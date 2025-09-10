#!/usr/bin/env python3
"""
Test script to check database connection
"""
import asyncio
from sqlalchemy import text

from src.infrastructure.database import async_engine

async def test_db_connection():
    """Test database connection."""
    try:
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("Database connection successful:", result.scalar())
    except Exception as e:
        print(f"Database connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db_connection())
