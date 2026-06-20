/*
 * @Description: 响应适配层 - 统一处理后端响应格式，转换字段命名，兼容旧数据
 */

import type {
  ISourceDocument,
  ITimeUsage,
  ITokenUsage,
  ITimeRecord,
  ILLMSetting,
  IRetrievalTrace,
  IWebSearchTrace,
  IKnowledgeFile,
  IBotInfo,
  IQARecord,
  IChatResponse,
  IPaginatedResponse,
  IApiResponse,
  IDataSourceItem,
  IChatItem,
  IChatItemInfo,
  ITimeInfo,
  ITokenInfo,
  IChatSetting,
} from './types';

const snakeToCamel = (str: string): string => {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
};

const transformKeys = <T extends Record<string, any>>(obj: any): T => {
  if (obj === null || obj === undefined) return obj as T;
  if (Array.isArray(obj)) {
    return obj.map(item => transformKeys(item)) as unknown as T;
  }
  if (typeof obj !== 'object') return obj as T;

  const result: Record<string, any> = {};
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const camelKey = snakeToCamel(key);
      result[camelKey] = transformKeys(obj[key]);
    }
  }
  return result as T;
};

const createDefaultSourceDocument = (): ISourceDocument => ({
  fileId: '',
  fileName: '',
  content: '',
  score: '0',
  fileUrl: '',
  retrievalQuery: '',
  embedVersion: '',
  docId: '',
  retrievalSource: '',
  headers: {},
  pageId: 0,
  nosKeys: '',
  detailDataSource: '',
});

export const adaptSourceDocument = (raw: any): ISourceDocument => {
  if (!raw) return createDefaultSourceDocument();
  const transformed = transformKeys<ISourceDocument>(raw);
  return { ...createDefaultSourceDocument(), ...transformed };
};

export const adaptSourceDocuments = (rawList: any[]): ISourceDocument[] => {
  if (!Array.isArray(rawList)) return [];
  return rawList.map(item => adaptSourceDocument(item));
};

const createDefaultTimeUsage = (): ITimeUsage => ({
  preprocess: 0,
  condenseQChain: 0,
  retrieverSearch: 0,
  webSearch: 0,
  rerank: 0,
  reprocess: 0,
  llmFirstReturn: 0,
  firstReturn: 0,
  llmCompleted: 0,
  chatCompleted: 0,
  obtainImagesTime: 0,
  rollbackLength: 0,
  tokensPerSecond: 0,
});

const createDefaultTokenUsage = (): ITokenUsage => ({
  totalTokens: 0,
  promptTokens: 0,
  completionTokens: 0,
  rewritePromptTokens: 0,
  rewriteCompletionTokens: 0,
});

export const adaptTimeRecord = (raw: any): ITimeRecord => {
  if (!raw) {
    return {
      timeUsage: createDefaultTimeUsage(),
      tokenUsage: createDefaultTokenUsage(),
    };
  }

  let timeUsage: ITimeUsage;
  let tokenUsage: ITokenUsage;

  if ('time_usage' in raw && 'token_usage' in raw) {
    timeUsage = { ...createDefaultTimeUsage(), ...transformKeys<ITimeUsage>(raw.time_usage) };
    tokenUsage = { ...createDefaultTokenUsage(), ...transformKeys<ITokenUsage>(raw.token_usage) };
  } else if ('timeUsage' in raw && 'tokenUsage' in raw) {
    timeUsage = { ...createDefaultTimeUsage(), ...transformKeys<ITimeUsage>(raw.timeUsage) };
    tokenUsage = { ...createDefaultTokenUsage(), ...transformKeys<ITokenUsage>(raw.tokenUsage) };
  } else {
    const legacyFormat = transformKeys<any>(raw);
    const timeKeys = Object.keys(createDefaultTimeUsage());
    const tokenKeys = Object.keys(createDefaultTokenUsage());

    const tu: Partial<ITimeUsage> = {};
    const tku: Partial<ITokenUsage> = {};

    for (const key in legacyFormat) {
      if (timeKeys.includes(key)) {
        (tu as any)[key] = legacyFormat[key];
      }
      if (tokenKeys.includes(key)) {
        (tku as any)[key] = legacyFormat[key];
      }
    }
    timeUsage = { ...createDefaultTimeUsage(), ...tu };
    tokenUsage = { ...createDefaultTokenUsage(), ...tku };
  }

  return { timeUsage, tokenUsage };
};

