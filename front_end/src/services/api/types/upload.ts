import type { FileStatus, IBaseKbParams } from './common';

export interface IUploadFileRawResponse {
  file_id?: string;
  file_name?: string;
  status?: FileStatus;
  msg?: string;
  [key: string]: unknown;
}

export interface IUploadFileResult {
  fileId: string;
  fileName: string;
  status: FileStatus;
  msg: string;
  raw: IUploadFileRawResponse;
}

export interface IUploadFileParams extends IBaseKbParams {
  files?: File[];
  [key: string]: unknown;
}

export interface IUploadUrlParams extends IBaseKbParams {
  url: string;
  [key: string]: unknown;
}

export interface IUploadFaqsParams extends IBaseKbParams {
  files?: File[];
  [key: string]: unknown;
}

export interface IUploadTask {
  fileId: string;
  fileName: string;
  status: FileStatus;
  percent: number;
  errorText: string;
  bytes: number;
  file?: File;
}

export type UploadTaskStatus = 'default' | 'inputing' | 'parsing' | 'success' | 'defeat' | 'hover';

export interface IUrlUploadTask {
  status: UploadTaskStatus;
  text: string;
  percent: number;
  borderRadius?: string;
}
