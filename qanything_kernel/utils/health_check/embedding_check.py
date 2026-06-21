import time
import asyncio
import aiohttp
from qanything_kernel.utils.health_check.base import BaseHealthChecker, ServiceStatus, DependencyHealth
from qanything_kernel.configs.model_config import LOCAL_EMBED_SERVICE_URL
from qanything_kernel.utils.custom_log import debug_logger


class EmbeddingHealthChecker(BaseHealthChecker):
    name = "embedding"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.service_url = f"http://{LOCAL_EMBED_SERVICE_URL}"

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        test_text = "Hello, this is a health check test."
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.service_url}/embedding",
                    json={"texts": [test_text]},
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, list) and len(result) > 0:
                            latency_ms = (time.time() - start_time) * 1000
                            return self._create_health(
                                status=ServiceStatus.HEALTHY,
                                message="Embedding service is healthy",
                                latency_ms=round(latency_ms, 2),
                                details={
                                    "service_url": self.service_url,
                                    "embedding_dim": len(result[0]) if result else 0,
                                }
                            )
                        else:
                            latency_ms = (time.time() - start_time) * 1000
                            return self._create_health(
                                status=ServiceStatus.DEGRADED,
                                message="Embedding service returned unexpected response format",
                                latency_ms=round(latency_ms, 2),
                                details={
                                    "service_url": self.service_url,
                                    "response_type": type(result).__name__,
                                }
                            )
                    else:
                        latency_ms = (time.time() - start_time) * 1000
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"Embedding service returned HTTP {response.status}",
                            latency_ms=round(latency_ms, 2),
                            details={
                                "service_url": self.service_url,
                                "http_status": response.status,
                            }
                        )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Embedding health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message="Embedding service connection timeout",
                latency_ms=round(latency_ms, 2),
                details={
                    "service_url": self.service_url,
                    "timeout": self.timeout,
                }
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Embedding health check failed: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Embedding service connection failed: {str(e)}",
                latency_ms=round(latency_ms, 2),
                details={
                    "service_url": self.service_url,
                    "error": str(e),
                }
            )