const createDefaultLLMSetting = (): ILLMSetting => ({
  model: 'gpt-4o-mini',
  apiBase: '',
  apiKey: '',
  apiContextLength: 4096,
  maxToken: 1024,
  temperature: 0.5,
  topP: 0.99,
  topK: 8,
  chunkSize: 500,
  rerank: true,
  hybridSearch: false,
  networking: false,
  onlyNeedSearchResults: false,
  promptTemplate: '',
});

const llmSettingFieldMap: Record<string, string> = {
  apiModelName: 'model',
  modelName: 'model',
  apiBase: 'apiBase',
  apiKey: 'apiKey',
  apiContextLength: 'apiContextLength',
  maxToken: 'maxToken',
  temperature: 'temperature',
  topP: 'topP',
  top_P: 'topP',
  topK: 'topK',
  top_K: 'topK',
  chunkSize: 'chunkSize',
  rerank: 'rerank',
  hybridSearch: 'hybridSearch',
  mixedSearch: 'hybridSearch',
  networking: 'networking',
  networkSearch: 'networking',
  onlyNeedSearchResults: 'onlyNeedSearchResults',
  onlySearch: 'onlyNeedSearchResults',
};

export const adaptLLMSetting = (raw: any): ILLMSetting => {
  if (!raw) return createDefaultLLMSetting();

  const transformed = typeof raw === 'string' ? JSON.parse(raw) : transformKeys<any>(raw);
  const normalized: Record<string, any> = {};

  for (const key in transformed) {
    const normalizedKey = llmSettingFieldMap[key] || key;
    if (normalizedKey in createDefaultLLMSetting()) {
      normalized[normalizedKey] = transformed[key];
    }
  }

  return { ...createDefaultLLMSetting(), ...normalized };
};

export const adaptRetrievalTrace = (raw: any): IRetrievalTrace => {
  const defaults: IRetrievalTrace = {
    query: '',
    retrievalMethod: '',
    totalResults: 0,
    filteredResults: 0,
    stage: '',
    timestamp: '',
  };
  return { ...defaults, ...transformKeys<IRetrievalTrace>(raw || {}) };
};

export const adaptWebSearchTrace = (raw: any): IWebSearchTrace => {
  const defaults: IWebSearchTrace = {
    query: '',
    searchEngine: '',
    resultCount: 0,
    selectedUrls: [],
    timestamp: '',
  };
  return { ...defaults, ...transformKeys<IWebSearchTrace>(raw || {}) };
};

export const adaptKnowledgeFile = (raw: any): IKnowledgeFile => {
  const defaults: IKnowledgeFile = {
    fileId: '',
    fileName: '',
    status: 'gray',
    bytes: 0,
    contentLength: 0,
    timestamp: '',
    fileLocation: '',
    fileUrl: '',
    chunksNumber: 0,
    msg: '',
    question: '',
    answer: '',
    estimatedChars: 0,
  };
  return { ...defaults, ...transformKeys<IKnowledgeFile>(raw || {}) };
};

export const adaptKnowledgeFiles = (rawList: any[]): IKnowledgeFile[] => {
  if (!Array.isArray(rawList)) return [];
  return rawList.map(item => adaptKnowledgeFile(item));
};

