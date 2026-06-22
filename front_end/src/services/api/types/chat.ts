import type { IBaseKbParams } from './common';

export interface IDataSourceRaw {
  dataSource?: string;
  detailDataSource?: string;
  file_name?: string | null;
  content?: string | null;
  score?: number | null;
  file_id?: string | null;
  file_url?: string | null;
  pdf_source_info?: {
    chunks_nos_url?: string;
    [key: string]: unknown;
  };
  chunks?: unknown;
  pageSizes?: unknown;
  [key: string]: unknown;
}

export interface IDataSource {
  dataSource: string;
  detailDataSource: string;
  fileName: string | null;
  content: string | null;
  score: number | null;
  fileId: string | null;
  fileUrl: string | null;
  showDetailDataSource: boolean;
  chunks?: unknown;
  pageSizes?: unknown;
  raw: IDataSourceRaw;
}

export interface ITimeInfo {
  preprocess: number;
  condense_q_chain: number;
  retriever_search: number;
  web_search: number;
  rerank: number;
  reprocess: number;
  llm_first_return: number;
  first_return: number;
  llm_completed: number;
  chat_completed: number;
}

export interface ITokenInfo {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  tokens_per_second: number;
}

export type ModelType = 'openAI' | 'ollama' | '自定义模型配置' | string;

export interface IModelCapabilities {
  networkSearch: boolean;
  mixedSearch: boolean;
  onlySearch: boolean;
  rerank: boolean;
}

export interface IChatSetting {
  modelType: ModelType;
  customId?: number;
  modelName?: string;
  apiKey?: string;
  apiBase: string;
  apiModelName: string;
  apiContextLength: number;
  context: number;
  maxToken: number;
  chunkSize: number;
  temperature: number;
  top_P: number;
  top_K: number;
  capabilities: IModelCapabilities;
  active: boolean;
}

export interface IChatItemInfo {
  timeInfo: ITimeInfo;
  tokenInfo: ITokenInfo;
  settingInfo: IChatSetting;
  dateInfo: number;
}

export type ChatRole = 'ai' | 'user';

export interface IChatItemRaw {
  type?: ChatRole;
  question?: string;
  answer?: string;
  result?: string;
  condense_question?: string;
  like?: boolean;
  unlike?: boolean;
  onlySearch?: boolean;
  source?: IDataSourceRaw[];
  sources?: IDataSourceRaw[];
  [key: string]: unknown;
}

export interface IChatItem {
  type: ChatRole;
  question: string;
  answer: string;
  like: boolean;
  unlike: boolean;
  copied: boolean;
  onlySearch: boolean;
  showTools: boolean;
  sources: IDataSource[];
  qaId?: string;
  itemInfo?: IChatItemInfo;
  raw: IChatItemRaw;
}

export interface ISendQuestionParams extends IBaseKbParams {
  kb_ids?: string[];
  question: string;
  only_search?: boolean;
  bot_id?: string;
  [key: string]: unknown;
}

export interface ISendQuestionRawResponse {
  result?: string;
  answer?: string;
  source?: IDataSourceRaw[];
  sources?: IDataSourceRaw[];
  condense_question?: string;
  time_info?: Partial<ITimeInfo>;
  token_info?: Partial<ITokenInfo>;
  [key: string]: unknown;
}

export interface ISendQuestionResult {
  answer: string;
  question: string;
  sources: IDataSource[];
  timeInfo?: ITimeInfo;
  tokenInfo?: ITokenInfo;
  raw: ISendQuestionRawResponse;
}

export interface IHistoryList {
  historyId: number;
  title: string;
  kbIds?: string[];
}
