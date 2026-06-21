import time
import asyncio
from qanything_kernel.utils.health_check.base import BaseHealthChecker, ServiceStatus, DependencyHealth
from qanything_kernel.configs.model_config import MILVUS_HOST_LOCAL, MILVUS_PORT
from qanything_kernel.utils.custom_log import debug_logger


class MilvusHealthChecker(BaseHealthChecker):
    name = "milvus"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.host = MILVUS_HOST_LOCAL
        self.port = MILVUS_PORT

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            def _check():
                from pymilvus import connections, utility
                connections.connect(host=self.host, port=self.port)
                utility.list_collections()

            await asyncio.wait_for(
                asyncio.to_thread(_check),
                timeout=self.timeout
            )

            latency_ms = (time.time() - start_time) * 1000
            return self._create_health(
                status=ServiceStatus.HEALTHY,
                message="Milvus connection is healthy",
                latency_ms=round(latency_ms, 2),
                details={
                    "host": self.host,
                    "port": self.port,
                }
            )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Milvus health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message="Milvus connection timeout",
                latency_ms=round(latency_ms, 2),
                details={
                    "host": self.host,
                    "port": self.port,
                    "timeout": self.timeout,
                }
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Milvus health check failed: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Milvus connection failed: {str(e)}",
                latency_ms=round(latency_ms, 2),
                details={
                    "host": self.host,
                    "port": self.port,
                    "error": str(e),
                }
            )
