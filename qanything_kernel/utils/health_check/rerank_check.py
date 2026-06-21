import time
import asyncio
import aiohttp
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.configs.model_config import LOCAL_RERANK_SERVICE_URL
from qanything_kernel.utils.custom_log import debug_logger


class RerankHealthChecker(BaseHealthChecker):
    name = "rerank"
    default_timeout = 5.0

    def __init__(self, timeout: float = 5.0):
        self.timeout = min(timeout, 8.0)
        raw_url = LOCAL_RERANK_SERVICE_URL
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"http://{raw_url}"
        self.service_url = raw_url.rstrip('/')
        self.endpoint = f"{self.service_url}/rerank"

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    json={"query": "ping", "passages": ["health check passage"]},
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout, connect=2.0)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000

                    if response.status != 200:
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"Rerank service returned HTTP {response.status}",
                            latency_ms=latency_ms,
                            details={
                                "endpoint": self.endpoint,
                                "http_status": response.status,
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    body = await response.json()

                    if not isinstance(body, list):
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message="Rerank service returned unexpected format (expected list of scores)",
                            latency_ms=latency_ms,
                            details={
                                "endpoint": self.endpoint,
                                "response_type": type(body).__name__,
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    if len(body) != 1:
                        return self._create_health(
                            status=ServiceStatus.DEGRADED,
                            message=f"Rerank returned {len(body)} scores, expected 1 for 1 passage",
                            latency_ms=latency_ms,
                            details={
                                "endpoint": self.endpoint,
                                "scores_count": len(body),
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    try:
                        float(body[0])
                    except (TypeError, ValueError):
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message="Rerank returned non-numeric score",
                            latency_ms=latency_ms,
                            details={
                                "endpoint": self.endpoint,
                                "score_value": str(body[0]),
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    return self._create_health(
                        status=ServiceStatus.HEALTHY,
                        message="Rerank service is healthy (application-level check passed)",
                        latency_ms=latency_ms,
                        details={
                            "endpoint": self.endpoint,
                            "score": body[0],
                        }
                    )

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Rerank health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Rerank service timeout after {self.timeout}s",
                latency_ms=latency_ms,
                details={"endpoint": self.endpoint, "timeout": self.timeout},
                error_type=ErrorType.TIMEOUT,
            )
        except aiohttp.ClientConnectorError as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Rerank health check connection refused: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Rerank service connection refused: {str(e)}",
                latency_ms=latency_ms,
                details={"endpoint": self.endpoint, "error": str(e)},
                error_type=ErrorType.CONNECTION_REFUSED,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            debug_logger.error(f"Rerank health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Rerank service check failed: {str(e)}",
                latency_ms=latency_ms,
                details={"endpoint": self.endpoint, "error": str(e)},
                error_type=error_type,
            )
