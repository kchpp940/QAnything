<template>
  <div class="bot-detail-edit-comp">
    <div class="name-avatar">
      <img src="@/assets/bots/bot-avatar.png" alt="avatar" />
      <a-input v-model:value="name" :placeholder="bots.inputBotName" show-count :maxlength="25" />
    </div>
    <div class="title">{{ bots.sceneTemplate }}</div>
    <div class="template-selector">
      <a-select
        v-model:value="activeTemplateId"
        :placeholder="bots.selectTemplate"
        style="width: 100%"
        @change="onTemplateChange"
      >
        <a-select-option value="">{{ bots.noTemplate }}</a-select-option>
        <a-select-option v-for="tpl in SCENE_TEMPLATES" :key="tpl.id" :value="tpl.id">
          {{ tpl.icon }} {{ isZh ? tpl.name : tpl.nameEn }}
        </a-select-option>
      </a-select>
    </div>
    <div v-if="activeTemplateId && currentTemplate" class="template-info-bar">
      <span class="template-info-text">{{
        isZh ? currentTemplate.description : currentTemplate.descriptionEn
      }}</span>
    </div>
    <div class="title-with-override">
      <span>{{ bots.roleSetting }}</span>
      <a-tag
        v-if="activeTemplateId && isFieldOverridden('prompt_setting')"
        color="orange"
        class="override-tag"
      >
        {{ bots.userModified }}
        <span class="reset-link" @click="resetField('prompt_setting')">
          {{ bots.resetToDefault }}
        </span>
      </a-tag>
      <a-tag v-else-if="activeTemplateId" color="blue" class="override-tag">
        {{ bots.templateDefault }}
      </a-tag>
    </div>
    <a-textarea
      v-model:value="roleSetting"
      class="role-setting-input"
      :auto-size="{ minRows: 7, maxRows: 7 }"
      :rows="7"
      @change="onFieldChange('prompt_setting')"
    />
    <div :class="['role-setting-length', matches && matches.length > 2000 ? 'over-length' : '']">
      {{ matches ? matches.length : 0 }} / 2000
    </div>
    <div class="title-with-override">
      <span>{{ bots.welcomeMessage }}</span>
      <a-tag
        v-if="activeTemplateId && isFieldOverridden('welcome_message')"
        color="orange"
        class="override-tag"
      >
        {{ bots.userModified }}
        <span class="reset-link" @click="resetField('welcome_message')">
          {{ bots.resetToDefault }}
        </span>
      </a-tag>
      <a-tag v-else-if="activeTemplateId" color="blue" class="override-tag">
        {{ bots.templateDefault }}
      </a-tag>
    </div>
    <a-textarea
      v-model:value="welcomeMessage"
      class="greeting-input"
      show-count
      :maxlength="100"
      :placeholder="bots.inputWelcomMsg"
      :auto-size="{ minRows: 6, maxRows: 6 }"
      :rows="6"
      @change="onFieldChange('welcome_message')"
    />
    <div class="title">{{ bots.associatedKb }}<span>*</span></div>
    <div v-for="(item, index) in curBot.kb_ids" :key="item" class="knowedge-item knowledge-info">
      <img class="knowledge-icon" src="@/assets/bots/knowledge.png" alt="knowledge" />
      <div class="kb-name">{{ curBot.kb_names[index] }}</div>
      <img
        class="remove-icon"
        src="@/assets/bots/remove.png"
        alt="remove"
        @click="removeKb(item)"
      />
    </div>
    <div class="knowedge-item add-knowledge-content" @click="setSelectKnowledgeVisible(true)">
      <img class="add-knowedge" src="@/assets/bots/add-knowedge.png" alt="icon" />
      {{ bots.clickAssociatedKb }}
    </div>
    <div class="title-with-override">
      <span>{{ bots.answerStyle }}</span>
      <a-tag
        v-if="activeTemplateId && isFieldOverridden('answer_style')"
        color="orange"
        class="override-tag"
      >
        {{ bots.userModified }}
        <span class="reset-link" @click="resetField('answer_style')">
          {{ bots.resetToDefault }}
        </span>
      </a-tag>
      <a-tag v-else-if="activeTemplateId" color="blue" class="override-tag">
        {{ bots.templateDefault }}
      </a-tag>
    </div>
    <a-select
      v-model:value="answerStyle"
      style="width: 100%; margin-bottom: 8px"
      @change="onFieldChange('answer_style')"
    >
      <a-select-option value="concise">{{ bots.answerStyleConcise }}</a-select-option>
      <a-select-option value="detailed">{{ bots.answerStyleDetailed }}</a-select-option>
      <a-select-option value="technical">{{ bots.answerStyleTechnical }}</a-select-option>
      <a-select-option value="strict_citation">
        {{ bots.answerStyleStrictCitation }}
      </a-select-option>
    </a-select>
    <div class="title">{{ common.modelSettingTitle }}</div>
    <ChatSettingForm ref="chatSettingFormRef" :context-length="QA_List.length" />
    <div class="chat-setting-form-footer">
      <a-button type="primary" style="width: auto" @click="handleOk">
        {{ common.confirmApplication }}
      </a-button>
    </div>
  </div>
