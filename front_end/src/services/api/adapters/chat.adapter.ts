import {
  ensureArray,
  ensureBoolean,
  ensureNumber,
  ensureString,
} from './common.adapter';
import type {
  IChatItem,
  IChatItemRaw,
  IDataSource,
  IDataSourceRaw,
  ISendQuestionResult,
  ISendQuestionRawResponse,
  ITimeInfo,
  ITokenInfo,
} from '../types/chat';
import type { ChatRole } from '../types/chat';

export function adaptDataSource(raw: IDataSourceRaw): IDataSource {
  return {
    dataSource: ensureString(raw.dataSource),
    detailDataSource: ensureString(raw.detailDataSource),
    fileName: raw.file_name ?? null,
    content: raw.content ?? null,
    score: raw.score ?? null,
    fileId: raw.file_id ?? null,
    fileUrl: raw.file_url ?? null,
    showDetailDataSource: ensureBoolean(raw.showDetailDataSource, false),
    chunks: raw.chunks,
    pageSizes: raw.pageSizes,
    raw,
  };
}

export function adaptDataSourceList(rawList: IDataSourceRaw[] | undefined): IDataSource[] {
  return ensureArray(rawList).map(adaptDataSource);
}

export function adaptChatItem(raw: IChatItemRaw, defaultType: ChatRole = 'ai'): IChatItem {
  const sourcesRaw = raw.source ?? raw.sources ?? [];
  return {
    type: (raw.type as ChatRole) ?? defaultType,
    question: ensureString(raw.question ?? raw.condense_question),
    answer: ensureString(raw.answer ?? raw.result),
    like: ensureBoolean(raw.like, false),
    unlike: ensureBoolean(raw.unlike, false),
    copied: false,
    onlySearch: ensureBoolean(raw.onlySearch, false),
    showTools: false,
    sources: adaptDataSourceList(sourcesRaw),
    qaId: raw.qaId ? ensureString(raw.qaId) : undefined,
    raw,
  };
}

export function adaptTimeInfo(raw: Partial<ITimeInfo> | undefined): ITimeInfo {
  return {
    preprocess: ensureNumber(raw?.preprocess, 0),
    condense_q_chain: ensureNumber(raw?.condense_q_chain, 0),
    retriever_search: ensureNumber(raw?.retriever_search, 0),
    web_search: ensureNumber(raw?.web_search, 0),
    rerank: ensureNumber(raw?.rerank, 0),
    reprocess: ensureNumber(raw?.reprocess, 0),
    llm_first_return: ensureNumber(raw?.llm_first_return, 0),
    first_return: ensureNumber(raw?.first_return, 0),
    llm_completed: ensureNumber(raw?.llm_completed, 0),
    chat_completed: ensureNumber(raw?.chat_completed, 0),
  };
}

export function adaptTokenInfo(raw: Partial<ITokenInfo> | undefined): ITokenInfo {
  return {
    total_tokens: ensureNumber(raw?.total_tokens, 0),
    prompt_tokens: ensureNumber(raw?.prompt_tokens, 0),
    completion_tokens: ensureNumber(raw?.completion_tokens, 0),
    tokens_per_second: ensureNumber(raw?.tokens_per_second, 0),
  };
}

export function adaptSendQuestionResult(
  raw: ISendQuestionRawResponse,
  originalQuestion?: string
): ISendQuestionResult {
  const sourcesRaw = raw.source ?? raw.sources ?? [];
  return {
    answer: ensureString(raw.result ?? raw.answer),
    question: ensureString(raw.condense_question ?? originalQuestion),
    sources: adaptDataSourceList(sourcesRaw),
    timeInfo: raw.time_info ? adaptTimeInfo(raw.time_info) : undefined,
    tokenInfo: raw.token_info ? adaptTokenInfo(raw.token_info) : undefined,
    raw,
  };
}
