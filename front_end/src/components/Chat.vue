<template>
  <HistoryChat
    :observer="observer"
    :observe-dom="observeDom"
    :qa-observe-dom="qaObserveDom"
    :qa-observer="qaObserver"
    :show-loading="showLoading"
    @scrollBottom="scrollBottom"
    @setObserveDom="setObserveDom"
    @setQaObserverDom="setQaObserverDom"
    @clearHistory="clearHistory"
  />
  <div class="container showSider">
    <div class="my-page">
      <div id="chat" ref="chatContainer" class="chat showSider">
        <ul id="chat-ul" ref="scrollDom">
          <li v-for="(item, index) in QA_List" :key="index">
            <div v-if="item.type === 'user'" class="user">
              <img class="avatar" src="../assets/home/avatar.png" alt="头像" />
              <p class="question-text">{{ item.question }}</p>
            </div>
            <div v-else class="ai">
              <img class="avatar" src="../assets/home/ai-avatar.png" alt="头像" />
              <div class="ai-content">
                <div class="ai-right">
                  <p
                    class="question-text"
                    :class="[
                      !item.source.length && !item?.picList?.length ? 'change-radius' : '',
                      item.showTools ? '' : 'flashing',
                    ]"
                  >
                    <HighLightMarkDown :content="item.answer.toString()" />
                    <ChatInfoPanel
                      v-if="Object.keys(item?.itemInfo?.tokenInfo || {}).length"
                      :chat-item-info="item.itemInfo"
                    />
                  </p>
                  <template v-if="item.source.length">
                    <div
                      :class="[
                        'source-total',
                        !showSourceIdxs.includes(index) ? 'source-total-last' : '',
                      ]"
                    >
                      <span v-if="language === 'zh'">
                        找到了{{ item.source.length }}个信息来源：
                      </span>
                      <span v-else> Found {{ item.source.length }} source of information </span>
                      <SvgIcon
                        v-show="!showSourceIdxs.includes(index)"
                        name="down"
                        @click="showSourceList(index)"
                      />
                      <SvgIcon
                        v-show="showSourceIdxs.includes(index)"
                        name="up"
                        @click="hideSourceList(index)"
                      />
                    </div>
                    <div v-show="showSourceIdxs.includes(index)" class="source-list">
                      <div
                        v-for="(sourceItem, sourceIndex) in item.source"
                        :key="sourceIndex"
                        class="data-source"
                      >
                        <p v-show="sourceItem.file_name" class="control">
                          <span class="tips">{{ common.dataSource }}{{ sourceIndex + 1 }}:</span>
                          <a
                            v-if="sourceItem.file_url.startsWith('http')"
                            :href="sourceItem.file_url"
                            target="_blank"
                          >
                            {{ sourceItem.file_name }}
                          </a>
                          <span
                            v-else
                            :class="[
                              'file',
                              checkFileType(sourceItem.file_name) ? 'filename-active' : '',
                            ]"
                            @click="handleChatSource(sourceItem)"
                          >
                            {{ sourceItem.file_name }}
                          </span>
                          <SvgIcon
                            v-show="sourceItem.showDetailDataSource"
                            name="iconup"
                            @click="hideDetail(item, sourceIndex)"
                          />
                          <SvgIcon
                            v-show="!sourceItem.showDetailDataSource"
                            name="icondown"
                            @click="showDetail(item, sourceIndex)"
                          />
                        </p>
                        <Transition name="sourceitem">
                          <div v-show="sourceItem.showDetailDataSource" class="source-content">
                            <!--                            <p v-html="sourceItem.content?.replaceAll('\n', '<br/>')"></p>-->
                            <HighLightMarkDown :content="sourceItem.content" />
                            <p class="score">
                              <span class="tips">{{ common.correlation }}</span>
                              {{ sourceItem.score }}
                            </p>
                          </div>
                        </Transition>
                      </div>
                    </div>
                  </template>
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
              </div>
            </div>
          </li>
        </ul>
      </div>
      <div v-if="showLoading" class="stop-btn">
        <a-button @click="stopChat">
          <template #icon>
            <SvgIcon name="stop" :class="showLoading ? 'loading' : ''"></SvgIcon>
          </template>
          {{ common.stop }}
        </a-button>
      </div>
      <div class="question-box">
        <div class="question">
          <ChatTextarea v-model:input-value="question" :options="mentionOptions" @send="send">
            <a-popover>
              <template #content>
                {{ selectList.length ? common.chatShare : common.chatShareNoChatId }}
              </template>
              <span
                :class="[
                  'question-icon',
                  showLoading || !selectList.length ? 'isPreventClick' : '',
                ]"
                @click="shareChat"
              >
                <SvgIcon name="chat-share" />
              </span>
            </a-popover>
            <a-popover placement="topLeft">
              <template #content>{{ common.chatToPic }}</template>
              <span
                :class="['question-icon', showLoading ? 'isPreventClick' : '']"
                @click="downloadChat"
              >
                <SvgIcon name="chat-download" />
              </span>
            </a-popover>
            <a-popover>
              <template #content>{{ common.clearChat }}</template>
              <span
                :class="['question-icon', showLoading ? 'isPreventClick' : '']"
                @click="deleteChat"
              >
                <SvgIcon name="chat-delete" />
              </span>
            </a-popover>
            <a-popover>
              <template #content>{{ common.modelSettingTitle }}</template>
              <span class="question-icon" @click="handleModalChange(true)">
                <SvgIcon name="chat-setting" />
              </span>
            </a-popover>
            <a-button type="primary" :disabled="showLoading" shape="circle" @click="send">
              <SvgIcon name="sendplane" />
            </a-button>
          </ChatTextarea>
        </div>
      </div>
    </div>
    <div class="scroll-btn-div">
      <img
        class="avatar"
        src="@/assets/home/scroll-down.png"
        alt="滑到底部"
        @click="scrollBottom"
      />
    </div>
  </div>
  <ChatSettingDialog ref="chatSettingForDialogRef" />
  <DefaultModal :content="content" :confirm-loading="confirmLoading" @ok="confirm" />
  <CopyUrlDialog />
