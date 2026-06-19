<template>
  <a-config-provider :theme="{ token: { colorPrimary: '#5a47e5' } }">
    <div class="bots-chat-container">
      <div class="header">
        <img src="@/assets/bots/bot-avatar.png" alt="avatar" />
        {{ botInfo.bot_name }}
      </div>
      <div class="my-page">
        <div id="chat" ref="chatContainer" class="chat showSider">
          <ul id="chat-ul" ref="scrollDom">
            <li class="ai">
              <img class="avatar" src="@/assets/home/ai-avatar.png" alt="头像" />
              <div class="ai-content">
                <div class="ai-right">
                  <p class="question-text welcome" v-html="botInfo.welcome_message"></p>
                </div>
              </div>
            </li>
            <li v-for="(item, index) in QA_List" :key="index">
              <div v-if="item.type === 'user'" class="user">
                <img class="avatar" src="@/assets/home/avatar.png" alt="头像" />
                <p class="question-text">{{ item.question }}</p>
              </div>
              <div v-else class="ai">
                <img class="avatar" src="@/assets/home/ai-avatar.png" alt="头像" />
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
                      <div v-if="item.web_search_trace" class="web-search-trace">
                        <div class="trace-header">
                          <span
                            :class="[
                              'trace-status',
                              item.web_search_trace.triggered ? 'status-triggered' : 'status-skipped',
                            ]"
                          >
                            {{
                              item.web_search_trace.triggered
                                ? common.webSearchEnabled
                                : common.webSearchDisabled
                            }}
                          </span>
                          <span class="trace-reason">
                            {{ getTriggerReasonText(item.web_search_trace.trigger_reason) }}
                          </span>
                        </div>
                        <div class="trace-stats">
                          <span class="stat-item">
                            <span class="stat-label">{{ common.sourceTypeLocal }}:</span>
                            <span class="stat-value">{{ item.web_search_trace.local_doc_count }}</span>
                          </span>
                          <span class="stat-item">
                            <span class="stat-label">{{ common.sourceTypeWeb }}:</span>
                            <span class="stat-value">{{ item.web_search_trace.web_result_count }}</span>
                          </span>
                          <span v-if="item.web_search_trace.web_ratio > 0" class="stat-item">
                            <span class="stat-label">{{ common.webSearchResultRatio }}:</span>
                            <span class="stat-value">{{
                              (item.web_search_trace.web_ratio * 100).toFixed(1)
                            }}%</span>
                          </span>
                          <span v-if="item.web_search_trace.local_recall_score > 0" class="stat-item">
                            <span class="stat-label">{{ common.localRecallScore }}:</span>
                            <span class="stat-value">{{ item.web_search_trace.local_recall_score.toFixed(3) }}</span>
                          </span>
                          <span v-if="item.web_search_trace.execution_time_ms > 0" class="stat-item">
                            <span class="stat-label">{{ common.webExecutionTime }}:</span>
                            <span class="stat-value">{{ item.web_search_trace.execution_time_ms }}ms</span>
                          </span>
                        </div>
                      </div>

                      <div
                        :class="[
                          'source-total',
                          !showSourceIdxs.includes(index) ? 'source-total-last' : '',
                        ]"
                      >
                        <span v-if="language === 'zh'">
                          找到了{{ item.source.length }}个信息来源
                          <span class="source-stats">
                            （{{ common.sourceTypeLocal }}: {{ getLocalSourceCount(item.source) }}，
                            {{ common.sourceTypeWeb }}: {{ getWebSourceCount(item.source) }}）
                          </span>
                        </span>
                        <span v-else>
                          Found {{ item.source.length }} source of information
                          <span class="source-stats">
                            ({{ common.sourceTypeLocal }}: {{ getLocalSourceCount(item.source) }},
                            {{ common.sourceTypeWeb }}: {{ getWebSourceCount(item.source) }})
                          </span>
                        </span>
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
                        <div v-if="getLocalSourceCount(item.source) > 0" class="source-group">
                          <div class="source-group-header">
                            <SvgIcon name="icon-database" class="group-icon" />
                            <span class="group-title">{{ common.sourceGroupLocal }}</span>
                            <span class="group-count">({{ getLocalSourceCount(item.source) }})</span>
                          </div>
                          <div
                            v-for="(sourceItem, sourceIndex) in getLocalSources(item.source)"
                            :key="'local-' + sourceIndex"
                            :class="['data-source', 'source-local']"
                          >
                            <p v-show="sourceItem.file_name" class="control">
                              <span class="tips">{{ common.dataSource }}{{ sourceIndex + 1 }}:</span>
                              <span :class="['source-type-tag', 'trust-high']">
                                {{ common.trustLevelHigh }}
                              </span>
                              <span
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
                                <HighLightMarkDown :content="sourceItem.content" />
                                <p class="score">
                                  <span class="tips">{{ common.correlation }}</span>
                                  {{ sourceItem.score }}
                                </p>
                              </div>
                            </Transition>
                          </div>
                        </div>
                        <div v-else class="source-group-empty">
                          {{ common.noLocalResults }}
                        </div>

                        <div v-if="getWebSourceCount(item.source) > 0" class="source-group">
                          <div class="source-group-header source-group-header-web">
                            <SvgIcon name="network-search" class="group-icon" />
                            <span class="group-title">{{ common.sourceGroupWeb }}</span>
                            <span class="group-count">({{ getWebSourceCount(item.source) }})</span>
                            <span :class="['source-type-tag', 'trust-medium', 'group-tag']">
                              {{ common.trustLevelMedium }}
                            </span>
                          </div>
                          <div
                            v-for="(sourceItem, sourceIndex) in getWebSources(item.source)"
                            :key="'web-' + sourceIndex"
                            :class="['data-source', 'source-web']"
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
                                <HighLightMarkDown :content="sourceItem.content" />
                                <p class="score">
                                  <span class="tips">{{ common.correlation }}</span>
                                  {{ sourceItem.score }}
                                </p>
                                <p class="web-meta">
                                  <span v-if="sourceItem.web_timestamp" class="web-time">
                                    {{ formatWebTimestamp(sourceItem.web_timestamp) }}
                                  </span>
                                </p>
                              </div>
                            </Transition>
                          </div>
                        </div>
                        <div v-else class="source-group-empty">
                          {{ common.noWebResults }}
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
              <a-popover placement="topLeft">
                <template #content>{{ common.chatToPic }}</template>
                <span
                  :class="['download', showLoading ? 'isPreventClick' : '']"
                  @click="downloadChat"
                >
                  <SvgIcon name="chat-download" />
                </span>
              </a-popover>
              <a-popover>
                <template #title>{{ common.contextLabel }}</template>
                <template #content>
                  <a-slider
                    v-model:value="chatSettingFormActive.context"
                    :min="0"
                    :max="11"
                    :step="1"
                    :tip-formatter="sliderFormatter"
                  />
                </template>
                <span class="setting">
                  <SvgIcon name="chat-setting" />
                </span>
              </a-popover>
              <a-button type="primary" :disabled="showLoading" shape="circle" @click="send">
                <SvgIcon name="sendplane" />
              </a-button>
            </ChatTextarea>
            <!--            <div class="send-box">-->
            <!--              <a-textarea-->
            <!--                v-model:value="question"-->
            <!--                class="send-textarea"-->
            <!--                max-length="200"-->
            <!--                :bordered="false"-->
            <!--                :placeholder="common.problemPlaceholder"-->
            <!--                :auto-size="{ minRows: 1, maxRows: 8 }"-->
            <!--                @keydown="textKeydownHandle"-->
            <!--              />-->
            <!--              &lt;!&ndash;            @pressEnter="send"&ndash;&gt;-->
            <!--              <div class="send-action"></div>-->
            <!--            </div>-->
          </div>
        </div>

        <div v-if="!botInfo.kb_ids || !botInfo.kb_ids.length" class="mask">
          <img src="@/assets/bots/lock.png" alt="icon" />
          <p>{{ bots.bindKbtoPreview }}</p>
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
  </a-config-provider>
  <DefaultModal :content="content" :confirm-loading="confirmLoading" @ok="confirm" />
