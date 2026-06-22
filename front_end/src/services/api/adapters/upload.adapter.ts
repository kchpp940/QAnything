import {
  ensureNumber,
  ensureString,
  normalizeFileStatus,
} from './common.adapter';
import type {
  IUploadFileResult,
  IUploadFileRawResponse,
  IUploadTask,
} from '../types/upload';
import type { FileStatus } from '../types/common';

export function adaptUploadResult(raw: IUploadFileRawResponse): IUploadFileResult {
  return {
    fileId: ensureString(raw.file_id),
    fileName: ensureString(raw.file_name),
    status: normalizeFileStatus(raw.status),
    msg: ensureString(raw.msg),
    raw,
  };
}

export function adaptUploadTask(
  raw: {
    file_id?: string;
    file_name?: string;
    status?: FileStatus;
    bytes?: number;
    errorText?: string;
    [key: string]: unknown;
  },
  options?: { percent?: number; file?: File }
): IUploadTask {
  return {
    fileId: ensureString(raw.file_id),
    fileName: ensureString(raw.file_name),
    status: normalizeFileStatus(raw.status),
    percent: ensureNumber(options?.percent, 0),
    errorText: ensureString(raw.errorText),
    bytes: ensureNumber(raw.bytes, 0),
    file: options?.file,
  };
}