</template>
<script lang="ts" setup>
import { throttle } from '@/utils/utils';
import { message } from 'ant-design-vue';
import SvgIcon from './SvgIcon.vue';
import { useKnowledgeBase } from '@/store/useKnowledgeBase';
import { useChat } from '@/store/useChat';
import DefaultModal from './DefaultModal.vue';
import urlResquest, { formatTimestamp, resultControl } from '@/services/urlConfig';
import { getLanguage } from '@/language';
import { useLanguage } from '@/store/useLanguage';
import ChatSettingDialog from '@/components/ChatSettingDialog.vue';
import HistoryChat from '@/components/Home/HistoryChat.vue';
import { useHomeChat } from '@/store/useHomeChat';
import HighLightMarkDown from '@/components/HighLightMarkDown.vue';
import { useChatSetting } from '@/store/useChatSetting';
import { useBots } from '@/store/useBots';
import CopyUrlDialog from '@/components/Bots/CopyUrlDialog.vue';
import ChatTextarea from '@/components/ChatTextarea.vue';
import { useChatSession } from '@/composables/useChatSession';
import { useChatActions } from '@/composables/useChatActions';
import { useChatSourceFile } from '@/composables/useChatSourceFile';
import { useDownloadChat } from '@/composables/useDownloadChat';

const common = getLanguage().common;

const { selectList, knowledgeBaseList } = storeToRefs(useKnowledgeBase());
const { QA_List, chatId, pageId, qaPageId, historyList } = storeToRefs(useHomeChat());
const { chatSettingFormActive } = storeToRefs(useChatSetting());
const { addHistoryList, updateHistoryList, addChatList, clearChatList } = useHomeChat();
const { setCopyUrlVisible, setWebUrl } = useBots();
const { language } = storeToRefs(useLanguage());
declare module _czc {
  const push: (array: any) => void;
}

