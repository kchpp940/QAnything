import type { IBaseBotParams } from './common';

export interface IBotRaw {
  bot_id?: string;
  bot_name?: string;
  bot_desc?: string;
  kb_ids?: string[];
  avatar?: string;
  icon_url?: string;
  is_public?: boolean;
  is_published?: boolean;
  create_time?: string;
  update_time?: string;
  bot_avatar?: string;
  bot_knowledge_list?: string[];
  [key: string]: unknown;
}

export interface IBot {
  id: string;
  name: string;
  description: string;
  kbIds: string[];
  avatar: string;
  isPublic: boolean;
  isPublished: boolean;
  createTime: string;
  updateTime: string;
  raw: IBotRaw;
}

export interface ICreateBotParams {
  bot_name?: string;
  bot_desc?: string;
  kb_ids?: string[];
  bot_avatar?: string;
  avatar?: string;
  [key: string]: unknown;
}

export interface IUpdateBotParams extends IBaseBotParams {
  bot_name?: string;
  bot_desc?: string;
  kb_ids?: string[];
  bot_avatar?: string;
  is_public?: boolean;
  is_published?: boolean;
  [key: string]: unknown;
}

export interface IQueryBotInfoParams {
  bot_id?: string;
  [key: string]: unknown;
}

export interface IDeleteBotParams extends IBaseBotParams {}

export interface IBotListResponse {
  bot_list?: IBotRaw[];
  default_bot_list?: IBotRaw[];
  data?: IBotRaw[];
  [key: string]: unknown;
}

export interface IBotListResult {
  bots: IBot[];
  defaultBots: IBot[];
  raw: IBotListResponse;
}
