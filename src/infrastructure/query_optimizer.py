"""
EasyPay Payment Gateway - Database Query Optimizer

This module provides database query optimization, indexing strategies,
and query performance monitoring.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select

from src.core.exceptions import DatabaseError


class IndexType(Enum):
    """Types of database indexes."""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    BRIN = "brin"


@dataclass
class IndexDefinition:
    """Definition of a database index."""
    name: str
    table: str
    columns: List[str]
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    partial: Optional[str] = None  # WHERE clause for partial index
    include: Optional[List[str]] = None  # INCLUDE columns for covering index


@dataclass
class QueryMetrics:
    """Metrics for query performance."""
    query_id: str
    query_text: str
    execution_time: float
    rows_returned: int
    rows_examined: int
    index_used: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class QueryOptimizer:
    """Database query optimizer with performance monitoring."""
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        self.query_metrics: List[QueryMetrics] = []
        self.slow_query_threshold = 1.0  # seconds
        
        # Predefined indexes for common queries
        self.recommended_indexes = [
            # Payment table indexes
            IndexDefinition("idx_payments_customer_id", "payments", ["customer_id"]),
            IndexDefinition("idx_payments_status", "payments", ["status"]),
            IndexDefinition("idx_payments_created_at", "payments", ["created_at"]),
            IndexDefinition("idx_payments_external_id", "payments", ["external_id"], unique=True),
            IndexDefinition("idx_payments_authnet_id", "payments", ["authorize_net_transaction_id"]),
            IndexDefinition("idx_payments_customer_status", "payments", ["customer_id", "status"]),
            IndexDefinition("idx_payments_status_created", "payments", ["status", "created_at"]),
            
            # Webhook table indexes
            IndexDefinition("idx_webhooks_event_type", "webhooks", ["event_type"]),
            IndexDefinition("idx_webhooks_status", "webhooks", ["status"]),
            IndexDefinition("idx_webhooks_created_at", "webhooks", ["created_at"]),
            IndexDefinition("idx_webhooks_external_id", "webhooks", ["external_id"], unique=True),
            IndexDefinition("idx_webhooks_next_retry", "webhooks", ["next_retry_at"]),
            IndexDefinition("idx_webhooks_status_retry", "webhooks", ["status", "next_retry_at"]),
            
            # Audit log table indexes
            IndexDefinition("idx_audit_logs_user_id", "audit_logs", ["user_id"]),
            IndexDefinition("idx_audit_logs_action", "audit_logs", ["action"]),
            IndexDefinition("idx_audit_logs_resource", "audit_logs", ["resource", "resource_id"]),
            IndexDefinition("idx_audit_logs_created_at", "audit_logs", ["created_at"]),
            IndexDefinition("idx_audit_logs_user_action", "audit_logs", ["user_id", "action"]),
        ]
    
    async def create_recommended_indexes(self) -> Dict[str, Any]:
        """Create all recommended indexes."""
        
        results = {
            "created": [],
            "skipped": [],
            "errors": []
        }
        
        for index_def in self.recommended_indexes:
            try:
                await self._create_index(index_def)
                results["created"].append(index_def.name)
                self.logger.info(f"Created index: {index_def.name}")
                
            except Exception as e:
                if "already exists" in str(e).lower():
                    results["skipped"].append(index_def.name)
                    self.logger.info(f"Index already exists: {index_def.name}")
                else:
                    results["errors"].append({"index": index_def.name, "error": str(e)})
                    self.logger.error(f"Failed to create index {index_def.name}: {e}")
        
        return results
    
    async def _create_index(self, index_def: IndexDefinition):
        """Create a single index."""
        
        # Build index creation SQL
        sql_parts = ["CREATE"]
        
        if index_def.unique:
            sql_parts.append("UNIQUE")
        
        sql_parts.append("INDEX")
        sql_parts.append(f'"{index_def.name}"')
        sql_parts.append("ON")
        sql_parts.append(f'"{index_def.table}"')
        
        # Add index type
        if index_def.index_type != IndexType.BTREE:
            sql_parts.append(f"USING {index_def.index_type.value}")
        
        # Add columns
        columns = [f'"{col}"' for col in index_def.columns]
        sql_parts.append(f"({', '.join(columns)})")
        
        # Add partial condition
        if index_def.partial:
            sql_parts.append(f"WHERE {index_def.partial}")
        
        # Add include columns
        if index_def.include:
            include_cols = [f'"{col}"' for col in index_def.include]
            sql_parts.append(f"INCLUDE ({', '.join(include_cols)})")
        
        sql = " ".join(sql_parts)
        
        async with self.engine.begin() as conn:
            await conn.execute(text(sql))
    
    async def analyze_query_performance(self, query_text: str) -> Dict[str, Any]:
        """Analyze query performance using EXPLAIN ANALYZE."""
        
        try:
            async with self.engine.begin() as conn:
                # Get query plan
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query_text}"
                result = await conn.execute(text(explain_query))
                plan = result.fetchone()[0]
                
                # Extract performance metrics
                execution_time = plan[0]["Execution Time"]
                planning_time = plan[0]["Planning Time"]
                total_time = execution_time + planning_time
                
                # Analyze plan for optimization opportunities
                optimization_suggestions = self._analyze_query_plan(plan[0])
                
                return {
                    "execution_time": execution_time,
                    "planning_time": planning_time,
                    "total_time": total_time,
                    "query_plan": plan,
                    "optimization_suggestions": optimization_suggestions
                }
                
        except Exception as e:
            raise DatabaseError(f"Failed to analyze query performance: {str(e)}")
    
    def _analyze_query_plan(self, plan: Dict[str, Any]) -> List[str]:
        """Analyze query plan for optimization opportunities."""
        
        suggestions = []
        
        # Check for sequential scans
        if self._has_sequential_scan(plan):
            suggestions.append("Consider adding an index to avoid sequential scan")
        
        # Check for nested loops
        if self._has_nested_loop(plan):
            suggestions.append("Consider optimizing join conditions or adding indexes")
        
        # Check for high cost operations
        if plan.get("Total Cost", 0) > 1000:
            suggestions.append("Query has high cost - consider optimization")
        
        # Check for missing indexes
        if self._has_missing_indexes(plan):
            suggestions.append("Consider adding indexes for better performance")
        
        return suggestions
    
    def _has_sequential_scan(self, plan: Dict[str, Any]) -> bool:
        """Check if plan contains sequential scans."""
        
        if plan.get("Node Type") == "Seq Scan":
            return True
        
        for child in plan.get("Plans", []):
            if self._has_sequential_scan(child):
                return True
        
        return False
    
    def _has_nested_loop(self, plan: Dict[str, Any]) -> bool:
        """Check if plan contains nested loops."""
        
        if plan.get("Node Type") == "Nested Loop":
            return True
        
        for child in plan.get("Plans", []):
            if self._has_nested_loop(child):
                return True
        
        return False
    
    def _has_missing_indexes(self, plan: Dict[str, Any]) -> bool:
        """Check if plan suggests missing indexes."""
        
        # This is a simplified check - in practice, you'd analyze the plan more thoroughly
        return "Seq Scan" in str(plan)
    
    async def optimize_query(self, query_text: str) -> str:
        """Optimize a query by rewriting it."""
        
        # This is a simplified optimizer - in practice, you'd implement more sophisticated logic
        
        # Remove unnecessary SELECT *
        if "SELECT *" in query_text.upper():
            self.logger.warning("Query uses SELECT * - consider specifying columns")
        
        # Check for missing WHERE clauses
        if "SELECT" in query_text.upper() and "WHERE" not in query_text.upper():
            self.logger.warning("Query lacks WHERE clause - may return large result set")
        
        # Check for inefficient joins
        if "JOIN" in query_text.upper():
            self.logger.info("Query contains JOINs - ensure proper indexing")
        
        return query_text
    
    async def get_slow_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get the slowest queries from metrics."""
        
        slow_queries = [
            metric for metric in self.query_metrics
            if metric.execution_time > self.slow_query_threshold
        ]
        
        # Sort by execution time (descending)
        slow_queries.sort(key=lambda x: x.execution_time, reverse=True)
        
        return slow_queries[:limit]
    
    async def get_query_statistics(self) -> Dict[str, Any]:
        """Get overall query statistics."""
        
        if not self.query_metrics:
            return {
                "total_queries": 0,
                "average_execution_time": 0,
                "slow_queries_count": 0,
                "slow_query_threshold": self.slow_query_threshold
            }
        
        total_queries = len(self.query_metrics)
        total_time = sum(metric.execution_time for metric in self.query_metrics)
        average_time = total_time / total_queries
        slow_queries_count = len([
            metric for metric in self.query_metrics
            if metric.execution_time > self.slow_query_threshold
        ])
        
        return {
            "total_queries": total_queries,
            "average_execution_time": average_time,
            "slow_queries_count": slow_queries_count,
            "slow_query_threshold": self.slow_query_threshold,
            "total_execution_time": total_time
        }
    
    def record_query_metrics(self, metrics: QueryMetrics):
        """Record query performance metrics."""
        
        self.query_metrics.append(metrics)
        
        # Keep only recent metrics (last 1000 queries)
        if len(self.query_metrics) > 1000:
            self.query_metrics = self.query_metrics[-1000:]
        
        # Log slow queries
        if metrics.execution_time > self.slow_query_threshold:
            self.logger.warning(
                f"Slow query detected: {metrics.execution_time:.3f}s - {metrics.query_text[:100]}..."
            )