const question = ref('');

const observeDom = ref(null);
const qaObserveDom = ref(null);

const chatContainer = ref(null);
const scrollDom = ref(null);

const scrollBottom = () => {
  nextTick(() => {
    scrollDom.value?.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
    });
  });
};

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      console.log('entry.isIntersecting');
      pageId.value++;
    }
  });
});

const qaObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      console.log('qa entry.isIntersecting');
      qaPageId.value++;
    }
  });
});

onMounted(() => {
  scrollBottom();
});

onBeforeUnmount(() => {
  if (observeDom.value) {
    observer.unobserve(observeDom.value);
  }
  if (qaObserveDom.value) {
    qaObserver.unobserve(qaObserveDom.value);
  }
});

const { handleChatSource, checkFileType } = useChatSourceFile();

const chatSettingForDialogRef = ref<InstanceType<typeof ChatSettingDialog>>();
const checkChatSetting = () => {
  return chatSettingForDialogRef.value.handleOk();
};

const {
  showLoading,
  stopChat,
  send: chatSend,
} = useChatSession({
  QA_List,
  chatSetting: chatSettingFormActive,
  scrollBottom,
  beforeSend: (q: string) => {
    try {
      if (chatId.value !== null) return;
      let title = q;
      if (title.length > 100) {
        title = title.substring(0, 100);
      }
      chatId.value = addHistoryList(title);
      updateChat(title, chatId.value, selectList.value);
    } catch (e) {
      message.error(e.msg || '创建对话失败');
    }
  },
  buildExtraParams: () => ({
    kb_ids: selectList.value,
  }),
  checkChatSetting,
  onChatListUpdate: () => {
    addChatList(chatId.value, QA_List.value);
  },
});

const {
  showSourceIdxs,
  like: chatLike,
  unlike,
  myCopy,
  reAnswer,
  showDetail,
  hideDetail,
  showSourceList,
  hideSourceList,
} = useChatActions({
  onReAnswer: (q: string) => {
    question.value = q;
    handleSend();
  },
});

const throttledLike = throttle((item, e) => {
  chatLike(item, e);
  _czc.push(['_trackEvent', 'qanything', '问答页面', '点赞', '', '']);
}, 800);

const like = (item, e) => {
  throttledLike(item, e);
};

const computedCallNumber = (q: string) => {
  const atCount = (q.match(/@/g) || []).length;
  return atCount <= 10;
};

const mentionOptions = ref<string[]>([]);
const getMentionOptions = async () => {
  const res: any = await resultControl(
    await urlResquest.getTags({
      kb_ids: selectList.value,
    })
  );
  mentionOptions.value = res.tags;
};
watch(
  () => selectList,
  () => {
    getMentionOptions();
  },
  {
    immediate: true,
    deep: true,
  }
);

function checkKbSelect() {
  if (!selectList.value.length) {
    return;
  }
  const list = [];
  selectList.value.forEach(kbId => {
    if (knowledgeBaseList.value.some(item => item.kb_id === kbId)) {
      list.push(kbId);
    }
  });
  selectList.value = list;
  historyList.value.forEach(item => {
    if (
      chatId.value !== null &&
      item.historyId === chatId.value &&
      item.kbIds.join('') !== selectList.value.join('')
    ) {
      updateChat(item.title, item.historyId, selectList.value);
    }
  });
}

const updateChat = (title: string, chatId: number, knowledgeListSelect) => {
  try {
    updateHistoryList(title, chatId, knowledgeListSelect);
  } catch (e) {
    message.error(e.msg || '更新对话失败');
  }
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

  checkKbSelect();
  if (!selectList.value.length) {
    return message.warning(common.chooseError);
  } else {
    message.info({
      content:
        common.type === 'zh'
          ? `已选择 ${selectList.value.length} 个知识库进行问答`
          : ` ${selectList.value.length} knowledge base has been selected`,
      icon: ' ',
    });
  }

  const q = question.value;
  question.value = '';
  await chatSend(q);
};

