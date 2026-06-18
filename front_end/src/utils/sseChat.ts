import { fetchEventSource } from '@microsoft/fetch-event-source';
import { Typewriter } from './typewriter';
import { ChatInfoClass } from './utils';
import { message } from 'ant-design-vue';

export type SseEventType = 'delta' | 'final' | 'error' | 'done';

export interface ISseDeltaData {
  response: string;
  time_record?: any;
}

export interface ISseFinalData {
  response: string;
  question?: string;
  model?: string;
  history?: any[];
  condense_question?: string;
  source_documents?: any[];
  retrieval_documents?: any[];
  time_record?: any;
  show_images?: string[];
}

export interface ISseErrorData {
  code: number;
  msg: string;
}

export interface IParsedSseMessage {
  event: SseEventType;
  data: any;
  isLegacy: boolean;
}

export function parseSseMessage(rawData: string): IParsedSseMessage | null {
  const trimmed = rawData.trim();

  if (!trimmed) {
    return null;
  }

  if (trimmed === '[DONE]') {
    return { event: 'done', data: {}, isLegacy: true };
  }

  try {
    const parsed = JSON.parse(trimmed);

    if (parsed && typeof parsed === 'object' && 'event' in parsed && 'data' in parsed) {
      const event = parsed.event as SseEventType;
      if (['delta', 'final', 'error', 'done'].includes(event)) {
        return { event, data: parsed.data || {}, isLegacy: false };
      }
    }

    if (parsed && typeof parsed === 'object') {
      if (parsed.code && parsed.code !== 200 && parsed.msg) {
        return {
          event: 'error',
          data: { code: parsed.code, msg: parsed.msg },
          isLegacy: true,
        };
      }

      const hasTimeUsage = !!(parsed.time_record && parsed.time_record.time_usage);
      const isDeltaShape = parsed.code === 200 && parsed.msg === 'success' && parsed.response !== undefined;

      if (isDeltaShape && !hasTimeUsage) {
        return {
          event: 'delta',
          data: {
            response: parsed.response,
            time_record: parsed.time_record,
          },
          isLegacy: true,
        };
      }

      if (parsed.response !== undefined || hasTimeUsage) {
        return {
          event: 'final',
          data: {
            response: parsed.response ?? '',
            question: parsed.question,
            model: parsed.model,
            history: parsed.history,
            condense_question: parsed.condense_question,
            source_documents: parsed.source_documents,
            retrieval_documents: parsed.retrieval_documents,
            time_record: parsed.time_record,
            show_images: parsed.show_images,
          },
          isLegacy: true,
        };
      }
    }

    return null;
  } catch (e) {
    console.error('SSE message parse error:', e, rawData);
    return null;
  }
}

export interface ISseChatHandlerOptions {
  typewriter: Typewriter;
  chatInfoClass: ChatInfoClass<any>;
  onDelta?: (data: ISseDeltaData) => void;
  onFinal?: (data: ISseFinalData) => void;
  onError?: (data: ISseErrorData) => void;
  onDone?: () => void;
  onOpen?: (e: any) => void;
  onClose?: (e: any) => void;
}

export function createSseMessageHandler(options: ISseChatHandlerOptions) {
  const {
    typewriter,
    chatInfoClass,
    onDelta,
    onFinal,
    onError,
    onDone,
    onOpen,
    onClose,
  } = options;

  let hasFinal = false;
  let isUserStopped = false;
  let doneEmitted = false;

  const handleOpen = (e: any) => {
    if (e.ok && e.headers.get('content-type') === 'text/event-stream') {
      typewriter.start();
    } else if (e.headers.get('content-type') === 'application/json') {
      typewriter.add('Error 请检查模型是否配置正确');
    }
    if (onOpen) {
      onOpen(e);
    }
  };

  const handleMessage = (msg: { data: string }) => {
    const parsed = parseSseMessage(msg.data);
    if (!parsed) {
      return;
    }

    const { event, data } = parsed;

    switch (event) {
      case 'delta':
        if (data?.response) {
          typewriter.add(data.response);
        }
        if (onDelta) {
          onDelta(data as ISseDeltaData);
        }
        break;

      case 'final':
        hasFinal = true;
        if (data?.time_record?.time_usage) {
          const timeObj = { ...data.time_record.time_usage };
          delete timeObj['retriever_search_by_milvus'];
          chatInfoClass.addTime(timeObj);
        }
        if (data?.time_record?.token_usage) {
          chatInfoClass.addToken(data.time_record.token_usage);
        }
        chatInfoClass.addDate(Date.now());
        if (onFinal) {
          onFinal(data as ISseFinalData);
        }
        break;

      case 'error':
        const errorMsg = data?.msg || '未知错误';
        message.error(errorMsg);
        if (onError) {
          onError(data as ISseErrorData);
        }
        break;

      case 'done':
        if (doneEmitted) {
          return;
        }
        doneEmitted = true;
        if (onDone) {
          onDone();
        }
        break;

      default:
        break;
    }
  };

  const handleClose = (e: any) => {
    if (onClose) {
      onClose(e);
    }
  };

  const handleError = (err: any) => {
    if (isUserStopped) {
      return;
    }
    console.error('SSE error:', err);
    const errorMsg = err?.msg || err?.message || '出错了';
    message.error(errorMsg);
    if (onError) {
      onError({ code: 500, msg: errorMsg });
    }
    throw err;
  };

  const setUserStopped = (val: boolean) => {
    isUserStopped = val;
  };

  const getHasFinal = () => hasFinal;

  return {
    handleOpen,
    handleMessage,
    handleClose,
    handleError,
    setUserStopped,
    getHasFinal,
  };
}

export interface IStartSseParams {
  url: string;
  body: any;
  signal: AbortSignal;
  handler: ReturnType<typeof createSseMessageHandler>;
}

export function startSseChat(params: IStartSseParams) {
  const { url, body, signal, handler } = params;

  fetchEventSource(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: ['text/event-stream', 'application/json'],
    },
    openWhenHidden: true,
    body: JSON.stringify(body),
    signal,
    onopen: handler.handleOpen,
    onmessage: handler.handleMessage,
    onclose: handler.handleClose,
    onerror: handler.handleError,
  });
}
