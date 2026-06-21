import asyncio
import time
from typing import List, Dict, Optional, Set
from qanything_kernel.utils.health_check.base import (
    BaseHealthChecker, HealthStatus, ServiceStatus, DependencyHealth
)
from qanything_kernel.utils.health_check.mysql_check import MySQLHealthChecker
from qanything_kernel.utils.health_check.milvus_check import MilvusHealthChecker
from qanything_kernel.utils.health_check.es_check import ElasticsearchHealthChecker
from qanything_kernel.utils.health_check.embedding_check import EmbeddingHealthChecker
from qanything_kernel.utils.health_check.rerank_check import RerankHealthChecker
from qanything_kernel.utils.health_check.llm_check import LLMHealthChecker
from qanything_kernel.utils.custom_log import debug_logger


class HealthCheckManager:
    def __init__(self, llm_api_base: str = "", llm_api_key: str = "", llm_model: str = ""):
        self.checkers: Dict[str, BaseHealthChecker] = {}
        self._cache: Optional[HealthStatus] = None
        self._cache_ttl: float = 5.0
        self._last_check_time: float = 0.0
        self._init_default_checkers(llm_api_base, llm_api_key, llm_model)

    def _init_default_checkers(self, llm_api_base: str, llm_api_key: str, llm_model: str):
        self.add_checker(MySQLHealthChecker())
        self.add_checker(MilvusHealthChecker())
        self.add_checker(ElasticsearchHealthChecker())
        self.add_checker(EmbeddingHealthChecker())
        self.add_checker(RerankHealthChecker())
        self.add_checker(LLMHealthChecker(
            api_base=llm_api_base,
            api_key=llm_api_key,
            model=llm_model,
        ))

    def add_checker(self, checker: BaseHealthChecker):
        self.checkers[checker.name] = checker

    def remove_checker(self, name: str):
        if name in self.checkers:
            del self.checkers[name]

    async def check_all(self, use_cache: bool = True) -> HealthStatus:
        if use_cache and self._cache and (time.time() - self._last_check_time) < self._cache_ttl:
            return self._cache

        tasks = []
        checker_names = []
        for name, checker in self.checkers.items():
            tasks.append(checker.check())
            checker_names.append(name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        dependencies: Dict[str, DependencyHealth] = {}
        for name, result in zip(checker_names, results):
            if isinstance(result, Exception):
                debug_logger.error(f"Health checker {name} raised exception: {result}")
                dependencies[name] = DependencyHealth(
                    name=name,
                    status=ServiceStatus.UNHEALTHY,
                    message=f"Checker exception: {str(result)}",
                    last_check_time=time.time(),
                )
            else:
                dependencies[name] = result

        overall_status = self._compute_overall_status(dependencies)

        health_status = HealthStatus(
            overall_status=overall_status,
            dependencies=dependencies,
            timestamp=time.time(),
        )

        self._cache = health_status
        self._last_check_time = time.time()

        return health_status

    async def check_specific(self, names: List[str]) -> HealthStatus:
        tasks = []
        checker_names = []
        for name in names:
            if name in self.checkers:
                tasks.append(self.checkers[name].check())
                checker_names.append(name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        dependencies: Dict[str, DependencyHealth] = {}
        for name, result in zip(checker_names, results):
            if isinstance(result, Exception):
                dependencies[name] = DependencyHealth(
                    name=name,
                    status=ServiceStatus.UNHEALTHY,
                    message=f"Checker exception: {str(result)}",
                    last_check_time=time.time(),
                )
            else:
                dependencies[name] = result

        overall_status = self._compute_overall_status(dependencies)

        return HealthStatus(
            overall_status=overall_status,
            dependencies=dependencies,
            timestamp=time.time(),
        )

    async def wait_for_services(
        self,
        required_services: List[str],
        timeout: float = 120.0,
        interval: float = 2.0,
    ) -> bool:
        start_time = time.time()
        required_set = set(required_services)

        debug_logger.info(f"Waiting for services: {required_services}, timeout: {timeout}s")

        while time.time() - start_time < timeout:
            health = await self.check_specific(required_services)
            all_healthy = all(
                dep.status == ServiceStatus.HEALTHY
                for name, dep in health.dependencies.items()
                if name in required_set
            )

            if all_healthy:
                debug_logger.info(f"All required services are healthy: {required_services}")
                return True

            unhealthy = [
                name for name, dep in health.dependencies.items()
                if name in required_set and dep.status != ServiceStatus.HEALTHY
            ]
            debug_logger.info(
                f"Waiting for services... unhealthy: {unhealthy}, "
                f"elapsed: {round(time.time() - start_time, 1)}s"
            )

            await asyncio.sleep(interval)

        debug_logger.error(f"Timeout waiting for services: {required_services} after {timeout}s")
        return False

    def _compute_overall_status(self, dependencies: Dict[str, DependencyHealth]) -> ServiceStatus:
        if not dependencies:
            return ServiceStatus.UNKNOWN

        statuses = [dep.status for dep in dependencies.values()]

        if all(s == ServiceStatus.HEALTHY for s in statuses):
            return ServiceStatus.HEALTHY

        if any(s == ServiceStatus.UNHEALTHY for s in statuses):
            return ServiceStatus.UNHEALTHY

        if any(s == ServiceStatus.DEGRADED for s in statuses):
            return ServiceStatus.DEGRADED

        return ServiceStatus.UNKNOWN

    def get_critical_services(self) -> List[str]:
        return ["mysql", "milvus", "elasticsearch", "embedding", "rerank"]

    def invalidate_cache(self):
        self._cache = None
        self._last_check_time = 0.0
