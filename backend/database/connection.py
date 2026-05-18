"""
Database connection management with connection pooling.

Uses a per-database thread-safe connection pool to reuse MySQL connections,
eliminating the ~3s connection overhead to remote Alibaba Cloud database.
"""
import pymysql
import threading
import logging
import time
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
        self._wait_count = 0

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
                try:
                    conn.close()
                except Exception:
                    pass
                with self._lock:
                    self._created = max(0, self._created - 1)
                return self.acquire(timeout=timeout)
        except Empty:
            should_create = False
            with self._lock:
                if self._created < self._max_size:
                    self._created += 1
                    should_create = True
            if should_create:
                try:
                    return self._new_conn()
                except Exception:
                    with self._lock:
                        self._created = max(0, self._created - 1)
                    raise
            try:
                with self._lock:
                    self._wait_count += 1
                return self._pool.get(block=True, timeout=timeout)
            except Empty as exc:
                raise TimeoutError(f"MySQL connection pool exhausted after {timeout}s: {self._key}") from exc

    def release(self, conn: pymysql.Connection) -> None:
        try:
            self._pool.put_nowait(conn)
        except Full:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created = max(0, self._created - 1)

    def _new_conn(self) -> pymysql.Connection:
        start = time.time()
        logging.info("[DB] Opening new MySQL connection to %s", self._key)
        conn = pymysql.connect(**self._config)
        logging.info("[DB] MySQL connection opened in %.2fs: %s", time.time() - start, self._key)
        return conn

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            created = self._created
            wait_count = self._wait_count
        idle = self._pool.qsize()
        return {
            "key": self._key,
            "created": created,
            "idle": idle,
            "in_use": max(0, created - idle),
            "max_size": self._max_size,
            "wait_count": wait_count,
        }

    @classmethod
    def all_stats(cls) -> List[Dict[str, Any]]:
        with cls._pools_lock:
            pools = list(cls._pools.values())
        return [pool.stats() for pool in pools]


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
                "connect_timeout": int(db.get("connect_timeout", 5)),
                "read_timeout": int(db.get("read_timeout", 20)),
                "write_timeout": int(db.get("write_timeout", 20)),
                "autocommit": True,
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
        start = time.time()
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                elapsed = time.time() - start
                if elapsed > 1:
                    logging.warning("[DB] Slow query completed in %.2fs, rows=%s", elapsed, len(rows))
                else:
                    logging.debug("[DB] Query completed in %.2fs, rows=%s", elapsed, len(rows))
                return rows

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        start = time.time()
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                conn.commit()
                lastrowid = cursor.lastrowid
                elapsed = time.time() - start
                if elapsed > 1:
                    logging.warning("[DB] Slow update completed in %.2fs, affected=%s", elapsed, affected_rows)
                else:
                    logging.debug("[DB] Update completed in %.2fs, affected=%s", elapsed, affected_rows)
                return lastrowid if lastrowid else affected_rows
