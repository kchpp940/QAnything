import {
  ensureArray,
  ensureNumber,
  ensureString,
  normalizeKbIds,
} from './common.adapter';
import type {
  IGetQAInfoResult,
  IQARecord,
  IQARecordRaw,
  IStatisticsOverview,
  IStatisticsOverviewRaw,
} from '../types/statistics';

export function adaptQARecord(raw: IQARecordRaw): IQARecord {
  const kbIds = normalizeKbIds(raw.kb_ids);
  return {
    id: ensureString(raw.qa_id),
    kbIds: kbIds.raw,
    kbIdsDisplay: kbIds.display,
    question: ensureString(raw.question ?? raw.condense_question),
    answer: ensureString(raw.answer ?? raw.result),
    date: ensureString(raw.timestamp ?? raw.time),
    timestamp: ensureString(raw.timestamp),
    raw,
  };
}

export function adaptQAInfoList(raw: {
  total_count?: number;
  total?: number;
  qa_infos?: IQARecordRaw[];
  list?: IQARecordRaw[];
  data?: IQARecordRaw[];
  [key: string]: unknown;
}): IGetQAInfoResult {
  const recordsRaw = raw.qa_infos ?? raw.list ?? raw.data ?? [];
  return {
    total: ensureNumber(raw.total_count ?? raw.total, 0),
    records: ensureArray(recordsRaw).map(adaptQARecord),
    raw: raw as IGetQAInfoResult['raw'],
  };
}

export function adaptStatisticsOverview(raw: IStatisticsOverviewRaw): IStatisticsOverview {
  return {
    totalQA: ensureNumber(raw.total_qa, 0),
    totalKb: ensureNumber(raw.total_kb, 0),
    totalFiles: ensureNumber(raw.total_files, 0),
    qaTrend: ensureArray(raw.qa_trend).map(item => ({
      date: ensureString((item as Record<string, unknown>)?.date),
      count: ensureNumber((item as Record<string, unknown>)?.count, 0),
    })),
    raw,
  };
}