</template>
<script lang="ts" setup>
import { useBots } from '@/store/useBots';
import urlResquest from '@/services/urlConfig';
import { resultControl } from '@/utils/utils';
import { message } from 'ant-design-vue';
import { getLanguage } from '@/language/index';
import ChatSettingForm from '@/components/ChatSettingForm.vue';
import { useChatSetting } from '@/store/useChatSetting';
import { useBotsChat } from '@/store/useBotsChat';
import {
  SCENE_TEMPLATES,
  getTemplateById,
  applyTemplateWithOverrides,
  computeUserOverrides,
} from '@/config/sceneTemplates';

const { curBot, knowledgeList, selectedTemplateId, userOverrides } = storeToRefs(useBots());
const { QA_List } = storeToRefs(useBotsChat());
const {
  setSelectKnowledgeVisible,
  setCurBot,
  applyTemplate,
  markFieldOverridden,
  isFieldOverridden,
  resetFieldToDefault,
  syncOverridesFromValues,
  loadBotTemplateState,
} = useBots();
const { setChatSettingConfigured } = useChatSetting();
const { chatSettingFormActive } = storeToRefs(useChatSetting());

const { bots, common } = getLanguage();
const isZh = getLanguage().common.type === 'zh';

const name = ref('');
const roleSetting = ref('');
const welcomeMessage = ref('');
const answerStyle = ref('');
const activeTemplateId = ref('');
const currentTemplate = computed(() => getTemplateById(activeTemplateId.value));
const matches: any = computed(() => roleSetting.value.match(/[^a-zA-Z\s]|\p{P}|\w+/g));

onMounted(() => {
  console.log('curBot', curBot.value);
  name.value = curBot.value.bot_name;
  welcomeMessage.value = curBot.value.welcome_message;
  roleSetting.value = curBot.value.prompt_setting;
  loadBotTemplateState(curBot.value);
  activeTemplateId.value = selectedTemplateId.value;
  if (selectedTemplateId.value) {
    const merged = applyTemplateWithOverrides(selectedTemplateId.value, userOverrides.value);
    roleSetting.value = merged.prompt_setting;
    welcomeMessage.value = merged.welcome_message;
    answerStyle.value = merged.answer_style || '';
  } else {
    const llm = curBot.value.llm_setting;
    const parsed = llm
      ? typeof llm === 'string'
        ? JSON.parse(llm).answer_style
        : llm?.answer_style
      : undefined;
    answerStyle.value = parsed || '';
  }
});

const onTemplateChange = (templateId: string) => {
  activeTemplateId.value = templateId;
  applyTemplate(templateId);
  if (templateId) {
    const tpl = getTemplateById(templateId);
    if (tpl) {
      roleSetting.value = tpl.defaults.prompt_setting;
      welcomeMessage.value = tpl.defaults.welcome_message;
      answerStyle.value = tpl.defaults.answer_style;
      message.success(bots.templateApplied);
    }
  }
};

const onFieldChange = (field: string) => {
  if (!activeTemplateId.value) return;
  const tpl = getTemplateById(activeTemplateId.value);
  if (!tpl) return;
  let currentVal: any;
  if (field === 'prompt_setting') currentVal = roleSetting.value;
  else if (field === 'welcome_message') currentVal = welcomeMessage.value;
  else if (field === 'answer_style') currentVal = answerStyle.value;
  if (currentVal !== tpl.defaults[field]) {
    markFieldOverridden(field);
  }
  syncCurrentOverrides();
};

