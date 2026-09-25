import os
from contextlib import asynccontextmanager

import asyncpg
from prometheus_client import Counter, Gauge, Histogram

DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "1"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
DB_TIMEOUT = float(os.getenv("DB_TIMEOUT", "5"))

POOL_SIZE = Gauge("db_pool_size", "Connexions ouvertes dans le pool")
POOL_IDLE = Gauge("db_pool_idle", "Connexions inactives dans le pool")
QUERY_LATENCY = Histogram("db_query_duration_seconds", "Latence des requetes", ["operation"])
QUERY_ERRORS = Counter("db_query_errors_total", "Erreurs de requete", ["operation"])


class Database:

    def __init__(self, service_name: str, logger=None):
        self.service_name = service_name
        self.logger = logger
        self.pool = None

    async def connect(self):
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL absent: le service ne peut pas demarrer")
        self.pool = await asyncpg.create_pool(
            dsn,
            min_size=DB_POOL_MIN,
            max_size=DB_POOL_MAX,
            command_timeout=DB_TIMEOUT,
        )
        if self.logger:
            self.logger.info(
                "Pool PostgreSQL ouvert (min=%s, max=%s)", DB_POOL_MIN, DB_POOL_MAX
            )
        return self.pool

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            if self.logger:
                self.logger.info("Pool PostgreSQL ferme")

    def _refresh_gauges(self):
        if self.pool:
            POOL_SIZE.set(self.pool.get_size())
            POOL_IDLE.set(self.pool.get_idle_size())

    @asynccontextmanager
    async def acquire(self, operation: str = "query"):
        self._refresh_gauges()
        with QUERY_LATENCY.labels(operation=operation).time():
            try:
                async with self.pool.acquire() as conn:
                    yield conn
            except Exception:
                QUERY_ERRORS.labels(operation=operation).inc()
                raise
            finally:
                self._refresh_gauges()

    async def fetch(self, query: str, *args, operation: str = "fetch"):
        async with self.acquire(operation) as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args, operation: str = "fetchrow"):
        async with self.acquire(operation) as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args, operation: str = "execute"):
        async with self.acquire(operation) as conn:
            return await conn.execute(query, *args)

    async def healthy(self) -> bool:
        try:
            async with self.acquire("health") as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False