const send = handleSend;

const shareChat = async () => {
  if (selectList.value.length === 0) return;
  try {
    const { bot_id } = (await resultControl(
      await urlResquest.createBot({
        bot_name: 'bot-' + formatTimestamp(Date.now()),
        description: '来源: 知识库创建-' + formatTimestamp(Date.now()),
      })
    )) as any;
    await resultControl(
      await urlResquest.updateBot({
        bot_id,
        kb_ids: [...selectList.value],
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
      })
    );
    setCopyUrlVisible(true);
    const { origin, pathname } = window.location;
    setWebUrl(`${origin + pathname}#/bots/${bot_id}/share`);
  } catch (e) {
    message.error(e?.msg || '分享失败');
  }
};

const { confirmLoading, content, downloadChat, deleteChat, confirm } = useDownloadChat({
  showLoading,
  onClear: () => {
    clearChatList(chatId.value);
    chatId.value = null;
    QA_List.value = [];
  },
});

const { showSettingModal } = storeToRefs(useChat());
const handleModalChange = newVal => {
  showSettingModal.value = newVal;
};

const setObserveDom = value => {
  observeDom.value = value;
};

const setQaObserverDom = value => {
  qaObserveDom.value = value;
};

function clearHistory() {
  console.log('清空');
}
</script>

<style lang="scss" scoped>
$avatar-width: 96px;

.container {
  position: relative;
  // padding-top: 16px;
  height: calc(100%);
  // margin-top: 65px;

  &.showSider {
    height: calc(100vh - 64px - 64px);
  }
}

.my-page {
  position: relative;
  height: 100%;
  margin: 0 auto;
  padding: 28px 28px 0 28px;
  //border-radius: 12px 0 0 0;
  //border-top-color: #26293b;
  display: flex;
  flex-direction: column;
  background: #f3f6fd;
  overflow: hidden;
}