</template>
<script lang="ts" setup>
import { apiBase } from '@/services';
import { IChatItem, IChatSetting, MakePartial } from '@/utils/types';
import { useThrottleFn, useClipboard } from '@vueuse/core';
import { message } from 'ant-design-vue';
import SvgIcon from '../SvgIcon.vue';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useBotsChat } from '@/store/useBotsChat';
import { useChat } from '@/store/useChat';
import { useChatSource } from '@/store/useChatSource';
import { Typewriter } from '@/utils/typewriter';
import DefaultModal from '../DefaultModal.vue';
import html2canvas from 'html2canvas';
import { getLanguage } from '@/language/index';
import { useLanguage } from '@/store/useLanguage';
import urlResquest from '@/services/urlConfig';
import { ChatInfoClass, resultControl } from '@/utils/utils';
import ChatInfoPanel from '@/components/ChatInfoPanel.vue';
import HighLightMarkDown from '@/components/HighLightMarkDown.vue';
import ChatTextarea from '@/components/ChatTextarea.vue';
import { useUser } from '@/store/useUser';

const props = defineProps({
  chatType: {
    type: String,
    default: 'edit',
  },
  botInfo: {
    type: Object as any,
    default: () => {},
  },
  virtualUserId: {
    type: String,
    default: 'user',
  },
});

