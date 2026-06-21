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
      <div class="service-list">
        <div
          v-for="dep in dependencyList"
          :key="dep.name"
          class="service-item"
          :class="`status-${dep.status}`"
        >
          <div class="service-status-dot" :class="`dot-${dep.status}`"></div>
          <div class="service-info">
            <span class="service-name">{{ getServiceLabel(dep.name) }}</span>
            <span class="service-latency" v-if="dep.status === 'healthy'">
              {{ dep.latency_ms.toFixed(0) }}ms
            </span>
          </div>
          <div class="service-message" v-if="dep.message && dep.status !== 'healthy'">
            {{ dep.message }}
          </div>
        </div>
      </div>

      <div class="health-actions">
        <a-button size="small" @click="refresh" :loading="loading">
          刷新
        </a-button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useHealthCheck } from '@/store/useHealthCheck';

const healthStore = useHealthCheck();
const expanded = ref(false);

const { loading, healthStatus, overallStatusLabel, fetchHealthStatus, getServiceLabel } = healthStore;

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

  &.minimal {
    border: none;
    background: transparent;
  }
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

.service-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.service-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  background: #fafafa;

  &.status-unhealthy {
    background: #fff2f0;
  }

  &.status-degraded {
    background: #fffbe6;
  }
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
}

.service-name {
  font-weight: 500;
  color: #333;
}

.service-latency {
  color: #999;
  font-size: 11px;
}

.service-message {
  width: 100%;
  font-size: 11px;
  color: #ff4d4f;
  padding-left: 14px;
  word-break: break-all;
}

.health-actions {
  margin-top: 12px;
  text-align: right;
}
</style>
