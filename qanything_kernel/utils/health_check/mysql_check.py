import time
import asyncio
from qanything_kernel.utils.health_check.base import BaseHealthChecker, ServiceStatus, DependencyHealth
from qanything_kernel.configs.model_config import (
    MYSQL_HOST_LOCAL, MYSQL_PORT_LOCAL, MYSQL_USER_LOCAL,
    MYSQL_PASSWORD_LOCAL, MYSQL_DATABASE_LOCAL
)
from qanything_kernel.utils.custom_log import debug_logger


class MySQLHealthChecker(BaseHealthChecker):
    name = "mysql"

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.host = MYSQL_HOST_LOCAL
        self.port = MYSQL_PORT_LOCAL
        self.user = MYSQL_USER_LOCAL
        self.database = MYSQL_DATABASE_LOCAL

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            import aiomysql

            async def _check():
                conn = await aiomysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=MYSQL_PASSWORD_LOCAL,
                    db=self.database,
                    connect_timeout=self.timeout,
                )
                try:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1")
                        await cur.fetchone()
                finally:
                    conn.close()

            await asyncio.wait_for(_check(), timeout=self.timeout)

            latency_ms = (time.time() - start_time) * 1000
            return self._create_health(
                status=ServiceStatus.HEALTHY,
                message="MySQL connection is healthy",
                latency_ms=round(latency_ms, 2),
                details={
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                }
            )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"MySQL health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"MySQL connection timeout",
                latency_ms=round(latency_ms, 2),
                details={
                    "host": self.host,
                    "port": self.port,
                    "timeout": self.timeout,
                }
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"MySQL health check failed: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"MySQL connection failed: {str(e)}",
                latency_ms=round(latency_ms, 2),
                details={
                    "host": self.host,
                    "port": self.port,
                    "error": str(e),
                }
            )
