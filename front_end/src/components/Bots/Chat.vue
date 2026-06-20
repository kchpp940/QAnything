<template>
  <div class="bots-chat-container">
    <div class="my-page">
      <div class="header">
        <img src="@/assets/bots/bot-avatar.png" alt="avatar" />
        {{ botInfo.bot_name }}
      </div>
      <div id="chat" class="chat">
        <ul id="chat-ul" ref="scrollDom">
          <div class="ai">
            <div class="content">
              <img class="avatar" src="@/assets/home/ai-avatar.png" alt="头像" />
              <p class="question-text" v-html="botInfo.welcome_message"></p>
            </div>
          </div>
          <li v-for="(item, index) in QA_List" :key="index">
            <div v-if="item.type === 'user'" class="user">
              <img class="avatar" src="@/assets/home/avatar.png" alt="头像" />
              <p class="question-text">{{ item.question }}</p>
            </div>
            <div v-else class="ai">
              <div class="content">
                <img class="avatar" src="@/assets/home/ai-avatar.png" alt="头像" />
                <p
                  v-if="!item.onlySearch"
                  class="question-text"
                  :class="[
                    !item.source.length && !item?.picList?.length ? 'change-radius' : '',
                    item.showTools ? '' : 'flashing',
                  ]"
                >
                  <HighLightMarkDown v-if="item.answer" :content="item.answer" />
                  <span v-else>{{ item.answer }}</span>
                  <ChatInfoPanel
                    v-if="Object.keys(item?.itemInfo?.tokenInfo || {}).length"
                    :chat-item-info="item.itemInfo"
                  />
                </p>
              </div>
              <template v-if="item?.picList?.length">
                <div
                  v-for="(picItem, picIndex) in item.picList"
                  :key="picItem + picIndex"
                  :class="[
                    'data-picList',
                    !item.source.length && picIndex + 1 === item.picList.length
                      ? 'picList-radius'
                      : '',
                  ]"
                >
                  <a-image :width="150" :src="picItem" class="responsive-image" />
                </div>
              </template>
              <SourcePanel
                v-if="item.source.length"
                :sources="item.source"
                variant="bots"
                content-mode="html"
              />
              <div v-if="item.showTools" class="feed-back">
                <div class="reload-box" @click="reAnswer(item)">
                  <SvgIcon name="reload"></SvgIcon>
                  <span class="reload-text">{{ common.regenerate }}</span>
                </div>
                <div class="tools">
                  <SvgIcon
                    :style="{
                      color: item.copied ? '#4D71FF' : '',
                    }"
                    name="copy"
                    @click="myCopy(item)"
                  ></SvgIcon>
                  <SvgIcon
                    :style="{
                      color: item.like ? '#4D71FF' : '',
                    }"
                    name="like"
                    @click="like(item, $event)"
                  ></SvgIcon>
                  <SvgIcon
                    :style="{
                      color: item.unlike ? '#4D71FF' : '',
                    }"
                    name="unlike"
                    @click="unlike(item)"
                  ></SvgIcon>
                </div>
              </div>
            </div>
          </li>
          <div v-show="showLoading" class="stop-placeholder"></div>
          <div v-show="showLoading" ref="stopBtn" class="stop-btn">
            <a-button @click="stopChat">
              <template #icon>
                <SvgIcon name="stop" :class="showLoading ? 'loading' : ''"></SvgIcon>
              </template>
              {{ common.stop }}
            </a-button>
          </div>
        </ul>
      </div>
      <div class="question-box">
        <div class="question">
          <!--          <a-popover placement="topLeft">-->
          <!--            <template #content>-->
          <!--              <p v-if="network">退出联网检索</p>-->
          <!--              <p v-else>开启联网检索</p>-->
          <!--            </template>-->
          <!--            <span :class="['network', `network-${network}`]">-->
          <!--              <SvgIcon name="network" @click="networkChat" />-->
          <!--            </span>-->
          <!--          </a-popover>-->
          <!--          <a-popover v-if="chatType === 'share'" placement="topLeft">-->
          <!--            <template #content>-->
          <!--              <p v-if="control">{{ bots.multiTurnConversation2 }}</p>-->
          <!--              <p v-else>{{ bots.multiTurnConversation1 }}</p>-->
          <!--            </template>-->
          <!--            <span :class="['control', `control-${control}`]">-->
          <!--              <SvgIcon name="chat-control" @click="controlChat" />-->
          <!--            </span>-->
          <!--          </a-popover>-->

          <!--          <span v-if="chatType === 'share'" class="download" @click="downloadChat">-->
          <!--            <SvgIcon name="chat-download" />-->
          <!--          </span>-->
          <ChatTextarea v-model:input-value="question" :options="mentionOptions" @send="send">
            <a-button type="primary" :disabled="showLoading" @click="send">
              <SvgIcon name="sendplane"></SvgIcon>
            </a-button>
          </ChatTextarea>
          <!--          <a-input-->
          <!--            v-model:value="question"-->
          <!--            max-length="200"-->
          <!--            :placeholder="common.problemPlaceholder"-->
          <!--            @keyup.enter="send"-->
          <!--          >-->
          <!--            <template #suffix>-->
          <!--              <div class="send-plane">-->
          <!--                <a-button type="primary" :disabled="showLoading" @click="send">-->
          <!--                  <SvgIcon name="sendplane"></SvgIcon>-->
          <!--                </a-button>-->
          <!--              </div>-->
          <!--            </template>-->
          <!--          </a-input>-->
        </div>
      </div>
    </div>
    <div v-if="!botInfo.kb_ids || !botInfo.kb_ids.length" class="mask">
      <img src="@/assets/bots/lock.png" alt="icon" />
      <p>{{ bots.bindKbtoPreview }}</p>
    </div>
    <ChatSettingDialog ref="chatSettingForDialogRef" />
  </div>
  <DefaultModal :content="content" :confirm-loading="confirmLoading" @ok="confirm" />
