import { post } from './base';
import { adaptBotList, adaptSingleBot } from '../adapters';
import type {
  IBot,
  IBotListResult,
  IBotRaw,
  ICreateBotParams,
  IDeleteBotParams,
  IQueryBotInfoParams,
  IUpdateBotParams,
} from '../types/bot';

const URL = {
  CREATE_BOT: '/local_doc_qa/new_bot',
  UPDATE_BOT: '/local_doc_qa/update_bot',
  QUERY_BOT: '/local_doc_qa/get_bot_info',
  DELETE_BOT: '/local_doc_qa/delete_bot',
};

type RawAdapterInput = Record<string, unknown>;

export const botApi = {
  async createBot(params: ICreateBotParams): Promise<unknown> {
    return post(URL.CREATE_BOT, params);
  },

  async updateBot(params: IUpdateBotParams): Promise<unknown> {
    return post(URL.UPDATE_BOT, params);
  },

  async getBotList(params: IQueryBotInfoParams = {}): Promise<IBotListResult> {
    const data = await post(URL.QUERY_BOT, params);
    return adaptBotList(data as RawAdapterInput);
  },

  async getBot(params: IQueryBotInfoParams): Promise<IBot | null> {
    const data = await post(URL.QUERY_BOT, params);
    return adaptSingleBot(data as unknown as IBotRaw | IBotRaw[]);
  },

  async deleteBot(params: IDeleteBotParams): Promise<unknown> {
    return post(URL.DELETE_BOT, params);
  },
};