class QueryBuilder:
    """Helper class for building optimized queries."""
    
    @staticmethod
    def build_payment_query(
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Select:
        """Build an optimized payment query."""
        
        from src.core.models.payment import Payment
        
        query = Payment.query
        
        # Add filters with proper indexing
        conditions = []
        
        if customer_id:
            conditions.append(Payment.customer_id == customer_id)
        
        if status:
            conditions.append(Payment.status == status)
        
        if start_date:
            conditions.append(Payment.created_at >= start_date)
        
        if end_date:
            conditions.append(Payment.created_at <= end_date)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        # Add ordering and pagination
        query = query.order_by(Payment.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query
    
    @staticmethod
    def build_webhook_query(
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Select:
        """Build an optimized webhook query."""
        
        from src.core.models.webhook import Webhook
        
        query = Webhook.query
        
        # Add filters with proper indexing
        conditions = []
        
        if event_type:
            conditions.append(Webhook.event_type == event_type)
        
        if status:
            conditions.append(Webhook.status == status)
        
        if start_date:
            conditions.append(Webhook.created_at >= start_date)
        
        if end_date:
            conditions.append(Webhook.created_at <= end_date)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        # Add ordering and pagination
        query = query.order_by(Webhook.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query
    
    @staticmethod
    def build_audit_log_query(
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Select:
        """Build an optimized audit log query."""
        
        from src.core.models.audit_log import AuditLog
        
        query = AuditLog.query
        
        # Add filters with proper indexing
        conditions = []
        
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        
        if action:
            conditions.append(AuditLog.action == action)
        
        if resource:
            conditions.append(AuditLog.resource == resource)
        
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        # Add ordering and pagination
        query = query.order_by(AuditLog.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query


class DatabaseMaintenance:
    """Database maintenance tasks for optimization."""
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.logger = logging.getLogger(__name__)
    
    async def analyze_tables(self) -> Dict[str, Any]:
        """Run ANALYZE on all tables to update statistics."""
        
        try:
            async with self.engine.begin() as conn:
                # Get all table names
                result = await conn.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """))
                tables = [row[0] for row in result.fetchall()]
                
                # Analyze each table
                for table in tables:
                    await conn.execute(text(f"ANALYZE \"{table}\""))
                    self.logger.info(f"Analyzed table: {table}")
                
                return {"analyzed_tables": tables}
                
        except Exception as e:
            raise DatabaseError(f"Failed to analyze tables: {str(e)}")
    
    async def vacuum_tables(self, full: bool = False) -> Dict[str, Any]:
        """Run VACUUM on all tables."""
        
        try:
            async with self.engine.begin() as conn:
                # Get all table names
                result = await conn.execute(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """))
                tables = [row[0] for row in result.fetchall()]
                
                # Vacuum each table
                vacuum_type = "VACUUM FULL" if full else "VACUUM"
                for table in tables:
                    await conn.execute(text(f"{vacuum_type} \"{table}\""))
                    self.logger.info(f"Vacuumed table: {table}")
                
                return {"vacuumed_tables": tables, "full_vacuum": full}
                
        except Exception as e:
            raise DatabaseError(f"Failed to vacuum tables: {str(e)}")
    
    async def reindex_tables(self) -> Dict[str, Any]:
        """Rebuild all indexes."""
        
        try:
            async with self.engine.begin() as conn:
                # Get all index names
                result = await conn.execute(text("""
                    SELECT indexname FROM pg_indexes 
                    WHERE schemaname = 'public'
                """))
                indexes = [row[0] for row in result.fetchall()]
                
                # Reindex each index
                for index in indexes:
                    await conn.execute(text(f"REINDEX INDEX \"{index}\""))
                    self.logger.info(f"Reindexed: {index}")
                
                return {"reindexed": indexes}
                
        except Exception as e:
            raise DatabaseError(f"Failed to reindex tables: {str(e)}")
    
    async def get_table_statistics(self) -> Dict[str, Any]:
        """Get table statistics and sizes."""
        
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """))
                
                tables = []
                for row in result.fetchall():
                    tables.append({
                        "schema": row[0],
                        "table": row[1],
                        "size": row[2],
                        "size_bytes": row[3]
                    })
                
                return {"tables": tables}
                
        except Exception as e:
            raise DatabaseError(f"Failed to get table statistics: {str(e)}")


# Global query optimizer instance
_query_optimizer: Optional[QueryOptimizer] = None


def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer instance."""
    global _query_optimizer
    
    if _query_optimizer is None:
        from src.infrastructure.database import async_engine
        _query_optimizer = QueryOptimizer(async_engine)
    
    return _query_optimizer


async def init_query_optimization(engine: AsyncEngine) -> QueryOptimizer:
    """Initialize query optimization system."""
    global _query_optimizer
    
    _query_optimizer = QueryOptimizer(engine)
    
    # Create recommended indexes
    await _query_optimizer.create_recommended_indexes()
    
    logging.getLogger(__name__).info("Query optimization system initialized")
    
    return _query_optimizer
