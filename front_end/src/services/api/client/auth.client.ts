import { get, post } from './base';

const URL = {
  CHECK_LOGIN: '/checkLogin.s',
  GET_LOGIN_INFO: '/j_spring_security_check',
};

export const authApi = {
  async checkLogin<T = unknown>(): Promise<T> {
    return get<T>(URL.CHECK_LOGIN);
  },

  async getLoginInfo<T = unknown>(params: Record<string, unknown>): Promise<T> {
    return post<T>(URL.GET_LOGIN_INFO, params);
  },
};
