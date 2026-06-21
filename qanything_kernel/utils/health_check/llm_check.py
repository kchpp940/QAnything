import time
import asyncio
import aiohttp
from qanything_kernel.utils.health_check.base import BaseHealthChecker, ServiceStatus, DependencyHealth
from qanything_kernel.utils.custom_log import debug_logger


class LLMHealthChecker(BaseHealthChecker):
    name = "llm"

    def __init__(self, api_base: str = "", api_key: str = "", model: str = "", timeout: float = 15.0):
        self.timeout = timeout
        self.api_base = api_base.rstrip('/') if api_base else ""
        self.api_key = api_key
        self.model = model

    async def check(self) -> DependencyHealth:
        start_time = time.time()

        if not self.api_base or not self.api_key:
            return self._create_health(
                status=ServiceStatus.DEGRADED,
                message="LLM service not configured (missing api_base or api_key)",
                latency_ms=0.0,
                details={
                    "api_base_configured": bool(self.api_base),
                    "api_key_configured": bool(self.api_key),
                }
            )

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            payload = {
                "model": self.model or "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
                "stream": False,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        latency_ms = (time.time() - start_time) * 1000
                        return self._create_health(
                            status=ServiceStatus.HEALTHY,
                            message="LLM service is healthy",
                            latency_ms=round(latency_ms, 2),
                            details={
                                "api_base": self.api_base,
                                "model": payload["model"],
                            }
                        )
                    else:
                        latency_ms = (time.time() - start_time) * 1000
                        error_msg = await response.text()
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"LLM service returned HTTP {response.status}",
                            latency_ms=round(latency_ms, 2),
                            details={
                                "api_base": self.api_base,
                                "http_status": response.status,
                                "error": error_msg[:200],
                            }
                        )
        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"LLM health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message="LLM service connection timeout",
                latency_ms=round(latency_ms, 2),
                details={
                    "api_base": self.api_base,
                    "timeout": self.timeout,
                }
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"LLM health check failed: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"LLM service connection failed: {str(e)}",
                latency_ms=round(latency_ms, 2),
                details={
                    "api_base": self.api_base,
                    "error": str(e),
                }
            )