const syncCurrentOverrides = () => {
  if (!activeTemplateId.value) return;
  const currentValues: Record<string, any> = {
    prompt_setting: roleSetting.value,
    welcome_message: welcomeMessage.value,
    answer_style: answerStyle.value,
  };
  syncOverridesFromValues(currentValues);
};

const resetField = (field: string) => {
  const tpl = getTemplateById(activeTemplateId.value);
  if (!tpl) return;
  const defaultVal = tpl.defaults[field];
  if (field === 'prompt_setting') roleSetting.value = defaultVal;
  else if (field === 'welcome_message') welcomeMessage.value = defaultVal;
  else if (field === 'answer_style') answerStyle.value = defaultVal;
  resetFieldToDefault(field);
  message.success(bots.templateReset);
};

const getBotInfo = async botId => {
  try {
    const res: any = await resultControl(await urlResquest.queryBotInfo({ bot_id: botId }));
    console.log('getBotInfo', res);
    setCurBot(res[0]);
  } catch (e) {
    message.error(e.msg || '获取Bot信息失败');
  }
};

const saveBotInfo = async () => {
  try {
    const updateParams: any = {
      bot_id: curBot.value.bot_id,
      bot_name: name.value,
      prompt_setting: roleSetting.value,
      welcome_message: welcomeMessage.value,
      only_need_search_results: chatSettingFormActive.value.capabilities.onlySearch,
      networking: chatSettingFormActive.value.capabilities.networkSearch,
      api_base: chatSettingFormActive.value.apiBase,
      api_key: chatSettingFormActive.value.apiKey,
      api_context_length: chatSettingFormActive.value.apiContextLength,
      top_p: chatSettingFormActive.value.top_P,
      temperature: chatSettingFormActive.value.temperature,
      top_k: chatSettingFormActive.value.top_K,
      model: chatSettingFormActive.value.apiModelName,
      max_token: chatSettingFormActive.value.maxToken,
      hybrid_search: chatSettingFormActive.value.capabilities.mixedSearch,
      chunk_size: chatSettingFormActive.value.chunkSize,
      rerank: chatSettingFormActive.value.capabilities.rerank,
      answer_style: answerStyle.value,
    };
    if (activeTemplateId.value) {
      updateParams.template_id = activeTemplateId.value;
      const currentValues: Record<string, any> = {
        prompt_setting: roleSetting.value,
        welcome_message: welcomeMessage.value,
        top_K: chatSettingFormActive.value.top_K,
        rerank: chatSettingFormActive.value.capabilities.rerank,
        networking: chatSettingFormActive.value.capabilities.networkSearch,
        hybrid_search: chatSettingFormActive.value.capabilities.mixedSearch,
        only_need_search_results: chatSettingFormActive.value.capabilities.onlySearch,
        temperature: chatSettingFormActive.value.temperature,
        top_P: chatSettingFormActive.value.top_P,
        answer_style: answerStyle.value,
      };
      const overrides = computeUserOverrides(activeTemplateId.value, currentValues);
      updateParams.user_overrides = JSON.stringify(overrides);
    } else {
      updateParams.template_id = '';
      updateParams.user_overrides = '{}';
    }
    await resultControl(await urlResquest.updateBot(updateParams));
    await getBotInfo(curBot.value.bot_id);
  } catch (e) {
    console.log('error--', e);
    message.error(e.msg || '保存失败，请重试');
  }
};

const removeKb = async data => {
  let kbIds = curBot.value.kb_ids;
  console.log('removeKb', data, kbIds);
  kbIds = kbIds.filter(item => item != data);
  try {
    await resultControl(
      await urlResquest.updateBot({
        bot_id: curBot.value.bot_id,
        kb_ids: kbIds,
      })
    );
    getBotInfo(curBot.value.bot_id);
    knowledgeList.value = knowledgeList.value.map(item => {
      if (item.kb_id === data) {
        item.state = item.state === 0 ? 1 : 0;
      }
      return item;
    });
    message.success(bots.removalSucessful);
  } catch (e) {
    message.error(e.msg || '请求失败');
  }
};

