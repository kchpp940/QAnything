/**
 * ==================== ⚠️ 已废弃 / DEPRECATED ====================
 *
 * 此文件为旧接口类型定义，禁止在新代码中使用。
 *
 * 响应基类型请改用：`@/services/api/types/common` 中的 `IApiBaseResponse<T>`
 * 响应码枚举请改用：`@/services/api/types/common` 中的 `EResponseCode`
 * 所有业务域的请求/响应类型统一收口在 `@/services/api/types/`：
 *   - knowledge.ts / chat.ts / bot.ts / statistics.ts / upload.ts
 * ================================================================
 */
/** @deprecated 请改用 `@/services/api/types/common` 中的 `IApiBaseResponse<T>` */
export interface IAajxRes {
  msg: string;
  code: number;
  data: any;
}