export const adaptBotInfo = (raw: any): IBotInfo => {
  const defaults: IBotInfo = {
    botId: '',
    botName: '',
    description: '',
    headImage: '',
    promptSetting: '',
    welcomeMessage: '',
    kbIds: [],
    kbNames: [],
    updateTime: '',
    llmSetting: createDefaultLLMSetting(),
    userId: '',
  };

  if (!raw) return defaults;

  const transformed = transformKeys<Partial<IBotInfo>>(raw);
  const result = { ...defaults, ...transformed };

  if (raw.llm_setting || raw.llmSetting) {
    result.llmSetting = adaptLLMSetting(raw.llm_setting || raw.llmSetting);
  }

  if (raw.kb_ids && typeof raw.kb_ids === 'string') {
    result.kbIds = raw.kb_ids.split(',').filter(Boolean);
  }

  return result;
};

export const adaptBotInfos = (rawList: any[]): IBotInfo[] => {
  if (!Array.isArray(rawList)) return [];
  return rawList.map(item => adaptBotInfo(item));
};

export const adaptQARecord = (raw: any): IQARecord => {
  const defaults: IQARecord = {
    qaId: '',
    userId: '',
    botId: '',
    kbIds: [],
    query: '',
    model: '',
    productSource: '',
    timeRecord: adaptTimeRecord(null),
    history: [],
    condenseQuestion: '',
    prompt: '',
    result: '',
    retrievalDocuments: [],
    sourceDocuments: [],
    timestamp: '',
    retrievalTrace: [],
    webSearchTrace: [],
    kbNames: '',
  };

  if (!raw) return defaults;

  const transformed = transformKeys<Partial<IQARecord>>(raw);
  const result = { ...defaults, ...transformed };

  result.timeRecord = adaptTimeRecord(raw.time_record || raw.timeRecord);
  result.sourceDocuments = adaptSourceDocuments(raw.source_documents || raw.sourceDocuments);
  result.retrievalDocuments = adaptSourceDocuments(raw.retrieval_documents || raw.retrievalDocuments);

  if (raw.kb_ids && typeof raw.kb_ids === 'string') {
    try {
      result.kbIds = JSON.parse(raw.kb_ids);
    } catch {
      result.kbIds = raw.kb_ids.split(',').filter(Boolean);
    }
  }

  if (raw.history && typeof raw.history === 'string') {
    try {
      result.history = JSON.parse(raw.history);
    } catch {
      result.history = [];
    }
  }

  return result;
};

export const adaptQARecords = (rawList: any[]): IQARecord[] => {
  if (!Array.isArray(rawList)) return [];
  return rawList.map(item => adaptQARecord(item));
};

export const adaptChatResponse = (raw: any): IChatResponse => {
  const defaults: IChatResponse = {
    code: 200,
    msg: 'success',
    question: '',
    response: '',
    model: '',
    history: [],
    condenseQuestion: '',
    sourceDocuments: [],
    retrievalDocuments: [],
    timeRecord: adaptTimeRecord(null),
    llmSetting: createDefaultLLMSetting(),
    retrievalTrace: [],
    webSearchTrace: [],
    showImages: [],
    botId: '',
    qaId: '',
    timestamp: '',
  };

  if (!raw) return defaults;

  const transformed = transformKeys<Partial<IChatResponse>>(raw);
  const result = { ...defaults, ...transformed };

  result.timeRecord = adaptTimeRecord(raw.time_record || raw.timeRecord);
  result.llmSetting = adaptLLMSetting(raw.llm_setting || raw.llmSetting);
  result.sourceDocuments = adaptSourceDocuments(raw.source_documents || raw.sourceDocuments);
  result.retrievalDocuments = adaptSourceDocuments(raw.retrieval_documents || raw.retrievalDocuments);

  if (raw.retrieval_trace || raw.retrievalTrace) {
    result.retrievalTrace = (raw.retrieval_trace || raw.retrievalTrace || []).map((t: any) =>
      adaptRetrievalTrace(t)
    );
  }

  if (raw.web_search_trace || raw.webSearchTrace) {
    result.webSearchTrace = (raw.web_search_trace || raw.webSearchTrace || []).map((t: any) =>
      adaptWebSearchTrace(t)
    );
  }

  return result;
};

