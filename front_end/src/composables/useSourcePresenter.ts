import {
  IDataSourceItem,
  IRetrievalTrace,
  IRetrievalCandidate,
  IWebSearchTrace,
  IWebSearchResult,
  IChatItem,
  WebSearchPolicy,
} from '@/utils/types';
import { useChatSourceFile } from './useChatSourceFile';
import { getLanguage } from '@/language';

const sourceLabels = getLanguage().source || {
  kbSources: '知识库来源',
  webSearch: '联网搜索',
  retrievalTrace: '检索追踪',
  otherSources: '其他来源',
};

export type SourceGroupType = 'kb' | 'web' | 'retrieval' | 'other';

export type ScoreLevel = 'high' | 'medium' | 'low' | 'unknown';

export type NormalizedSourceRaw = IDataSourceItem | IRetrievalCandidate | IWebSearchResult;

export interface NormalizedSourceItem {
  id: string;
  name: string | null;
  content: string | null;
  score: number | null;
  scoreText: string;
  scoreLevel: ScoreLevel;
  linkUrl: string | null;
  isExternalLink: boolean;
  isPreviewable: boolean;
  raw: NormalizedSourceRaw;
  sourceType: SourceGroupType;
  rank?: number;
  retrievalSource?: string;
}

export interface SourceGroup {
  type: SourceGroupType;
  label: string;
  items: NormalizedSourceItem[];
  count: number;
  totalCount?: number;
  retrievalQuery?: string;
  durationMs?: number;
  retrievalSource?: string;
}

export interface WebSearchMeta {
  triggered: boolean;
  policy: WebSearchPolicy;
  policyText: string;
  reason?: string;
  count?: number;
  durationMs?: number;
}

export interface SourcePanelViewModel {
  groups: SourceGroup[];
  totalCount: number;
  hasContent: boolean;
  hasKbSources: boolean;
  hasWebSearch: boolean;
  hasRetrievalTrace: boolean;
  webSearch: WebSearchMeta;
}

const POLICY_TEXT: Record<WebSearchPolicy, string> = {
  auto: '自动判断',
  always: '强制联网',
  never: '禁止联网',
};

const getScoreLevel = (score: number | null): ScoreLevel => {
  if (score === null || score === undefined || Number.isNaN(score)) return 'unknown';
  if (score >= 0.8) return 'high';
  if (score >= 0.5) return 'medium';
  return 'low';
};

const formatScore = (score: number | null): string => {
  if (score === null || score === undefined || Number.isNaN(score)) return '-';
  return Number(score).toFixed(2);
};

const normalizeFromDataSource = (item: IDataSourceItem, index: number): NormalizedSourceItem => {
  const { checkFileType } = useChatSourceFile();
  const linkUrl = item.file_url || item.file_id;
  const isExternalLink = !!(linkUrl && typeof linkUrl === 'string' && linkUrl.startsWith('http'));
  const isPreviewable = checkFileType(item.file_name || '');
  const scoreNum = typeof item.score === 'string' ? parseFloat(item.score) : item.score;
  const sourceType: 'kb' | 'web' | 'other' = isExternalLink ? 'web' : item.file_id ? 'kb' : 'other';

  return {
    id: `ds-${index}-${item.file_id || item.file_url || index}`,
    name: item.file_name,
    content: item.content,
    score: scoreNum,
    scoreText: formatScore(scoreNum),
    scoreLevel: getScoreLevel(scoreNum),
    linkUrl,
    isExternalLink,
    isPreviewable,
    raw: item,
    sourceType,
  };
};

const normalizeFromRetrievalCandidate = (
  item: IRetrievalCandidate,
  index: number
): NormalizedSourceItem => {
  return {
    id: `rt-${index}-${item.doc_id}`,
    name: item.doc_name,
    content: item.content || null,
    score: item.score,
    scoreText: formatScore(item.score),
    scoreLevel: getScoreLevel(item.score),
    linkUrl: item.doc_id,
    isExternalLink: false,
    isPreviewable: false,
    raw: item,
    sourceType: 'retrieval',
    rank: item.rank,
    retrievalSource: item.retrieval_source,
  };
};

