import type { FileStatus, IBaseKbParams, IStatusCount } from './common';

export interface IKnowledgeBaseRaw {
  kb_id: string;
  kb_name: string;
  isFaq?: boolean;
  createTime?: unknown;
  [key: string]: unknown;
}

export interface IKnowledgeBase {
  id: string;
  name: string;
  isFaq: boolean;
  createTime?: string;
  raw: IKnowledgeBaseRaw;
}

export interface ICreateKbParams {
  kb_name: string;
  is_faq?: boolean;
  is_quick?: boolean;
}

export interface IRenameKbParams extends IBaseKbParams {
  new_kb_name: string;
}

export interface IDeleteKbParams {
  kb_ids: string[];
}

export interface IKbStatusCount {
  status_count: IStatusCount;
  total: number;
}

export interface IKbTotalStatus {
  [kb_id: string]: IKbStatusCount;
}

export interface IKbFileRaw {
  file_id: string;
  file_name: string;
  status: FileStatus;
  bytes?: number;
  content_length?: number;
  tags?: string[];
  timestamp?: string;
  msg?: string;
  question?: string;
  answer?: string;
  picUrlList?: string[];
  errorText?: string;
  [key: string]: unknown;
}

export interface IKbFile {
  id: string;
  name: string;
  status: FileStatus;
  bytes: number;
  contentLength: number;
  tags: string[];
  timestamp: string;
  createTime: string;
  remark: string | Record<string, string>;
  raw: IKbFileRaw;
}

export interface IFaqFile {
  id: string;
  question: string;
  answer: string;
  status: FileStatus;
  contentLength: number;
  timestamp: string;
  createTime: string;
  picUrlList: string[];
  raw: IKbFileRaw;
}

export interface IFileListParams extends IBaseKbParams {
  page_id?: number;
  page_limit?: number;
}

export interface IFileListRawResponse {
  status_count: IStatusCount;
  total: number;
  details: IKbFileRaw[];
  [key: string]: unknown;
}

export interface IFileListResult {
  statusCount: IStatusCount;
  total: number;
  files: IKbFile[];
  raw: IFileListRawResponse;
}

export interface IFaqListResult {
  statusCount: IStatusCount;
  total: number;
  faqs: IFaqFile[];
  raw: IFileListRawResponse;
}

export interface IDeleteFileParams extends IBaseKbParams {
  file_ids: string[];
}

export interface IClearUploadParams {
  status: string;
  kb_ids: string[];
}

export interface IGetFileBase64Params {
  file_id: string;
}

export interface IGetFileBase64Response {
  file_base64?: string;
  data?: string;
  [key: string]: unknown;
}

export interface IFileBase64Result {
  base64: string;
}

export interface IChunkRaw {
  chunk_id: string;
  chunk_type: string;
  content?: string;
  locations?: Array<{
    page_id: number;
    page_w: number;
    page_h: number;
    lines?: unknown;
    bbox?: number[];
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
}

export interface IGetDocCompletedParams {
  file_id: string;
  kb_id?: string;
}

export interface IGetDocCompletedResponse {
  chunks: IChunkRaw[];
  [key: string]: unknown;
}

export interface IChunkLocation {
  pageId: number;
  pageW: number;
  pageH: number;
  linesBox: unknown;
  bbox: number[];
}

export interface IChunk {
  chunkId: string;
  chunkType: string;
  content: string;
  locations: IChunkLocation[];
  raw: IChunkRaw;
}

export interface IDocChunksResult {
  chunks: IChunk[];
  pagesInfo: IChunkLocation[][];
  pageSizes: Array<{ page_w: number; page_h: number }>;
}

export interface IUpdateChunksParams {
  file_id: string;
  kb_id?: string;
  chunks: IChunkRaw[];
}

export interface ITagItem {
  kb_id?: string;
  file_id?: string;
  tags: string[];
}

export interface IGetTagsParams {
  kb_ids?: string[];
}

export interface IUpdateTagsParams {
  kb_tags?: ITagItem[];
  file_tags?: ITagItem[];
}

export interface IGetTagsResponse {
  [kb_or_file_id: string]: string[];
}
