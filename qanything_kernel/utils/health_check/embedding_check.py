import time
import asyncio
import aiohttp
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.configs.model_config import LOCAL_EMBED_SERVICE_URL
from qanything_kernel.utils.custom_log import debug_logger


class EmbeddingHealthChecker(BaseHealthChecker):
    name = "embedding"
    default_timeout = 5.0

    def __init__(self, timeout: float = 5.0):
        self.timeout = min(timeout, 8.0)
        raw_url = LOCAL_EMBED_SERVICE_URL
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"http://{raw_url}"
        self.service_url = raw_url.rstrip('/')
        self.endpoint = f"{self.service_url}/embedding"

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    json={"texts": ["ping"]},
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout, connect=2.0)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000

                    if response.status != 200:
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"Embedding service returned HTTP {response.status}",
                            latency_ms=latency_ms,
                            details={
                                "endpoint": self.endpoint,
                                "http_status": response.status,
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    body = await response.json()

                    if not isinstance(body, list) or len(body) == 0:
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message="Embedding service returned unexpected format (expected non-empty list)",
                            latency_ms=latency_ms,
                            details={
                                "endpoint": self.endpoint,
                                "response_type": type(body).__name__,
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    first_embedding = body[0]
                    if not isinstance(first_embedding, list) or len(first_embedding) == 0:
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message="Embedding result is not a valid vector (expected list of floats)",
                            latency_ms=latency_ms,
                            details={
                                "endpoint": self.endpoint,
                                "first_element_type": type(first_embedding).__name__,
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    return self._create_health(
                        status=ServiceStatus.HEALTHY,
                        message="Embedding service is healthy (application-level check passed)",
                        latency_ms=latency_ms,
                        details={
                            "endpoint": self.endpoint,
                            "embedding_dim": len(first_embedding),
                        }
                    )

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Embedding health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Embedding service timeout after {self.timeout}s",
                latency_ms=latency_ms,
                details={"endpoint": self.endpoint, "timeout": self.timeout},
                error_type=ErrorType.TIMEOUT,
            )
        except aiohttp.ClientConnectorError as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Embedding health check connection refused: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Embedding service connection refused: {str(e)}",
                latency_ms=latency_ms,
                details={"endpoint": self.endpoint, "error": str(e)},
                error_type=ErrorType.CONNECTION_REFUSED,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            debug_logger.error(f"Embedding health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Embedding service check failed: {str(e)}",
                latency_ms=latency_ms,
                details={"endpoint": self.endpoint, "error": str(e)},
                error_type=error_type,
            )
