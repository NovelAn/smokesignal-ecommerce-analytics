"""
Database connection management
"""
import pymysql
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from backend.database.db_config_manager import DBConfigManager


class Database:
    """Database connection handler"""

    def __init__(self, db_name: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_name: Optional database name identifier (uses 'name' field from config).
                     If None, uses first database from config.
        """
        # Load database configuration from system-level config file
        db_configs = DBConfigManager.load_db_config()

        if not db_configs:
            raise FileNotFoundError("No database configuration found in ~/database_config.json")

        # Convert to pymysql format
        pymysql_configs = []
        for db in db_configs:
            config = {
                "host": db.get("host"),
                "user": db.get("user"),
                "password": db.get("password"),
                "database": db.get("database"),
                "port": db.get("port"),
                "charset": db.get("charset", "utf8mb4"),
                "cursorclass": pymysql.cursors.DictCursor
            }
            # Add the original name for matching
            config["_name"] = db.get("name")
            pymysql_configs.append(config)

        # Use first database config (or find by name if specified)
        if db_name:
            # Try to match by name (case-insensitive, partial match)
            self.config = next(
                (cfg for cfg in pymysql_configs if db_name.lower() in cfg["_name"].lower()),
                pymysql_configs[0]
            )
        else:
            self.config = pymysql_configs[0]

        # Remove the internal name field
        self.config.pop("_name", None)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                conn.commit()
                return affected_rows