const common = getLanguage().common;
const bots = getLanguage().bots;

const typewriter = new Typewriter((str: string) => {
  if (str) {
    QA_List.value[QA_List.value.length - 1].answer += str || '';
  }
});

const { QA_List } = storeToRefs(useBotsChat());

const { copy } = useClipboard();
const { setChatSourceVisible, setSourceType, setSourceUrl, setTextContent } = useChatSource();
const { language } = storeToRefs(useLanguage());
const { userInfo } = useUser();
declare module _czc {
  const push: (array: any) => void;
}

// 当前问的问题
const question = ref('');

// 格式化 chatSetting
type ShareSettingType = MakePartial<IChatSetting, 'modelType'>;
// eslint-disable-next-line vue/no-setup-props-destructure
const { llm_setting } = props.botInfo;
const chatSetting = JSON.parse(llm_setting);
const chatSettingFormActive = ref<ShareSettingType>();
// 初始化 chatSetting 为自己的格式
onMounted(() => {
  chatSettingFormActive.value = {
    apiKey: chatSetting.api_key,
    apiBase: chatSetting.api_base,
    apiModelName: chatSetting.model,
    apiContextLength: chatSetting.api_context_length,
    maxToken: chatSetting.max_token,
    chunkSize: chatSetting.chunk_size,
    temperature: chatSetting.temperature,
    context: 0,
    top_K: chatSetting.top_k,
    top_P: chatSetting.top_p,
    webSearchPolicy: chatSetting.web_search_policy || 'disabled',
    capabilities: {
      onlySearch: chatSetting.only_need_search_results,
      mixedSearch: chatSetting.hybrid_search,
      networkSearch: chatSetting.networking,
      rerank: chatSetting.rerank,
    },
    active: true,
  };
});

// 上下文条数，无限制tooltip
const sliderFormatter = (value: number) => {
  // 11代表无限制，所以最后发送的时候如果是11，需要做无限制处理
  return value >= 11 ? '无限制' : value;
};

//问答的上下文
const history = computed(() => {
  const context = chatSettingFormActive.value.context;
  if (context === 0) return [];
  const usefulChat = QA_List.value.filter(item => item.type === 'ai');
  const historyChat = context === 11 ? usefulChat : usefulChat.slice(-context);
  return historyChat.map(item => [item.question, item.answer]);
});

//当前是否回答中
const showLoading = ref(false);

const showSourceIdxs = ref([]);

//取消请求用
let ctrl: AbortController;

const chatContainer = ref(null);

const scrollDom = ref(null);

const scrollBottom = () => {
  nextTick(() => {
    nextTick(() => {
      scrollDom.value?.scrollIntoView({
        behavior: 'smooth',
        block: 'end',
      });
    });
  });
};

onMounted(() => {
  scrollBottom();
});

const like = useThrottleFn((item, e) => {
  item.like = !item.like;
  item.unlike = false;
  _czc.push(['_trackEvent', 'qanything', '问答页面', '点赞', '', '']);
  if (item.like) {
    e.target.parentNode.style.animation = 'shake ease-in .5s';
    const timer = setTimeout(() => {
      clearTimeout(timer);
      e.target.parentNode.style.animation = '';
    }, 600);
  }
}, 800);
const unlike = (item: IChatItem) => {
  item.unlike = !item.unlike;
  item.like = false;
  _czc.push(['_trackEvent', 'qanything', '问答页面', '点踩', '', '']);
};

