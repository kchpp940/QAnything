export enum FileProcessState {
  PENDING = 'pending',
  CLAIMED = 'claimed',
  PARSING = 'parsing',
  SPLITTING = 'splitting',
  EMBEDDING = 'embedding',
  INDEXING = 'indexing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  RETRYING = 'retrying',
  RETRYING_CLAIMED = 'retrying_claimed',
}

export enum ProcessStage {
  UPLOAD = 'upload',
  PARSE = 'parse',
  SPLIT = 'split',
  EMBED = 'embed',
  INDEX = 'index',
  COMPLETE = 'complete',
}

export enum ErrorCategory {
  PARSE_ERROR = 'parse_error',
  SPLIT_ERROR = 'split_error',
  EMBEDDING_ERROR = 'embedding_error',
  MILVUS_ERROR = 'milvus_error',
  ES_ERROR = 'es_error',
  MYSQL_ERROR = 'mysql_error',
  TIMEOUT_ERROR = 'timeout_error',
  CONTENT_TOO_LARGE = 'content_too_large',
  CONTENT_EMPTY = 'content_empty',
  UNKNOWN_ERROR = 'unknown_error',
}

export interface StageEvent {
  stage: ProcessStage;
  timestamp: number;
  progress: number;
  message: string;
  rollback_result?: RollbackResult | null;
}

export interface RollbackResult {
  file_id: string;
  success_actions: string[];
  errors: Record<string, string>;
  has_errors: boolean;
}

export interface ErrorInfo {
  error_category: ErrorCategory;
  error_message: string;
  stage: ProcessStage;
  timestamp: number;
  retry_count: number;
  stack_trace?: string;
  is_retryable: boolean;
}

export interface ProcessStateDisplay {
  state: FileProcessState;
  current_stage: ProcessStage;
  progress: number;
  progress_percent: number;
  is_completed: boolean;
  is_failed: boolean;
  is_processing: boolean;
  is_pending: boolean;
  is_retrying: boolean;
  is_claimed: boolean;
  claim_expired: boolean;
  worker_id: string | null;
  claim_time: number | null;
  can_retry: boolean;
  retry_count: number;
  retry_stage: ProcessStage | null;
  stage_events: StageEvent[];
  error_history: ErrorInfo[];
  latest_error: ErrorInfo | null;
  completed_stages: ProcessStage[];
  metadata: Record<string, any>;
  legacy_status: string;
}

export const STAGE_ORDER: ProcessStage[] = [
  ProcessStage.UPLOAD,
  ProcessStage.PARSE,
  ProcessStage.SPLIT,
  ProcessStage.EMBED,
  ProcessStage.INDEX,
  ProcessStage.COMPLETE,
];

export const STAGE_LABEL_MAP: Record<ProcessStage, string> = {
  [ProcessStage.UPLOAD]: '上传',
  [ProcessStage.PARSE]: '解析',
  [ProcessStage.SPLIT]: '切分',
  [ProcessStage.EMBED]: '向量化',
  [ProcessStage.INDEX]: '索引构建',
  [ProcessStage.COMPLETE]: '完成',
};

export const STATE_LABEL_MAP: Record<FileProcessState, string> = {
  [FileProcessState.PENDING]: '等待处理',
  [FileProcessState.CLAIMED]: '已领取',
  [FileProcessState.PARSING]: '解析中',
  [FileProcessState.SPLITTING]: '切分中',
  [FileProcessState.EMBEDDING]: '向量化中',
  [FileProcessState.INDEXING]: '索引构建中',
  [FileProcessState.COMPLETED]: '处理完成',
  [FileProcessState.FAILED]: '处理失败',
  [FileProcessState.RETRYING]: '重试中',
  [FileProcessState.RETRYING_CLAIMED]: '重试处理中',
};

export const ERROR_CATEGORY_LABEL_MAP: Record<ErrorCategory, string> = {
  [ErrorCategory.PARSE_ERROR]: '解析错误',
  [ErrorCategory.SPLIT_ERROR]: '切分错误',
  [ErrorCategory.EMBEDDING_ERROR]: '向量化错误',
  [ErrorCategory.MILVUS_ERROR]: '向量数据库错误',
  [ErrorCategory.ES_ERROR]: '搜索引擎错误',
  [ErrorCategory.MYSQL_ERROR]: '数据库错误',
  [ErrorCategory.TIMEOUT_ERROR]: '处理超时',
  [ErrorCategory.CONTENT_TOO_LARGE]: '内容过大',
  [ErrorCategory.CONTENT_EMPTY]: '内容为空',
  [ErrorCategory.UNKNOWN_ERROR]: '未知错误',
};

export function isProcessingState(state: FileProcessState): boolean {
  return [
    FileProcessState.CLAIMED,
    FileProcessState.PARSING,
    FileProcessState.SPLITTING,
    FileProcessState.EMBEDDING,
    FileProcessState.INDEXING,
    FileProcessState.RETRYING,
    FileProcessState.RETRYING_CLAIMED,
  ].includes(state);
}

export function getStateLabel(state: FileProcessState): string {
  return STATE_LABEL_MAP[state] || '未知状态';
}

export function getStageLabel(stage: ProcessStage): string {
  return STAGE_LABEL_MAP[stage] || '未知阶段';
}

export function getErrorCategoryLabel(category: ErrorCategory): string {
  return ERROR_CATEGORY_LABEL_MAP[category] || '未知错误';
}

export function getStatusFromProcessState(processState: ProcessStateDisplay | null | undefined): string {
  if (!processState) {
    return 'gray';
  }
  if (processState.is_completed) {
    return 'green';
  }
  if (processState.is_failed) {
    return 'red';
  }
  if (processState.is_processing) {
    return 'yellow';
  }
  return 'gray';
}

export function getDisplayStatusText(processState: ProcessStateDisplay | null | undefined): string {
  if (!processState) {
    return '';
  }
  if (processState.is_retrying || processState.state === FileProcessState.RETRYING_CLAIMED) {
    return `重试中(${processState.retry_count})`;
  }
  if (processState.is_claimed || processState.state === FileProcessState.CLAIMED) {
    const stageLabel = getStageLabel(processState.current_stage as any);
    return `${stageLabel}中(${processState.worker_id || 'worker'})`;
  }
  if (processState.is_processing) {
    return getStageLabel(processState.current_stage as any) + '中';
  }
  return getStateLabel(processState.state);
}

export function getStageIndex(stage: ProcessStage): number {
  return STAGE_ORDER.indexOf(stage);
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
