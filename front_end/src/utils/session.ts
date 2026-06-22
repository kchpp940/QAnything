import { useUser } from '@/store/useUser';

export const DEFAULT_USER_ID = 'user';

export const userId = DEFAULT_USER_ID;

let _userPhoneCache: string = '';

export function getUserPhone(): string {
  if (_userPhoneCache) return _userPhoneCache;
  try {
    const { userInfo } = useUser();
    _userPhoneCache = userInfo?.phoneNumber || '';
  } catch {
    _userPhoneCache = '';
  }
  return _userPhoneCache;
}

export const userPhone = getUserPhone();

export function getUserContext() {
  return {
    user_id: DEFAULT_USER_ID,
    user_info: getUserPhone(),
  };
}

export function injectUserContext<T extends Record<string, unknown>>(
  params: T
): T & { user_id: string; user_info: string } {
  return {
    user_id: DEFAULT_USER_ID,
    user_info: getUserPhone(),
    ...params,
  };
}
