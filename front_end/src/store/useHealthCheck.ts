import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import urlResquest from '@/services/urlConfig';

export type DepStatus = 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
export type DepErrorType =
  | 'none'
  | 'timeout'
  | 'connection_refused'
  | 'dns_error'
  | 'auth_failed'
  | 'not_found'
  | 'bad_response'
  | 'config_missing'
  | 'unknown_error';

export interface DependencyHealth {
  name: string;
  status: DepStatus;
  error_type: DepErrorType;
  message: string;
  latency_ms: number;
  details: Record<string, any>;
  last_check_time: number;
}

export interface HealthStatus {
  status: DepStatus;
  status_code: number;
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

const ERROR_TYPE_LABELS: Record<string, string> = {
  none: '-',
  timeout: '连接超时',
  connection_refused: '连接被拒绝（服务未启动）',
  dns_error: '域名解析失败',
  auth_failed: '认证失败',
  not_found: '资源不存在',
  bad_response: '响应异常',
  config_missing: '配置缺失',
  unknown_error: '未知错误',
};

const ERROR_TROUBLESHOOT: Record<string, string> = {
  timeout: '检查服务是否过载或网络是否通畅',
  connection_refused: '检查对应服务是否已经启动，端口是否正确',
  dns_error: '检查 hosts 配置或 DNS 服务器设置',
  auth_failed: '检查账号密码或 API Key 是否正确',
  not_found: '检查索引或资源是否已正确初始化',
  bad_response: '检查服务版本是否兼容，日志是否有报错',
  config_missing: '检查环境变量或配置文件是否完整',
  unknown_error: '查看服务端日志获取详细错误信息',
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
  const livenessAlive = ref<boolean>(false);
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

  function getErrorTypeLabel(errorType: string): string {
    return ERROR_TYPE_LABELS[errorType] || errorType;
  }

  function getErrorTroubleshoot(errorType: string): string {
    return ERROR_TROUBLESHOOT[errorType] || '请检查服务日志';
  }

  function normalizeDependency(raw: any): DependencyHealth {
    return {
      name: raw.name || 'unknown',
      status: (raw.status || 'unknown') as DepStatus,
      error_type: (raw.error_type || 'unknown_error') as DepErrorType,
      message: raw.message || '',
      latency_ms: typeof raw.latency_ms === 'number' ? raw.latency_ms : 0,
      details: raw.details || {},
      last_check_time: raw.last_check_time || Date.now() / 1000,
    };
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

      if (!res) {
        throw new Error('请求无响应');
      }

      if (res.code !== 200) {
        throw new Error(res.msg || `请求失败 (code=${res.code})`);
      }

      const deps: Record<string, DependencyHealth> = {};
      if (res.dependencies && typeof res.dependencies === 'object') {
        for (const [name, rawDep] of Object.entries<any>(res.dependencies)) {
          deps[name] = normalizeDependency(rawDep);
        }
      }

      healthStatus.value = {
        status: (res.status || 'unknown') as DepStatus,
        status_code: res.status_code || (res.status === 'healthy' ? 200 : 503),
        dependencies: deps,
        timestamp: res.timestamp || now / 1000,
        critical_services: res.critical_services || [],
      };

      lastFetchTime.value = now;
      livenessAlive.value = true;
      return healthStatus.value;
    } catch (e: any) {
      error.value = e.message || '健康检查请求失败';
      livenessAlive.value = false;
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function checkLiveness(): Promise<boolean> {
    try {
      const res = await urlResquest.healthCheck();
      livenessAlive.value = !!(res && res.code === 200);
      return livenessAlive.value;
    } catch {
      livenessAlive.value = false;
      return false;
    }
  }

  function startPolling(interval = 15000) {
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
    livenessAlive,
    isHealthy,
    isUnhealthy,
    unhealthyServices,
    criticalUnhealthy,
    overallStatusLabel,
    fetchHealthStatus,
    checkLiveness,
    startPolling,
    stopPolling,
    getServiceLabel,
    getStatusLabel,
    getErrorTypeLabel,
    getErrorTroubleshoot,
  };
});
