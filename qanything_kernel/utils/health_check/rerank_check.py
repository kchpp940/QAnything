import time
import asyncio
from urllib.parse import urlparse
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.configs.model_config import LOCAL_RERANK_SERVICE_URL
from qanything_kernel.utils.custom_log import debug_logger


class RerankHealthChecker(BaseHealthChecker):
    name = "rerank"
    default_timeout = 3.0

    def __init__(self, timeout: float = 3.0):
        self.timeout = min(timeout, 5.0)
        raw_url = LOCAL_RERANK_SERVICE_URL
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"http://{raw_url}"
        parsed = urlparse(raw_url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 80
        self.service_url = raw_url.rstrip('/')

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
                    message="Rerank service TCP connection successful",
                    latency_ms=latency_ms,
                    details={
                        "service_url": self.service_url,
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
            debug_logger.error(f"Rerank health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Rerank service connection timeout after {self.timeout}s",
                latency_ms=latency_ms,
                details={
                    "service_url": self.service_url,
                    "timeout": self.timeout,
                },
                error_type=ErrorType.TIMEOUT,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            debug_logger.error(f"Rerank health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Rerank service connection failed: {str(e)}",
                latency_ms=latency_ms,
                details={
                    "service_url": self.service_url,
                    "error": str(e),
                },
                error_type=error_type,
            )
