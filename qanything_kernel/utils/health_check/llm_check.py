import time
import asyncio
from urllib.parse import urlparse
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, ServiceStatus, DependencyHealth, ErrorType
)
from qanything_kernel.utils.custom_log import debug_logger


class LLMHealthChecker(BaseHealthChecker):
    name = "llm"
    default_timeout = 3.0

    def __init__(self, api_base: str = "", api_key: str = "", model: str = "", timeout: float = 3.0):
        self.timeout = min(timeout, 5.0)
        self.api_base = api_base.rstrip('/') if api_base else ""
        self.api_key = api_key
        self.model = model
        self.host = None
        self.port = None
        if self.api_base:
            try:
                parsed = urlparse(self.api_base)
                self.host = parsed.hostname
                self.port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            except Exception:
                pass

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
                },
                error_type=ErrorType.CONFIG_MISSING,
            )

        if not self.host or not self.port:
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message="LLM api_base is malformed, cannot parse host/port",
                latency_ms=(time.time() - start_time) * 1000,
                details={
                    "api_base": self.api_base,
                },
                error_type=ErrorType.CONFIG_MISSING,
            )

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
            try:
                latency_ms = (time.time() - start_time) * 1000
                return self._create_health(
                    status=ServiceStatus.HEALTHY,
                    message="LLM service TCP connection successful",
                    latency_ms=latency_ms,
                    details={
                        "api_base": self.api_base,
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
            debug_logger.error(f"LLM health check timeout after {self.timeout}s")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"LLM service connection timeout after {self.timeout}s",
                latency_ms=latency_ms,
                details={
                    "api_base": self.api_base,
                    "timeout": self.timeout,
                },
                error_type=ErrorType.TIMEOUT,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = self._classify_error(e)
            debug_logger.error(f"LLM health check failed ({error_type.value}): {e}")
            return self._create_health(
                status=ServiceStatus.UNHEALTHY,
                message=f"LLM service connection failed: {str(e)}",
                latency_ms=latency_ms,
                details={
                    "api_base": self.api_base,
                    "error": str(e),
                },
                error_type=error_type,
            )
