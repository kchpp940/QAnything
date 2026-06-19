<template>
  <div class="diagnosis-container">
    <div class="filter-area">
      <a-select
        v-model:value="selectedKbId"
        placeholder="选择知识库"
        style="width: 240px"
        :options="kbOptions"
        @change="onKbChange"
      />
      <a-range-picker
        v-model:value="searchDate"
        style="margin-left: 12px"
        @change="onDateChange"
      />
      <a-button type="primary" style="margin-left: 12px" @click="fetchAllData">查询</a-button>
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">召回趋势（按天）</div>
        <div v-if="summaryLoading" class="chart-loading"><a-spin /></div>
        <div v-else-if="!summaryData.length" class="no-data">暂无数据</div>
        <div v-else ref="summaryChartRef" class="chart-box"></div>
      </div>

      <div class="chart-card chart-card-small">
        <div class="chart-title">空召回原因分布</div>
        <div v-if="failureLoading" class="chart-loading"><a-spin /></div>
        <div v-else-if="!failureData.length" class="no-data">暂无数据</div>
        <div v-else ref="failureChartRef" class="chart-box"></div>
      </div>
    </div>

    <div class="table-card">
      <div class="chart-title">高频低置信问题（top_score < 0.5）</div>
      <a-table
        :data-source="lowConfidenceData"
        :columns="lowConfidenceColumns"
        :loading="lowConfidenceLoading"
        :pagination="{ pageSize: 10, showSizeChanger: false, showTotal: total => `共 ${total} 条` }"
        :scroll="{ x: 900 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'topScore'">
            <span :style="{ color: record.topScore < 0.28 ? '#EE6666' : '#FAAD14' }">
              {{ record.topScore?.toFixed(4) }}
            </span>
          </template>
          <template v-else-if="column.key === 'query'">
            <a-tooltip placement="topLeft">
              <template #title>{{ record.query }}</template>
              <span>{{ record.query }}</span>
            </a-tooltip>
          </template>
        </template>
      </a-table>
    </div>

    <div class="table-card" style="margin-top: 20px">
      <div class="chart-title">诊断记录明细</div>
      <a-table
        :data-source="diagnosisListData"
        :columns="diagnosisListColumns"
        :loading="diagnosisListLoading"
        :pagination="diagnosisListPagination"
        :scroll="{ x: 1400 }"
        size="small"
        @change="onDiagnosisListChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'rerankUsed'">
            <a-tag :color="record.rerankUsed ? 'green' : 'default'">
              {{ record.rerankUsed ? '是' : '否' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'emptyRecallReason'">
            <a-tag v-if="record.emptyRecallReason" color="red">
              {{ emptyReasonMap[record.emptyRecallReason] || record.emptyRecallReason }}
            </a-tag>
            <span v-else style="color: #91CC75">正常召回</span>
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts';
import urlResquest from '@/services/urlConfig';
import { resultControl } from '@/utils/utils';
import { useKnowledgeBase } from '@/store/useKnowledgeBase';
import { message } from 'ant-design-vue';
import dayjs, { Dayjs } from 'dayjs';

type RangeValue = [Dayjs, Dayjs];

const { knowledgeBaseList, getList } = useKnowledgeBase();

const kbOptions = computed(() =>
  knowledgeBaseList.value.map(item => ({
    value: item.kb_id,
    label: item.kb_name || item.kb_id,
  }))
);

const selectedKbId = ref('');
const searchDate = ref<RangeValue>([
  dayjs().subtract(30, 'day'),
  dayjs(),
]);

const emptyReasonMap: Record<string, string> = {
  no_knowledge_base: '无绑定知识库',
  vector_and_es_empty: '向量+ES均无结果',
  rerank_filtered_all: 'rerank过滤全部',
  unknown_empty_recall: '未知空召回',
};

const getParams = () => ({
  kb_id: selectedKbId.value,
  time_start: searchDate.value?.[0]?.format('YYYY-MM-DD') || '',
  time_end: searchDate.value?.[1]?.format('YYYY-MM-DD') || '',
});

// ========== 召回趋势 ==========
const summaryLoading = ref(false);
const summaryData = ref<any[]>([]);
const summaryChartRef = ref<HTMLElement | null>(null);
let summaryChartInstance: echarts.ECharts | null = null;

const fetchSummary = async () => {
  if (!selectedKbId.value) return;
  summaryLoading.value = true;
  try {
    const res: any = await resultControl(
      await urlResquest.getRetrievalDiagnosis({
        ...getParams(),
        data_type: 'summary',
      })
    );
    summaryData.value = res.data || [];
    nextTick(() => initSummaryChart());
  } catch (e: any) {
    message.error(e.msg || '获取召回趋势失败');
  } finally {
    summaryLoading.value = false;
  }
};

const initSummaryChart = () => {
  if (!summaryChartRef.value) return;
  if (summaryChartInstance) summaryChartInstance.dispose();
  summaryChartInstance = echarts.init(summaryChartRef.value);

  const dates = summaryData.value.map((r: any) => r.date);
  const totalCounts = summaryData.value.map((r: any) => Number(r.total_count) || 0);
  const successCounts = summaryData.value.map((r: any) => Number(r.success_count) || 0);
  const emptyCounts = summaryData.value.map((r: any) => Number(r.empty_count) || 0);
  const avgScores = summaryData.value.map((r: any) => Number(r.avg_top_score)?.toFixed(4) || 0);

  summaryChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['总召回', '成功召回', '空召回', '平均Top Score'] },
    grid: { left: 60, right: 60, bottom: 30, top: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: [
      { type: 'value', name: '数量' },
      { type: 'value', name: 'Score', min: 0, max: 1 },
    ],
    series: [
      { name: '总召回', type: 'bar', data: totalCounts, itemStyle: { color: '#5a47e5' } },
      { name: '成功召回', type: 'bar', data: successCounts, itemStyle: { color: '#91CC75' } },
      { name: '空召回', type: 'bar', data: emptyCounts, itemStyle: { color: '#EE6666' } },
      { name: '平均Top Score', type: 'line', yAxisIndex: 1, data: avgScores, itemStyle: { color: '#FAAD14' } },
    ],
  });
};

