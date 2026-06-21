from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import time


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class DependencyHealth:
    name: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    last_check_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['status'] = self.status.value
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

    async def check(self) -> DependencyHealth:
        raise NotImplementedError

    def _create_health(self, status: ServiceStatus, message: str = "",
                       latency_ms: float = 0.0, details: Optional[Dict[str, Any]] = None) -> DependencyHealth:
        return DependencyHealth(
            name=self.name,
            status=status,
            message=message,
            latency_ms=latency_ms,
            details=details or {},
            last_check_time=time.time(),
        )