//拷贝
const myCopy = (item: IChatItem) => {
  copy(item.answer)
    .then(() => {
      item.copied = !item.copied;
      message.success(common.copySuccess, 1);
      const timer = setTimeout(() => {
        clearTimeout(timer);
        item.copied = !item.copied;
      }, 1000);
    })
    .catch(() => {
      message.error(common.copyFailed, 1);
    });
};

const addQuestion = q => {
  QA_List.value.push({
    question: q,
    type: 'user',
  });
  scrollBottom();
};

const addAnswer = (question: string) => {
  QA_List.value.push({
    answer: '',
    question,
    onlySearch: chatSettingFormActive.value.capabilities.onlySearch,
    type: 'ai',
    copied: false,
    like: false,
    unlike: false,
    source: [],
    showTools: false,
    web_search_trace: undefined,
  });
};

const chatInfoClass = new ChatInfoClass<ShareSettingType>();

const stopChat = () => {
  if (ctrl) {
    ctrl.abort('停止对话');
  }
  typewriter.done();
  showLoading.value = false;
  QA_List.value[QA_List.value.length - 1].showTools = true;
};

// 问答前处理 判断创建对话
const beforeSend = title => {
  try {
    // 判断需不需要新建对话, 为null直接跳出
    if (title.length > 100) {
      title = title.substring(0, 100);
    }
  } catch (e) {
    message.error(e.msg || '创建对话失败');
  }
};

// Mention 的 配置项
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
// 统计几个 @ 超过10个报错
const computedCallNumber = (question: string) => {
  const atCount = (question.match(/@/g) || []).length;
  return atCount <= 10;
};