const normalizeFromWebSearchResult = (
  item: IWebSearchResult,
  index: number
): NormalizedSourceItem => {
  return {
    id: `ws-${index}-${item.url}`,
    name: item.title,
    content: item.snippet || null,
    score: item.score ?? null,
    scoreText: formatScore(item.score ?? null),
    scoreLevel: getScoreLevel(item.score ?? null),
    linkUrl: item.url,
    isExternalLink: true,
    isPreviewable: false,
    raw: item,
    sourceType: 'web',
  };
};

const isArrayWithContent = (v: unknown): v is unknown[] => {
  return Array.isArray(v) && v.length > 0;
};

const isRetrievalTrace = (v: unknown): v is IRetrievalTrace => {
  if (!v || typeof v !== 'object') return false;
  const obj = v as Record<string, unknown>;
  return isArrayWithContent(obj.candidates) || typeof obj.retrieval_query === 'string';
};

const isWebSearchTrace = (v: unknown): v is IWebSearchTrace => {
  if (!v || typeof v !== 'object') return false;
  const obj = v as Record<string, unknown>;
  return (
    typeof obj.triggered === 'boolean' ||
    typeof obj.policy === 'string' ||
    isArrayWithContent(obj.results)
  );
};

const createGroup = (
  type: SourceGroupType,
  items: NormalizedSourceItem[],
  extras: Partial<SourceGroup> = {}
): SourceGroup | null => {
  if (!items.length) return null;

  const labelMap: Record<SourceGroupType, string> = {
    kb: sourceLabels.kbSources || '知识库来源',
    web: sourceLabels.webSearch || '联网搜索',
    retrieval: sourceLabels.retrievalTrace || '检索追踪',
    other: sourceLabels.otherSources || '其他来源',
  };

  return {
    type,
    label: labelMap[type],
    items,
    count: items.length,
    ...extras,
  };
};

const buildWebSearchMeta = (trace?: IWebSearchTrace | null): WebSearchMeta => {
  if (!trace) {
    return {
      triggered: false,
      policy: 'auto',
      policyText: POLICY_TEXT.auto,
    };
  }
  const policy = trace.policy || 'auto';
  return {
    triggered: !!trace.triggered,
    policy,
    policyText: POLICY_TEXT[policy] || policy,
    reason: trace.reason,
    count: trace.count ?? trace.results?.length,
    durationMs: trace.duration_ms,
  };
};

