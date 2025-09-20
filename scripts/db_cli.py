#!/usr/bin/env python3
"""
EasyPay Database CLI Tool
Quick command-line interface for database operations.
"""
import asyncio
import sys
import argparse
from typing import List, Dict, Any
import json

from src.infrastructure.database import get_db_session
from sqlalchemy import text


class DatabaseCLI:
    """Command-line interface for database operations."""
    
    def __init__(self):
        self.session = None
    
    async def connect(self):
        """Connect to database."""
        try:
            async for session in get_db_session():
                self.session = session
                break
            print("✅ Connected to database")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            sys.exit(1)
    
    async def execute_query(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """Execute a SQL query."""
        try:
            # Add LIMIT if not present and it's a SELECT query
            if query.strip().upper().startswith('SELECT') and 'LIMIT' not in query.upper():
                query = f"{query} LIMIT {limit}"
            
            result = await self.session.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            
            return {
                "columns": list(columns),
                "rows": [dict(zip(columns, row)) for row in rows],
                "total_rows": len(rows),
                "query": query
            }
        except Exception as e:
            return {"error": str(e), "query": query}
    
    async def list_tables(self) -> List[Dict[str, Any]]:
        """List all database tables."""
        query = """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        result = await self.execute_query(query)
        return result.get("rows", [])
    
    async def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Describe a table structure."""
        query = f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        return await self.execute_query(query)
    
    async def get_table_stats(self) -> Dict[str, Any]:
        """Get table statistics."""
        query = """
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
        """
        return await self.execute_query(query)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            result = await self.execute_query("SELECT 1 as test, NOW() as current_time, version() as version")
            if "error" not in result:
                return {
                    "status": "healthy",
                    "test": result["rows"][0]["test"],
                    "current_time": result["rows"][0]["current_time"],
                    "version": result["rows"][0]["version"]
                }
            else:
                return {"status": "unhealthy", "error": result["error"]}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def format_output(self, data: Any, format_type: str = "table") -> str:
        """Format output data."""
        if format_type == "json":
            return json.dumps(data, indent=2, default=str)
        
        if isinstance(data, dict) and "rows" in data:
            if not data["rows"]:
                return "No rows returned"
            
            # Format as table
            columns = data["columns"]
            rows = data["rows"]
            
            # Calculate column widths
            widths = [len(col) for col in columns]
            for row in rows:
                for i, col in enumerate(columns):
                    widths[i] = max(widths[i], len(str(row.get(col, ""))))
            
            # Create header
            header = " | ".join(f"{col:<{widths[i]}}" for i, col in enumerate(columns))
            separator = "-+-".join("-" * width for width in widths)
            
            # Create rows
            formatted_rows = []
            for row in rows:
                formatted_rows.append(" | ".join(f"{str(row.get(col, '')):<{widths[i]}}" for i, col in enumerate(columns)))
            
            return f"{header}\n{separator}\n" + "\n".join(formatted_rows)
        
        return str(data)
    
    async def close(self):
        """Close database connection."""
        if self.session:
            await self.session.close()


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="EasyPay Database CLI Tool")
    parser.add_argument("command", choices=[
        "query", "tables", "describe", "stats", "health", "help"
    ], help="Command to execute")
    parser.add_argument("-q", "--query", help="SQL query to execute")
    parser.add_argument("-t", "--table", help="Table name for describe command")
    parser.add_argument("-l", "--limit", type=int, default=100, help="Row limit for queries")
    parser.add_argument("-f", "--format", choices=["table", "json"], default="table", help="Output format")
    
    args = parser.parse_args()
    
    cli = DatabaseCLI()
    
    try:
        await cli.connect()
        
        if args.command == "health":
            result = await cli.health_check()
            print(cli.format_output(result, args.format))
        
        elif args.command == "tables":
            result = await cli.list_tables()
            print(cli.format_output({"columns": ["table_name", "table_type"], "rows": result}, args.format))
        
        elif args.command == "describe":
            if not args.table:
                print("❌ Table name required for describe command")
                sys.exit(1)
            result = await cli.describe_table(args.table)
            print(cli.format_output(result, args.format))
        
        elif args.command == "stats":
            result = await cli.get_table_stats()
            print(cli.format_output(result, args.format))
        
        elif args.command == "query":
            if not args.query:
                print("❌ Query required for query command")
                sys.exit(1)
            result = await cli.execute_query(args.query, args.limit)
            print(cli.format_output(result, args.format))
        
        elif args.command == "help":
            print("""
🗄️ EasyPay Database CLI Tool

Commands:
  health     - Check database health and connectivity
  tables     - List all database tables
  describe   - Describe table structure (use -t TABLE_NAME)
  stats      - Show table statistics
  query      - Execute SQL query (use -q "SELECT ...")
  help       - Show this help message

Options:
  -q, --query    SQL query to execute
  -t, --table    Table name for describe command
  -l, --limit    Row limit for queries (default: 100)
  -f, --format   Output format: table or json (default: table)

Examples:
  python scripts/db_cli.py health
  python scripts/db_cli.py tables
  python scripts/db_cli.py describe -t payments
  python scripts/db_cli.py query -q "SELECT * FROM payments LIMIT 5"
  python scripts/db_cli.py stats -f json
            """)
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await cli.close()


if __name__ == "__main__":
    asyncio.run(main())
