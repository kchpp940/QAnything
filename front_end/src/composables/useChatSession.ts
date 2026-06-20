import { apiBase } from '@/services';
import { IChatItem, IChatSetting, MakePartial } from '@/utils/types';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { message } from 'ant-design-vue';
import { ChatInfoClass } from '@/utils/utils';
import { Typewriter } from '@/utils/typewriter';
import { userId, userPhone } from '@/services/urlConfig';
import urlResquest, { resultControl } from '@/services/urlConfig';
import { getLanguage } from '@/language';

const common = getLanguage().common;

type ChatSettingType = IChatSetting | MakePartial<IChatSetting, 'modelType'>;

export interface UseChatSessionOptions {
  QA_List: Ref<IChatItem[]>;
  chatSetting: Ref<ChatSettingType>;
  scrollBottom: () => void;
  beforeSend?: (question: string) => void;
  buildExtraParams?: () => Record<string, any>;
  checkChatSetting?: () => Promise<boolean>;
  onChatListUpdate?: () => void;
  transformResponse?: (response: string) => string;
  showErrorOnStreamError?: boolean;
  extraAnswerFields?: () => Record<string, any>;
}

export function useChatSession(options: UseChatSessionOptions) {
  const {
    QA_List,
    chatSetting,
    scrollBottom,
    beforeSend,
    buildExtraParams,
    checkChatSetting,
    onChatListUpdate,
    transformResponse,
    showErrorOnStreamError = true,
    extraAnswerFields,
  } = options;

  const showLoading = ref(false);
  let ctrl: AbortController;

  const typewriter = new Typewriter((str: string) => {
    if (str) {
      QA_List.value[QA_List.value.length - 1].answer += str || '';
    }
  });

  const chatInfoClass = new ChatInfoClass<ChatSettingType>();

  const addQuestion = (q: string) => {
    QA_List.value.push({
      question: q,
      type: 'user',
    });
    scrollBottom();
  };

  const addAnswer = (question: string) => {
    const baseAnswer: IChatItem = {
      answer: '',
      question,
      onlySearch: chatSetting.value.capabilities.onlySearch,
      type: 'ai',
      copied: false,
      like: false,
      unlike: false,
      source: [],
      showTools: false,
    };
    const extra = extraAnswerFields?.() || {};
    QA_List.value.push({ ...baseAnswer, ...extra });
  };

  const history = computed(() => {
    const context = chatSetting.value.context;
    if (context === 0) return [];
    const usefulChat = QA_List.value.filter(item => item.type === 'ai');
    const historyChat = context === 11 ? usefulChat : usefulChat.slice(-context);
    return historyChat.map(item => [item.question, item.answer]);
  });

  const buildSendData = (question: string) => {
    const setting = chatSetting.value;
    return {
      kb_ids: [],
      history: history.value,
      question,
      streaming: setting.capabilities.onlySearch === false,
      networking: setting.capabilities.networkSearch,
      product_source: 'saas',
      rerank: setting.capabilities.rerank,
      only_need_search_results: setting.capabilities.onlySearch,
      hybrid_search: setting.capabilities.mixedSearch,
      max_token: setting.maxToken,
      api_base: setting.apiBase,
      api_key: setting.apiKey,
      model: setting.apiModelName,
      api_context_length: setting.apiContextLength,
      chunk_size: setting.chunkSize,
      top_p: setting.top_P,
      top_k: setting.top_K,
      temperature: setting.temperature,
    };
  };

  const stopChat = () => {
    if (ctrl) {
      ctrl.abort('停止对话');
    }
    typewriter.done();
    showLoading.value = false;
    QA_List.value[QA_List.value.length - 1].showTools = true;
  };

  const finishCurrentAnswer = () => {
    showLoading.value = false;
    QA_List.value[QA_List.value.length - 1].showTools = true;
    QA_List.value.at(-1).itemInfo = chatInfoClass.getChatInfo();
    onChatListUpdate?.();
    nextTick(() => {
      scrollBottom();
    });
  };

  const handleOnlySearch = async (sendData: any, question: string) => {
    chatInfoClass.addChatSetting(chatSetting.value);
    addAnswer(question);
    try {
      const res: any = await resultControl(
        await urlResquest.sendQuestion(sendData, { signal: ctrl.signal })
      );
      if (res.code === 200) {
        QA_List.value[QA_List.value.length - 1].answer = res?.source_documents.length
          ? common.searchCompleted
          : common.searchNotFound;
        QA_List.value[QA_List.value.length - 1].source = res?.source_documents;
      }
    } catch (e) {
      console.log('出错', e);
      QA_List.value[QA_List.value.length - 1].answer = e.msg || 'error';
    }
    showLoading.value = false;
    QA_List.value[QA_List.value.length - 1].showTools = true;
    onChatListUpdate?.();
    await nextTick(() => {
      scrollBottom();
    });
  };

  const handleStreaming = (sendData: any, question: string) => {
    fetchEventSource(apiBase + '/local_doc_qa/local_doc_chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: ['text/event-stream', 'application/json'],
      },
      openWhenHidden: true,
      body: JSON.stringify(sendData),
      signal: ctrl.signal,
      onopen(e: any) {
        console.log('open', e);
        addAnswer(question);
        if (e.ok && e.headers.get('content-type') === 'text/event-stream') {
          chatInfoClass.addChatSetting(chatSetting.value);
          typewriter.start();
        } else if (e.headers.get('content-type') === 'application/json') {
          typewriter.add('Error 请检查模型是否配置正确');
        }
      },
      onmessage(msg: { data: string }) {
        console.log('message', msg);
        const res: any = JSON.parse(msg.data);
        if (res?.code == 200 && res?.response && res.msg === 'success') {
          const responseText = transformResponse ? transformResponse(res?.response) : res?.response;
          typewriter.add(responseText);
          scrollBottom();
        } else {
          if (res?.time_record) {
            const timeObj = res.time_record.time_usage;
            delete timeObj['retriever_search_by_milvus'];
            chatInfoClass.addTime(res.time_record.time_usage);
            chatInfoClass.addToken(res.time_record.token_usage);
            chatInfoClass.addDate(Date.now());
          }
        }

        if (res?.source_documents?.length) {
          QA_List.value[QA_List.value.length - 1].source = res?.source_documents;
        }

        if (res?.show_images?.length) {
          res?.show_images.map((item: string) => {
            typewriter.add(item);
          });
        }
      },
      onclose(e: any) {
        console.log('close', e);
        typewriter.done();
        ctrl.abort();
        finishCurrentAnswer();
      },
      onerror(err: any) {
        console.log('error', err);
        typewriter?.done();
        ctrl?.abort();
        showLoading.value = false;
        QA_List.value[QA_List.value.length - 1].showTools = true;
        if (showErrorOnStreamError) {
          message.error(err.msg || '出错了');
        }
        onChatListUpdate?.();
        nextTick(() => {
          scrollBottom();
        });
        throw err;
      },
    });
  };

  const send = async (question: string) => {
    if (!question.trim().length) {
      return;
    }
    if (showLoading.value) {
      message.warn('正在聊天中...请等待结束');
      return;
    }
    if (checkChatSetting && !(await checkChatSetting())) {
      message.error('模型设置错误，请先检查模型配置');
      return;
    }

    beforeSend?.(question);

    addQuestion(question);
    onChatListUpdate?.();
    showLoading.value = true;
    ctrl = new AbortController();

    const baseSendData = buildSendData(question);
    const extraParams = buildExtraParams?.() || {};
    const sendData = {
      user_id: userId,
      user_info: userPhone,
      ...baseSendData,
      ...extraParams,
    };

    if (chatSetting.value.capabilities.onlySearch) {
      await handleOnlySearch(sendData, question);
    } else {
      handleStreaming(sendData, question);
    }
  };

  return {
    showLoading,
    stopChat,
    send,
    addQuestion,
    addAnswer,
    history,
    typewriter,
    chatInfoClass,
  };
}
