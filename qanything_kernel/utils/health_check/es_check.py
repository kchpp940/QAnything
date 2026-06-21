import time
import asyncio
import aiohttp
from qanything_kernel.utils.health_check.base import BaseHealthChecker, ServiceStatus, DependencyHealth
from qanything_kernel.configs.model_config import ES_URL, ES_INDEX_NAME
from qanything_kernel.utils.custom_log import debug_logger


class ElasticsearchHealthChecker(BaseHealthChecker):
    name = "elasticsearch"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.es_url = ES_URL.rstrip('/')
        self.index_name = ES_INDEX_NAME

    async def check(self) -> DependencyHealth:
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.es_url}/_cluster/health",
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    cluster_health = await response.json()

                cluster_status = cluster_health.get("status", "unknown")

                status_map = {
                    "green": ServiceStatus.HEALTHY,
                    "yellow": ServiceStatus.DEGRADED,
                    "red": ServiceStatus.UNHEALTHY,
                }
                status = status_map.get(cluster_status, ServiceStatus.UNKNOWN)

                try:
                    async with session.head(
                        f"{self.es_url}/{self.index_name}",
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
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
                    latency_ms=round(latency_ms, 2),
                    details={
                        "es_url": self.es_url,
                        "cluster_status": cluster_status,
                        "index_name": self.index_name,
                        "index_exists": index_exists,
                        "number_of_nodes": cluster_health.get("number_of_nodes"),
                        "number_of_data_nodes": cluster_health.get("number_of_data_nodes"),
                    }
                )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Elasticsearch health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message="Elasticsearch connection timeout",
                latency_ms=round(latency_ms, 2),
                details={
                    "es_url": self.es_url,
                    "timeout": self.timeout,
                }
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"Elasticsearch health check failed: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"Elasticsearch connection failed: {str(e)}",
                latency_ms=round(latency_ms, 2),
                details={
                    "es_url": self.es_url,
                    "error": str(e),
                }
            )
