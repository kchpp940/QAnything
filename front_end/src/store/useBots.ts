import { useRouter } from 'vue-router';
import { getTemplateById } from '@/config/sceneTemplates';

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

  const botList = ref([]);
  const setBotList = value => {
    botList.value = value;
  };

  const defaultBotList = ref([]);
  const setDefaultBotList = value => {
    defaultBotList.value = value;
  };

  const curBot = ref(null);
  const setCurBot = value => {
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

  const selectedTemplateId = ref('');
  const setSelectedTemplateId = (value: string) => {
    selectedTemplateId.value = value;
  };

  const userOverrides = ref<Record<string, any>>({});
  const setUserOverrides = (value: Record<string, any>) => {
    userOverrides.value = value;
  };

  const overriddenFields = ref<Set<string>>(new Set());

  const markFieldOverridden = (field: string) => {
    overriddenFields.value = new Set([...overriddenFields.value, field]);
  };
  const unmarkFieldOverridden = (field: string) => {
    const s = new Set(overriddenFields.value);
    s.delete(field);
    overriddenFields.value = s;
  };
  const isFieldOverridden = (field: string): boolean => {
    return overriddenFields.value.has(field);
  };

  const resetFieldToDefault = (field: string) => {
    const tpl = getTemplateById(selectedTemplateId.value);
    if (tpl) {
      const newVal = tpl.defaults[field];
      if (newVal !== undefined) {
        unmarkFieldOverridden(field);
        const newOverrides = { ...userOverrides.value };
        delete newOverrides[field];
        userOverrides.value = newOverrides;
      }
    }
  };

  const applyTemplate = (templateId: string) => {
    selectedTemplateId.value = templateId;
    userOverrides.value = {};
    overriddenFields.value = new Set();
  };

  const getMergedConfigValue = (field: string, fallback?: any) => {
    if (curBot.value && curBot.value.merged_config) {
      const val = curBot.value.merged_config[field];
      if (val !== undefined) return val;
    }
    const tpl = getTemplateById(selectedTemplateId.value);
    if (tpl && tpl.defaults[field] !== undefined) return tpl.defaults[field];
    return fallback;
  };

  const loadBotTemplateState = (botData: any) => {
    if (botData) {
      selectedTemplateId.value = botData.template_id || '';
      userOverrides.value = botData.user_overrides || {};
      overriddenFields.value = new Set((botData.overridden_fields as string[]) || []);
    } else {
      selectedTemplateId.value = '';
      userOverrides.value = {};
      overriddenFields.value = new Set();
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
    selectedTemplateId,
    setSelectedTemplateId,
    userOverrides,
    setUserOverrides,
    overriddenFields,
    markFieldOverridden,
    unmarkFieldOverridden,
    isFieldOverridden,
    resetFieldToDefault,
    applyTemplate,
    getMergedConfigValue,
    loadBotTemplateState,
  };
});
