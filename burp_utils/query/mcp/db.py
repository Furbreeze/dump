import sqlite3
import asyncio
from typing import List, Dict, Any, Optional, Union
from fastmcp import FastMCP

class SQLiteHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        try:
            self.db = sqlite3.connect(db_path, check_same_thread=False)
            self.db.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Error opening database: {e}")
            raise
    
    async def execute_query(self, sql: str, values: List[Any] = None) -> List[Dict[str, Any]]:
        if values is None:
            values = []
        
        try:
            cursor = self.db.cursor()
            cursor.execute(sql, values)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise e
    
    async def execute_run(self, sql: str, values: List[Any] = None) -> Dict[str, Union[int, None]]:
        if values is None:
            values = []
        
        try:
            cursor = self.db.cursor()
            cursor.execute(sql, values)
            self.db.commit()
            
            return {
                'lastID': cursor.lastrowid,
                'changes': cursor.rowcount
            }
        except sqlite3.Error as e:
            self.db.rollback()
            raise e
    
    async def list_tables(self) -> List[Dict[str, Any]]:
        return await self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        return await self.execute_query(f"PRAGMA table_info({table_name})")
    
    def close(self):
        if self.db:
            self.db.close()

# Initialize FastMCP server
mcp = FastMCP("SQLite Database Handler")

# Default database handler
DB_PATH = "./test.db"
db_handler = SQLiteHandler(DB_PATH)

# Dictionary to manage multiple database connections
db_connections = {}

def get_db_handler(db_path: str = None) -> SQLiteHandler:
    """Get database handler for the specified path or default"""
    if db_path is None:
        return db_handler
    
    if db_path not in db_connections:
        db_connections[db_path] = SQLiteHandler(db_path)
    
    return db_connections[db_path]

@mcp.tool()
async def connect_to_database(db_path: str) -> Dict[str, str]:
    """
    Connect to a SQLite database at the specified file path.
    
    Args:
        db_path: Path to the SQLite database file
    
    Returns:
        Dictionary with connection status and database path
    """
    try:
        # Test the connection by creating a handler
        test_handler = SQLiteHandler(db_path)
        
        # Store the connection for future use
        db_connections[db_path] = test_handler
        
        return {
            "status": "connected",
            "database_path": db_path,
            "message": f"Successfully connected to database at {db_path}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "database_path": db_path,
            "message": f"Failed to connect to database: {str(e)}"
        }

@mcp.tool()
async def execute_query(sql: str, values: Optional[List[Any]] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query on the SQLite database.
    
    Args:
        sql: The SQL SELECT query to execute
        values: Optional list of parameter values for the query
        db_path: Optional path to specific database file (uses default if not provided)
    
    Returns:
        List of dictionaries representing the query results
    """
    try:
        handler = get_db_handler(db_path)
        return await handler.execute_query(sql, values or [])
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")

@mcp.tool()
async def execute_update(sql: str, values: Optional[List[Any]] = None, db_path: Optional[str] = None) -> Dict[str, Union[int, None]]:
    """
    Execute an INSERT, UPDATE, or DELETE query on the SQLite database.
    
    Args:
        sql: The SQL query to execute (INSERT, UPDATE, DELETE)
        values: Optional list of parameter values for the query
        db_path: Optional path to specific database file (uses default if not provided)
    
    Returns:
        Dictionary with 'lastID' and 'changes' information
    """
    try:
        handler = get_db_handler(db_path)
        return await handler.execute_run(sql, values or [])
    except Exception as e:
        raise Exception(f"Update execution failed: {str(e)}")

@mcp.tool()
async def list_tables(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all user tables in the SQLite database.
    
    Args:
        db_path: Optional path to specific database file (uses default if not provided)
    
    Returns:
        List of dictionaries with table names
    """
    try:
        handler = get_db_handler(db_path)
        return await handler.list_tables()
    except Exception as e:
        raise Exception(f"Failed to list tables: {str(e)}")

@mcp.tool()
async def get_table_schema(table_name: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get the schema information for a specific table.
    
    Args:
        table_name: Name of the table to get schema for
        db_path: Optional path to specific database file (uses default if not provided)
    
    Returns:
        List of dictionaries with column information
    """
    try:
        handler = get_db_handler(db_path)
        return await handler.get_table_schema(table_name)
    except Exception as e:
        raise Exception(f"Failed to get table schema: {str(e)}")

@mcp.tool()
async def describe_database(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Get a comprehensive description of the database structure.
    
    Args:
        db_path: Optional path to specific database file (uses default if not provided)
    
    Returns:
        Dictionary containing all tables and their schemas
    """
    try:
        handler = get_db_handler(db_path)
        current_path = db_path or DB_PATH
        
        tables = await handler.list_tables()
        database_info = {
            "database_path": current_path,
            "tables": {}
        }
        
        for table in tables:
            table_name = table['name']
            schema = await handler.get_table_schema(table_name)
            database_info["tables"][table_name] = {
                "columns": schema,
                "column_count": len(schema)
            }
        
        database_info["table_count"] = len(tables)
        return database_info
    except Exception as e:
        raise Exception(f"Failed to describe database: {str(e)}")

@mcp.tool()
async def run_safe_query(table_name: str, limit: int = 10, where_clause: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Run a safe SELECT query with built-in protections.
    
    Args:
        table_name: Name of the table to query
        limit: Maximum number of rows to return (default: 10, max: 1000)
        where_clause: Optional WHERE clause (without the WHERE keyword)
        db_path: Optional path to specific database file (uses default if not provided)
    
    Returns:
        List of dictionaries representing the query results
    """
    try:
        # Validate limit
        limit = min(max(1, limit), 1000)
        
        # Build safe query
        if where_clause:
            # Basic validation - in production you'd want more sophisticated sanitization
            if any(dangerous in where_clause.upper() for dangerous in ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER']):
                raise ValueError("WHERE clause contains potentially dangerous keywords")
            sql = f"SELECT * FROM {table_name} WHERE {where_clause} LIMIT {limit}"
        else:
            sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        
        handler = get_db_handler(db_path)
        return await handler.execute_query(sql)
    except Exception as e:
        raise Exception(f"Safe query failed: {str(e)}")

@mcp.tool()
async def list_connected_databases() -> Dict[str, Any]:
    """
    List all currently connected databases.
    
    Returns:
        Dictionary with information about connected databases
    """
    try:
        connected_dbs = {
            "default_database": DB_PATH,
            "additional_connections": list(db_connections.keys()),
            "total_connections": len(db_connections) + 1  # +1 for default
        }
        return connected_dbs
    except Exception as e:
        raise Exception(f"Failed to list connected databases: {str(e)}")

# Cleanup function to close all database connections
def cleanup():
    db_handler.close()
    for handler in db_connections.values():
        handler.close()

if __name__ == "__main__":
    import atexit
    atexit.register(cleanup)
    
    # Run the MCP server
    mcp.run()
