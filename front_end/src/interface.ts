import type { IApiResponse } from './utils/types';

export type { IApiResponse };

export interface IAajxRes<T = any> extends IApiResponse<T> {
  msg: string;
  code: number;
  data: T;
}