//发送问答消息
const send = async () => {
  if (!question.value.trim().length) {
    return;
  }
  if (showLoading.value) {
    message.warn('正在聊天中...请等待结束');
    return;
  }
  if (!computedCallNumber(question.value)) {
    message.error('不可@超过10个');
    return;
  }

  const q = question.value;
  beforeSend(q);
  question.value = '';
  addQuestion(q);
  showLoading.value = true;
  ctrl = new AbortController();

  const sendData = {
    user_id: props.virtualUserId,
    user_info: userInfo.phoneNumber,
    bot_id: props.botInfo.bot_id,
    history: history.value,
    question: q,
    streaming: chatSettingFormActive.value.capabilities.onlySearch === false,
    networking: chatSettingFormActive.value.capabilities.networkSearch,
    web_search_policy: chatSettingFormActive.value.webSearchPolicy || 'disabled',
    product_source: 'saas',
    rerank: chatSettingFormActive.value.capabilities.rerank,
    only_need_search_results: chatSettingFormActive.value.capabilities.onlySearch,
    hybrid_search: chatSettingFormActive.value.capabilities.mixedSearch,
    max_token: chatSettingFormActive.value.maxToken,
    api_base: chatSettingFormActive.value.apiBase,
    api_key: chatSettingFormActive.value.apiKey,
    model: chatSettingFormActive.value.apiModelName,
    api_context_length: chatSettingFormActive.value.apiContextLength,
    chunk_size: chatSettingFormActive.value.chunkSize,
    top_p: chatSettingFormActive.value.top_P,
    top_k: chatSettingFormActive.value.top_K,
    temperature: chatSettingFormActive.value.temperature,
  };

  // 如果是仅检索
  if (chatSettingFormActive.value.capabilities.onlySearch) {
    // 模型配置添加进去
    chatInfoClass.addChatSetting(chatSettingFormActive.value);
    addAnswer(q);
    try {
      const res: any = await resultControl(
        await urlResquest.sendQuestion(sendData, { signal: ctrl.signal })
      );
      if (res.code === 200) {
        QA_List.value[QA_List.value.length - 1].answer = res?.source_documents.length
          ? common.searchCompleted
          : common.searchNotFound;
        QA_List.value[QA_List.value.length - 1].source = res?.source_documents;
        if (res?.web_search_trace) {
          QA_List.value[QA_List.value.length - 1].web_search_trace = res.web_search_trace;
        }
      }
    } catch (e) {
      console.log('出错', e);
      // message.error(e.msg || '出错了');
      QA_List.value[QA_List.value.length - 1].answer = e.msg || 'error';
    }
    // 无论成不成功,结束后的操作
    showLoading.value = false;
    QA_List.value[QA_List.value.length - 1].showTools = true;
    await nextTick(() => {
      scrollBottom();
    });
  } else {
    fetchEventSource(apiBase + '/local_doc_qa/local_doc_chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: ['text/event-stream', 'application/json'],
      },
      openWhenHidden: true,
      body: JSON.stringify({
        ...sendData,
      }),
      signal: ctrl.signal,
      onopen(e: any) {
        console.log('open', e);
        addAnswer(q);
        if (e.ok && e.headers.get('content-type') === 'text/event-stream') {
          // 模型配置添加进去
          chatInfoClass.addChatSetting(chatSettingFormActive.value);
          typewriter.start();
        } else if (e.headers.get('content-type') === 'application/json') {
          typewriter.add('Error 请检查模型是否配置正确');
        }
      },
      onmessage(msg: { data: string }) {
        console.log('message', msg);
        const res: any = JSON.parse(msg.data);
        if (res?.code == 200 && res?.response && res.msg === 'success') {
          // 中间的回答
          // QA_List.value[QA_List.value.length - 1].answer += res.result.response;
          // typewriter.add(res?.response.replaceAll('\n', '<br/>'));
          typewriter.add(res?.response);
          scrollBottom();
        } else {
          // 最后一次回答
          const timeObj = res.time_record.time_usage;
          delete timeObj['retriever_search_by_milvus'];
          chatInfoClass.addTime(res.time_record.time_usage);
          chatInfoClass.addToken(res.time_record.token_usage);
          chatInfoClass.addDate(Date.now());
        }

        if (res?.source_documents?.length) {
          QA_List.value[QA_List.value.length - 1].source = res?.source_documents;
        }

        if (res?.web_search_trace) {
          QA_List.value[QA_List.value.length - 1].web_search_trace = res.web_search_trace;
        }

        if (res?.show_images?.length) {
          res?.show_images.map(item => {
            typewriter.add(item);
            console.log(QA_List.value.at(-1).answer);
          });
        }
      },
      onclose(e: any) {
        console.log('close', e);
        typewriter.done();
        ctrl.abort();
        showLoading.value = false;
        QA_List.value[QA_List.value.length - 1].showTools = true;
        // 将chat info添加进回答中
        QA_List.value.at(-1).itemInfo = chatInfoClass.getChatInfo();
        nextTick(() => {
          scrollBottom();
        });
      },
      onerror(err: any) {
        console.log('error', err);
        typewriter?.done();
        ctrl?.abort();
        showLoading.value = false;
        QA_List.value[QA_List.value.length - 1].showTools = true;
        message.error(err.msg || '出错了');
        nextTick(() => {
          scrollBottom();
        });
        throw err;
      },
    });
  }
};

const reAnswer = (item: IChatItem) => {
  console.log('reAnswer');
  question.value = item.question;
  send();
};

//点击查看是否显示详细来源
const showDetail = (item: IChatItem, index) => {
  item.source[index].showDetailDataSource = !item.source[index].showDetailDataSource;
};

const hideDetail = (item: IChatItem, index) => {
  item.source[index].showDetailDataSource = false;
};

const showSourceList = index => {
  showSourceIdxs.value.push(index);
};

const hideSourceList = index => {
  showSourceIdxs.value = showSourceIdxs.value.filter(item => item !== index);
};

const getLocalSourceCount = sources => {
  if (!sources || !sources.length) return 0;
  return sources.filter(s => !s.file_url?.startsWith('http')).length;
};

const getWebSourceCount = sources => {
  if (!sources || !sources.length) return 0;
  return sources.filter(s => s.file_url?.startsWith('http')).length;
};

const getLocalSources = sources => {
  if (!sources || !sources.length) return [];
  return sources.filter(s => !s.file_url?.startsWith('http'));
};

const getWebSources = sources => {
  if (!sources || !sources.length) return [];
  return sources.filter(s => s.file_url?.startsWith('http'));
};

const getTriggerReasonText = reason => {
  const reasonMap: Record<string, string> = {
    policy_always: common.triggerReasonPolicyAlways,
    policy_low_recall: common.triggerReasonPolicyLowRecall,
    policy_manual: common.triggerReasonPolicyManual,
    skipped_disabled: common.triggerReasonSkippedDisabled,
    skipped_manual_off: common.triggerReasonSkippedManualOff,
    skipped_high_recall: common.triggerReasonSkippedHighRecall,
  };
  return reasonMap[reason] || reason;
};

