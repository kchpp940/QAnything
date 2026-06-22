import {
  ensureArray,
  ensureBoolean,
  ensureString,
} from './common.adapter';
import type {
  IBot,
  IBotListResult,
  IBotRaw,
} from '../types/bot';

export function adaptBot(raw: IBotRaw): IBot {
  const kbIds = ensureArray(raw.kb_ids ?? raw.bot_knowledge_list).map(id => ensureString(id));
  return {
    id: ensureString(raw.bot_id),
    name: ensureString(raw.bot_name),
    description: ensureString(raw.bot_desc),
    kbIds,
    avatar: ensureString(raw.bot_avatar ?? raw.avatar ?? raw.icon_url),
    isPublic: ensureBoolean(raw.is_public, false),
    isPublished: ensureBoolean(raw.is_published, false),
    createTime: ensureString(raw.create_time),
    updateTime: ensureString(raw.update_time),
    raw,
  };
}

export function adaptBotList(raw: {
  bot_list?: IBotRaw[];
  default_bot_list?: IBotRaw[];
  data?: IBotRaw[];
  [key: string]: unknown;
}): IBotListResult {
  const botListRaw = raw.bot_list ?? raw.data ?? [];
  const defaultBotListRaw = raw.default_bot_list ?? [];
  return {
    bots: ensureArray(botListRaw).map(adaptBot),
    defaultBots: ensureArray(defaultBotListRaw).map(adaptBot),
    raw: raw as IBotListResult['raw'],
  };
}

export function adaptSingleBot(raw: IBotRaw | IBotRaw[] | undefined): IBot | null {
  if (Array.isArray(raw)) {
    return raw.length > 0 ? adaptBot(raw[0]) : null;
  }
  return raw ? adaptBot(raw) : null;
}
