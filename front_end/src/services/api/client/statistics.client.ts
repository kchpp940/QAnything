import { post, postWithBlob } from './base';
import {
  adaptQAInfoList,
  adaptKbStatusByDate,
  adaptQAOverviewByDay,
  adaptStatisticsOverview,
} from '../adapters';
import type {
  IGetQAInfoParams,
  IGetQAInfoResult,
  IGetQAOverviewResult,
  IGetKbStatusParams,
  IGetKbStatusResult,
  IStatisticsOverview,
  IStatisticsOverviewRaw,
} from '../types/statistics';

const URL = {
  GET_QA_INFO: '/local_doc_qa/get_qa_info',
  GET_KB_STATUS: '/local_doc_qa/get_total_status',
};

type RawAdapterInput = Record<string, unknown>;

export const statisticsApi = {
  async getQAList(params: IGetQAInfoParams): Promise<IGetQAInfoResult> {
    const data = await post(URL.GET_QA_INFO, params);
    return adaptQAInfoList(data as RawAdapterInput);
  },

  async getQAOverviewByDay(params: IGetQAInfoParams): Promise<IGetQAOverviewResult> {
    const data = await post(URL.GET_QA_INFO, { ...params, only_need_count: true });
    return adaptQAOverviewByDay(data as IGetQAOverviewResult['raw']);
  },

  async getKbStatusByDate(params: IGetKbStatusParams, userKey: string): Promise<IGetKbStatusResult> {
    const data = await post(URL.GET_KB_STATUS, { ...params, by_date: true });
    return adaptKbStatusByDate(data as IGetKbStatusResult['raw'], userKey);
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
