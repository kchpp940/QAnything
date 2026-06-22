import {
  ensureArray,
  ensureNumber,
  ensureString,
  normalizeKbIds,
} from './common.adapter';
import type {
  IGetQAInfoResult,
  IGetQAOverviewResult,
  IGetKbStatusResult,
  IKbFileStatusCount,
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

function adaptStatusCount(raw: Record<string, unknown>): IKbFileStatusCount {
  return {
    green: ensureNumber(raw.green, 0),
    yellow: ensureNumber(raw.yellow, 0),
    red: ensureNumber(raw.red, 0),
    gray: ensureNumber(raw.gray, 0),
  };
}

export function adaptKbStatusByDate(
  raw: IGetKbStatusResult['raw'],
  userKey: string
): IGetKbStatusResult {
  const status = raw.status ?? {};
  const byDateRaw = status[userKey] as unknown as Record<string, Record<string, number>> | undefined;

  const byDate: IGetKbStatusResult['byDate'] = [];
  if (byDateRaw && typeof byDateRaw === 'object') {
    Object.entries(byDateRaw).forEach(([date, fileStatus]) => {
      byDate.push({
        date: ensureString(date),
        fileStatus: adaptStatusCount(fileStatus as Record<string, unknown>),
      });
    });
  }

  return {
    byUser: { green: 0, yellow: 0, red: 0, gray: 0 },
    byDate,
    raw,
  };
}

export function adaptQAOverviewByDay(
  raw: IGetQAOverviewResult['raw']
): IGetQAOverviewResult {
  const byDayRaw = raw.qa_infos_by_day ?? {};
  const byDate: IGetQAOverviewResult['byDate'] = [];

  if (byDayRaw && typeof byDayRaw === 'object') {
    Object.entries(byDayRaw).forEach(([date, count]) => {
      byDate.push({
        date: ensureString(date),
        count: ensureNumber(count, 0),
      });
    });
  }

  return {
    byDate,
    total: ensureNumber(raw.total_count, 0),
    raw,
  };
}
