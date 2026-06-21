import time
import asyncio
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.configs.model_config import MILVUS_HOST_LOCAL, MILVUS_PORT
from qanything_kernel.utils.custom_log import debug_logger


class MilvusHealthChecker(BaseHealthChecker):
    name = "milvus"
    default_timeout = 3.0

    def __init__(self, timeout: float = 3.0):
        self.timeout = min(timeout, 5.0)
        self.host = MILVUS_HOST_LOCAL
        self.port = MILVUS_PORT

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            try:
                latency_ms = (time.time() - start_time) * 1000
                return self._create_health(
                    status=ServiceStatus.HEALTHY,
                    message="Milvus TCP connection successful",
                    latency_ms=latency_ms,
                    details={
                        "host": self.host,
                        "port": self.port,
                    }
                )
            finally:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Milvus health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Milvus connection timeout after {self.timeout}s",
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
            debug_logger.error(f"Milvus health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Milvus connection failed: {str(e)}",
                latency_ms=latency_ms,
                details={
                    "host": self.host,
                    "port": self.port,
                    "error": str(e),
                },
                error_type=error_type,
            )
