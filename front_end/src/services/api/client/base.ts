import services from '../..';
import { useUser } from '@/store/useUser';
import { EHttpMethod, EResponseCode } from '../types/common';
import type { IApiBaseResponse, IRequestOptions } from '../types/common';
import { injectUserContext } from '@/utils/session';

export { getUserContext } from '@/utils/session';
export { injectUserContext } from '@/utils/session';

export function isSuccessResponse(res: IApiBaseResponse): boolean {
  const code = Number(res.code ?? res.errorCode);
  return (
    code === EResponseCode.SUCCESS || code === EResponseCode.SUCCESS_V2 || res.errorCode === '0'
  );
}

export function extractResponseData<T>(res: IApiBaseResponse<T>): T | undefined {
  return res.data ?? res.result;
}

export interface IApiClientOptions extends IRequestOptions {
  method: EHttpMethod;
  url: string;
}

export async function requestRaw<T = unknown>(
  method: EHttpMethod,
  url: string,
  params?: object,
  options?: IRequestOptions
): Promise<IApiBaseResponse<T>> {
  const { ...restOptions } = options ?? {};
  const data = injectUserContext((params ?? {}) as Record<string, unknown>);

  if (method === EHttpMethod.GET) {
    return services.get(url, data, restOptions) as Promise<IApiBaseResponse<T>>;
  }
  return services.post(url, data, restOptions) as Promise<IApiBaseResponse<T>>;
}

export async function requestBlob(
  method: EHttpMethod,
  url: string,
  params?: object,
  options?: IRequestOptions
): Promise<unknown> {
  const data = injectUserContext((params ?? {}) as Record<string, unknown>);
  if (method === EHttpMethod.GET) {
    return services.get(url, data, { ...options, responseType: 'blob', getResponseHeader: true });
  }
  return services.post(url, data, { ...options, responseType: 'blob', getResponseHeader: true });
}

export async function requestData<T = unknown>(
  method: EHttpMethod,
  url: string,
  params?: object,
  options?: IRequestOptions
): Promise<T> {
  const res = (await requestRaw<T>(method, url, params, options)) as IApiBaseResponse<T> & {
    request?: { responseType?: string };
  };

  if (res?.request?.responseType === 'blob') {
    return res as unknown as T;
  }

  if (isSuccessResponse(res)) {
    return (extractResponseData(res) ?? (res as unknown)) as T;
  }

  if (res.errorCode === '111') {
    const { setUserInfo } = useUser();
    setUserInfo({ token: '' });
  }

  return Promise.reject(res);
}

export async function get<T = unknown>(
  url: string,
  params?: object,
  options?: IRequestOptions
): Promise<T> {
  return requestData<T>(EHttpMethod.GET, url, params, options);
}

export async function post<T = unknown>(
  url: string,
  params?: object,
  options?: IRequestOptions
): Promise<T> {
  return requestData<T>(EHttpMethod.POST, url, params, options);
}

export async function postWithBlob(
  url: string,
  params?: object,
  options?: IRequestOptions
): Promise<unknown> {
  return requestBlob(EHttpMethod.POST, url, params, options);
}