// ========== 失败原因分布 ==========
const failureLoading = ref(false);
const failureData = ref<any[]>([]);
const failureChartRef = ref<HTMLElement | null>(null);
let failureChartInstance: echarts.ECharts | null = null;

const fetchFailure = async () => {
  if (!selectedKbId.value) return;
  failureLoading.value = true;
  try {
    const res: any = await resultControl(
      await urlResquest.getRetrievalDiagnosis({
        ...getParams(),
        data_type: 'failure_distribution',
      })
    );
    failureData.value = res.data || [];
    nextTick(() => initFailureChart());
  } catch (e: any) {
    message.error(e.msg || '获取失败原因分布失败');
  } finally {
    failureLoading.value = false;
  }
};

const initFailureChart = () => {
  if (!failureChartRef.value) return;
  if (failureChartInstance) failureChartInstance.dispose();
  failureChartInstance = echarts.init(failureChartRef.value);

  const pieData = failureData.value.map((r: any) => ({
    name: emptyReasonMap[r.reason] || r.reason,
    value: Number(r.count),
  }));

  failureChartInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        data: pieData,
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
        label: { formatter: '{b}\n{d}%' },
      },
    ],
  });
};

// ========== 低置信问题 ==========
const lowConfidenceLoading = ref(false);
const lowConfidenceData = ref<any[]>([]);

const lowConfidenceColumns = [
  { title: '问题', dataIndex: 'query', key: 'query', width: '30%', ellipsis: true },
  { title: '改写问题', dataIndex: 'condenseQuestion', key: 'condenseQuestion', width: '25%', ellipsis: true },
  { title: 'Top Score', dataIndex: 'topScore', key: 'topScore', width: '12%' },
  { title: '引用数', dataIndex: 'finalCitationCount', key: 'finalCitationCount', width: '8%' },
  { title: '检索耗时(ms)', dataIndex: 'retrievalTimeMs', key: 'retrievalTimeMs', width: '12%' },
  { title: '空召回原因', dataIndex: 'emptyRecallReason', key: 'emptyRecallReason', width: '13%' },
];

const fetchLowConfidence = async () => {
  if (!selectedKbId.value) return;
  lowConfidenceLoading.value = true;
  try {
    const res: any = await resultControl(
      await urlResquest.getRetrievalDiagnosis({
        ...getParams(),
        data_type: 'low_confidence',
        top_k: 20,
      })
    );
    lowConfidenceData.value = (res.data || []).map((r: any, i: number) => ({
      ...r,
      key: i,
      topScore: Number(r.top_score),
      finalCitationCount: r.final_citation_count,
      retrievalTimeMs: r.retrieval_time_ms,
      emptyRecallReason: r.empty_recall_reason,
      condenseQuestion: r.condense_question,
    }));
  } catch (e: any) {
    message.error(e.msg || '获取低置信问题失败');
  } finally {
    lowConfidenceLoading.value = false;
  }
};

