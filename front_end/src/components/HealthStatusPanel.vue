<template>
  <div class="health-status-panel">
    <div class="health-status-header" @click="toggleExpand">
      <div class="status-indicator" :class="statusClass">
        <span class="status-dot"></span>
        <span class="status-text">{{ overallStatusLabel }}</span>
      </div>
      <span class="expand-icon">{{ expanded ? '▼' : '▲' }}</span>
    </div>

    <div v-if="expanded" class="health-status-content">
      <div v-if="healthStore.error" class="fetch-error">
        <a-alert type="error" :message="healthStore.error" show-icon />
      </div>

      <div class="service-list">
        <div
          v-for="dep in dependencyList"
          :key="dep.name"
          class="service-item"
          :class="`status-${dep.status}`"
        >
          <div class="service-row">
            <div class="service-status-dot" :class="`dot-${dep.status}`"></div>
            <div class="service-info">
              <span class="service-name">{{ healthStore.getServiceLabel(dep.name) }}</span>
              <span v-if="dep.status === 'healthy'" class="service-latency">
                {{ dep.latency_ms.toFixed(0) }}ms
              </span>
              <span
                v-else
                class="service-error-type"
                :title="healthStore.getErrorTroubleshoot(dep.error_type)"
              >
                {{ healthStore.getErrorTypeLabel(dep.error_type) }}
              </span>
            </div>
            <span class="service-status-badge" :class="`badge-${dep.status}`">
              {{ healthStore.getStatusLabel(dep.status) }}
            </span>
          </div>
          <div v-if="dep.message && dep.status !== 'healthy'" class="service-message">
            {{ dep.message }}
          </div>
          <div
            v-if="dep.status !== 'healthy' && dep.error_type !== 'none'"
            class="service-troubleshoot"
          >
            <span class="troubleshoot-label">排查建议：</span>
            {{ healthStore.getErrorTroubleshoot(dep.error_type) }}
          </div>
          <div
            v-if="dep.status !== 'healthy' && dep.details && Object.keys(dep.details).length"
            class="service-details"
            @click="toggleDetails(dep.name)"
          >
            <span class="details-toggle">
              {{ expandedDetails[dep.name] ? '▼' : '▶' }}
              技术详情
            </span>
            <pre v-if="expandedDetails[dep.name]" class="details-content">{{ formatDetails(dep.details) }}</pre>
          </div>
        </div>
      </div>

      <div class="health-legend">
        <div class="legend-item"><span class="legend-dot dot-healthy"></span>正常</div>
        <div class="legend-item"><span class="legend-dot dot-degraded"></span>降级</div>
        <div class="legend-item"><span class="legend-dot dot-unhealthy"></span>异常</div>
        <div class="legend-item"><span class="legend-dot dot-unknown"></span>未知</div>
      </div>

      <div class="health-actions">
        <a-button size="small" @click="refresh" :loading="loading">
          刷新状态
        </a-button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { useHealthCheck } from '@/store/useHealthCheck';

const healthStore = useHealthCheck();
const expanded = ref(false);
const expandedDetails = reactive<Record<string, boolean>>({});

const { loading, healthStatus, overallStatusLabel, fetchHealthStatus } = healthStore;

const statusClass = computed(() => {
  return `status-${healthStatus.value?.status || 'unknown'}`;
});

const dependencyList = computed(() => {
  if (!healthStatus.value?.dependencies) return [];
  return Object.values(healthStatus.value.dependencies);
});

function toggleExpand() {
  expanded.value = !expanded.value;
  if (expanded.value) {
    fetchHealthStatus();
  }
}

function toggleDetails(name: string) {
  expandedDetails[name] = !expandedDetails[name];
}

function formatDetails(details: Record<string, any>): string {
  try {
    return JSON.stringify(details, null, 2);
  } catch {
    return String(details);
  }
}

function refresh() {
  fetchHealthStatus(true);
}