</template>
<script lang="ts" setup>
import { message } from 'ant-design-vue';
import SvgIcon from '../SvgIcon.vue';
import { useBotsChat } from '@/store/useBotsChat';
import DefaultModal from '../DefaultModal.vue';
import { getLanguage } from '@/language/index';
import urlResquest from '@/services/urlConfig';
import { resultControl, throttle } from '@/utils/utils';
import { useChatSetting } from '@/store/useChatSetting';
import ChatInfoPanel from '@/components/ChatInfoPanel.vue';
import HighLightMarkDown from '@/components/HighLightMarkDown.vue';
import ChatSettingDialog from '@/components/ChatSettingDialog.vue';
import ChatTextarea from '@/components/ChatTextarea.vue';
import { useChatSession } from '@/composables/useChatSession';
import { useChatActions } from '@/composables/useChatActions';
import { useDownloadChat } from '@/composables/useDownloadChat';
import SourcePanel from '@/components/SourcePanel.vue';

const props = defineProps({
  chatType: {
    type: String,
    default: 'edit',
  },
  botInfo: {
    type: Object as any,
    default: () => {},
  },
});

const common = getLanguage().common;
const bots = getLanguage().bots;

const { QA_List } = storeToRefs(useBotsChat());
const { chatSettingFormActive } = storeToRefs(useChatSetting());

const question = ref('');

const scrollDom = ref(null);
const stopBtn = ref(null);

const scrollBottom = () => {
  nextTick(() => {
    scrollDom.value?.scrollIntoView(false);
  });
};

const checkSettingOk = inject('checkSettingOk') as Function;
const checkChatSetting = async () => {
  return await checkSettingOk();
};

const {
  showLoading,
  stopChat,
  send: chatSend,
} = useChatSession({
  QA_List,
  chatSetting: chatSettingFormActive,
  scrollBottom,
  buildExtraParams: () => ({
    bot_id: props.botInfo.bot_id,
  }),
  checkChatSetting,
  transformResponse: (response: string) => response.replaceAll('\n', '<br/>'),
  showErrorOnStreamError: false,
  extraAnswerFields: () => ({
    picList: null,
  }),
});

