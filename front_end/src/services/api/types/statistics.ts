import type { IPaginationParams } from './common';

export interface IQARecordRaw {
  qa_id?: string;
  kb_ids?: string[] | string;
  question?: string;
  condense_question?: string;
  answer?: string;
  result?: string;
  timestamp?: string;
  time?: string;
  [key: string]: unknown;
}

export interface IQARecord {
  id: string;
  kbIds: string[];
  kbIdsDisplay: string;
  question: string;
  answer: string;
  date: string;
  timestamp: string;
  raw: IQARecordRaw;
}

export interface IGetQAInfoParams extends IPaginationParams {
  time_start?: string;
  time_end?: string;
  query?: string;
  question?: string;
  save_to_excel?: boolean;
  qa_ids?: string[];
}

export interface IGetQAInfoRawResponse {
  total_count?: number;
  total?: number;
  qa_infos?: IQARecordRaw[];
  list?: IQARecordRaw[];
  data?: IQARecordRaw[];
  [key: string]: unknown;
}

export interface IGetQAInfoResult {
  total: number;
  records: IQARecord[];
  raw: IGetQAInfoRawResponse;
}

export interface IStatisticsOverviewRaw {
  total_qa?: number;
  total_kb?: number;
  total_files?: number;
  qa_trend?: Array<{ date: string; count: number }>;
  [key: string]: unknown;
}

export interface IStatisticsOverview {
  totalQA: number;
  totalKb: number;
  totalFiles: number;
  qaTrend: Array<{ date: string; count: number }>;
  raw: IStatisticsOverviewRaw;
}