export function useSourcePresenter() {
  const { handleChatSource } = useChatSourceFile();

  const showSourceIdxs = ref<number[]>([]);
  const showDetailIdxs = ref<Record<number, number[]>>({});

  const buildViewModel = (chatItem: IChatItem): SourcePanelViewModel => {
    const sourceItems = isArrayWithContent(chatItem.source) ? chatItem.source : [];
    const retrievalTrace = isRetrievalTrace(chatItem.retrieval_trace)
      ? chatItem.retrieval_trace
      : null;
    const webSearchTrace = isWebSearchTrace(chatItem.web_search_trace)
      ? chatItem.web_search_trace
      : null;

    const kbItems: NormalizedSourceItem[] = [];
    const webItems: NormalizedSourceItem[] = [];
    const retrievalItems: NormalizedSourceItem[] = [];
    const otherItems: NormalizedSourceItem[] = [];

    sourceItems.forEach((item, index) => {
      const normalized = normalizeFromDataSource(item, index);
      switch (normalized.sourceType) {
        case 'kb':
          kbItems.push(normalized);
          break;
        case 'web':
          webItems.push(normalized);
          break;
        default:
          otherItems.push(normalized);
      }
    });

    if (retrievalTrace && isArrayWithContent(retrievalTrace.candidates)) {
      retrievalTrace.candidates.forEach((item, index) => {
        retrievalItems.push(normalizeFromRetrievalCandidate(item, index));
      });
    }

    if (webSearchTrace && isArrayWithContent(webSearchTrace.results)) {
      webSearchTrace.results.forEach((item, index) => {
        webItems.push(normalizeFromWebSearchResult(item, index));
      });
    }

    const groups: SourceGroup[] = [];
    const kbGroup = createGroup('kb', kbItems);
    const webGroup = createGroup('web', webItems, {
      totalCount: webSearchTrace?.count,
      durationMs: webSearchTrace?.duration_ms,
    });
    const retrievalGroup = createGroup('retrieval', retrievalItems, {
      totalCount: retrievalTrace?.total_count,
      retrievalQuery: retrievalTrace?.retrieval_query,
      durationMs: retrievalTrace?.duration_ms,
      retrievalSource: retrievalTrace?.retrieval_source,
    });
    const otherGroup = createGroup('other', otherItems);

    if (kbGroup) groups.push(kbGroup);
    if (retrievalGroup) groups.push(retrievalGroup);
    if (webGroup) groups.push(webGroup);
    if (otherGroup) groups.push(otherGroup);

    const totalCount = kbItems.length + webItems.length + retrievalItems.length + otherItems.length;

    const webSearch = buildWebSearchMeta(webSearchTrace);
    const hasWebSearch =
      webItems.length > 0 || webSearch.triggered || typeof webSearch.count === 'number';

    return {
      groups,
      totalCount,
      hasContent: groups.length > 0,
      hasKbSources: kbItems.length > 0,
      hasWebSearch,
      hasRetrievalTrace: retrievalItems.length > 0,
      webSearch,
    };
  };

  const normalizeSources = (sources: IDataSourceItem[]): NormalizedSourceItem[] => {
    return sources.map((item, index) => normalizeFromDataSource(item, index));
  };

  const groupSources = (sources: IDataSourceItem[]): SourceGroup[] => {
    const normalized = normalizeSources(sources);
    const kbItems: NormalizedSourceItem[] = [];
    const webItems: NormalizedSourceItem[] = [];
    const otherItems: NormalizedSourceItem[] = [];

    normalized.forEach(item => {
      switch (item.sourceType) {
        case 'kb':
          kbItems.push(item);
          break;
        case 'web':
          webItems.push(item);
          break;
        default:
          otherItems.push(item);
      }
    });

    const groups: SourceGroup[] = [];
    const kbGroup = createGroup('kb', kbItems);
    const webGroup = createGroup('web', webItems);
    const otherGroup = createGroup('other', otherItems);

    if (kbGroup) groups.push(kbGroup);
    if (webGroup) groups.push(webGroup);
    if (otherGroup) groups.push(otherGroup);

    return groups;
  };

  const showSourceList = (index: number) => {
    if (!showSourceIdxs.value.includes(index)) {
      showSourceIdxs.value.push(index);
    }
  };

  const hideSourceList = (index: number) => {
    showSourceIdxs.value = showSourceIdxs.value.filter(i => i !== index);
  };

  const isSourceVisible = (index: number): boolean => {
    return showSourceIdxs.value.includes(index);
  };

  const showDetail = (msgIndex: number, sourceIndex: number) => {
    if (!showDetailIdxs.value[msgIndex]) {
      showDetailIdxs.value[msgIndex] = [];
    }
    if (!showDetailIdxs.value[msgIndex].includes(sourceIndex)) {
      showDetailIdxs.value[msgIndex].push(sourceIndex);
    }
  };

  const hideDetail = (msgIndex: number, sourceIndex: number) => {
    if (showDetailIdxs.value[msgIndex]) {
      showDetailIdxs.value[msgIndex] = showDetailIdxs.value[msgIndex].filter(
        i => i !== sourceIndex
      );
    }
  };

  const isDetailVisible = (msgIndex: number, sourceIndex: number): boolean => {
    return !!(
      showDetailIdxs.value[msgIndex] && showDetailIdxs.value[msgIndex].includes(sourceIndex)
    );
  };

  const toggleDetail = (msgIndex: number, sourceIndex: number) => {
    if (isDetailVisible(msgIndex, sourceIndex)) {
      hideDetail(msgIndex, sourceIndex);
    } else {
      showDetail(msgIndex, sourceIndex);
    }
  };

  const handleSourceClick = (sourceItem: IDataSourceItem) => {
    handleChatSource(sourceItem);
  };

  return {
    showSourceIdxs,
    showDetailIdxs,
    buildViewModel,
    normalizeSources,
    groupSources,
    showSourceList,
    hideSourceList,
    isSourceVisible,
    showDetail,
    hideDetail,
    isDetailVisible,
    toggleDetail,
    handleSourceClick,
    formatScore,
    getScoreLevel,
  };
}