// ========== 诊断记录明细 ==========
const diagnosisListLoading = ref(false);
const diagnosisListData = ref<any[]>([]);
const diagnosisListPagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: false,
  showTotal: (total: number) => `共 ${total} 条`,
});

const diagnosisListColumns = [
  { title: '问题', dataIndex: 'query', key: 'query', width: '15%', ellipsis: true },
  { title: '改写问题', dataIndex: 'condenseQuestion', key: 'condenseQuestion', width: '15%', ellipsis: true },
  { title: '检索耗时(ms)', dataIndex: 'retrievalTimeMs', key: 'retrievalTimeMs', width: '10%' },
  { title: '候选数', dataIndex: 'candidateCount', key: 'candidateCount', width: '6%' },
  { title: 'Milvus命中', dataIndex: 'milvusHitCount', key: 'milvusHitCount', width: '8%' },
  { title: 'ES命中', dataIndex: 'esHitCount', key: 'esHitCount', width: '7%' },
  { title: 'Rerank', dataIndex: 'rerankUsed', key: 'rerankUsed', width: '7%' },
  { title: '最终引用数', dataIndex: 'finalCitationCount', key: 'finalCitationCount', width: '8%' },
  { title: 'Top Score', dataIndex: 'topScore', key: 'topScore', width: '8%' },
  { title: '空召回原因', dataIndex: 'emptyRecallReason', key: 'emptyRecallReason', width: '10%' },
  { title: '时间', dataIndex: 'timestamp', key: 'timestamp', width: '10%' },
];

const fetchDiagnosisList = async () => {
  if (!selectedKbId.value) return;
  diagnosisListLoading.value = true;
  try {
    const res: any = await resultControl(
      await urlResquest.getRetrievalDiagnosis({
        ...getParams(),
        data_type: 'list',
        page_id: diagnosisListPagination.value.current,
        page_limit: diagnosisListPagination.value.pageSize,
      })
    );
    const d = res.data || {};
    diagnosisListData.value = (d.records || []).map((r: any, i: number) => ({
      ...r,
      key: r.diagnosis_id || i,
      condenseQuestion: r.condense_question,
      retrievalTimeMs: r.retrieval_time_ms,
      candidateCount: r.candidate_count,
      milvusHitCount: r.milvus_hit_count,
      esHitCount: r.es_hit_count,
      rerankUsed: r.rerank_used,
      finalCitationCount: r.final_citation_count,
      topScore: Number(r.top_score)?.toFixed(4),
      emptyRecallReason: r.empty_recall_reason,
    }));
    diagnosisListPagination.value.total = d.total || 0;
  } catch (e: any) {
    message.error(e.msg || '获取诊断记录失败');
  } finally {
    diagnosisListLoading.value = false;
  }
};

const onDiagnosisListChange = (pagination: any) => {
  diagnosisListPagination.value.current = pagination.current;
  fetchDiagnosisList();
};

const onKbChange = () => {
  fetchAllData();
};

const onDateChange = () => {};

const fetchAllData = () => {
  fetchSummary();
  fetchFailure();
  fetchLowConfidence();
  diagnosisListPagination.value.current = 1;
  fetchDiagnosisList();
};

onMounted(async () => {
  await getList();
  if (knowledgeBaseList.value.length > 0 && !selectedKbId.value) {
    selectedKbId.value = knowledgeBaseList.value[0].kb_id;
  }
  fetchAllData();
});

onUnmounted(() => {
  if (summaryChartInstance) {
    summaryChartInstance.dispose();
    summaryChartInstance = null;
  }
  if (failureChartInstance) {
    failureChartInstance.dispose();
    failureChartInstance = null;
  }
});
</script>

<style scoped lang="scss">
.diagnosis-container {
  width: 100%;
  height: 100%;
  overflow-y: auto;
}

.filter-area {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.charts-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  flex: 1;
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
  min-height: 360px;

  &.chart-card-small {
    max-width: 400px;
  }
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #222222;
  margin-bottom: 12px;
}

.chart-loading,
.no-data {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 280px;
  color: #bfbfbf;
}

.chart-box {
  width: 100%;
  height: 280px;
}

.table-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 20px;
}
</style>
