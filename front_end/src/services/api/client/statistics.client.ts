import { post, postWithBlob } from './base';
import { adaptQAInfoList, adaptStatisticsOverview } from '../adapters';
import type {
  IGetQAInfoParams,
  IGetQAInfoResult,
  IStatisticsOverview,
  IStatisticsOverviewRaw,
} from '../types/statistics';

const URL = {
  GET_QA_INFO: '/local_doc_qa/get_qa_info',
};

type RawAdapterInput = Record<string, unknown>;

export const statisticsApi = {
  async getQAList(params: IGetQAInfoParams): Promise<IGetQAInfoResult> {
    const data = await post(URL.GET_QA_INFO, params);
    return adaptQAInfoList(data as RawAdapterInput);
  },

  async exportQA(params: IGetQAInfoParams): Promise<unknown> {
    return postWithBlob(URL.GET_QA_INFO, {
      ...params,
      save_to_excel: true,
    });
  },

  async getOverview(params?: Record<string, unknown>): Promise<IStatisticsOverview> {
    const data = await post<IStatisticsOverviewRaw>(URL.GET_QA_INFO, params ?? {});
    return adaptStatisticsOverview(data);
  },
};
