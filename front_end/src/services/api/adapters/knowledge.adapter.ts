import {
  ensureArray,
  ensureBoolean,
  ensureNumber,
  ensureString,
  normalizeBytes,
  normalizeFileStatus,
  normalizeStatusCount,
  normalizeTags,
  normalizeTimestamp,
  parseRemarkMessage,
} from './common.adapter';
import type {
  IDocChunksResult,
  IFileBase64Result,
  IFileListResult,
  IFaqFile,
  IFaqListResult,
  IKbFile,
  IKbFileRaw,
  IKnowledgeBase,
  IKnowledgeBaseRaw,
  IChunk,
  IChunkLocation,
  IChunkRaw,
} from '../types/knowledge';
import type { EFileStatus } from '../types/common';

export function adaptKnowledgeBase(raw: IKnowledgeBaseRaw): IKnowledgeBase {
  return {
    id: ensureString(raw.kb_id),
    name: ensureString(raw.kb_name),
    isFaq: ensureBoolean(raw.isFaq, false),
    createTime: ensureString(raw.createTime),
    raw,
  };
}

export function adaptKnowledgeBaseList(rawList: IKnowledgeBaseRaw[] | undefined): IKnowledgeBase[] {
  return ensureArray(rawList).map(adaptKnowledgeBase);
}

export function adaptKbFile(raw: IKbFileRaw): IKbFile {
  const status = normalizeFileStatus(raw.status);
  const bytes = normalizeBytes(raw.bytes);
  return {
    id: ensureString(raw.file_id),
    name: ensureString(raw.file_name),
    status,
    bytes: bytes.raw,
    contentLength: ensureNumber(raw.content_length, 0),
    tags: normalizeTags(raw.tags),
    timestamp: ensureString(raw.timestamp),
    createTime: normalizeTimestamp(raw.timestamp),
    remark: parseRemarkMessage(raw.msg, status as EFileStatus),
    raw,
  };
}

export function adaptFaqFile(raw: IKbFileRaw): IFaqFile {
  const status = normalizeFileStatus(raw.status);
  return {
    id: ensureString(raw.file_id),
    question: ensureString(raw.question),
    answer: ensureString(raw.answer),
    status,
    contentLength: ensureNumber(raw.content_length, 0),
    timestamp: ensureString(raw.timestamp),
    createTime: normalizeTimestamp(raw.timestamp),
    picUrlList: ensureArray(raw.picUrlList).map(u => ensureString(u)),
    raw,
  };
}

export function adaptFileList(raw: {
  status_count?: Record<string, unknown>;
  total?: number;
  details?: IKbFileRaw[];
  [key: string]: unknown;
}): IFileListResult {
  return {
    statusCount: normalizeStatusCount(raw.status_count),
    total: ensureNumber(raw.total, 0),
    files: ensureArray(raw.details).map(adaptKbFile),
    raw: raw as IFileListResult['raw'],
  };
}

export function adaptFaqList(raw: {
  status_count?: Record<string, unknown>;
  total?: number;
  details?: IKbFileRaw[];
  [key: string]: unknown;
}): IFaqListResult {
  return {
    statusCount: normalizeStatusCount(raw.status_count),
    total: ensureNumber(raw.total, 0),
    faqs: ensureArray(raw.details).map(adaptFaqFile),
    raw: raw as IFaqListResult['raw'],
  };
}

export function adaptFileBase64(raw: {
  file_base64?: string;
  data?: string;
  [key: string]: unknown;
}): IFileBase64Result {
  return {
    base64: ensureString(raw.file_base64 ?? raw.data),
  };
}

export function adaptChunk(raw: IChunkRaw): IChunk {
  const locations = ensureArray(raw.locations).map<IChunkLocation>(loc => ({
    pageId: ensureNumber((loc as Record<string, unknown>)?.page_id, 0),
    pageW: ensureNumber((loc as Record<string, unknown>)?.page_w, 0),
    pageH: ensureNumber((loc as Record<string, unknown>)?.page_h, 0),
    linesBox: (loc as Record<string, unknown>)?.lines,
    bbox: ensureArray((loc as Record<string, unknown>)?.bbox).map(n => ensureNumber(n, 0)),
  }));
  return {
    chunkId: ensureString(raw.chunk_id),
    chunkType: ensureString(raw.chunk_type),
    content: ensureString(raw.content),
    locations,
    raw,
  };
}

export function adaptDocChunks(raw: {
  chunks?: IChunkRaw[];
  [key: string]: unknown;
}): IDocChunksResult {
  const chunks = ensureArray(raw.chunks).map(adaptChunk);

  let sizeArr: Array<{ page_w: number; page_h: number }> = [];
  let pagesInfoArr: IChunkLocation[][] = [];

  chunks.forEach(chunk => {
    if (chunk.chunkType === 'normal') {
      chunk.locations.forEach(loc => {
        const pageId = loc.pageId;
        if (!sizeArr[pageId]) {
          sizeArr[pageId] = { page_w: loc.pageW, page_h: loc.pageH };
        }
        if (!pagesInfoArr[pageId]) {
          pagesInfoArr[pageId] = [];
        }
        pagesInfoArr[pageId].push({
          pageId: loc.pageId,
          pageW: loc.pageW,
          pageH: loc.pageH,
          linesBox: loc.linesBox,
          bbox: loc.bbox,
        });
      });
    } else {
      chunk.locations.forEach(loc => {
        const pageId = loc.pageId;
        if (!sizeArr[pageId]) {
          sizeArr[pageId] = { page_w: loc.pageW, page_h: loc.pageH };
        }
      });
    }
  });

  return {
    chunks,
    pagesInfo: pagesInfoArr,
    pageSizes: sizeArr,
  };
}

export function adaptTagsResponse(raw: Record<string, unknown>): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  Object.keys(raw).forEach(key => {
    result[key] = normalizeTags(raw[key]);
  });
  return result;
}
