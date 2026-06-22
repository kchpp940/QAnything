export * from './base';
export * from './knowledge.client';
export * from './chat.client';
export * from './bot.client';
export * from './statistics.client';
export * from './upload.client';
export * from './auth.client';

import { knowledgeApi } from './knowledge.client';
import { chatApi } from './chat.client';
import { botApi } from './bot.client';
import { statisticsApi } from './statistics.client';
import { uploadApi } from './upload.client';
import { authApi } from './auth.client';

export const api = {
  knowledge: knowledgeApi,
  chat: chatApi,
  bot: botApi,
  statistics: statisticsApi,
  upload: uploadApi,
  auth: authApi,
};

export default api;
