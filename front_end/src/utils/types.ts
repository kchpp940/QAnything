/*
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2024-01-09 15:28:56
 * @LastEditors: Ianarua 306781523@qq.com
 * @LastEditTime: 2024-08-05 16:36:28
 * @FilePath: front_end/src/utils/types.ts
 * @Description: 统一的类型定义，与后端 serializer 保持一致
 */

// ============================================
// 基础数据类型
// ============================================

export interface ISourceDocument {
  file_id: string;
  file_name: string;
  content: string;
  score: string;
  file_url: string;
  retrieval_query: string;
  embed_version: string;
  doc_id: string;
  retrieval_source: string;
  headers: Record<string, any>;
  page_id: number;
  nos_keys: string;
  detail_data_source: string;
}

export interface ITimeUsage {
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
  obtain_images_time: number;
  rollback_length: number;
  tokens_per_second: number;
}

export interface ITokenUsage {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  rewrite_prompt_tokens: number;
  rewrite_completion_tokens: number;
}

export interface ITimeRecord {
  time_usage: ITimeUsage;
  token_usage: ITokenUsage;
}

export interface ILLMSetting {
  model: string;
  api_base: string;
  api_key: string;
  api_context_length: number;
  max_token: number;
  temperature: number;
  top_p: number;
  top_k: number;
  chunk_size: number;
  rerank: boolean;
  hybrid_search: boolean;
  networking: boolean;
  only_need_search_results: boolean;
  prompt_template: string;
}

export interface IRetrievalTrace {
  query: string;
  retrieval_method: string;
  total_results: number;
  filtered_results: number;
  stage: string;
  timestamp: string;
}

export interface IWebSearchTrace {
  query: string;
  search_engine: string;
  result_count: number;
  selected_urls: string[];
  timestamp: string;
}

// ============================================
// 业务数据类型
// ============================================

export interface IKnowledgeItem {
  kb_id: string;
  kb_name: string;
  isFaq?: boolean;
  createTime?: string;
  edit?: boolean;
}

export interface IKnowledgeFile {
  file_id: string;
  file_name: string;
  status: 'gray' | 'green' | 'yellow' | 'red' | 'loading';
  bytes: number;
  content_length: number;
  timestamp: string;
  file_location: string;
  file_url: string;
  chunks_number: number;
  msg: string;
  question: string;
  answer: string;
  estimated_chars: number;
}

export interface IBotInfo {
  bot_id: string;
  bot_name: string;
  description: string;
  head_image: string;
  prompt_setting: string;
  welcome_message: string;
  kb_ids: string[];
  kb_names: string[];
  update_time: string;
  llm_setting: ILLMSetting;
  user_id: string;
}

export interface IQARecord {
  qa_id: string;
  user_id: string;
  bot_id: string;
  kb_ids: string[];
  query: string;
  model: string;
  product_source: string;
  time_record: ITimeRecord;
  history: Array<[string, string]>;
  condense_question: string;
  prompt: string;
  result: string;
  retrieval_documents: ISourceDocument[];
  source_documents: ISourceDocument[];
  timestamp: string;
  retrieval_trace: IRetrievalTrace[];
  web_search_trace: IWebSearchTrace[];
  kb_names: string;
}

export interface IChatResponse {
  code: number;
  msg: string;
  question: string;
  response: string;
  model: string;
  history: Array<[string, string]>;
  condense_question: string;
  source_documents: ISourceDocument[];
  retrieval_documents: ISourceDocument[];
  time_record: ITimeRecord;
  llm_setting: ILLMSetting;
  retrieval_trace: IRetrievalTrace[];
  web_search_trace: IWebSearchTrace[];
  show_images: string[];
  bot_id: string;
  qa_id: string;
  timestamp: string;
}

export interface IPaginatedResponse<T> {
  total: number;
  total_page: number;
  page_id: number;
  page_limit: number;
  status_count: Record<string, number>;
  details: T[];
  qa_infos?: IQARecord[];
  total_count?: number;
}

export interface IApiResponse<T = any> {
  code: number;
  msg: string;
  data: T;
}

// ============================================
// 前端业务类型
// ============================================

export interface IDataSourceItem extends ISourceDocument {
  dataSource?: string;
  detailDataSource?: string;
  showDetailDataSource?: boolean;
}

export interface IChatItem {
  type: 'ai' | 'user';
  question?: string;
  answer?: string;
  like?: boolean;
  unlike?: boolean;
  copied?: boolean;
  onlySearch?: boolean;
  showTools?: boolean;
  source?: IDataSourceItem[];
  picList?: string[];
  qaId?: string;
  itemInfo?: IChatItemInfo;
}

export interface IHistoryList {
  historyId: number;
  title: string;
  kbIds?: string[];
}

export interface IChatItemInfo {
  timeInfo: ITimeUsage;
  tokenInfo: ITokenInfo;
  settingInfo: IChatSetting;
  dateInfo: number;
}

export interface ITimeInfo extends ITimeUsage {}

export interface ITokenInfo extends ITokenUsage {
  tokens_per_second: number;
}

export type inputStatus = 'default' | 'inputing' | 'parsing' | 'success' | 'defeat' | 'hover';

export interface IUrlListItem {
  status: inputStatus;
  text: string;
  percent: number;
  borderRadius?: string;
}

export interface IFileListItem {
  file?: File;
  file_name: string;
  status: string;
  file_id: string;
  percent?: number;
  errorText?: string;
  text?: string;
  order?: number;
  bytes: number;
}

type ICapabilities = {
  networkSearch: boolean;
  mixedSearch: boolean;
  onlySearch: boolean;
  rerank: boolean;
};

export interface IChatSetting {
  modelType: 'openAI' | 'ollama' | '自定义模型配置' | string;
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
  capabilities: ICapabilities;
  active: boolean;
}

export type MakePartial<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