const chatSettingFormRef = ref<InstanceType<typeof ChatSettingForm>>();
const handleOk = async (_, msg = '应用成功') => {
  const checkRes = await chatSettingFormRef.value.onCheck();
  if (!Object.hasOwn(checkRes, 'errorFields')) {
    await saveBotInfo();
    setChatSettingConfigured(checkRes);
    message.success(msg);
    return true;
  }
  return false;
};

defineExpose({ handleOk });
</script>
<style lang="scss" scoped>
.bot-detail-edit-comp {
  width: calc(58% - 20px);
  height: calc(100% - 22px);
  padding: 26px;
  background: #fff;
  overflow: auto;

  .name-avatar {
    width: 100%;
    height: 56px;
    display: flex;
    align-items: center;

    img {
      width: 56px;
      height: 56px;
      margin-right: 16px;
    }

    .ant-input-affix-wrapper {
      height: 40px;
    }
  }

  .title {
    font-size: 16px;
    font-weight: 500;
    color: #222222;
    margin-top: 24px;
    margin-bottom: 12px;

    span {
      color: #ff0000;
    }
  }

  .title-with-override {
    font-size: 16px;
    font-weight: 500;
    color: #222222;
    margin-top: 24px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;

    span:first-child {
      flex-shrink: 0;
    }

    .override-tag {
      font-size: 11px;
      line-height: 18px;
      padding: 0 6px;
      border-radius: 4px;

      .reset-link {
        color: #5a47e5;
        cursor: pointer;
        margin-left: 4px;
        text-decoration: underline;
      }
    }
  }

  .template-selector {
    margin-bottom: 4px;
  }

  .template-info-bar {
    margin-bottom: 8px;
    padding: 8px 12px;
    background: #f0eeff;
    border-radius: 6px;

    .template-info-text {
      font-size: 12px;
      color: #5a47e5;
      line-height: 1.5;
    }
  }

  .save {
    width: 100%;
    margin-top: 22px;
    display: flex;
    justify-content: end;

    .save-btn {
      width: 68px;
      height: 32px;
      font-size: 14px;
      background: #5a47e5 !important;
      margin-top: 5px;
    }
  }

  .model-select {
    height: 40px;
    margin: 24px 0;
    display: flex;
    align-items: center;

    .model-title {
      margin: 0 28px 0 0;
    }

    .model-list {
      border-radius: 8px;
      font-size: 14px;
      display: flex;

      .model-item {
        height: 40px;
        width: 120px;
        text-align: center;
        line-height: 40px;
        box-sizing: border-box;
        border: 1px solid #ededed;
        cursor: pointer;

        &:first-child {
          border-radius: 8px 0 0 8px;
        }

        &:last-child {
          border-radius: 0 8px 8px 0;
        }
      }

      .model-item-active {
        color: #5a47e5;
        border: 1px solid #5a47e5;
        background: #eeecfc;
        font-weight: 500;
      }
    }
  }

  .knowedge-item {
    width: 100%;
    height: 56px;
    border-radius: 8px;
    background: #f9f9fc;
    font-size: 14px;
    padding: 0 20px;
    margin-top: 12px;
    display: flex;
    align-items: center;
  }

  .add-knowledge-content {
    justify-content: center;
    color: #999999;
    cursor: pointer;

    .add-knowedge {
      width: 20px;
      height: 20px;
      margin-right: 8px;
    }
  }

  .knowledge-info {
    display: flex;
    align-items: center;

    .knowledge-icon {
      width: 32px;
      height: 32px;
      margin-right: 12px;
    }

    .kb-name {
      flex-grow: 1;
      color: #222222;
    }

    .remove-icon {
      width: 20px;
      height: 20px;
      cursor: pointer;
    }
  }

  .role-setting-input {
    overflow: auto !important;
  }

  .role-setting-length {
    width: 100%;
    color: rgba(0, 0, 0, 0.45);
    text-align: end;
  }

  .over-length {
    color: #ff0000;
  }

  .chat-setting-form-footer {
    display: flex;
    justify-content: flex-end;
  }
}
</style>
<style lang="scss">
.bot-detail-edit-comp {
  .ant-input {
    color: #666666 !important;
  }
}
</style>
