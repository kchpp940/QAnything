import time
import asyncio
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.configs.model_config import (
    MYSQL_HOST_LOCAL, MYSQL_PORT_LOCAL
)
from qanything_kernel.utils.custom_log import debug_logger


class MySQLHealthChecker(BaseHealthChecker):
    name = "mysql"
    default_timeout = 2.0

    def __init__(self, timeout: float = 2.0):
        self.timeout = min(timeout, 5.0)
        self.host = MYSQL_HOST_LOCAL
        self.port = MYSQL_PORT_LOCAL

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            try:
                data = await asyncio.wait_for(
                    reader.read(1024),
                    timeout=self.timeout
                )
                if data and len(data) >= 4:
                    latency_ms = (time.time() - start_time) * 1000
                    return self._create_health(
                        status=ServiceStatus.HEALTHY,
                        message="MySQL TCP handshake successful",
                        latency_ms=latency_ms,
                        details={
                            "host": self.host,
                            "port": self.port,
                        }
                    )
                else:
                    latency_ms = (time.time() - start_time) * 1000
                    return self._create_health(
                        status=ServiceStatus.DEGRADED,
                        message="MySQL connected but no handshake response",
                        latency_ms=latency_ms,
                        details={
                            "host": self.host,
                            "port": self.port,
                        },
                        error_type=ErrorType.BAD_RESPONSE,
                    )
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"MySQL health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"MySQL connection timeout after {self.timeout}s",
                latency_ms=latency_ms,
                details={
                    "host": self.host,
                    "port": self.port,
                    "timeout": self.timeout,
                },
                error_type=ErrorType.TIMEOUT,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            debug_logger.error(f"MySQL health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"MySQL connection failed: {str(e)}",
                latency_ms=latency_ms,
                details={
                    "host": self.host,
                    "port": self.port,
                    "error": str(e),
                },
                error_type=error_type,
            )
