import {
  IRetrievalCandidate,
  IWebSearchResult,
  NormalizedRetrievalTrace,
  NormalizedWebSearchTrace,
} from '@/utils/types';

const isArray = (v: unknown): v is unknown[] => Array.isArray(v);

const isArrayWithContent = (v: unknown): v is unknown[] => isArray(v) && v.length > 0;

const isRecord = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === 'object' && !isArray(v);

const asString = (v: unknown): string | undefined =>
  typeof v === 'string' && v.length > 0 ? v : undefined;

const asNumber = (v: unknown): number | undefined =>
  typeof v === 'number' && Number.isFinite(v) ? v : undefined;

const asBoolean = (v: unknown): boolean | undefined => (typeof v === 'boolean' ? v : undefined);

const asRetrievalCandidate = (v: unknown): IRetrievalCandidate | null => {
  if (!isRecord(v)) return null;
  const doc_id = asString(v.doc_id) || '';
  const doc_name = asString(v.doc_name) || '';
  const scoreRaw = typeof v.score === 'string' ? parseFloat(v.score) : v.score;
  const score = asNumber(scoreRaw) ?? 0;
  if (!doc_id && !doc_name) return null;
  return {
    doc_id,
    doc_name,
    score,
    content: asString(v.content),
    rank: asNumber(v.rank),
    retrieval_source: asString(v.retrieval_source),
    embed_version: asString(v.embed_version),
  };
};

const asWebSearchResult = (v: unknown): IWebSearchResult | null => {
  if (!isRecord(v)) return null;
  const title = asString(v.title) || '';
  const url = asString(v.url) || '';
  if (!url) return null;
  const scoreRaw = typeof v.score === 'string' ? parseFloat(v.score) : v.score;
  return {
    title,
    url,
    snippet: asString(v.snippet),
    score: asNumber(scoreRaw),
  };
};

const mapCandidates = (raw: unknown): IRetrievalCandidate[] => {
  if (!isArrayWithContent(raw)) return [];
  return raw.map(asRetrievalCandidate).filter((c): c is IRetrievalCandidate => c !== null);
};

const mapResults = (raw: unknown): IWebSearchResult[] => {
  if (!isArrayWithContent(raw)) return [];
  return raw.map(asWebSearchResult).filter((r): r is IWebSearchResult => r !== null);
};

export const adaptRetrievalTrace = (raw: unknown): NormalizedRetrievalTrace => {
  const empty: NormalizedRetrievalTrace = {
    candidates: [],
    hasContent: false,
  };

  if (!raw) return empty;

  if (isArray(raw)) {
    const candidates = mapCandidates(raw);
    return {
      candidates,
      hasContent: candidates.length > 0,
    };
  }

  if (!isRecord(raw)) return empty;

  const candidates = mapCandidates(raw.candidates);
  const retrievalQuery =
    asString(raw.retrieval_query) || asString(raw.retrievalQuery) || asString(raw.query);
  const totalCount =
    asNumber(raw.total_count) ||
    asNumber(raw.totalCount) ||
    (candidates.length > 0 ? candidates.length : undefined);
  const durationMs =
    asNumber(raw.duration_ms) || asNumber(raw.durationMs) || asNumber(raw.duration);
  const retrievalSource =
    asString(raw.retrieval_source) || asString(raw.retrievalSource) || asString(raw.source);

  const hasContent =
    candidates.length > 0 || typeof retrievalQuery === 'string' || typeof totalCount === 'number';

  return {
    candidates,
    retrievalQuery,
    totalCount,
    durationMs,
    retrievalSource,
    hasContent,
  };
};

const DEFAULT_POLICY = 'auto';

const POLICY_TEXT_MAP: Record<string, string> = {
  auto: '自动判断',
  always: '强制联网',
  disabled: '禁止联网',
  never: '禁止联网',
  manual: '手动触发',
  low_recall: '低召回触发',
};

export const getPolicyText = (policy: string): string => POLICY_TEXT_MAP[policy] || policy;

export const adaptWebSearchTrace = (raw: unknown): NormalizedWebSearchTrace => {
  const empty: NormalizedWebSearchTrace = {
    triggered: false,
    policy: DEFAULT_POLICY,
    results: [],
    hasContent: false,
  };

  if (!raw) return empty;

  if (isArray(raw)) {
    const results = mapResults(raw);
    return {
      triggered: results.length > 0,
      policy: DEFAULT_POLICY,
      results,
      count: results.length > 0 ? results.length : undefined,
      hasContent: results.length > 0,
    };
  }

  if (!isRecord(raw)) return empty;

  const results = mapResults(raw.results);
  const triggered =
    asBoolean(raw.triggered) ??
    (typeof raw.triggered === 'string' ? raw.triggered === 'true' : results.length > 0);
  const policy = asString(raw.policy) || DEFAULT_POLICY;
  const reason = asString(raw.reason);
  const count = asNumber(raw.count) || (results.length > 0 ? results.length : undefined);
  const durationMs =
    asNumber(raw.duration_ms) || asNumber(raw.durationMs) || asNumber(raw.duration);

  const hasContent =
    results.length > 0 ||
    triggered ||
    (typeof reason === 'string' && reason.length > 0) ||
    typeof count === 'number' ||
    (policy !== DEFAULT_POLICY && policy.length > 0);

  return {
    triggered,
    policy,
    reason,
    count,
    results,
    durationMs,
    hasContent,
  };
};

export interface AdaptedTraces {
  retrieval: NormalizedRetrievalTrace;
  webSearch: NormalizedWebSearchTrace;
}

export const adaptTraces = (chatItem: {
  retrieval_trace?: unknown;
  web_search_trace?: unknown;
}): AdaptedTraces => ({
  retrieval: adaptRetrievalTrace(chatItem.retrieval_trace),
  webSearch: adaptWebSearchTrace(chatItem.web_search_trace),
});
