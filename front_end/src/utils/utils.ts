/*
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2024-01-09 15:28:56
 * @LastEditors: Ianarua 306781523@qq.com
 * @LastEditTime: 2024-08-01 17:15:29
 * @FilePath: front_end/src/utils/utils.ts
 * @Description:
 */

import { useUser } from '@/store/useUser';
import { IChatSetting, IFileListItem, ITimeInfo, ITokenInfo } from './types';

export function addWindowsAttr(name, value) {
  window[name] = value;
}

export function getRandomString(strLen = 5) {
  const strCeils = 'abcdefghijklmnopqrstuvwxyz1234567890';
  let str = '';
  for (let i = 0; i < strLen; i += 1) {
    str = `${str}${strCeils[Math.floor(Math.random() * 36)]}`;
  }
  return str;
}

export function clearTimer(timer) {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
}

export function isMac() {
  return /macintosh|mac os x/i.test(navigator.userAgent);
}

/**
 * 节流
 * @param {*} fn
 * @param {*} delay
 */
export const throttle = <T extends (...args: any[]) => any>(fn: T, delay: number) => {
  let timer: number | undefined;
  let last = 0;
  return function (this: ThisParameterType<T>, ...args: Parameters<T>) {
    const now = Date.now();
    if (now - last >= delay) {
      clearTimeout(timer as number);
      last = now;
      fn.apply(this, args);
    } else {
      clearTimeout(timer as number);
      timer = window.setTimeout(() => {
        fn.apply(this, args);
      }, delay);
    }
  } as T;
};

//格式化上传状态
export const getStatus = (item: IFileListItem) => {
  let str = '';
  switch (item.status) {
    case 'loading':
      str = '上传中';
      break;
    case 'red':
      if (item.errorText) {
        str = item.errorText;
      } else {
        str = '解析失败';
      }
      break;
    case 'gray':
      str = '上传成功待解析';
      break;
    case 'green':
      str = '解析成功';
      break;
    case 'yellow':
      str = '解析失败';
      break;
    default:
      break;
  }
  return str;
};

//对接口的返回值作统一处理
export const resultControl = async res => {
  return new Promise((resolve, reject) => {
    if (res?.request?.responseType === 'blob') {
      resolve(res);
    }
    if (res.errorCode === '0' || res.code === 200) {
      resolve(res.result || res.data || res);
    } else if (res.errorCode === '111') {
      const { setUserInfo } = useUser();
      setUserInfo({ token: '' });
    } else {
      reject(res);
    }
  });
};

export const formatFileSize = sizeInBytes => {
  if (sizeInBytes < 0) {
    return '未知';
  } else if (sizeInBytes < 1024) {
    return sizeInBytes + 'B';
  } else if (sizeInBytes < 1024 * 1024) {
    return (sizeInBytes / 1024).toFixed(2) + 'KB';
  } else if (sizeInBytes < 1024 * 1024 * 1024) {
    return (sizeInBytes / (1024 * 1024)).toFixed(2) + 'MB';
  } else {
    return (sizeInBytes / (1024 * 1024 * 1024)).toFixed(2) + 'G';
  }
};

export const formatDate = (timestamp, symbol = '-', timeSymbol = ':') => {
  if (!timestamp) {
    return '';
  }

  // 拆分日期和时间部分
  const datePart = timestamp.slice(0, 8); // 取前8位作为日期
  const timePart = timestamp.slice(8); // 剩余部分作为时间

  // 解析日期部分
  const year = datePart.slice(0, 4);
  const month = datePart.slice(4, 6);
  const day = datePart.slice(6, 8);

  // 检查时间部分是否存在，并解析时间
  let hour, minute;
  if (timePart) {
    hour = timePart.slice(0, 2);
    minute = timePart.slice(2, 4);
  }

  // 构建日期字符串
  let dateString = `${year}${symbol}${month}${symbol}${day}`;

  // 如果存在时间部分，添加到日期字符串
  if (timePart) {
    dateString += ` ${hour}${timeSymbol}${minute}`;
  }

  return dateString;
};

/**
 * @description 返回最近14天的日期范围
 */
export const getLastDaysRange = (days: number = 14) => {
  const today = new Date();
  const timeEnd = today.toISOString().split('T')[0]; // 获取今天的日期，格式为 'YYYY-MM-DD'

  const timeStart = new Date(today.getTime());
  timeStart.setDate(today.getDate() - days - 1); // 设置日期为今天减去days-1天
  const timeStartStr = timeStart.toISOString().split('T')[0]; // 获取14天前的日期，格式为 'YYYY-MM-DD'

  return {
    time_start: timeStartStr,
    time_end: timeEnd,
  };
};

/**
 * @description 将文件后缀和文件名分开
 * @param filePath 文件全部名称
 */
export const parseFileName = (filePath: string) => {
  const parts = filePath.split('.');
  const fileName = parts.slice(0, -1).join('.'); // 获取文件名部分
  const fileExtension = parts.at(-1); // 获取文件扩展名部分

  return {
    fileName: fileName,
    fileExtension: fileExtension,
  };
};

/**
 * @description 保存ai回答的time token信息和当前ai的模型配置
 */
export class ChatInfoClass<T = IChatSetting> {
  private timeObj: ITimeInfo;
  private tokenObj: ITokenInfo;
  private settingObj: T;
  private date: number;

  constructor() {
    this.timeObj = {
      preprocess: 0,
      condense_q_chain: 0,
      retriever_search: 0,
      web_search: 0,
      rerank: 0,
      reprocess: 0,
      llm_first_return: 0,
      first_return: 0,
      llm_completed: 0,
      chat_completed: 0,
    };
  }

  addTime(timeInfo: ITimeInfo) {
    this.timeObj = { ...this.timeObj, ...timeInfo };
  }

  addToken(tokenInfo: ITokenInfo) {
    this.tokenObj = tokenInfo;
  }

  addChatSetting(chatSettingInfo: T) {
    this.settingObj = chatSettingInfo;
  }

  addDate(date: number) {
    this.date = date;
  }

  getChatInfo() {
    return {
      timeInfo: this.timeObj,
      tokenInfo: this.tokenObj,
      settingInfo: this.settingObj,
      dateInfo: this.date,
    };
  }
}

/**
 * @description 将时间戳格式化为 2024/8/1 12:30:12 的格式
 * @param timestamp {number} 时间戳
 */
export function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp);
  const year = date.getFullYear(); // 获取年份
  const month = (date.getMonth() + 1).toString().padStart(2, '0'); // 获取月份，月份从0开始计数
  const day = date.getDate().toString().padStart(2, '0'); // 获取日
  const hours = date.getHours().toString().padStart(2, '0'); // 获取小时
  const minutes = date.getMinutes().toString().padStart(2, '0'); // 获取分钟
  const seconds = date.getSeconds().toString().padStart(2, '0'); // 获取秒

  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * @description 下载文件的通用函数
 * @param url URL.createObjectURL 的文件链接
 * @param fileName 下载文件的名称，如果不提供，默认为空字符串
 * @param callback 下载完成后的回调函数，如果提供了回调函数，在下载触发后执行
 */
export function downLoad(url, fileName = '', callback?) {
  let aLink = document.createElement('a');
  aLink.download = fileName;
  aLink.style.display = 'none';
  aLink.href = url;
  document.body.appendChild(aLink);
  aLink.click();
  document.body.removeChild(aLink);
  if (callback) {
    callback();
  }
}

/**
 * 从请求头中提取内容处置（Content-Disposition）字段的文件名
 * @param {Headers} headers - 请求响应头对象，包含所有响应头字段
 * @return {string} 返回解析出的文件名，如果无法解析或字段不存在，则返回空字符串
 */
export function getContentDispositionByHeader(headers: Headers): string {
  return decodeURIComponent(
    (headers['content-disposition']?.split('filename=') || [])[1].slice(1, -1) || ''
  );
}

import LlmSchemaRaw from '/llm_param_schema.json';

export interface LlmParamSchema {
  type: 'bool' | 'int' | 'float' | 'str' | 'list';
  default: any;
  required_for_request: boolean;
  fill_default_for_bot: boolean;
  allow_null?: boolean;
  min?: number;
  max?: number;
  description: string;
}

const FALLBACK_SCHEMA: Record<string, LlmParamSchema> = {
  api_key: { type: 'str', default: 'ollama', required_for_request: true, fill_default_for_bot: true, description: 'LLM API Key' },
  api_base: { type: 'str', default: '', required_for_request: true, fill_default_for_bot: true, description: 'LLM API Base URL' },
  model: { type: 'str', default: 'gpt-4o-mini', required_for_request: false, fill_default_for_bot: true, description: 'LLM Model Name' },
  api_context_length: { type: 'int', default: 4096, min: 1, required_for_request: true, fill_default_for_bot: true, description: 'LLM Context Window Size' },
  max_token: { type: 'int', default: null, allow_null: true, required_for_request: false, fill_default_for_bot: true, description: 'Max Output Tokens' },
  chunk_size: { type: 'int', default: 300, min: 50, required_for_request: false, fill_default_for_bot: true, description: 'Document Chunk Size' },
  temperature: { type: 'float', default: 0.5, min: 0.0, max: 2.0, required_for_request: true, fill_default_for_bot: true, description: 'Sampling Temperature' },
  top_k: { type: 'int', default: 8, min: 1, max: 100, required_for_request: true, fill_default_for_bot: true, description: 'Vector Search Top-K' },
  top_p: { type: 'float', default: 0.99, min: 0.0, max: 0.999, required_for_request: true, fill_default_for_bot: true, description: 'Nucleus Sampling Top-P (max 0.999, 1.0 is invalid)' },
  rerank: { type: 'bool', default: true, required_for_request: false, fill_default_for_bot: true, description: 'Enable Rerank' },
  hybrid_search: { type: 'bool', default: false, required_for_request: false, fill_default_for_bot: true, description: 'Enable Hybrid Search' },
  networking: { type: 'bool', default: false, required_for_request: false, fill_default_for_bot: true, description: 'Enable Web Search' },
  only_need_search_results: { type: 'bool', default: false, required_for_request: false, fill_default_for_bot: true, description: 'Return Search Results Only' },
};

export const LLM_SCHEMA_META = (LlmSchemaRaw as any)?.post_process || {
  top_p_1_0_correction: { enabled: true, from: 1.0, to: 0.99 },
};

function loadSchemaFromShared(): Record<string, LlmParamSchema> {
  try {
    const rawFields = (LlmSchemaRaw as any)?.fields;
    if (!rawFields || typeof rawFields !== 'object') return FALLBACK_SCHEMA;
    return rawFields as Record<string, LlmParamSchema>;
  } catch (e) {
    console.warn('[loadSchemaFromShared] 加载共享 schema 失败，使用内置回退:', e);
    return FALLBACK_SCHEMA;
  }
}

export const LLM_PARAM_SCHEMA: Record<string, LlmParamSchema> = loadSchemaFromShared();

export function parseParamBySchema(value: any, schema: LlmParamSchema): any {
  const paramType = schema.type;
  const defaultValue = schema.default;
  const allowNull = schema.allowNull ?? false;

  if (value === null && allowNull) return null;

  switch (paramType) {
    case 'bool': return parseBool(value, defaultValue);
    case 'int': return parseInt_(value, defaultValue);
    case 'float': return parseFloat_(value, defaultValue);
    case 'str': return value === null || value === undefined ? defaultValue : String(value);
    case 'list': return parseList(value, defaultValue ?? []);
    default: throw new Error(`Unknown param type: ${paramType}`);
  }
}

export function normalizeLlmParamsFromSchema(llmDict: Record<string, any>): Record<string, any> {
  const result: Record<string, any> = {};
  for (const [field, schema] of Object.entries(LLM_PARAM_SCHEMA)) {
    const rawValue = llmDict[field];
    result[field] = parseParamBySchema(rawValue, schema);
  }
  if (result.top_p === 1.0) result.top_p = 0.99;
  return result;
}

export function getDefaultLlmSetting(): Record<string, any> {
  return normalizeLlmParamsFromSchema({});
}

export function parseBool(value: any, defaultValue: boolean = false): boolean {
  if (value === null || value === undefined || value === '') return defaultValue;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value !== 0;
  const str = String(value).trim().toLowerCase();
  if (['true', '1', 'yes', 'on', 'y', 't'].includes(str)) return true;
  if (['false', '0', 'no', 'off', 'n', 'f'].includes(str)) return false;
  return defaultValue;
}

export function parseInt_(value: any, defaultValue: number = 0): number {
  if (value === null || value === undefined || value === '') return defaultValue;
  if (typeof value === 'number') return Math.floor(value);
  if (typeof value === 'boolean') return value ? 1 : 0;
  const str = String(value).trim();
  if (!str) return defaultValue;
  const num = Number(str);
  if (!isNaN(num)) return Math.floor(num);
  const floatNum = parseFloat(str);
  if (!isNaN(floatNum)) return Math.floor(floatNum);
  return defaultValue;
}

export function parseFloat_(value: any, defaultValue: number = 0): number {
  if (value === null || value === undefined || value === '') return defaultValue;
  if (typeof value === 'number') return value;
  if (typeof value === 'boolean') return value ? 1 : 0;
  const str = String(value).trim();
  if (!str) return defaultValue;
  const num = parseFloat(str);
  if (!isNaN(num)) return num;
  return defaultValue;
}

export function parseList(value: any, defaultValue: any[] = [], separator: string = ','): any[] {
  if (value === null || value === undefined || value === '') return defaultValue;
  if (Array.isArray(value)) return value;
  if (typeof value === 'string') {
    const str = value.trim();
    if (!str) return defaultValue;
    if (str.startsWith('[') && str.endsWith(']')) {
      try {
        const parsed = JSON.parse(str);
        if (Array.isArray(parsed)) return parsed;
      } catch (e) {
        // fall through to split
      }
    }
    return str.split(separator).map(s => s.trim()).filter(s => s !== '');
  }
  return defaultValue;
}

export interface NormalizedBotLlmSetting {
  api_key: string;
  api_base: string;
  model: string;
  api_context_length: number;
  max_token: number | null;
  chunk_size: number;
  temperature: number;
  top_k: number;
  top_p: number;
  rerank: boolean;
  hybrid_search: boolean;
  networking: boolean;
  only_need_search_results: boolean;
}

export function normalizeBotLlmSetting(llmSettingRaw: string | object): NormalizedBotLlmSetting {
  const raw = typeof llmSettingRaw === 'string' ? JSON.parse(llmSettingRaw) : llmSettingRaw;
  const normalized = normalizeLlmParamsFromSchema(raw);
  return normalized as NormalizedBotLlmSetting;
}

export interface IChatCapabilities {
  onlySearch: boolean;
  networkSearch: boolean;
  mixedSearch: boolean;
  rerank: boolean;
}

export interface IChatSettingCore {
  apiKey: string;
  apiBase: string;
  apiModelName: string;
  apiContextLength: number;
  maxToken: number | null;
  chunkSize: number;
  temperature: number;
  top_K: number;
  top_P: number;
  capabilities: IChatCapabilities;
}

export interface BuildChatSendDataOptions {
  kb_ids?: string[];
  bot_id?: string;
  history: any[];
  question: string;
  user_id: string;
  user_info: string;
  chatSetting: IChatSettingCore;
  product_source?: string;
}