const {
  like: chatLike,
  unlike,
  myCopy,
  reAnswer,
} = useChatActions({
  onReAnswer: (q: string) => {
    question.value = q;
    handleSend();
  },
});

const throttledLike = throttle((item, e) => {
  chatLike(item, e);
}, 800);

const like = (item, e) => {
  throttledLike(item, e);
};

const mentionOptions = ref<string[]>([]);
const getMentionOptions = async () => {
  const res: any = await resultControl(
    await urlResquest.getTags({
      kb_ids: props.botInfo.kb_ids,
    })
  );
  mentionOptions.value = res.tags;
};
onMounted(() => {
  getMentionOptions();
});
watch(
  () => props.botInfo,
  () => {
    getMentionOptions();
  },
  {
    immediate: true,
    deep: true,
  }
);

const computedCallNumber = (q: string) => {
  const atCount = (q.match(/@/g) || []).length;
  return atCount <= 10;
};

const handleSend = async () => {
  if (!question.value.trim().length) {
    return;
  }
  if (showLoading.value) {
    message.warn('正在聊天中...请等待结束');
    return;
  }
  if (!(await checkChatSetting())) {
    message.error('模型设置错误，请先检查模型配置');
    return;
  }
  if (!computedCallNumber(question.value)) {
    message.error('不可@超过10个');
    return;
  }

  const q = question.value;
  question.value = '';
  scrollDom.value?.scrollIntoView(true);
  await chatSend(q);
};

const send = handleSend;

const { clearQAList } = useBotsChat();
const { confirmLoading, content, confirm } = useDownloadChat({
  showLoading,
  onClear: () => {
    clearQAList();
  },
});

scrollBottom();
</script>

<style lang="scss" scoped>
.bots-chat-container {
  width: 100%;
  height: calc(100% - 22px);
  // padding-top: 16px;
  border-radius: 12px;
  background: #fff;
  font-family: PingFang SC;
  position: relative;
  // background-color: #26293b;
}

.my-page {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  margin: 0 auto;
  // border-radius: 12px 0 0 0;
  // background: #f3f6fd;
}

.header {
  width: 100%;
  height: 52px;
  font-size: 14px;
  font-weight: 500;
  color: #222222;
  border-top-right-radius: 12px;
  border-top-left-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #ededed;

  img {
    width: 32px;
    height: 32px;
    margin-right: 8px;
  }
}

.chat {
  margin: 0 auto;
  width: calc(90% - 52px);
  // min-width: 900px;
  max-width: 1239px;
  flex: 1;
  // height: calc(100vh - 64px - 22px - 66px - 52px - 48px - 80px);
  overflow-x: hidden;
  overflow-y: auto;
  padding-top: 28px;

  #chat-ul {
    // background: #f3f6fd;
    position: relative;
  }

  .avatar {
    width: 32px;
    height: 32px;
    margin-right: 16px;
  }

  .user {
    display: flex;
    margin-bottom: 16px;

    .question-text {
      padding: 13px 20px;
      font-size: 14px;
      font-weight: normal;
      line-height: 22px;
      color: #222222;
      background: #e9e1ff;
      border-radius: 12px;
      word-wrap: break-word;
    }
  }

  .ai {
    margin: 16px 0 28px 0;

    .content {
      display: flex;

      .question-text {
        flex: 1;
        padding: 13px 20px;
        font-size: 14px;
        font-weight: normal;
        line-height: 22px;
        color: $title1;
        background: #f9f9fc;
        border-radius: 12px 12px 0 0;
        word-wrap: break-word;
      }

      .flashing {
        &:after {
          -webkit-animation: blink 1s steps(5, start) infinite;
          animation: blink 1s steps(5, start) infinite;
          content: '▋';
          margin-left: 0.25rem;
          vertical-align: baseline;
        }
      }

      .change-radius {
        border-radius: 12px;
      }
    }

    .data-picList {
      margin-left: 48px;
      background: #f9f9fc;
      padding: 10px 20px;
    }

    .picList-radius {
      border-radius: 0 0 12px 12px;
    }

    .feed-back {
      display: flex;
      height: 20px;
      margin-top: 8px;
      margin-left: 48px;

      .reload-box {
        display: flex;
        cursor: pointer;
        align-items: center;
        margin-right: auto;
        color: #5a47e5;

        .reload-text {
          height: 22px;
          line-height: 22px;
        }
      }

      .tools {
        display: flex;
        align-items: center;

        svg {
          margin-left: 16px;
        }
      }

      svg {
        width: 16px !important;
        height: 16px !important;
        cursor: pointer !important;
      }
    }
  }
}

