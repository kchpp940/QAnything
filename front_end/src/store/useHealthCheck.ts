import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import urlResquest from '@/services/urlConfig';

export interface DependencyHealth {
  name: string;
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  message: string;
  latency_ms: number;
  details: Record<string, any>;
  last_check_time: number;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  dependencies: Record<string, DependencyHealth>;
  timestamp: number;
  critical_services: string[];
}

const STATUS_LABELS: Record<string, string> = {
  healthy: '正常',
  unhealthy: '异常',
  degraded: '降级',
  unknown: '未知',
};

const SERVICE_LABELS: Record<string, string> = {
  mysql: 'MySQL 数据库',
  milvus: 'Milvus 向量库',
  elasticsearch: 'Elasticsearch',
  embedding: 'Embedding 服务',
  rerank: 'Rerank 服务',
  llm: 'LLM 大模型',
};

export const useHealthCheck = defineStore('healthCheck', () => {
  const healthStatus = ref<HealthStatus | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastFetchTime = ref<number>(0);
  let pollTimer: number | null = null;

  const isHealthy = computed(() => {
    return healthStatus.value?.status === 'healthy';
  });

  const isUnhealthy = computed(() => {
    return healthStatus.value?.status === 'unhealthy';
  });

  const unhealthyServices = computed(() => {
    if (!healthStatus.value) return [];
    return Object.values(healthStatus.value.dependencies).filter(
      dep => dep.status !== 'healthy'
    );
  });

  const criticalUnhealthy = computed(() => {
    if (!healthStatus.value) return [];
    const critical = new Set(healthStatus.value.critical_services || []);
    return Object.values(healthStatus.value.dependencies).filter(
      dep => critical.has(dep.name) && dep.status !== 'healthy'
    );
  });

  const overallStatusLabel = computed(() => {
    return STATUS_LABELS[healthStatus.value?.status || 'unknown'] || '未知';
  });

  function getServiceLabel(name: string): string {
    return SERVICE_LABELS[name] || name;
  }

  function getStatusLabel(status: string): string {
    return STATUS_LABELS[status] || status;
  }

  async function fetchHealthStatus(force = false): Promise<HealthStatus | null> {
    if (loading.value) return healthStatus.value;

    const now = Date.now();
    if (!force && healthStatus.value && now - lastFetchTime.value < 5000) {
      return healthStatus.value;
    }

    loading.value = true;
    error.value = null;

    try {
      const res = await urlResquest.dependencyHealth();
      if (res && res.code === 200) {
        healthStatus.value = {
          status: res.status,
          dependencies: res.dependencies || {},
          timestamp: res.timestamp,
          critical_services: res.critical_services || [],
        };
        lastFetchTime.value = now;
        return healthStatus.value;
      } else {
        throw new Error(res?.msg || '健康检查请求失败');
      }
    } catch (e: any) {
      error.value = e.message || '健康检查请求失败';
      return null;
    } finally {
      loading.value = false;
    }
  }

  function startPolling(interval = 10000) {
    stopPolling();
    fetchHealthStatus();
    pollTimer = window.setInterval(() => {
      fetchHealthStatus();
    }, interval);
  }

  function stopPolling() {
    if (pollTimer !== null) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  return {
    healthStatus,
    loading,
    error,
    isHealthy,
    isUnhealthy,
    unhealthyServices,
    criticalUnhealthy,
    overallStatusLabel,
    fetchHealthStatus,
    startPolling,
    stopPolling,
    getServiceLabel,
    getStatusLabel,
  };
});