const formatWebTimestamp = timestamp => {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleString();
};

//下载 清除聊天记录相关
const { showModal } = storeToRefs(useChat());
const confirmLoading = ref(false);
const content = ref('');
const type = ref('');
const downloadChat = () => {
  if (showLoading.value) return;
  type.value = 'download';
  showModal.value = true;
  content.value = common.saveTip;
};

const confirm = async () => {
  confirmLoading.value = true;
  if (type.value === 'download') {
    console.log('download');
    try {
      const ele = document.getElementById('chat-ul');
      const canvas = await html2canvas(ele as HTMLDivElement, {
        useCORS: true,
      });
      const imgUrl = canvas.toDataURL('image/png');
      const tempLink = document.createElement('a');
      tempLink.style.display = 'none';
      tempLink.href = imgUrl;
      tempLink.setAttribute('download', 'chat-shot.png');
      if (typeof tempLink.download === 'undefined') tempLink.setAttribute('target', '_blank');

      document.body.appendChild(tempLink);
      tempLink.click();
      document.body.removeChild(tempLink);
      window.URL.revokeObjectURL(imgUrl);
      message.success('下载成功');
      Promise.resolve();
    } catch (e) {
      console.log(e);
      message.error(e.message || e.msg || '出错了');
    }
  } else if (type.value === 'delete') {
    console.log('delete');
    QA_List.value = [];
  }
  type.value = '';
  content.value = '';
  confirmLoading.value = false;
  showModal.value = false;
};

// 检查信息来源的文件是否支持窗口化渲染
let supportSourceTypes = [
  'md',
  'txt',
  'pdf',
  'jpg',
  'png',
  'jpeg',
  'doc',
  'docx',
  'xls',
  'xlsx',
  'ppt',
  'pptx',
  'jsonl',
  'csv',
  'eml',
];
const checkFileType = filename => {
  if (!filename) {
    return false;
  }
  const arr = filename.split('.');
  if (arr.length) {
    const suffix = arr.pop();
    if (supportSourceTypes.includes(suffix)) {
      return true;
    } else {
      return false;
    }
  } else {
    return false;
  }
};

const handleChatSource = file => {
  console.log('handleChatSource', file);
  const isSupport = checkFileType(file.file_name);
  if (isSupport) {
    queryFile(file);
  }
};

async function queryFile(file) {
  try {
    setSourceUrl(null);
    const res: any = await resultControl(await urlResquest.getFile({ file_id: file.file_id }));
    console.log('queryFile', res);
    const suffix = file.file_name.split('.').pop();
    const b64Type = getB64Type(suffix);
    console.log('b64Type', b64Type);
    setSourceType(suffix);
    setSourceUrl(`data:${b64Type};base64,${res.file_base64}`);
    if (suffix === 'txt' || suffix === 'md' || suffix === 'csv' || suffix === 'eml') {
      const decodedTxt = atob(res.file_base64);
      const correctStr = decodeURIComponent(escape(decodedTxt));
      console.log('decodedTxt', correctStr);
      setTextContent(correctStr);
      setChatSourceVisible(true);
    } else {
      setChatSourceVisible(true);
    }
  } catch (e) {
    message.error(e.msg || '获取文件失败');
  }
}

let b64Types = [
  'text/markdown', // md
  'text/plain', // txt
  'application/pdf', // pdf
  'image/jpeg', // jpg
  'image/png', // png
  'image/jpeg', // jpeg
  'application/msword', // doc
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // docx
  'application/vnd.ms-excel', // xls
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // xlsx
  'application/vnd.ms-powerpoint', // ppt
  'application/vnd.openxmlformats-officedocument.presentationml.presentation', // pptx
  'application/jsonl', // jsonl
  'text/csv', // csv
  'message/rfc822', // eml
];

function getB64Type(suffix) {
  const index = supportSourceTypes.indexOf(suffix);
  return b64Types[index];
}
</script>

<style lang="scss" scoped>
$avatar-width: 96px;

.bots-chat-container {
  width: 100%;
  height: 100%;
  border-radius: 12px;
  background: #fff;
  font-family: PingFang SC;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
  box-sizing: border-box;
}

