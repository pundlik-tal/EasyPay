"""
EasyPay Payment Gateway - Admin API Endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
import os

from src.infrastructure.database import get_db_session
from src.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/database", response_class=HTMLResponse)
async def database_admin_interface():
    """
    Serve the database admin web interface.
    """
    html_file_path = os.path.join(os.path.dirname(__file__), "db_admin.html")
    return FileResponse(html_file_path)


@router.get("/database/tables")
async def get_database_tables(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get list of all database tables and their basic info.
    """
    try:
        # Get table names
        result = await db.execute(text("""
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = result.fetchall()
        
        table_info = []
        for table in tables:
            # Get column info for each table
            columns_result = await db.execute(text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table[0]}' 
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """))
            columns = columns_result.fetchall()
            
            table_info.append({
                "name": table[0],
                "type": table[1],
                "columns": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "default": col[3]
                    } for col in columns
                ]
            })
        
        return {
            "tables": table_info,
            "total_tables": len(table_info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/database/query")
async def execute_query(
    query: str = Query(..., description="SQL query to execute"),
    limit: int = Query(100, description="Maximum number of rows to return"),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Execute a read-only SQL query and return results.
    Note: Only SELECT queries are allowed for security.
    """
    try:
        # Basic security check - only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            raise HTTPException(
                status_code=400, 
                detail="Only SELECT queries are allowed for security reasons"
            )
        
        # Add LIMIT if not present
        if 'LIMIT' not in query_upper:
            query = f"{query} LIMIT {limit}"
        
        result = await db.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()
        
        return {
            "columns": list(columns),
            "rows": [dict(zip(columns, row)) for row in rows],
            "total_rows": len(rows),
            "query": query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@router.get("/database/stats")
async def get_database_stats(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get database statistics and table row counts.
    """
    try:
        # Get database size
        size_result = await db.execute(text("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as size
        """))
        db_size = size_result.fetchone()[0]
        
        # Get table row counts
        tables_result = await db.execute(text("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC
        """))
        table_stats = tables_result.fetchall()
        
        # Get connection info
        connections_result = await db.execute(text("""
            SELECT 
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections
            FROM pg_stat_activity
        """))
        conn_info = connections_result.fetchone()
        
        return {
            "database_size": db_size,
            "total_connections": conn_info[0],
            "active_connections": conn_info[1],
            "table_statistics": [
                {
                    "schema": row[0],
                    "table": row[1],
                    "inserts": row[2],
                    "updates": row[3],
                    "deletes": row[4],
                    "live_rows": row[5],
                    "dead_rows": row[6]
                } for row in table_stats
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")


@router.get("/database/health")
async def database_health_check(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Check database health and connectivity.
    """
    try:
        # Test basic connectivity
        result = await db.execute(text("SELECT 1 as test"))
        test_value = result.fetchone()[0]
        
        # Get database version
        version_result = await db.execute(text("SELECT version()"))
        version = version_result.fetchone()[0]
        
        # Get current time
        time_result = await db.execute(text("SELECT NOW() as current_time"))
        current_time = time_result.fetchone()[0]
        
        return {
            "status": "healthy",
            "test_query": test_value,
            "version": version,
            "current_time": current_time.isoformat(),
            "database_url": settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else "hidden"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_url": settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else "hidden"
        }