export const adaptPaginatedResponse = <T>(
  raw: any,
  itemAdapter: (item: any) => T
): IPaginatedResponse<T> => {
  const defaults: IPaginatedResponse<any> = {
    total: 0,
    totalPage: 0,
    pageId: 1,
    pageLimit: 10,
    statusCount: {},
    details: [],
  };

  if (!raw) return { ...defaults, details: [] };

  const transformed = transformKeys<any>(raw);
  const result = { ...defaults, ...transformed };

  if (transformed.details && Array.isArray(transformed.details)) {
    result.details = transformed.details.map(itemAdapter);
  }

  if (raw.qa_infos || raw.qaInfos) {
    result.qaInfos = adaptQARecords(raw.qa_infos || raw.qaInfos);
  }

  return result;
};

export const adaptApiResponse = <T>(
  raw: any,
  dataAdapter?: (data: any) => T
): IApiResponse<T> => {
  const defaults: IApiResponse<any> = {
    code: 200,
    msg: 'success',
    data: null,
  };

  if (!raw) return { ...defaults, data: null } as IApiResponse<T>;

  const result = { ...defaults, ...transformKeys<any>(raw) };

  if (dataAdapter && raw.data !== undefined) {
    result.data = dataAdapter(raw.data);
  }

  return result as IApiResponse<T>;
};

// ============================================
// 前端业务数据适配器
// ============================================

export const toDataSourceItem = (doc: ISourceDocument): IDataSourceItem => ({
  ...doc,
  showDetailDataSource: false,
});

export const toDataSourceItems = (docs: ISourceDocument[]): IDataSourceItem[] => {
  return docs.map(doc => toDataSourceItem(doc));
};

export const toChatItemInfo = (
  timeRecord: ITimeRecord,
  chatSetting: IChatSetting,
  dateInfo?: number
): IChatItemInfo => ({
  timeInfo: timeRecord.timeUsage,
  tokenInfo: {
    ...timeRecord.tokenUsage,
    tokensPerSecond: timeRecord.timeUsage.tokensPerSecond,
  },
  settingInfo: chatSetting,
  dateInfo: dateInfo || Date.now(),
});

export const toAIChatItem = (
  chatResponse: IChatResponse,
  chatSetting: IChatSetting
): IChatItem => ({
  type: 'ai',
  answer: chatResponse.response,
  question: chatResponse.question,
  showTools: true,
  onlySearch: chatResponse.llmSetting.onlyNeedSearchResults,
  source: toDataSourceItems(chatResponse.sourceDocuments),
  picList: chatResponse.showImages.length ? chatResponse.showImages : undefined,
  qaId: chatResponse.qaId,
  itemInfo: toChatItemInfo(chatResponse.timeRecord, chatSetting),
  like: false,
  unlike: false,
  copied: false,
});

export const toUserChatItem = (question: string): IChatItem => ({
  type: 'user',
  question,
});

export const toTimeInfo = (timeUsage: ITimeUsage): ITimeInfo => ({
  ...timeUsage,
});

export const toTokenInfo = (timeRecord: ITimeRecord): ITokenInfo => ({
  ...timeRecord.tokenUsage,
  tokensPerSecond: timeRecord.timeUsage.tokensPerSecond,
});

// ============================================
// 向后兼容 - 旧数据格式转换
// ============================================

export const adaptLegacyChatResponse = (raw: any): IChatResponse => {
  if (!raw) return adaptChatResponse(raw);

  const normalized: any = { ...raw };

  if (raw.result && !raw.response) {
    normalized.response = raw.result;
  }
  if (raw.query && !raw.question) {
    normalized.question = raw.query;
  }
  if (raw.answer && !raw.response) {
    normalized.response = raw.answer;
  }

  return adaptChatResponse(normalized);
};

export const adaptLegacyQARecord = (raw: any): IQARecord => {
  if (!raw) return adaptQARecord(raw);

  const normalized: any = { ...raw };

  if (raw.result && !raw.response) {
    normalized.response = raw.result;
  }
  if (raw.query && !raw.question) {
    normalized.question = raw.query;
  }

  return adaptQARecord(normalized);
};