.header {
  width: 100%;
  padding: 0.25rem 0;
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

.my-page {
  position: relative;
  width: 100%;
  height: 100%;
  margin: 0 auto;
  padding: 28px 28px 0 28px;
  //border-radius: 12px 0 0 0;
  //border-top-color: #26293b;
  display: flex;
  flex-direction: column;
  background: #f3f6fd;
  overflow: hidden;
  box-sizing: border-box;
}

.chat {
  margin: 0 auto;
  width: 100%;
  max-width: 816px;
  //min-width: 500px;
  padding: 28px 0 0 0;
  flex: 1;
  overflow-y: auto;
  box-sizing: border-box;

  #chat-ul {
    //padding-bottom: 20px;
    display: flex;
    flex-direction: column;
    background: #f3f6fd;
    overflow: hidden;
    box-sizing: border-box;
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

      .welcome {
        border-radius: 12px;
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
      font-size: 14px;
      color: rgba(0, 0, 0, 0.88);

      span {
        margin-right: 5px;
      }

      .source-stats {
        color: #999;
        font-size: 12px;
        margin-left: 8px;
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

    .source-web {
      background: rgba(90, 71, 229, 0.03);
      border-left: 3px solid #5a47e5;
    }

    .source-type-tag {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      margin-right: 8px;
      line-height: 1.4;

      &.trust-high {
        background: rgba(82, 196, 26, 0.1);
        color: #52c41a;
      }

      &.trust-medium {
        background: rgba(250, 173, 20, 0.1);
        color: #faad14;
      }

      &.trust-low {
        background: rgba(255, 77, 79, 0.1);
        color: #ff4d4f;
      }
    }

    .web-meta {
      margin-top: 12px;
      font-size: 12px;
      color: #999;

      .web-time {
        margin-left: 12px;
      }
    }

    .web-search-trace {
      background: linear-gradient(135deg, #f0f4ff 0%, #f5f0ff 100%);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 12px;
      border: 1px solid #e0e5f5;

      .trace-header {
        display: flex;
        align-items: center;
        margin-bottom: 8px;

        .trace-status {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          margin-right: 8px;

          &.status-triggered {
            background: rgba(90, 71, 229, 0.1);
            color: #5a47e5;
          }

          &.status-skipped {
            background: rgba(153, 153, 153, 0.1);
            color: #999;
          }
        }

        .trace-reason {
          font-size: 13px;
          color: #666;
        }
      }

      .trace-stats {
        display: flex;
        flex-wrap: wrap;
        gap: 12px 20px;
        font-size: 12px;

        .stat-item {
          display: flex;
          align-items: center;

          .stat-label {
            color: #999;
            margin-right: 4px;
          }

          .stat-value {
            color: #333;
            font-weight: 500;
          }
        }
      }
    }

    .source-group {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      .source-group-header {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        background: #f5f7fa;
        border-radius: 6px 6px 0 0;
        font-size: 13px;
        font-weight: 500;
        color: #333;
        margin-bottom: 8px;

        .group-icon {
          width: 16px;
          height: 16px;
          margin-right: 6px;
        }

        .group-title {
          flex: 1;
        }

        .group-count {
          color: #999;
          font-weight: normal;
          margin-right: 8px;
        }

        .group-tag {
          margin-left: 8px;
          margin-right: 0;
        }

        &.source-group-header-web {
          background: rgba(90, 71, 229, 0.05);
          color: #5a47e5;
        }
      }

      .source-group-empty {
        padding: 16px;
        text-align: center;
        color: #bbb;
        font-size: 12px;
        background: #fafafa;
        border-radius: 6px;
      }

      .data-source {
        margin-left: 0;
        margin-bottom: 8px;

        &:last-child {
          margin-bottom: 0;
        }
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
  box-sizing: border-box;

  .question {
    position: relative;
    max-width: calc(816px - $avatar-width);
    //width: 40%;
    //min-width: 550px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    box-sizing: border-box;

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
      display: flex;
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

      .download,
      .delete,
      .setting {
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

@media (max-width: 1023px) {
  .chat {
    padding: 0 1rem;
  }
}

//@media (min-width: 1500px) {
//  .chat {
//    padding: 0 20%;
//  }
//}
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