onMounted(() => {
  healthStore.startPolling(15000);
});

onUnmounted(() => {
  healthStore.stopPolling();
});
</script>

<style lang="scss" scoped>
.health-status-panel {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  overflow: hidden;
  font-size: 13px;
  min-width: 360px;
  max-width: 480px;
}

.health-status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;

  &:hover {
    background: #f5f5f5;
  }
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;

  .status-healthy & {
    background: #52c41a;
    box-shadow: 0 0 6px rgba(82, 196, 26, 0.5);
  }

  .status-unhealthy & {
    background: #ff4d4f;
    box-shadow: 0 0 6px rgba(255, 77, 79, 0.5);
    animation: pulse 1.5s infinite;
  }

  .status-degraded & {
    background: #faad14;
    box-shadow: 0 0 6px rgba(250, 173, 20, 0.5);
  }

  .status-unknown & {
    background: #bfbfbf;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  .status-healthy & { color: #52c41a; }
  .status-unhealthy & { color: #ff4d4f; }
  .status-degraded & { color: #faad14; }
  .status-unknown & { color: #bfbfbf; }
}

.expand-icon {
  font-size: 10px;
  color: #999;
}

.health-status-content {
  padding: 12px;
}

.fetch-error {
  margin-bottom: 10px;
}

.service-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.service-item {
  padding: 8px 10px;
  border-radius: 4px;
  background: #fafafa;
  border-left: 3px solid transparent;

  &.status-unhealthy {
    background: #fff2f0;
    border-left-color: #ff4d4f;
  }

  &.status-degraded {
    background: #fffbe6;
    border-left-color: #faad14;
  }

  &.status-healthy {
    border-left-color: #52c41a;
  }
}

.service-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.service-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;

  &.dot-healthy { background: #52c41a; }
  &.dot-unhealthy { background: #ff4d4f; }
  &.dot-degraded { background: #faad14; }
  &.dot-unknown { background: #bfbfbf; }
}

.service-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  flex-wrap: wrap;
}

.service-name {
  font-weight: 500;
  color: #333;
}

.service-latency {
  color: #52c41a;
  font-size: 11px;
  font-family: monospace;
}

.service-error-type {
  color: #d4380d;
  font-size: 11px;
  padding: 1px 6px;
  background: #fff1f0;
  border-radius: 3px;
  cursor: help;
}

.service-status-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;

  &.badge-healthy {
    background: #f6ffed;
    color: #52c41a;
  }
  &.badge-unhealthy {
    background: #fff1f0;
    color: #ff4d4f;
  }
  &.badge-degraded {
    background: #fffbe6;
    color: #faad14;
  }
  &.badge-unknown {
    background: #f5f5f5;
    color: #bfbfbf;
  }
}

.service-message {
  margin-top: 6px;
  padding-left: 14px;
  font-size: 11px;
  color: #ff4d4f;
  line-height: 1.5;
  word-break: break-all;
}

.service-troubleshoot {
  margin-top: 4px;
  padding-left: 14px;
  font-size: 11px;
  color: #8c8c8c;
  line-height: 1.5;

  .troubleshoot-label {
    color: #faad14;
    font-weight: 500;
  }
}

.service-details {
  margin-top: 4px;
  padding-left: 14px;

  .details-toggle {
    cursor: pointer;
    color: #1890ff;
    font-size: 11px;

    &:hover {
      text-decoration: underline;
    }
  }

  .details-content {
    margin: 4px 0 0;
    padding: 6px 8px;
    background: #262626;
    color: #d9d9d9;
    border-radius: 3px;
    font-size: 10px;
    font-family: monospace;
    max-height: 120px;
    overflow: auto;
  }
}

.health-legend {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e8e8e8;

  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    color: #8c8c8c;
  }

  .legend-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }
}

.health-actions {
  margin-top: 10px;
  text-align: right;
}
</style>
