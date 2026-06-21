import time
import asyncio
import aiohttp
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.configs.model_config import ES_URL, ES_INDEX_NAME
from qanything_kernel.utils.custom_log import debug_logger


class ElasticsearchHealthChecker(BaseHealthChecker):
    name = "elasticsearch"
    default_timeout = 3.0

    def __init__(self, timeout: float = 3.0):
        self.timeout = min(timeout, 5.0)
        self.es_url = ES_URL.rstrip('/')
        self.index_name = ES_INDEX_NAME

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.es_url}/_cluster/health",
                    timeout=aiohttp.ClientTimeout(total=self.timeout, connect=2.0)
                ) as response:
                    if response.status != 200:
                        latency_ms = (time.time() - start_time) * 1000
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"Elasticsearch returned HTTP {response.status}",
                            latency_ms=latency_ms,
                            details={
                                "es_url": self.es_url,
                                "http_status": response.status,
                            },
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    cluster_health = await response.json()

                cluster_status = cluster_health.get("status", "unknown")

                status_map = {
                    "green": ServiceStatus.HEALTHY,
                    "yellow": ServiceStatus.DEGRADED,
                    "red": ServiceStatus.UNHEALTHY,
                }
                status = status_map.get(cluster_status, ServiceStatus.UNKNOWN)

                index_exists = False
                try:
                    async with session.head(
                        f"{self.es_url}/{self.index_name}",
                        timeout=aiohttp.ClientTimeout(total=self.timeout, connect=2.0)
                    ) as idx_resp:
                        index_exists = idx_resp.status == 200
                except Exception:
                    index_exists = False

                latency_ms = (time.time() - start_time) * 1000
                message = f"Elasticsearch cluster status: {cluster_status}"
                if not index_exists:
                    message += f", index '{self.index_name}' not found"

                return self._create_health(
                    status=status,
                    message=message,
                    latency_ms=latency_ms,
                    details={
                        "es_url": self.es_url,
                        "cluster_status": cluster_status,
                        "index_name": self.index_name,
                        "index_exists": index_exists,
                        "number_of_nodes": cluster_health.get("number_of_nodes"),
                    },
                    error_type=ErrorType.NONE if status == ServiceStatus.HEALTHY else ErrorType.BAD_RESPONSE,
                )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Elasticsearch health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Elasticsearch connection timeout after {self.timeout}s",
                latency_ms=latency_ms,
                details={
                    "es_url": self.es_url,
                    "timeout": self.timeout,
                },
                error_type=ErrorType.TIMEOUT,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            debug_logger.error(f"Elasticsearch health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Elasticsearch connection failed: {str(e)}",
                latency_ms=latency_ms,
                details={
                    "es_url": self.es_url,
                    "error": str(e),
                },
                error_type=error_type,
            )
