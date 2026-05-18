"""
Database connection management with connection pooling.

Uses a per-database thread-safe connection pool to reuse MySQL connections,
eliminating the ~3s connection overhead to remote Alibaba Cloud database.
"""
import pymysql
import threading
from queue import Queue, Empty, Full
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from backend.database.db_config_manager import DBConfigManager


class ConnectionPool:
    """Thread-safe connection pool for a single database."""

    _pools: Dict[str, 'ConnectionPool'] = {}
    _pools_lock = threading.Lock()

    def __init__(self, config: dict, pool_size: int = 5, max_size: int = 15):
        self._config = {k: v for k, v in config.items() if not k.startswith('_')}
        self._max_size = max_size
        self._pool: Queue = Queue(maxsize=max_size)
        self._created = 0
        self._lock = threading.Lock()
        self._key = f"{config.get('host')}:{config.get('port', 3306)}/{config.get('database')}"

    @classmethod
    def get_pool(cls, config: dict, **kwargs) -> 'ConnectionPool':
        key = f"{config.get('host')}:{config.get('port', 3306)}/{config.get('database')}"
        with cls._pools_lock:
            if key not in cls._pools:
                cls._pools[key] = cls(config, **kwargs)
            return cls._pools[key]

    def acquire(self, timeout: float = 30.0) -> pymysql.Connection:
        try:
            conn = self._pool.get(block=False)
            try:
                conn.ping(reconnect=True)
                return conn
            except Exception:
                with self._lock:
                    self._created -= 1
                return self._new_conn()
        except Empty:
            with self._lock:
                if self._created < self._max_size:
                    return self._new_conn()
            return self._pool.get(block=True, timeout=timeout)

    def release(self, conn: pymysql.Connection) -> None:
        try:
            self._pool.put_nowait(conn)
        except Full:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created -= 1

    def _new_conn(self) -> pymysql.Connection:
        conn = pymysql.connect(**self._config)
        with self._lock:
            self._created += 1
        return conn


class Database:
    """Database connection handler with connection pooling."""

    def __init__(self, db_name: Optional[str] = None):
        db_configs = DBConfigManager.load_db_config()

        if not db_configs:
            raise FileNotFoundError("No database configuration found in ~/database_config.json")

        pymysql_configs = []
        for db in db_configs:
            config = {
                "host": db.get("host"),
                "user": db.get("user"),
                "password": db.get("password"),
                "database": db.get("database"),
                "port": db.get("port"),
                "charset": db.get("charset", "utf8mb4"),
                "cursorclass": pymysql.cursors.DictCursor,
            }
            config["_name"] = db.get("name")
            pymysql_configs.append(config)

        if db_name:
            matched = next(
                (cfg for cfg in pymysql_configs if db_name.lower() in cfg["_name"].lower()),
                pymysql_configs[0],
            )
        else:
            matched = pymysql_configs[0]

        self.config = {k: v for k, v in matched.items() if not k.startswith('_')}
        self._pool = ConnectionPool.get_pool(matched)

    @contextmanager
    def get_connection(self):
        conn = self._pool.acquire()
        try:
            yield conn
        finally:
            self._pool.release(conn)

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                conn.commit()
                lastrowid = cursor.lastrowid
                return lastrowid if lastrowid else affected_rows