.chat {
  margin: 0 auto;
  width: 100%;
  max-width: 816px;
  //min-width: 500px;
  padding: 28px 0 0 0;
  flex: 1;
  overflow-y: auto;

  &.showSider {
    //height: calc(100vh - 280px);
  }

  #chat-ul {
    //padding-bottom: 20px;
    display: flex;
    flex-direction: column;
    background: #f3f6fd;
    overflow: hidden;
  }

  .avatar {
    width: 32px;
    height: 32px;
    margin-right: 16px;
  }

  .user {
    display: flex;
    flex-direction: row-reverse;
    justify-content: flex-start;
    margin-bottom: 16px;

    .avatar {
      margin: 0 0 0 16px;
    }

    .question-text {
      padding: 13px 20px;
      margin-left: 48px;
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
    display: flex;

    .ai-content {
      display: flex;
      flex-direction: column;
      padding-right: 48px;
      min-width: 20%;

      .question-text {
        flex: 1;
        padding: 13px 20px;
        font-size: 14px;
        font-weight: normal;
        line-height: 22px;
        color: $title1;
        background: #fff;
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

    .source-total {
      padding: 10px 20px;
      background: #fff;
      display: flex;
      align-items: center;

      span {
        margin-right: 5px;
      }

      svg {
        width: 16px !important;
        height: 16px !important;
        cursor: pointer !important;
      }
    }

    .source-total-last {
      border-radius: 0px 0 12px 12px;
    }

    .source-list {
      background: #fff;
      border-radius: 0px 12px 12px 12px;
    }

    .data-source {
      padding: 13px 20px;
      font-size: 14px;
      line-height: 22px;
      color: $title1;

      .control {
        display: flex;
        align-items: center;
      }

      .score {
        margin-top: 26px;
      }

      .source-content {
        margin-top: 26px;
      }

      .tips {
        min-width: 78px;
        height: 22px;
        line-height: 22px;
        color: $title2;
        margin-right: 8px;
      }

      .file {
        color: $baseColor;
        margin-right: 8px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .filename-active {
        color: #5a47e5;
        text-decoration: underline;
        cursor: pointer;
      }

      svg {
        width: 14px;
        height: 14px;
        color: $baseColor;
        cursor: pointer;
      }

      a {
        color: #5a47e5;
        text-decoration: underline;
        cursor: pointer;
      }
    }

    .feed-back {
      display: flex;
      height: 20px;
      margin-top: 8px;

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
  margin: 18px 0;

  :deep(.ant-btn) {
    width: 92px;
    height: 32px;
    border: 1px solid #e2e2e2;
    color: $title2;
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

.question-box {
  width: 100%;
  margin: 32px 0;

  .question {
    position: relative;
    max-width: calc(816px - $avatar-width);
    //width: 40%;
    //min-width: 550px;
    margin: 0 auto;
    display: flex;
    align-items: center;

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

    .send-box {
      position: relative;
      width: 100%;
      height: 100%;
      display: none;
      flex-direction: column;
      justify-content: flex-end;
      align-items: center;
      background-color: #fff;
      border: 1px solid #d9d9d9;
      border-radius: 18px;

      &:hover {
        border-color: $baseColor;
        transition: border-color 0.3s, height 0s;
      }

      &:not(:hover) {
        border-color: #d9d9d9;
        transition: border-color 0.3s;
      }

      &:focus {
        box-shadow: 0 0 0 2px rgba(5, 145, 255, 0.1);
      }

      .send-textarea {
        //position: absolute;
        //bottom: 0;
        min-height: 42px;
        line-height: 25px;
        padding: 11px 15px;
        display: flex;
        align-items: center;
        font-size: 14px;
        border-radius: 18px;
      }
    }

    .send-action {
      width: 100%;
      height: 40px;
      padding-right: 10px;
      display: flex;
      justify-content: flex-end;
      align-items: center;
      color: #fff;
      z-index: 101;

      .isPreventClick {
        cursor: not-allowed !important;
      }

      .question-icon {
        cursor: pointer;
        padding: 8px;
        display: flex;
        margin-right: 16px;
        border-radius: 50%;
        background: #ffffff;
        //border: 1px solid #e5e5e5;
        color: #666666;

        &:hover {
          //border: 1px solid #5a47e5;
          background-color: #e5e5e5;
          color: #5a47e5;
        }

        svg {
          width: 18px;
          height: 18px;
        }
      }

      :deep(.ant-btn-primary) {
        width: 36px;
        height: 26px;
        padding: 8px 10px 8px 8px;
        border-radius: 18px;
        display: flex;
        justify-content: center;
        align-items: center;
        background: linear-gradient(300deg, #7b5ef2 1%, #c383fe 97%);
      }

      :deep(.ant-btn-primary:disabled) {
        //height: 36px;
        display: flex;
        justify-content: center;
        align-items: center;
        background: linear-gradient(300deg, #7b5ef2 1%, #c383fe 97%);
        color: #fff !important;
        border-color: transparent !important;
      }

      svg {
        width: 24px;
        height: 24px;
      }
    }
  }
}

.scroll-btn-div {
  position: absolute;
  bottom: 120px;
  right: 32px;
  cursor: pointer;

  svg {
    width: 20px;
    height: 20px;
    margin-top: 5px;
  }
}

.sourceitem-leave, // 离开前,进入后透明度是1
.sourceitem-enter-to {
  opacity: 1;
}

.sourceitem-leave-active,
.sourceitem-enter-active {
  transition: opacity 0.5s; //过度是.5s秒
}

.sourceitem-leave-to,
.sourceitem-enter {
  opacity: 0;
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
