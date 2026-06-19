<template>
  <Teleport to="body">
    <a-modal
      v-model:open="newBotsVisible"
      :title="bots.createBots"
      centered
      :destroyOnClose="true"
      width="520px"
      wrap-class-name="new-bot-modal"
      :footer="null"
    >
      <div class="new-bots-comp">
        <a-form
          :model="formState"
          name="new_bots"
          class="new-bots-form"
          @finish="onFinish"
          @finishFailed="onFinishFailed"
        >
          <a-form-item name="name" :rules="[{ required: true, message: bots.nameCantEmpty }]">
            <div class="item-title">{{ bots.botName }} <span>*</span></div>
            <a-input
              class="name-input"
              v-model:value="formState.name"
              :placeholder="bots.inputName"
              show-count
              :maxlength="20"
              allow-clear
            />
          </a-form-item>
          <a-form-item name="introduction">
            <div class="item-title">{{ bots.botFunctionIntro }}</div>
            <a-textarea
              class="intro-input"
              v-model:value="formState.introduction"
              :placeholder="bots.introBotFunction"
              show-count
              :maxlength="200"
              :auto-size="{ minRows: 3, maxRows: 3 }"
            />
          </a-form-item>
          <a-form-item name="templateId">
            <div class="item-title">{{ bots.sceneTemplate }}</div>
            <div class="template-desc">{{ bots.templateDesc }}</div>
            <div class="template-list">
              <div
                :class="['template-item', selectedTemplateId === '' ? 'template-active' : '']"
                @click="onSelectTemplate('')"
              >
                <div class="template-icon">🚫</div>
                <div class="template-name">{{ bots.noTemplate }}</div>
              </div>
              <div
                v-for="tpl in SCENE_TEMPLATES"
                :key="tpl.id"
                :class="['template-item', selectedTemplateId === tpl.id ? 'template-active' : '']"
                @click="onSelectTemplate(tpl.id)"
              >
                <div class="template-icon">{{ tpl.icon }}</div>
                <div class="template-name">{{ isZh ? tpl.name : tpl.nameEn }}</div>
              </div>
            </div>
            <div v-if="selectedTemplateId && currentTemplate" class="template-preview">
              <div class="preview-label">
                {{ isZh ? currentTemplate.description : currentTemplate.descriptionEn }}
              </div>
            </div>
          </a-form-item>
          <a-form-item>
            <div class="footer">
              <a-button class="cancel-btn" @click="setNewBotsVisible(false)">
                {{ common.cancel }}
              </a-button>
              <a-button :loading="loading" type="primary" html-type="submit" class="login-form-btn">
                {{ common.confirm2 }}
              </a-button>
            </div>
          </a-form-item>
        </a-form>
      </div>
    </a-modal>
  </Teleport>
</template>
<script lang="ts" setup>
import { useBots } from '@/store/useBots';
import { useBotsChat } from '@/store/useBotsChat';
import urlResquest from '@/services/urlConfig';
import { resultControl } from '@/utils/utils';
import { message } from 'ant-design-vue';
import routeController from '@/controller/router';
import { getLanguage } from '@/language/index';
import { SCENE_TEMPLATES, getTemplateById } from '@/config/sceneTemplates';

const { changePage } = routeController();
const { newBotsVisible } = storeToRefs(useBots());
const { setNewBotsVisible, setCurBot, setTabIndex, applyTemplate } = useBots();
const { setQaList } = useBotsChat();
const bots = getLanguage().bots;
const common = getLanguage().common;
const isZh = getLanguage().common.type === 'zh';

interface FormState {
  name: string;
  introduction: string;
}

const loading = ref(false);
const selectedTemplateId = ref('');
const currentTemplate = computed(() => getTemplateById(selectedTemplateId.value));

const formState = reactive<FormState>({
  name: '',
  introduction: '',
});

const onSelectTemplate = (templateId: string) => {
  selectedTemplateId.value = templateId;
  applyTemplate(templateId);
};

const getBotInfo = async botId => {
  try {
    const res: any = await resultControl(await urlResquest.queryBotInfo({ bot_id: botId }));
    setCurBot(res[0]);
  } catch (e) {
    message.error(e.msg || '获取Bot信息失败');
  }
};

const onFinish = async (values: any) => {
  console.log('Success:', values);
  try {
    const createParams: any = {
      bot_name: values.name,
      description: values.introduction,
      template_id: selectedTemplateId.value || '',
      user_overrides: {},
    };
    const res: any = await resultControl(await urlResquest.createBot(createParams));
    await getBotInfo(res.bot_id);
    message.success(bots.creationSuccessful);
    setTabIndex(0);
    setQaList([]);
    formState.name = '';
    formState.introduction = '';
    selectedTemplateId.value = '';
    changePage(`/bots/${res.bot_id}/edit`);
  } catch (e) {
    message.error(e.msg || '创建失败');
  }
  setNewBotsVisible(false);
};

const onFinishFailed = (errorInfo: any) => {
  console.log('Failed:', errorInfo);
};
</script>
<style lang="scss" scoped>
.new-bots-comp {
  width: 100%;
  height: 100%;
  font-family: PingFang SC;
  .item-title {
    font-size: 14px;
    font-weight: 500;
    color: #222222;
    margin-bottom: 12px;
    span {
      color: #ff0000;
    }
  }
  .template-desc {
    font-size: 12px;
    color: #999999;
    margin-bottom: 12px;
  }
  .template-list {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    .template-item {
      flex: 1;
      min-width: 90px;
      max-width: 110px;
      padding: 10px 8px;
      border-radius: 8px;
      background: #f9f9fc;
      box-sizing: border-box;
      border: 1px solid #ededed;
      cursor: pointer;
      text-align: center;
      transition: all 0.2s;
      &:hover {
        border-color: #b8a8f0;
      }
      .template-icon {
        font-size: 22px;
        margin-bottom: 4px;
      }
      .template-name {
        font-size: 12px;
        color: #666666;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
    .template-active {
      border-color: #5a47e5;
      background: #eeecfc;
      .template-name {
        color: #5a47e5;
        font-weight: 500;
      }
    }
  }
  .template-preview {
    margin-top: 8px;
    padding: 8px 12px;
    background: #f9f9fc;
    border-radius: 6px;
    .preview-label {
      font-size: 12px;
      color: #888;
      line-height: 1.5;
    }
  }
  .footer {
    display: flex;
    justify-content: end;
    .cancel-btn {
      height: 32px;
      padding: 0 20px;
      margin-right: 16px;
    }
    .login-form-btn {
      height: 32px;
      padding: 0 20px;
      background: #5a47e5 !important;
    }
  }
}
</style>
