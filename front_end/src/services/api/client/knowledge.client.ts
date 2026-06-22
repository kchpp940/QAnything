import { post } from './base';
import {
  adaptDocChunks,
  adaptFaqList,
  adaptFileBase64,
  adaptFileList,
  adaptKnowledgeBaseList,
  adaptTagsResponse,
} from '../adapters';
import type {
  IClearUploadParams,
  ICreateKbParams,
  IDeleteFileParams,
  IDeleteKbParams,
  IDocChunksResult,
  IFileBase64Result,
  IFileListParams,
  IFileListResult,
  IFaqListResult,
  IGetDocCompletedParams,
  IGetFileBase64Params,
  IGetTagsParams,
  IKnowledgeBase,
  IRenameKbParams,
  IUpdateChunksParams,
  IUpdateTagsParams,
} from '../types/knowledge';

const URL = {
  LIST_KB: '/local_doc_qa/list_knowledge_base',
  CREATE_KB: '/local_doc_qa/new_knowledge_base',
  DELETE_KB: '/local_doc_qa/delete_knowledge_base',
  RENAME_KB: '/local_doc_qa/rename_knowledge_base',
  LIST_FILES: '/local_doc_qa/list_files',
  DELETE_FILES: '/local_doc_qa/delete_files',
  CLEAR_UPLOAD: '/local_doc_qa/clean_files_by_status',
  GET_FILE_BASE64: '/local_doc_qa/get_file_base64',
  GET_DOC_COMPLETED: '/local_doc_qa/get_doc_completed',
  UPDATE_CHUNKS: '/local_doc_qa/update_chunks',
  GET_TOTAL_STATUS: '/local_doc_qa/get_total_status',
  GET_TAGS: '/local_doc_qa/get_tags',
  UPDATE_TAGS: '/local_doc_qa/update_tags',
};

type RawAdapterInput = Record<string, unknown>;

export const knowledgeApi = {
  async getKbList(): Promise<IKnowledgeBase[]> {
    const data = await post<unknown[]>(URL.LIST_KB, undefined, { showLoading: true });
    return adaptKnowledgeBaseList(data as Parameters<typeof adaptKnowledgeBaseList>[0]);
  },

  async createKb(params: ICreateKbParams): Promise<unknown> {
    return post(URL.CREATE_KB, params, { showLoading: true });
  },

  async deleteKb(params: IDeleteKbParams): Promise<unknown> {
    return post(URL.DELETE_KB, params);
  },

  async renameKb(params: IRenameKbParams): Promise<unknown> {
    return post(URL.RENAME_KB, params, { showLoading: true });
  },

  async getFileList(params: IFileListParams): Promise<IFileListResult> {
    const data = await post(URL.LIST_FILES, params);
    return adaptFileList(data as RawAdapterInput);
  },

  async getFaqList(params: IFileListParams): Promise<IFaqListResult> {
    const data = await post(URL.LIST_FILES, params);
    return adaptFaqList(data as RawAdapterInput);
  },

  async deleteFiles(params: IDeleteFileParams): Promise<unknown> {
    return post(URL.DELETE_FILES, params, { showLoading: true });
  },

  async clearUpload(params: IClearUploadParams): Promise<unknown> {
    return post(URL.CLEAR_UPLOAD, params);
  },

  async getFileBase64(params: IGetFileBase64Params): Promise<IFileBase64Result> {
    const data = await post(URL.GET_FILE_BASE64, params);
    return adaptFileBase64(data as RawAdapterInput);
  },

  async getDocCompleted(params: IGetDocCompletedParams): Promise<IDocChunksResult> {
    const data = await post(URL.GET_DOC_COMPLETED, params);
    return adaptDocChunks(data as RawAdapterInput);
  },

  async updateChunks(params: IUpdateChunksParams): Promise<unknown> {
    return post(URL.UPDATE_CHUNKS, params);
  },

  async getTotalStatus(): Promise<unknown> {
    return post(URL.GET_TOTAL_STATUS);
  },

  async getTags(params: IGetTagsParams): Promise<Record<string, string[]>> {
    const data = await post(URL.GET_TAGS, params);
    return adaptTagsResponse(data as Record<string, unknown>);
  },

  async updateTags(params: IUpdateTagsParams): Promise<unknown> {
    return post(URL.UPDATE_TAGS, params);
  },
};
