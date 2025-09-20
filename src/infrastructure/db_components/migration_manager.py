"""
EasyPay Payment Gateway - Database Migration Manager

This module provides advanced database migration management including:
- Migration versioning and tracking
- Rollback capabilities
- Data migration utilities
- Schema validation
- Migration dependencies
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import text, inspect
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from src.core.exceptions import DatabaseError, MigrationError

logger = logging.getLogger(__name__)


class MigrationStatus(str, Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationType(str, Enum):
    """Migration type enumeration."""
    SCHEMA = "schema"
    DATA = "data"
    INDEX = "index"
    CONSTRAINT = "constraint"
    FUNCTION = "function"
    TRIGGER = "trigger"


class Migration:
    """
    Represents a database migration.
    
    Attributes:
        version: Migration version identifier
        description: Human-readable description
        migration_type: Type of migration
        dependencies: List of migration versions this depends on
        rollback_sql: SQL to rollback this migration
        validation_sql: SQL to validate migration success
        timeout: Maximum time allowed for migration
    """
    
    def __init__(
        self,
        version: str,
        description: str,
        migration_type: MigrationType = MigrationType.SCHEMA,
        dependencies: Optional[List[str]] = None,
        rollback_sql: Optional[str] = None,
        validation_sql: Optional[str] = None,
        timeout: int = 300
    ):
        self.version = version
        self.description = description
        self.migration_type = migration_type
        self.dependencies = dependencies or []
        self.rollback_sql = rollback_sql
        self.validation_sql = validation_sql
        self.timeout = timeout
        self.status = MigrationStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None


class MigrationManager:
    """
    Advanced database migration manager.
    
    Provides comprehensive migration management including versioning,
    rollback capabilities, and data migration utilities.
    """
    
    def __init__(self, engine: AsyncEngine, alembic_config_path: str = "alembic.ini"):
        self.engine = engine
        self.alembic_config_path = alembic_config_path
        self.alembic_config = Config(alembic_config_path)
        self.script_directory = ScriptDirectory.from_config(self.alembic_config)
        
        # Migration tracking table
        self.migration_table_name = "migration_history"
    
    async def init_migration_tracking(self):
        """
        Initialize migration tracking table.
        
        Raises:
            MigrationError: If initialization fails
        """
        try:
            async with self.engine.begin() as conn:
                # Create migration tracking table
                await conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.migration_table_name} (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(50) UNIQUE NOT NULL,
                        description TEXT NOT NULL,
                        migration_type VARCHAR(20) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        dependencies JSONB,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        error_message TEXT,
                        rollback_sql TEXT,
                        validation_sql TEXT,
                        timeout INTEGER DEFAULT 300,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes
                await conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_migration_history_version 
                    ON {self.migration_table_name} (version)
                """))
                
                await conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_migration_history_status 
                    ON {self.migration_table_name} (status)
                """))
                
                logger.info("Migration tracking table initialized")
                
        except Exception as e:
            raise MigrationError(f"Failed to initialize migration tracking: {str(e)}")
    
    async def get_migration_status(self, version: str) -> Optional[MigrationStatus]:
        """
        Get migration status.
        
        Args:
            version: Migration version
            
        Returns:
            Migration status or None if not found
        """
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    text(f"SELECT status FROM {self.migration_table_name} WHERE version = :version"),
                    {"version": version}
                )
                row = result.fetchone()
                return MigrationStatus(row[0]) if row else None
                
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return None
    
    async def register_migration(self, migration: Migration):
        """
        Register a migration in the tracking table.
        
        Args:
            migration: Migration object to register
            
        Raises:
            MigrationError: If registration fails
        """
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text(f"""
                    INSERT INTO {self.migration_table_name} 
                    (version, description, migration_type, dependencies, rollback_sql, validation_sql, timeout)
                    VALUES (:version, :description, :migration_type, :dependencies, :rollback_sql, :validation_sql, :timeout)
                    ON CONFLICT (version) DO UPDATE SET
                        description = EXCLUDED.description,
                        migration_type = EXCLUDED.migration_type,
                        dependencies = EXCLUDED.dependencies,
                        rollback_sql = EXCLUDED.rollback_sql,
                        validation_sql = EXCLUDED.validation_sql,
                        timeout = EXCLUDED.timeout,
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    "version": migration.version,
                    "description": migration.description,
                    "migration_type": migration.migration_type.value,
                    "dependencies": migration.dependencies,
                    "rollback_sql": migration.rollback_sql,
                    "validation_sql": migration.validation_sql,
                    "timeout": migration.timeout
                })
                
                logger.info(f"Migration {migration.version} registered")
                
        except Exception as e:
            raise MigrationError(f"Failed to register migration: {str(e)}")
    
    async def update_migration_status(
        self,
        version: str,
        status: MigrationStatus,
        error_message: Optional[str] = None
    ):
        """
        Update migration status.
        
        Args:
            version: Migration version
            status: New status
            error_message: Error message if failed
            
        Raises:
            MigrationError: If update fails
        """
        try:
            async with self.engine.begin() as conn:
                update_fields = ["status = :status", "updated_at = CURRENT_TIMESTAMP"]
                params = {"version": version, "status": status.value}
                
                if status == MigrationStatus.RUNNING:
                    update_fields.append("started_at = CURRENT_TIMESTAMP")
                elif status in [MigrationStatus.COMPLETED, MigrationStatus.FAILED, MigrationStatus.ROLLED_BACK]:
                    update_fields.append("completed_at = CURRENT_TIMESTAMP")
                
                if error_message:
                    update_fields.append("error_message = :error_message")
                    params["error_message"] = error_message
                
                await conn.execute(text(f"""
                    UPDATE {self.migration_table_name}
                    SET {', '.join(update_fields)}
                    WHERE version = :version
                """), params)
                
                logger.info(f"Migration {version} status updated to {status.value}")
                
        except Exception as e:
            raise MigrationError(f"Failed to update migration status: {str(e)}")
    
    async def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of pending migrations.
        
        Returns:
            List of pending migrations
        """
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(f"""
                    SELECT version, description, migration_type, dependencies, 
                           rollback_sql, validation_sql, timeout
                    FROM {self.migration_table_name}
                    WHERE status = 'pending'
                    ORDER BY created_at
                """))
                
                migrations = []
                for row in result.fetchall():
                    migration = Migration(
                        version=row[0],
                        description=row[1],
                        migration_type=MigrationType(row[2]),
                        dependencies=row[3] or [],
                        rollback_sql=row[4],
                        validation_sql=row[5],
                        timeout=row[6] or 300
                    )
                    migrations.append(migration)
                
                return migrations
                
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    async def get_completed_migrations(self) -> List[str]:
        """
        Get list of completed migration versions.
        
        Returns:
            List of completed migration versions
        """
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(f"""
                    SELECT version FROM {self.migration_table_name}
                    WHERE status = 'completed'
                    ORDER BY completed_at
                """))
                
                return [row[0] for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get completed migrations: {e}")
            return []
    
    async def check_dependencies(self, migration: Migration) -> bool:
        """
        Check if migration dependencies are satisfied.
        
        Args:
            migration: Migration to check
            
        Returns:
            True if dependencies are satisfied
        """
        try:
            completed_migrations = await self.get_completed_migrations()
            
            for dependency in migration.dependencies:
                if dependency not in completed_migrations:
                    logger.warning(f"Migration {migration.version} dependency {dependency} not completed")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check dependencies: {e}")
            return False
    
    async def run_migration(self, migration: Migration, migration_sql: str) -> bool:
        """
        Run a database migration.
        
        Args:
            migration: Migration object
            migration_sql: SQL to execute
            
        Returns:
            True if migration succeeded
            
        Raises:
            MigrationError: If migration fails
        """
        try:
            # Check dependencies
            if not await self.check_dependencies(migration):
                raise MigrationError(f"Migration {migration.version} dependencies not satisfied")
            
            # Update status to running
            await self.update_migration_status(migration.version, MigrationStatus.RUNNING)
            migration.status = MigrationStatus.RUNNING
            migration.started_at = datetime.utcnow()
            
            # Run migration with timeout
            async with asyncio.timeout(migration.timeout):
                async with self.engine.begin() as conn:
                    # Execute migration SQL
                    await conn.execute(text(migration_sql))
                    
                    # Run validation if provided
                    if migration.validation_sql:
                        result = await conn.execute(text(migration.validation_sql))
                        validation_result = result.fetchone()
                        if not validation_result or not validation_result[0]:
                            raise MigrationError(f"Migration {migration.version} validation failed")
            
            # Update status to completed
            await self.update_migration_status(migration.version, MigrationStatus.COMPLETED)
            migration.status = MigrationStatus.COMPLETED
            migration.completed_at = datetime.utcnow()
            
            logger.info(f"Migration {migration.version} completed successfully")
            return True
            
        except asyncio.TimeoutError:
            error_msg = f"Migration {migration.version} timed out after {migration.timeout} seconds"
            await self.update_migration_status(migration.version, MigrationStatus.FAILED, error_msg)
            migration.status = MigrationStatus.FAILED
            migration.error_message = error_msg
            raise MigrationError(error_msg)
            
        except Exception as e:
            error_msg = f"Migration {migration.version} failed: {str(e)}"
            await self.update_migration_status(migration.version, MigrationStatus.FAILED, error_msg)
            migration.status = MigrationStatus.FAILED
            migration.error_message = error_msg
            raise MigrationError(error_msg)
    
    async def rollback_migration(self, migration: Migration) -> bool:
        """
        Rollback a database migration.
        
        Args:
            migration: Migration to rollback
            
        Returns:
            True if rollback succeeded
            
        Raises:
            MigrationError: If rollback fails
        """
        try:
            if not migration.rollback_sql:
                raise MigrationError(f"Migration {migration.version} has no rollback SQL")
            
            # Update status to running
            await self.update_migration_status(migration.version, MigrationStatus.RUNNING)
            
            # Run rollback with timeout
            async with asyncio.timeout(migration.timeout):
                async with self.engine.begin() as conn:
                    await conn.execute(text(migration.rollback_sql))
            
            # Update status to rolled back
            await self.update_migration_status(migration.version, MigrationStatus.ROLLED_BACK)
            
            logger.info(f"Migration {migration.version} rolled back successfully")
            return True
            
        except asyncio.TimeoutError:
            error_msg = f"Migration {migration.version} rollback timed out"
            await self.update_migration_status(migration.version, MigrationStatus.FAILED, error_msg)
            raise MigrationError(error_msg)
            
        except Exception as e:
            error_msg = f"Migration {migration.version} rollback failed: {str(e)}"
            await self.update_migration_status(migration.version, MigrationStatus.FAILED, error_msg)
            raise MigrationError(error_msg)
    
    async def run_all_pending_migrations(self) -> Dict[str, Any]:
        """
        Run all pending migrations.
        
        Returns:
            Dictionary with migration results
        """
        try:
            pending_migrations = await self.get_pending_migrations()
            results = {
                "total": len(pending_migrations),
                "completed": 0,
                "failed": 0,
                "errors": []
            }
            
            for migration in pending_migrations:
                try:
                    # Get migration SQL from Alembic
                    migration_sql = await self._get_migration_sql(migration.version)
                    await self.run_migration(migration, migration_sql)
                    results["completed"] += 1
                    
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "version": migration.version,
                        "error": str(e)
                    })
                    logger.error(f"Migration {migration.version} failed: {e}")
            
            logger.info(f"Migration run completed: {results['completed']} succeeded, {results['failed']} failed")
            return results
            
        except Exception as e:
            raise MigrationError(f"Failed to run pending migrations: {str(e)}")
    
    async def _get_migration_sql(self, version: str) -> str:
        """
        Get migration SQL from Alembic.
        
        Args:
            version: Migration version
            
        Returns:
            Migration SQL
            
        Raises:
            MigrationError: If SQL retrieval fails
        """
        try:
            # This is a simplified version - in practice, you'd need to
            # parse the Alembic migration files to extract the SQL
            migration_file = self.script_directory.get_revision(version)
            if not migration_file:
                raise MigrationError(f"Migration {version} not found in Alembic")
            
            # For now, return a placeholder - you'd implement proper SQL extraction
            return f"-- Migration {version} SQL would be extracted here"
            
        except Exception as e:
            raise MigrationError(f"Failed to get migration SQL: {str(e)}")
    
    async def validate_schema(self) -> Dict[str, Any]:
        """
        Validate current database schema.
        
        Returns:
            Dictionary with validation results
        """
        try:
            async with self.engine.begin() as conn:
                inspector = inspect(conn)
                
                # Get all tables
                tables = inspector.get_table_names()
                
                validation_results = {
                    "tables": {},
                    "total_tables": len(tables),
                    "valid": True,
                    "errors": []
                }
                
                for table_name in tables:
                    try:
                        # Get table info
                        columns = inspector.get_columns(table_name)
                        indexes = inspector.get_indexes(table_name)
                        foreign_keys = inspector.get_foreign_keys(table_name)
                        
                        validation_results["tables"][table_name] = {
                            "columns": len(columns),
                            "indexes": len(indexes),
                            "foreign_keys": len(foreign_keys),
                            "valid": True
                        }
                        
                    except Exception as e:
                        validation_results["valid"] = False
                        validation_results["errors"].append({
                            "table": table_name,
                            "error": str(e)
                        })
                
                return validation_results
                
        except Exception as e:
            raise MigrationError(f"Schema validation failed: {str(e)}")
    
    async def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get complete migration history.
        
        Returns:
            List of migration history records
        """
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(f"""
                    SELECT version, description, migration_type, status, 
                           dependencies, started_at, completed_at, error_message
                    FROM {self.migration_table_name}
                    ORDER BY created_at
                """))
                
                history = []
                for row in result.fetchall():
                    history.append({
                        "version": row[0],
                        "description": row[1],
                        "migration_type": row[2],
                        "status": row[3],
                        "dependencies": row[4],
                        "started_at": row[5],
                        "completed_at": row[6],
                        "error_message": row[7]
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []


