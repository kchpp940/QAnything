export enum EHttpMethod {
  POST = 'post',
  GET = 'get',
}

export enum EResponseCode {
  SUCCESS = 200,
  SUCCESS_V2 = 0,
  NO_LOGIN = 401,
  NO_PERMISSION = 403,
  SERVER_ERROR = 500,
}

export enum EFileStatus {
  SUCCESS = 'green',
  PARSING = 'yellow',
  WAITING = 'gray',
  FAILED = 'red',
  LOADING = 'loading',
}

export type FileStatus = EFileStatus | string;

export interface IApiBaseResponse<T = unknown> {
  code: number;
  msg?: string;
  message?: string;
  data?: T;
  result?: T;
  errorCode?: string;
  [key: string]: unknown;
}

export interface IRequestOptions {
  showLoading?: boolean;
  loadingId?: string;
  cancelRepeat?: boolean;
  sign?: boolean;
  signal?: AbortSignal;
  responseType?: 'arraybuffer' | 'blob' | 'document' | 'json' | 'text' | 'stream';
  getResponseHeader?: boolean;
  timeout?: number;
  headers?: Record<string, string>;
  [key: string]: unknown;
}

export interface IPaginationParams {
  page_id?: number;
  page_limit?: number;
}

export interface IPaginationResult<T> {
  total: number;
  total_count?: number;
  details?: T[];
  list?: T[];
  items?: T[];
  [key: string]: unknown;
}

export interface IStatusCount {
  green: number;
  gray: number;
  yellow: number;
  red: number;
  [key: string]: number;
}

export interface IUserContext {
  user_id: string;
  user_info: string;
}

export interface IBaseKbParams {
  kb_id: string;
}

export interface IBaseBotParams {
  bot_id: string;
}

export interface IBaseFileParams {
  file_id: string;
}
