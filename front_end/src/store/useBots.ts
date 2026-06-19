import { useRouter } from 'vue-router';
import urlConfig from '@/services/urlConfig';
import urlResquest from '@/services/index';
import { getTemplateById as getLocalTemplateById } from '@/config/sceneTemplates';

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

  const sceneTemplates = ref<any[]>([]);
  const templateSchemaVersion = ref('');
  const overridableFields = ref<string[]>([]);
  const templatesLoaded = ref(false);
  const templateDefaultsMap = ref<Record<string, Record<string, any>>>({});
  const noTemplateDefaults = ref<Record<string, any>>({});

  const fetchTemplates = async () => {
    if (templatesLoaded.value && sceneTemplates.value.length > 0) {
      return {
        templates: sceneTemplates.value,
        schema_version: templateSchemaVersion.value,
        overridable_fields: overridableFields.value,
      };
    }
    try {
      const res = await urlResquest.post(
        urlConfig.url.listBotTemplates.url,
        urlConfig.url.listBotTemplates.param
      );
      if (res && res.code === 200 && res.data) {
        sceneTemplates.value = res.data.templates || [];
        templateSchemaVersion.value = res.data.schema_version || '';
        overridableFields.value = res.data.overridable_fields || [];
        noTemplateDefaults.value = res.data.no_template_defaults || {};
        const map: Record<string, Record<string, any>> = {};
        for (const tpl of res.data.templates || []) {
          if (tpl.id && tpl.defaults) {
            map[tpl.id] = tpl.defaults;
          }
        }
        templateDefaultsMap.value = map;
        templatesLoaded.value = true;
        return res.data;
      }
    } catch (e) {
      console.warn('Failed to fetch templates from backend, using fallback local templates', e);
    }
    const localFallback = [
      {
        id: 'customer_service',
        name: '客服问答',
        nameEn: 'Customer Service',
        icon: '🧑‍💼',
        description: '简洁、礼貌的客服问答',
      },
      {
        id: 'enterprise_knowledge',
        name: '企业知识助手',
        nameEn: 'Enterprise Knowledge Assistant',
        icon: '🏢',
        description: '详尽的企业知识查询',
      },
      {
        id: 'code_doc_assistant',
        name: '代码文档助手',
        nameEn: 'Code Documentation Assistant',
        icon: '💻',
        description: '精确的代码和API说明',
      },
      {
        id: 'strict_citation',
        name: '严谨引用模式',
        nameEn: 'Strict Citation Mode',
        icon: '📋',
        description: '严格引用来源',
      },
    ];
    sceneTemplates.value = localFallback;
    templatesLoaded.value = true;
    return {
      templates: localFallback,
      schema_version: '',
      overridable_fields: [],
    };
  };

  const getTemplateDefaults = (templateId: string): Record<string, any> | null => {
    if (!templateId) return null;
    if (curBot.value && curBot.value.template_defaults && curBot.value.template_id === templateId) {
      return curBot.value.template_defaults;
    }
    if (templateDefaultsMap.value[templateId]) {
      return templateDefaultsMap.value[templateId];
    }
    const local = getLocalTemplateById(templateId);
    return local?.defaults || null;
  };

  const getTemplateById = (templateId: string) => {
    if (!templateId) return null;
    const fromBackend = sceneTemplates.value.find(t => t.id === templateId);
    if (fromBackend) {
      const defaults = getTemplateDefaults(templateId);
      return { ...fromBackend, defaults: defaults || {} };
    }
    return getLocalTemplateById(templateId);
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
    const defaults = getTemplateDefaults(selectedTemplateId.value);
    if (defaults && defaults[field] !== undefined) {
      unmarkFieldOverridden(field);
      const newOverrides = { ...userOverrides.value };
      delete newOverrides[field];
      userOverrides.value = newOverrides;
      return defaults[field];
    }
    return undefined;
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
    const defaults = getTemplateDefaults(selectedTemplateId.value);
    if (defaults && defaults[field] !== undefined) return defaults[field];
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
    sceneTemplates,
    templateSchemaVersion,
    overridableFields,
    templatesLoaded,
    templateDefaultsMap,
    noTemplateDefaults,
    fetchTemplates,
    getTemplateDefaults,
    getTemplateById,
  };
});