export function buildChatSendData(options: BuildChatSendDataOptions): Record<string, any> {
  const { kb_ids, bot_id, history, question, user_id, user_info, chatSetting, product_source = 'saas' } = options;
  const { capabilities } = chatSetting;

  const sendData: Record<string, any> = {
    user_id,
    user_info,
    history,
    question,
    streaming: parseBool(capabilities.onlySearch === false, false),
    networking: parseBool(capabilities.networkSearch, false),
    product_source,
    rerank: parseBool(capabilities.rerank, LLM_PARAM_SCHEMA.rerank.default),
    only_need_search_results: parseBool(capabilities.onlySearch, LLM_PARAM_SCHEMA.only_need_search_results.default),
    hybrid_search: parseBool(capabilities.mixedSearch, LLM_PARAM_SCHEMA.hybrid_search.default),
    max_token: chatSetting.maxToken !== null && chatSetting.maxToken !== undefined
      ? parseInt_(chatSetting.maxToken)
      : LLM_PARAM_SCHEMA.max_token.default,
    api_base: String(chatSetting.apiBase || LLM_PARAM_SCHEMA.api_base.default),
    api_key: String(chatSetting.apiKey || LLM_PARAM_SCHEMA.api_key.default),
    model: String(chatSetting.apiModelName || LLM_PARAM_SCHEMA.model.default),
    api_context_length: parseInt_(chatSetting.apiContextLength, LLM_PARAM_SCHEMA.api_context_length.default),
    chunk_size: parseInt_(chatSetting.chunkSize, LLM_PARAM_SCHEMA.chunk_size.default),
    top_p: parseFloat_(chatSetting.top_P, LLM_PARAM_SCHEMA.top_p.default),
    top_k: parseInt_(chatSetting.top_K, LLM_PARAM_SCHEMA.top_k.default),
    temperature: parseFloat_(chatSetting.temperature, LLM_PARAM_SCHEMA.temperature.default),
  };

  if (kb_ids !== undefined) {
    sendData.kb_ids = kb_ids;
  }
  if (bot_id !== undefined) {
    sendData.bot_id = bot_id;
  }

  return sendData;
}

export interface BuildUpdateBotParamsOptions {
  bot_id: string;
  kb_ids?: string[];
  chatSetting: IChatSettingCore;
  bot_name?: string;
  description?: string;
  head_image?: string;
  prompt_setting?: string;
  welcome_message?: string;
}

export function buildUpdateBotParams(options: BuildUpdateBotParamsOptions): Record<string, any> {
  const { bot_id, kb_ids, chatSetting } = options;
  const { capabilities } = chatSetting;

  const params: Record<string, any> = {
    bot_id,
    rerank: parseBool(capabilities.rerank),
    only_need_search_results: parseBool(capabilities.onlySearch),
    hybrid_search: parseBool(capabilities.mixedSearch),
    networking: parseBool(capabilities.networkSearch),
    max_token: chatSetting.maxToken !== null && chatSetting.maxToken !== undefined
      ? parseInt_(chatSetting.maxToken)
      : LLM_PARAM_SCHEMA.max_token.default,
    api_base: String(chatSetting.apiBase || ''),
    api_key: String(chatSetting.apiKey || ''),
    model: String(chatSetting.apiModelName || ''),
    api_context_length: parseInt_(chatSetting.apiContextLength),
    chunk_size: parseInt_(chatSetting.chunkSize),
    top_p: parseFloat_(chatSetting.top_P),
    top_k: parseInt_(chatSetting.top_K),
    temperature: parseFloat_(chatSetting.temperature),
  };

  if (kb_ids !== undefined) params.kb_ids = kb_ids;
  if (options.bot_name !== undefined) params.bot_name = options.bot_name;
  if (options.description !== undefined) params.description = options.description;
  if (options.head_image !== undefined) params.head_image = options.head_image;
  if (options.prompt_setting !== undefined) params.prompt_setting = options.prompt_setting;
  if (options.welcome_message !== undefined) params.welcome_message = options.welcome_message;

  return params;
}