.stop-btn {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 10px 0;
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);

  :deep(.ant-btn) {
    width: 92px;
    height: 32px;
    border: 1px solid #e2e2e2;
    color: $title2;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  svg {
    width: 12px;
    height: 12px;
    margin-right: 4px;
  }

  .loading {
    animation: loading 3s infinite;
  }
}

.stop-placeholder {
  width: 100%;
  height: 52px;
}

.question-box {
  // position: absolute;
  // bottom: 28px;
  // left: 280px;
  width: 100%;
  margin-top: 10px;

  .question {
    position: relative;
    width: 90%;
    // min-width: 900px;
    //max-width: 1239px;
    //height: 48px;
    margin: 0 auto;
    display: flex;
    align-items: center;

    .download,
    .delete,
    .network {
      cursor: pointer;
      padding: 8px;
      display: flex;
      margin-right: 16px;
      border-radius: 8px;
      background: #ffffff;
      border: 1px solid #e5e5e5;
      color: #666666;

      &:hover {
        border: 1px solid #5a47e5;
        color: #5a47e5;
      }

      svg {
        width: 24px;
        height: 24px;
      }

      &.network-true {
        border: 1px solid #5a47e5;
        color: #5a47e5;
      }

      &.network-false {
        border: 1px solid #e5e5e5;
        color: #666666;
      }
    }

    .send-plane {
      width: 56px;
      height: 36px;
      border-radius: 8px;
      color: #fff;
      background: #5a47e5;

      :deep(.ant-btn-primary) {
        height: 100%;
        display: flex;
        align-items: center;
        background: linear-gradient(300deg, #7b5ef2 1%, #c383fe 97%);
      }

      :deep(.ant-btn-primary:disabled) {
        background: linear-gradient(300deg, #7b5ef2 1%, #c383fe 97%);
        color: #fff !important;
        border-color: transparent !important;
      }

      svg {
        width: 24px;
        height: 24px;
      }
    }

    :deep(.ant-input-affix-wrapper) {
      width: 100%;
      max-width: 1108px;
      border-color: #e5e5e5;
      box-shadow: none !important;

      &:hover,
      &:focus,
      &:active {
        border-color: #5a47e5 !important;
        box-shadow: none !important;
      }
    }

    :deep(.ant-input:hover) {
      border-color: $baseColor;
    }

    :deep(.ant-input:focus) {
      border-color: $baseColor;
    }

    :deep(.ant-input-affix-wrapper) {
      padding: 4px 4px 4px 11px;
    }
  }
}

.mask {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  color: #fff;
  font-size: 16px;
  border-radius: 12px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: absolute;
  top: 0;
  left: 0;

  img {
    width: 40px;
    height: 40px;
    margin-bottom: 10px;
  }

  p {
    padding: 0 40px;
  }
}
</style>
<style lang="scss">
@keyframes shake {
  0% {
    transform: rotate(0deg);
  }

  10% {
    transform: rotate(10deg);
  }

  20% {
    transform: rotate(20deg);
  }
  30% {
    transform: rotate(20deg);
  }
  40% {
    transform: rotate(20deg);
  }

  50% {
    transform: rotate(15deg);
  }

  60% {
    transform: rotate(0deg);
  }
  70% {
    transform: rotate(-15deg);
  }
  80% {
    transform: rotate(-30deg);
  }
  90% {
    transform: rotate(-15deg);
  }

  100% {
    transform: rotate(0deg);
  }
}

@keyframes blink {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

@keyframes loading {
  0% {
    transform: rotate(0deg);
  }

  25% {
    transform: rotate(90deg);
  }
  50% {
    transform: rotate(180deg);
  }
  75% {
    transform: rotate(270deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
