<template>
  <div class="chart-container">
    <LineEchart
      v-if="!qaLoading"
      title="30天对话量:"
      format-desc="问答数量"
      :list="chatQAChartList"
    />
    <LineEchart
      v-if="!kbLoading"
      title="7天知识库上传文件情况:"
      format-desc="文件数量"
      :list="kbChartList"
    />
  </div>
</template>

<script setup lang="ts">
import { formatDate, getLastDaysRange } from '@/utils/utils';
import LineEchart, { type IChartList } from '@/views/Statistics/components/lineEchart.vue';
import { message } from 'ant-design-vue';
import { useUser } from '@/store/useUser';
import { api, type IKbStatusByDate } from '@/services/api';

const { userInfo } = useUser();

// 问答图表的处理

const qaLoading = ref(false);

const chatQAChartList = ref<IChartList[]>([]);

const handleQAInfo = (byDate: Array<{ date: string; count: number }>) => {
  chatQAChartList.value.push({
    data: byDate.map(item => ({
      name: item.date,
      value: item.count,
    })),
  });
};

// 获取对话记录相关信息
const getQAInfo = async () => {
  qaLoading.value = true;
  const { time_start, time_end } = getLastDaysRange(30);
  try {
    const result = await api.statistics.getQAOverviewByDay({
      time_start,
      time_end,
    });
    handleQAInfo(result.byDate);
  } catch (e) {
    message.error((e as { msg?: string }).msg || '出错了');
  } finally {
    qaLoading.value = false;
  }
};

// 以下是kb图表的处理

// 处理后的知识库信息
const kbInfoData = ref<IKbStatusByDate[]>([]);

// 图表的信息
const kbChartList = ref<IChartList[]>([]);

const kbLoading = ref(true);

// 处理知识库信息
const handleKbInfo = (byDate: IKbStatusByDate[]) => {
  kbInfoData.value = byDate;
  handleKbChartList(kbInfoData.value);
};

// 处理表格的信息
const handleKbChartList = (kbInfoData: IKbStatusByDate[]) => {
  const listType = [
    {
      type: 'green' as const,
      color: '#91CC75',
      name: '成功',
    },
    {
      type: 'red' as const,
      color: '#EE6666',
      name: '失败',
    },
  ];
  listType.map(item => {
    kbChartList.value.push({
      options: {
        lineColor: item.color,
        name: item.name,
      },
      data: kbInfoData.map(info => ({
        name: formatDate(info.date, '-'),
        value: info.fileStatus[item.type] || 0,
      })),
    });
  });
};

// 获取知识库相关信息
const getKbInfo = async () => {
  try {
    const userKey = `user__${userInfo.phoneNumber}`;
    const result = await api.statistics.getKbStatusByDate({}, userKey);
    handleKbInfo(result.byDate);
  } catch (e) {
    message.error((e as { msg?: string }).msg || '出错了');
  } finally {
    kbLoading.value = false;
  }
};

onMounted(() => {
  getKbInfo();
  getQAInfo();
});
</script>

<style scoped lang="scss">
.chart-container {
  width: 100%;
  height: 100%;
}
</style>
