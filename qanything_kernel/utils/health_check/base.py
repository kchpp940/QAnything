from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import time


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ErrorType(str, Enum):
    NONE = "none"
    TIMEOUT = "timeout"
    CONNECTION_REFUSED = "connection_refused"
    DNS_ERROR = "dns_error"
    AUTH_FAILED = "auth_failed"
    NOT_FOUND = "not_found"
    BAD_RESPONSE = "bad_response"
    CONFIG_MISSING = "config_missing"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class DependencyHealth:
    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    error_type: ErrorType = ErrorType.NONE
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    last_check_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value
        result['error_type'] = self.error_type.value
        return result


@dataclass
class HealthStatus:
    overall_status: ServiceStatus = ServiceStatus.UNKNOWN
    dependencies: Dict[str, DependencyHealth] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_status': self.overall_status.value,
            'dependencies': {name: dep.to_dict() for name, dep in self.dependencies.items()},
            'timestamp': self.timestamp,
        }


class BaseHealthChecker:
    name: str = "base"
    default_timeout: float = 3.0

    async def check(self) -> DependencyHealth:
        raise NotImplementedError

    def _classify_error(self, exc: Exception) -> ErrorType:
        msg = str(exc).lower()
        exc_name = type(exc).__name__.lower()

        if 'timeout' in msg or 'timed out' in msg:
            return ErrorType.TIMEOUT
        if 'refused' in msg or 'connectionrefusederror' in exc_name:
            return ErrorType.CONNECTION_REFUSED
        if 'dns' in msg or 'getaddrinfo' in msg or 'nodename nor servname' in msg:
            return ErrorType.DNS_ERROR
        if 'auth' in msg or 'password' in msg or 'access denied' in msg or '401' in msg or '403' in msg:
            return ErrorType.AUTH_FAILED
        if 'not found' in msg or '404' in msg or 'nosuch' in exc_name:
            return ErrorType.NOT_FOUND
        if any(k in msg for k in ['bad response', 'unexpected', 'format', 'parse']):
            return ErrorType.BAD_RESPONSE
        return ErrorType.UNKNOWN_ERROR

    def _create_health(self, status: ServiceStatus, message: str = "",
                       latency_ms: float = 0.0, details: Optional[Dict[str, Any]] = None,
                       error_type: ErrorType = ErrorType.NONE) -> DependencyHealth:
        return DependencyHealth(
            name=self.name,
            status=status,
            error_type=error_type,
            message=message,
            latency_ms=round(latency_ms, 2),
            details=details or {},
            last_check_time=time.time(),
        )
