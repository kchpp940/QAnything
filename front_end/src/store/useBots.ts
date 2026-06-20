import { useRouter } from 'vue-router';
import urlResquest from '@/services/urlConfig';
import { resultControl } from '@/utils/utils';
import { message } from 'ant-design-vue';
import type { IBotApiResponse, ICurBot, IBotConfig } from '@/utils/types';
import {
  buildBotConfig,
  normalizeBotApiResponse,
  chatSettingFromBot,
  type BuildBotConfigOptions,
} from '@/utils/botConfig';
import type { IChatSetting } from '@/utils/types';

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

  const botList = ref<IBotApiResponse[]>([]);
  const setBotList = value => {
    botList.value = value;
  };

  const defaultBotList = ref([]);
  const setDefaultBotList = value => {
    defaultBotList.value = value;
  };

  const curBot = ref<ICurBot | null>(null);
  const setCurBot = (value: IBotApiResponse | null) => {
    curBot.value = value;
  };

  const knowledgeList = ref([]);
  const setKnowledgeList = value => {
    knowledgeList.value = value;
  };

  const webUrl = ref('');
  const setWebUrl = value => {
    webUrl.value = value;
  };

  // ========== Bot Config 统一 Action（唯一契约入口） ==========

  /**
   * 获取 Bot 列表，自动规范化每一项后存入 botList（可选）。
   * 返回规范化后的列表。
   */
  const fetchBotList = async (): Promise<IBotApiResponse[]> => {
    const res = await resultControl(
      await urlResquest.queryBotInfo()
    );
    const list: IBotApiResponse[] = (res || []).map(normalizeBotApiResponse);
    return list;
  };

  /**
   * 获取单个 Bot 信息并规范化，不写入 curBot（只读查询场景，如分享页）。
   */
  const fetchBotReadOnly = async (botId: string): Promise<IBotApiResponse> => {
    const res = await resultControl(
      await urlResquest.queryBotInfo({ bot_id: botId })
    );
    return normalizeBotApiResponse(res[0]);
  };

  /**
   * 获取 Bot 信息，自动规范化后存入 curBot。
   * 这是 curBot 唯一的写入入口，确保 store 中只存 normalized config。
   * 返回规范化后的 Bot 信息，同时调用者可以获得 kb_ids 以便后续调用 getKbList 等。
   */
  const fetchBotInfo = async (botId: string): Promise<IBotApiResponse> => {
    const normalized = await fetchBotReadOnly(botId);
    setCurBot(normalized);
    return normalized;
  };

  /**
   * 创建 Bot，自动获取并规范化新 Bot 信息。
   * 返回创建的 bot_id。
   */
  const createBot = async (opts: BuildBotConfigOptions): Promise<string> => {
    const bot_config = buildBotConfig(opts);
    const res = await resultControl(
      await urlResquest.createBot({ bot_config })
    );
    return res.bot_id;
  };

  /**
   * 更新 Bot，自动获取并规范化更新后的 Bot 信息。
   */
  const updateBot = async (botId: string, opts: BuildBotConfigOptions): Promise<IBotApiResponse> => {
    const bot_config = buildBotConfig(opts);
    await resultControl(
      await urlResquest.updateBot({ bot_id: botId, bot_config })
    );
    return fetchBotInfo(botId);
  };

  /**
   * 快捷方法：更新 Bot 的知识库绑定。
   * 组件不再直接拼 kb_ids 并调用 urlResquest.updateBot。
   */
  const updateBotKbIds = async (botId: string, kbIds: string[]): Promise<IBotApiResponse> => {
    return updateBot(botId, { kb_ids: kbIds });
  };

  /**
   * 从 curBot 获取 ChatSettingForm 所需的 IChatSetting。
   * 组件不再直接操作 curBot.llm_setting 进行字段转换。
   */
  const getChatSettingFromBot = (existingConfigured?: Partial<IChatSetting>): IChatSetting | null => {
    if (!curBot.value) return null;
    return chatSettingFromBot(curBot.value, existingConfigured);
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
    QA_List,
    setQaList,
    // ========== 统一契约 Action ==========
    fetchBotList,
    fetchBotReadOnly,
    fetchBotInfo,
    createBot,
    updateBot,
    updateBotKbIds,
    getChatSettingFromBot,
  };
});
