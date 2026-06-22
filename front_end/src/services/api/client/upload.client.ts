import { post } from './base';
import { adaptUploadResult } from '../adapters';
import type {
  IUploadFaqsParams,
  IUploadFileParams,
  IUploadFileResult,
  IUploadUrlParams,
} from '../types/upload';

const URL = {
  UPLOAD_FILE: '/local_doc_qa/upload_files',
  UPLOAD_URL: '/local_doc_qa/upload_weblink',
  UPLOAD_FAQS: '/local_doc_qa/upload_faqs',
};

export const uploadApi = {
  async uploadFile(
    params: IUploadFileParams,
    options?: { onUploadProgress?: (progressEvent: unknown) => void; timeout?: number }
  ): Promise<IUploadFileResult> {
    const data = await post(URL.UPLOAD_FILE, params, {
      timeout: options?.timeout,
      ...options,
    } as Record<string, unknown>);
    return adaptUploadResult(data as Record<string, unknown>);
  },

  async uploadUrl(params: IUploadUrlParams): Promise<IUploadFileResult> {
    const data = await post(URL.UPLOAD_URL, params);
    return adaptUploadResult(data as Record<string, unknown>);
  },

  async uploadFaqs(
    params: IUploadFaqsParams,
    options?: { timeout?: number }
  ): Promise<IUploadFileResult> {
    const data = await post(URL.UPLOAD_FAQS, params, {
      timeout: options?.timeout,
    } as Record<string, unknown>);
    return adaptUploadResult(data as Record<string, unknown>);
  },
};
