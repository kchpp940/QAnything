import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import {
  api,
  IBot,
  IKnowledgeBase,
} from '@/services/api';

export const useBots = defineStore('useBots', () => {
  const route = useRouter();
  const getRouterName = () => {
    const name = route.currentRoute.value.name;
    console.log('zj-route-name', name);
    return name === 'edit' ? 0 : 1;
  };
  const newBotsVisible = ref(false);
  const setNewBotsVisible = value => {
    newBotsVisible.value = value;
  };
  const selectKnowledgeVisible = ref(false);
  const setSelectKnowledgeVisible = value => {
    selectKnowledgeVisible.value = value;
  };
  const copyUrlVisible = ref(false);
  const setCopyUrlVisible = value => {
    copyUrlVisible.value = value;
  };

  const tabIndex = ref(getRouterName());
  const setTabIndex = value => {
    tabIndex.value = value;
  };

  const QA_List = ref([]);
  const setQaList = value => {
    QA_List.value = value;
  };

  const botList = ref<IBot[]>([]);
  const setBotList = (value: IBot[]) => {
    botList.value = value;
  };

  const defaultBotList = ref<IBot[]>([]);
  const setDefaultBotList = (value: IBot[]) => {
    defaultBotList.value = value;
  };

  const curBot = ref<IBot | null>(null);
  const setCurBot = (value: IBot | null) => {
    curBot.value = value;
  };

  const knowledgeList = ref<IKnowledgeBase[]>([]);
  const setKnowledgeList = (value: IKnowledgeBase[]) => {
    knowledgeList.value = value;
  };

  const webUrl = ref('');
  const setWebUrl = value => {
    webUrl.value = value;
  };

  const fetchBotList = async (botId?: string): Promise<IBot[]> => {
    try {
      const params = botId ? { bot_id: botId } : {};
      const result = await api.bot.getBotList(params);
      setBotList(result.bots);
      setDefaultBotList(result.defaultBots);
      return result.bots;
    } catch (e) {
      message.error((e as { msg?: string }).msg || '获取Bot列表失败');
      return [];
    }
  };

  const fetchSingleBot = async (botId: string): Promise<IBot | null> => {
    try {
      const bot = await api.bot.getBot({ bot_id: botId });
      if (bot) setCurBot(bot);
      return bot;
    } catch (e) {
      message.error((e as { msg?: string }).msg || '获取Bot信息失败');
      return null;
    }
  };

  const fetchKnowledgeList = async (): Promise<IKnowledgeBase[]> => {
    try {
      const list = await api.knowledge.getKbList();
      setKnowledgeList(list);
      return list;
    } catch (e) {
      message.error((e as { msg?: string }).msg || '获取知识库列表失败');
      return [];
    }
  };

  return {
    newBotsVisible,
    setNewBotsVisible,
    botList,
    setBotList,
    tabIndex,
    setTabIndex,
    selectKnowledgeVisible,
    setSelectKnowledgeVisible,
    knowledgeList,
    setKnowledgeList,
    webUrl,
    setWebUrl,
    copyUrlVisible,
    setCopyUrlVisible,
    defaultBotList,
    setDefaultBotList,
    curBot,
    setCurBot,
    QA_List,
    setQaList,
    fetchBotList,
    fetchSingleBot,
    fetchKnowledgeList,
  };
});
