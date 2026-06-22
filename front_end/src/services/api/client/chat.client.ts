import { post } from './base';
import { adaptSendQuestionResult, adaptTagsResponse } from '../adapters';
import type {
  IGetTagsParams,
  IUpdateTagsParams,
} from '../types/knowledge';
import type {
  ISendQuestionParams,
  ISendQuestionResult,
} from '../types/chat';

const URL = {
  SEND_QUESTION: '/local_doc_qa/local_doc_chat',
  GET_TAGS: '/local_doc_qa/get_tags',
  UPDATE_TAGS: '/local_doc_qa/update_tags',
};

export const chatApi = {
  async sendQuestion(
    params: ISendQuestionParams,
    options?: { signal?: AbortSignal }
  ): Promise<ISendQuestionResult> {
    const data = await post(URL.SEND_QUESTION, params, {
      signal: options?.signal,
    });
    return adaptSendQuestionResult(data as Record<string, unknown>, params.question);
  },

  async getTags(params: IGetTagsParams): Promise<Record<string, string[]>> {
    const data = await post(URL.GET_TAGS, params);
    return adaptTagsResponse(data as Record<string, unknown>);
  },

  async updateTags(params: IUpdateTagsParams): Promise<unknown> {
    return post(URL.UPDATE_TAGS, params);
  },
};
