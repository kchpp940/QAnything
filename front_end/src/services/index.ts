/*
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2024-01-09 15:28:56
 * @LastEditors: Ianarua 306781523@qq.com
 * @LastEditTime: 2024-08-05 16:36:28
 * @FilePath: /QAnything/front_end/src/services/index.ts
 * @Description: 统一的 API 请求封装，集成响应适配层
 */

import axios from './axiosInterceptor/index';
import { useUser } from '@/store/useUser';
import { adaptApiResponse, adaptChatResponse, adaptLegacyChatResponse } from '@/utils/responseAdapter';
import type { IApiResponse, IChatResponse } from '@/utils/types';

const { checkPhone } = useUser();

export const apiBase =
  import.meta.env.VITE_APP_MODE === 'dev' ? '' : import.meta.env.VITE_APP_API_HOST;

function validateStatus(status: number) {
  return status >= 200 && status < 300;
}

export const bondParams = {};

interface IRequestOptions {
  getResponseHeader?: boolean;
  adapter?: (data: any) => any;
  [key: string]: any;
}

export default {
  get(baseUrl: string, _query = {} as any, option: IRequestOptions = {} as any) {
    let url = /http/.test(baseUrl) ? `${baseUrl}` : `${apiBase}${baseUrl}`;
    const query = {
      ...bondParams,
      ..._query,
    };

    const { getResponseHeader, adapter, ...others } = option;
    const options = {
      method: 'get',
      url,
      mode: 'cors',
      withCredentials: false,
      validateStatus,
      ...others,
      params: query,
    };

    if (!checkPhone()) return {};

    const data = axios.request(options).then(
      res => {
        const result = getResponseHeader ? res : res.data;
        if (adapter && result) {
          return adapter(result);
        }
        return result;
      },
      error => error
    );
    return data;
  },

  post(baseUrl: string, data = {}, option: IRequestOptions = {} as any) {
    const params = {
      ...bondParams,
      ...data,
    } as any;
    const _url = `${apiBase}${baseUrl}`;
    const url = /http/.test(baseUrl) ? baseUrl : _url;
    const { getResponseHeader, adapter, ...others } = option;

    const options = {
      method: 'post',
      url,
      mode: 'cors',
      withCredentials: false,
      validateStatus,
      data: params,
      ...option,
      ...others,
    };

    if (!checkPhone()) return {};

    const resData = axios.request(options).then(
      res => {
        const result = getResponseHeader ? res : res.data;
        if (adapter && result) {
          return adapter(result);
        }
        return result;
      },
      error => Promise.reject(error)
    );
    return resData;
  },

  request<T = any>(
    method: 'get' | 'post',
    baseUrl: string,
    data?: any,
    option: IRequestOptions = {} as any
  ): Promise<T> {
    const fn = method === 'get' ? this.get : this.post;
    return fn(baseUrl, data, option) as Promise<T>;
  },

  requestChatResponse(
    method: 'get' | 'post',
    baseUrl: string,
    data?: any,
    option: IRequestOptions = {} as any
  ): Promise<IChatResponse> {
    return this.request<IChatResponse>(method, baseUrl, data, {
      ...option,
      adapter: (res: IApiResponse<any>) => {
        if (res && res.data) {
          return adaptChatResponse(res.data);
        }
        return adaptLegacyChatResponse(res);
      },
    });
  },
} as any;
