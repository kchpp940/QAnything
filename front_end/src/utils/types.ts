/*
 * @Author: 祝占朋 wb.zhuzhanpeng01@mesg.corp.netease.com
 * @Date: 2024-01-09 15:28:56
 * @LastEditors: Ianarua 306781523@qq.com
 * @LastEditTime: 2024-08-05 16:36:28
 * @FilePath: front_end/src/utils/types.ts
 * @Description:
 *
 * ==================== ⚠️ 逐步废弃中 / PARTIALLY DEPRECATED ====================
 *
 * 本文件中与接口响应相关的类型已迁移到 `@/services/api/types/`，
 * 新代码请直接从 `@/services/api` 导入对应的规范化业务对象类型。
 *
 * 已迁移对照：
 *   IDataSourceItem  →  @/services/api/types/chat       IDataSource
 *   IChatItem        →  @/services/api/types/chat       IChatItem
 *   ITimeInfo        →  @/services/api/types/chat       ITimeInfo
 *   ITokenInfo       →  @/services/api/types/chat       ITokenInfo
 *   IChatSetting     →  @/services/api/types/chat       IChatSetting
 *   IFileListItem    →  @/services/api/types/knowledge  IKbFile
 *   IUrlListItem     →  @/services/api/types/upload     IUploadTask
 *
 * store 和组件必须消费 adapter 后的规范化业务对象，禁止直接依赖原始响应结构。
 * =============================================================================
 */

/** @deprecated 请改用 `@/services/api/types/chat` 中的 `IDataSource` */
export interface IDataSourceItem {
  dataSource?: string; //数据来源
  detailDataSource?: string; //详细来源信息
  file_name: string | null; //文件名
  content: string | null; //内容
  score: number | null; // 相关性
  file_id: string | null; // 来源文件id（知识库的文件）
  file_url: string | null; // 来源网址（联网检索）
  showDetailDataSource?: boolean; //是否展示详细来源信息
}

/** @deprecated 请改用 `@/services/api/types/chat` 中的 `IChatItem` */
export interface IChatItem {
  type: 'ai' | 'user'; //区别用户提问 和ai回复
  question?: string; //问题
  answer?: string; //问题 | 回复内容
  like?: boolean; //点赞
  unlike?: boolean; //点踩
  copied?: boolean; //点拷贝置为true 提示拷贝成功 然后置为false  重置原因:点击拷贝后添加颜色提示拷贝过了 1s后置为普通颜色
  onlySearch?: boolean; // 只检索知识库来源不回答

  showTools?: boolean; //当期问答是否结束 结束展示复制等小工具和取消闪烁
  source?: Array<IDataSourceItem>; // 数据来源

  picList?: any; // 不知道是啥，用到了，不敢删
  qaId?: any; // 同上

  itemInfo?: IChatItemInfo; // 当前对话相关信息 token time chatSetting
}

// 历史记录
export interface IHistoryList {
  historyId: number;
  title: string;
  kbIds?: string[];
}

// 对话的耗时信息
/** @deprecated 请改用 `@/services/api/types/chat` 中的 `ITimeInfo` */
export interface ITimeInfo {
  preprocess: number;
  condense_q_chain: number;
  retriever_search: number;
  web_search: number;
  rerank: number;
  reprocess: number;
  llm_first_return: number;
  first_return: number; // 前7个加起来。外层显示
  llm_completed: number;
  chat_completed: number; // 后俩加起来。外层显示
}

// 对话的耗token信息
/** @deprecated 请改用 `@/services/api/types/chat` 中的 `ITokenInfo` */
export interface ITokenInfo {
  total_tokens: number; // 外层显示
  prompt_tokens: number; // 外层显示
  completion_tokens: number; // 外层显示
  tokens_per_second: number;
}

// 对话的信息：耗token、耗时、当时的模型信息、当时聊天的日期等
export interface IChatItemInfo {
  timeInfo: ITimeInfo; // 耗时相关
  tokenInfo: ITokenInfo; // token相关
  settingInfo: IChatSetting; // 模型配置相关
  dateInfo: number; // 当时聊天的日期，时间戳
}

//url解析状态（前端展示）
export type inputStatus = 'default' | 'inputing' | 'parsing' | 'success' | 'defeat' | 'hover';

//url类型约束
/** @deprecated 请改用 `@/services/api/types/upload` 中的 `IUploadTask` */
export interface IUrlListItem {
  status: inputStatus;
  text: string;
  percent: number;
  borderRadius?: string;
}

//上传文件
/** @deprecated 请改用 `@/services/api/types/knowledge` 中的 `IKbFile` */
export interface IFileListItem {
  file?: File; // 这个只有在上传时候加，接收没有这个
  file_name: string;
  status: string;
  file_id: string;
  percent?: number;
  errorText?: string;
  text?: string;
  order?: number;
  bytes: number;
}

// 模型设置
type ICapabilities = {
  /* 是否联网搜索 */
  networkSearch: boolean;
  /* 是否混合搜索 */
  mixedSearch: boolean;
  /* 是否仅检索 */
  onlySearch: boolean;
  /* 是否增强检索 */
  rerank: boolean;
};

/** @deprecated 请改用 `@/services/api/types/chat` 中的 `IChatSetting` */
export interface IChatSetting {
  /* 模型类型，string为自定义名称，不用传 */
  modelType: 'openAI' | 'ollama' | '自定义模型配置' | string;
  /* 自定义模型id，如果不是自定义就没有，不用传 */
  customId?: number;
  /* 自定义的模型名称，只有自定义时候用 */
  modelName?: string;
  /* 秘钥，openAI用 */
  apiKey?: string;
  /* api路径 */
  apiBase: string;
  /* 模型名称 */
  apiModelName: string;
  /* 上下文token数量 */
  apiContextLength: number;
  /* 上下文的消息数量上限条数，不用传 */
  context: number;
  /* 返回的最大token */
  maxToken: number;
  /* 切片的token数 */
  chunkSize: number;
  /* 联想与发散 0~1 */
  temperature: number;
  /* top_P 0~1 */
  top_P: number;
  /* 控制数据来源数量 1~100 */
  top_K: number;
  /* 模型能力 */
  capabilities: ICapabilities;
  /* 是否开启（只有一个） */
  active: boolean;
}

// 第一个对象类型，第二个参数联合类型，把联合类型里面的参数设定为可选
// MakePartial<IChatSetting, 'modelType'>
export type MakePartial<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
