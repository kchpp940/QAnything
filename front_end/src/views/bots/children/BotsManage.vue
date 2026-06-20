<template>
  <div class="container">
    <div class="bots-manage">
      <div v-if="isLoading" class="loading">
        <a-spin :indicator="indicator" />
      </div>
      <div v-else>
        <BotList v-if="botList.length" />
        <BotsHome v-else />
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
import BotsHome from '@/components/Bots/BotsHome.vue';
import BotList from '@/components/Bots/BotList.vue';
import { useBots } from '@/store/useBots';
import { message } from 'ant-design-vue';
import { LoadingOutlined } from '@ant-design/icons-vue';
import type { IBotApiResponse } from '@/utils/types';

const { botList } = storeToRefs(useBots());
const { setBotList, fetchBotList } = useBots();
const isLoading = ref(true);

const indicator = h(LoadingOutlined, {
  style: {
    fontSize: '48px',
  },
  spin: true,
});

const getBotList = async () => {
  try {
    const res: IBotApiResponse[] = await fetchBotList();
    renderData(res, res.length, 0, 10);
  } catch (e) {
    message.error(e.msg || '获取Bot列表失败');
  }
  isLoading.value = false;
};

// 时间分片优化
const renderData = (data: Array<IBotApiResponse>, total: number, pageNum: number, pageSize: number) => {
  if (total <= 0) return;

  const renderCount = Math.min(total, pageSize);

  requestAnimationFrame(() => {
    const startIdx = pageNum * pageSize;
    const endIdx = startIdx + renderCount;
    const dataList = data.slice(startIdx, endIdx);
    setBotList([...botList.value, ...dataList]);
    renderData(data, total - renderCount, pageNum + 1, pageSize);
  });
};

onMounted(async () => {
  await getBotList();
});

onUnmounted(() => setBotList([]));
</script>
<style lang="scss" scoped>
.container {
  background-color: #26293b;
}

.bots-manage {
  width: 100%;
  height: calc(100vh - 64px);
  overflow: auto;
  background: #f3f6fd;
  border-radius: 12px 0 0 0;
  font-family: PingFang SC;

  .loading {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
}
</style>
