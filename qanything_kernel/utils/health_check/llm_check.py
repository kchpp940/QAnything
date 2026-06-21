import time
import asyncio
import aiohttp
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.utils.custom_log import debug_logger


class LLMHealthChecker(BaseHealthChecker):
    name = "llm"
    default_timeout = 8.0

    def __init__(self, api_base: str = "", api_key: str = "", model: str = "", timeout: float = 8.0):
        self.timeout = min(timeout, 15.0)
        self.api_base = api_base.rstrip('/') if api_base else ""
        self.api_key = api_key
        self.model = model

    async def check(self) -> DependencyHealth:
        start_time = time.time()

        if not self.api_base or not self.api_key:
            return self._create_health(
                status=ServiceStatus.DEGRADED,
                message="LLM not configured (api_base/api_key empty at startup; runtime values may differ)",
                latency_ms=0.0,
                details={
                    "api_base_configured": bool(self.api_base),
                    "api_key_configured": bool(self.api_key),
                },
                error_type=ErrorType.CONFIG_MISSING,
            )

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            payload = {
                "model": self.model or "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 2,
                "stream": False,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout, connect=3.0)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000

                    if response.status == 401 or response.status == 403:
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"LLM auth failed (HTTP {response.status})",
                            latency_ms=latency_ms,
                            details={"api_base": self.api_base, "http_status": response.status},
                            error_type=ErrorType.AUTH_FAILED,
                        )

                    if response.status == 404:
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"LLM endpoint not found (HTTP 404), check api_base path",
                            latency_ms=latency_ms,
                            details={"api_base": self.api_base},
                            error_type=ErrorType.NOT_FOUND,
                        )

                    if response.status != 200:
                        text = await response.text()
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message=f"LLM returned HTTP {response.status}",
                            latency_ms=latency_ms,
                            details={"api_base": self.api_base, "http_status": response.status, "body": text[:200]},
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    body = await response.json()
                    choices = body.get("choices")
                    if not isinstance(choices, list) or len(choices) == 0:
                        return self._create_health(
                            status=ServiceStatus.UNHEALTHY,
                            message="LLM response missing 'choices' array",
                            latency_ms=latency_ms,
                            details={"api_base": self.api_base, "response_keys": list(body.keys())},
                            error_type=ErrorType.BAD_RESPONSE,
                        )

                    return self._create_health(
                        status=ServiceStatus.HEALTHY,
                        message="LLM service is healthy (application-level check passed)",
                        latency_ms=latency_ms,
                        details={
                            "api_base": self.api_base,
                            "model": payload["model"],
                        }
                    )

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"LLM health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"LLM service timeout after {self.timeout}s",
                latency_ms=latency_ms,
                details={"api_base": self.api_base, "timeout": self.timeout},
                error_type=ErrorType.TIMEOUT,
            )
        except aiohttp.ClientConnectorError as e:
            latency_ms = (time.time() - start_time) * 1000
            debug_logger.error(f"LLM health check connection refused: {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"LLM service connection refused: {str(e)}",
                latency_ms=latency_ms,
                details={"api_base": self.api_base, "error": str(e)},
                error_type=ErrorType.CONNECTION_REFUSED,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            debug_logger.error(f"LLM health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"LLM service check failed: {str(e)}",
                latency_ms=latency_ms,
                details={"api_base": self.api_base, "error": str(e)},
                error_type=error_type,
            )
