<template>
  <div class="bot-share">
    <div v-if="isLoading" class="loading">
      <a-spin :indicator="indicator" />
    </div>
    <ChatShare v-else :bot-info="botInfo" chat-type="share" />
    <ChatSourceDialog />
  </div>
</template>
<script lang="ts" setup>
import ChatShare from '@/components/Bots/ChatShare.vue';
import ChatSourceDialog from '@/components/ChatSourceDialog.vue';
import FingerprintJS from '@fingerprintjs/fingerprintjs';
import { useBots } from '@/store/useBots';
import { message } from 'ant-design-vue';
import routeController from '@/controller/router';
import { LoadingOutlined } from '@ant-design/icons-vue';

const { getCurrentRoute } = routeController();
const { fetchBotReadOnly } = useBots();
const botInfo = ref(null);
const botId = ref(null);
const isLoading = ref(true);
const userId = ref(null);

const indicator = h(LoadingOutlined, {
  style: {
    fontSize: '48px',
  },
  spin: true,
});

onMounted(() => {
  const meta = document.createElement('meta');
  meta.name = 'viewport';
  meta.content = 'width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover';
  meta.id = 'no-zoom';
  document.getElementsByTagName('head')[0].appendChild(meta);
});

onUnmounted(() => {
  document.title = 'Qanything';
  const meta = document.getElementById('no-zoom');
  if (meta) {
    meta.parentNode.removeChild(meta);
  }
});

init();

const getBotInfo = async botIdParam => {
  try {
    console.log('zj-botId', botIdParam);
    const info = await fetchBotReadOnly(botIdParam);
    botInfo.value = info;
    document.title = `Qanything-${info.bot_name}`;
    isLoading.value = false;
  } catch (e) {
    message.error(e.msg || '获取Bot信息失败');
  }
};

async function init() {
  try {
    const route = getCurrentRoute();
    botId.value = route.value.params.botId;
    const fp = await FingerprintJS.load();
    const result = await fp.get();
    userId.value = 'q' + result.visitorId;
    await getBotInfo(botId.value);
    console.log('visitorId', result.visitorId);
  } catch (error) {
    console.error('获取浏览器指纹失败', error);
  }
}
</script>
<style lang="scss" scoped>
.bot-share {
  width: 100%;
  height: 100%;
  margin: 0 auto;
  overflow: hidden;
  touch-action: manipulation;
  .loading {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
}
</style>
