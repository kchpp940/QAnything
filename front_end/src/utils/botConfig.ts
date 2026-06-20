import type { IChatSetting } from './types';

export function chatSettingToLLMSetting(setting: IChatSetting) {
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
  llm_setting: Record<string, any>,
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

export interface BuildBotConfigOptions {
  bot_name?: string;
  description?: string;
  head_image?: string;
  prompt_setting?: string;
  welcome_message?: string;
  kb_ids?: string[];
  llm_setting?: IChatSetting | Record<string, any>;
  fromChatSetting?: boolean;
}

export function buildBotConfigPayload(opts: BuildBotConfigOptions) {
  const botConfig: Record<string, any> = {};
  if (opts.bot_name !== undefined) botConfig.bot_name = opts.bot_name;
  if (opts.description !== undefined) botConfig.description = opts.description;
  if (opts.head_image !== undefined) botConfig.head_image = opts.head_image;
  if (opts.prompt_setting !== undefined) botConfig.prompt_setting = opts.prompt_setting;
  if (opts.welcome_message !== undefined) botConfig.welcome_message = opts.welcome_message;
  if (opts.kb_ids !== undefined) botConfig.kb_ids = opts.kb_ids;
  if (opts.llm_setting !== undefined) {
    if (opts.fromChatSetting) {
      botConfig.llm_setting = chatSettingToLLMSetting(opts.llm_setting as IChatSetting);
    } else {
      botConfig.llm_setting = opts.llm_setting;
    }
  }
  return botConfig;
}
