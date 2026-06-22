<template>
  <div class="container">
    <div class="bot-edit">
      <div v-if="isLoading" class="loading">
        <a-spin :indicator="indicator" />
      </div>
      <div v-else>
        <div class="header">
          <img src="@/assets/bots/bot-avatar.png" alt="avatar" />
          <div class="name">{{ curBot?.name }}</div>
          <div class="tabs">
            <div
              v-for="item in tabList"
              :key="item.name"
              :class="[
                'tab-item',
                tabIndex === item.value ? 'tab-active' : '',
                (!curBot?.kbIds || !curBot?.kbIds.length) && item.value === 1 ? 'tab-disable' : '',
              ]"
              @click="changeEditTab(item.value)"
            >
              {{ item.name }}
            </div>
          </div>
        </div>
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>
<script lang="ts" setup>
import { useBots } from '@/store/useBots';
import { api } from '@/services/api';
import routeController from '@/controller/router';
import { message } from 'ant-design-vue';
import { LoadingOutlined } from '@ant-design/icons-vue';
import { getLanguage } from '@/language/index';

const { getCurrentRoute, changePage } = routeController();
const { tabIndex, curBot } = storeToRefs(useBots());
const { setTabIndex, setCurBot, setKnowledgeList } = useBots();

const bots = getLanguage().bots;

const tabList = [
  {
    name: bots.edit,
    value: 0,
  },
  {
    name: bots.publish,
    value: 1,
  },
];

const botId = ref(null);
const isLoading = ref(true);

const indicator = h(LoadingOutlined, {
  style: {
    fontSize: '48px',
  },
  spin: true,
});

const getKbList = async kbIds => {
  try {
    const res = await api.knowledge.getKbList();
    const list = res.filter(item => !/.*_FAQ$/.test(item.name));
    let kbs = [...list];
    console.log('kbs', kbs, kbIds);
    if (kbIds && kbIds.length) {
      kbs = kbs.map(kb => {
        // state: 0 未绑定 1 绑定
        if (kbIds.some(item => item === kb.id)) {
          kb.state = 1;
        } else {
          kb.state = 0;
        }
        return kb;
      });
    } else {
      kbs = kbs.map(kb => {
        kb.state = 0;
        return kb;
      });
    }
    console.log('kbs2', kbs);
    setKnowledgeList(kbs);
  } catch (e) {
    message.error(e.msg || '获取知识库列表失败');
  }
};

const getBotInfo = async botId => {
  try {
    const bot = await api.bot.getBot({ bot_id: botId });
    if (bot) {
      setCurBot(bot);
      getKbList(bot.kbIds);
    }
    isLoading.value = false;
  } catch (e) {
    message.error((e as { msg?: string }).msg || '获取Bot信息失败');
  }
};

init();
function init() {
  const route = getCurrentRoute();
  console.log('zj-route', route);
  botId.value = route.value.params.botId;
  getBotInfo(botId.value);
}

function changeEditTab(value) {
  if (value === 1 && (!curBot.value?.kbIds || !curBot.value?.kbIds.length)) {
    return;
  }
  if (tabIndex.value === value) {
    return;
  }
  setTabIndex(value);
  if (value === 0) {
    changePage(`/bots/${botId.value}/edit`);
  } else {
    changePage(`/bots/${botId.value}/publish`);
  }
}
</script>
<style lang="scss" scoped>
.container {
  background-color: #26293b;
}
.bot-edit {
  width: 100%;
  height: calc(100vh - 64px);
  background: #f3f6fd;
  border-radius: 12px 0 0 0;
  font-family: PingFang SC;
  padding: 22px 26px;
  .header {
    width: 100%;
    height: 40px;
    padding: 0 32px;
    display: flex;
    align-items: center;
    margin-bottom: 26px;
    img {
      width: 40px;
      height: 40px;
      margin-right: 16px;
    }
    .name {
      flex-grow: 1;
      font-size: 24px;
      font-weight: 500;
      color: #222222;
    }
    .tabs {
      width: 120px;
      display: flex;
      justify-content: space-between;
      .tab-item {
        font-size: 16px;
        font-weight: 500;
        color: #666666;
        cursor: pointer;
      }
      .tab-active {
        color: #5a47e5;
      }
      .tab-disable {
        color: #666666;
        cursor: not-allowed;
      }
    }
  }
  .loading {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
}
</style>
