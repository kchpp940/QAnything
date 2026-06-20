import type {
  IChatSetting,
  IBotConfig,
  IBotBasicConfig,
  IBotLLMSetting,
  IBotApiResponse,
} from './types';

// ========== IChatSetting ↔ IBotLLMSetting 双向转换 ==========

export function chatSettingToLLMSetting(setting: IChatSetting): IBotLLMSetting {
  return {
    api_key: setting.apiKey ?? '',
    api_base: setting.apiBase,
    model: setting.apiModelName,
    api_context_length: setting.apiContextLength,
    max_token: setting.maxToken ?? null,
    chunk_size: setting.chunkSize,
    temperature: setting.temperature,
    top_k: setting.top_K,
    top_p: setting.top_P,
    rerank: setting.capabilities.rerank,
    hybrid_search: setting.capabilities.mixedSearch,
    networking: setting.capabilities.networkSearch,
    only_need_search_results: setting.capabilities.onlySearch,
  };
}

export function llmSettingToChatSetting(
  llm_setting: Partial<IBotLLMSetting> | Record<string, any>,
  partial?: Partial<IChatSetting>,
): IChatSetting {
  return {
    modelType: partial?.modelType ?? '自定义模型配置',
    customId: partial?.customId,
    modelName: partial?.modelName,
    apiKey: llm_setting.api_key ?? '',
    apiBase: llm_setting.api_base ?? '',
    apiModelName: llm_setting.model ?? '',
    apiContextLength: llm_setting.api_context_length ?? 4096,
    context: partial?.context ?? 20,
    maxToken: llm_setting.max_token ?? 1024,
    chunkSize: llm_setting.chunk_size ?? 128,
    temperature: llm_setting.temperature ?? 0.5,
    top_P: llm_setting.top_p ?? 0.99,
    top_K: llm_setting.top_k ?? 4,
    capabilities: {
      networkSearch: llm_setting.networking ?? false,
      mixedSearch: llm_setting.hybrid_search ?? false,
      onlySearch: llm_setting.only_need_search_results ?? false,
      rerank: llm_setting.rerank ?? true,
    },
    active: partial?.active ?? false,
  };
}

// ========== 结构化 IBotConfig 构造器 ==========

export interface BuildBotConfigOptions {
  bot_name?: string;
  description?: string;
  head_image?: string;
  prompt_setting?: string;
  welcome_message?: string;
  kb_ids?: string[];
  llm_setting?: IChatSetting | Partial<IBotLLMSetting>;
  fromChatSetting?: boolean;
}

/**
 * 构造结构化的 IBotConfig，作为前端 → 后端的唯一契约格式。
 * 组件不再直接拼散字段，统一调用此函数生成 IBotConfig 结构。
 */
export function buildBotConfig(opts: BuildBotConfigOptions): Partial<IBotConfig> {
  const config: Partial<IBotConfig> = {};

  const basic: Partial<IBotBasicConfig> = {};
  let hasBasic = false;
  if (opts.bot_name !== undefined) {
    basic.bot_name = opts.bot_name;
    hasBasic = true;
  }
  if (opts.description !== undefined) {
    basic.description = opts.description;
    hasBasic = true;
  }
  if (opts.head_image !== undefined) {
    basic.head_image = opts.head_image;
    hasBasic = true;
  }
  if (opts.prompt_setting !== undefined) {
    basic.prompt_setting = opts.prompt_setting;
    hasBasic = true;
  }
  if (opts.welcome_message !== undefined) {
    basic.welcome_message = opts.welcome_message;
    hasBasic = true;
  }
  if (hasBasic) {
    config.basic = basic as IBotBasicConfig;
  }

  if (opts.llm_setting !== undefined) {
    if (opts.fromChatSetting) {
      config.llm_setting = chatSettingToLLMSetting(opts.llm_setting as IChatSetting);
    } else {
      config.llm_setting = opts.llm_setting as Partial<IBotLLMSetting>;
    }
  }

  if (opts.kb_ids !== undefined) {
    config.kb_ids = opts.kb_ids;
  }

  return config;
}

/**
 * 兼容旧版组件的调用方式（内部调用 buildBotConfig）。
 * 新代码应直接使用 buildBotConfig。
 */
export function buildBotConfigPayload(opts: BuildBotConfigOptions) {
  return buildBotConfig(opts);
}

// ========== 后端响应规范化 ==========

const DEFAULT_LLM_SETTING: IBotLLMSetting = {
  api_key: '',
  api_base: '',
  model: '',
  api_context_length: 4096,
  max_token: null,
  chunk_size: 128,
  temperature: 0.5,
  top_k: 4,
  top_p: 0.99,
  rerank: true,
  hybrid_search: false,
  networking: false,
  only_need_search_results: false,
};

const DEFAULT_BASIC_CONFIG: IBotBasicConfig = {
  bot_name: '',
  description: '',
  head_image: '',
  prompt_setting: '',
  welcome_message: '',
};

/**
 * 规范化后端 get_bot_info 返回的数据，确保：
 * 1. 所有字段都有默认值，不会出现 undefined
 * 2. llm_setting 是完整的 IBotLLMSetting
 * 3. bot_config 是完整的 IBotConfig
 *
 * 这是前端 curBot 唯一的入口，确保 store 中只存 normalized config。
 */
export function normalizeBotApiResponse(raw: Record<string, any>): IBotApiResponse {
  const llm_setting: IBotLLMSetting = {
    ...DEFAULT_LLM_SETTING,
    ...(raw.llm_setting || {}),
  };

  const basic: IBotBasicConfig = {
    ...DEFAULT_BASIC_CONFIG,
    bot_name: raw.bot_name,
    description: raw.description,
    head_image: raw.head_image,
    prompt_setting: raw.prompt_setting,
    welcome_message: raw.welcome_message,
  };

  const kb_ids = Array.isArray(raw.kb_ids) ? raw.kb_ids : [];
  const kb_names = Array.isArray(raw.kb_names) ? raw.kb_names : [];

  const bot_config: IBotConfig = {
    basic,
    llm_setting,
    kb_ids,
  };

  return {
    bot_id: raw.bot_id,
    user_id: raw.user_id,
    bot_name: basic.bot_name,
    description: basic.description,
    head_image: basic.head_image,
    prompt_setting: basic.prompt_setting,
    welcome_message: basic.welcome_message,
    kb_ids,
    kb_names,
    update_time: raw.update_time || '',
    llm_setting,
    bot_config,
  };
}

/**
 * 从 curBot 中提取 ChatSettingForm 所需的 IChatSetting。
 * 组件不再直接操作 curBot.llm_setting 进行字段转换。
 */
export function chatSettingFromBot(
  bot: IBotApiResponse,
  existingConfigured?: Partial<IChatSetting>,
): IChatSetting {
  return llmSettingToChatSetting(bot.llm_setting, existingConfigured);
}
