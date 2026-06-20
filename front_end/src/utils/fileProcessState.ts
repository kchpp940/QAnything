export enum FileProcessState {
  PENDING = 'pending',
  PARSING = 'parsing',
  SPLITTING = 'splitting',
  EMBEDDING = 'embedding',
  INDEXING = 'indexing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  RETRYING = 'retrying',
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
  can_retry: boolean;
  retry_count: number;
  latest_error: ErrorInfo | null;
  legacy_status: string;
}

export const STAGE_LABEL_MAP: Record<ProcessStage, string> = {
  [ProcessStage.UPLOAD]: '上传中',
  [ProcessStage.PARSE]: '解析中',
  [ProcessStage.SPLIT]: '切分中',
  [ProcessStage.EMBED]: '向量化中',
  [ProcessStage.INDEX]: '索引构建中',
  [ProcessStage.COMPLETE]: '处理完成',
};

export const STATE_LABEL_MAP: Record<FileProcessState, string> = {
  [FileProcessState.PENDING]: '等待处理',
  [FileProcessState.PARSING]: '解析中',
  [FileProcessState.SPLITTING]: '切分中',
  [FileProcessState.EMBEDDING]: '向量化中',
  [FileProcessState.INDEXING]: '索引构建中',
  [FileProcessState.COMPLETED]: '处理完成',
  [FileProcessState.FAILED]: '处理失败',
  [FileProcessState.RETRYING]: '重试中',
};

export function isProcessingState(state: FileProcessState): boolean {
  return [
    FileProcessState.PARSING,
    FileProcessState.SPLITTING,
    FileProcessState.EMBEDDING,
    FileProcessState.INDEXING,
    FileProcessState.RETRYING,
  ].includes(state);
}

export function getStateLabel(state: FileProcessState): string {
  return STATE_LABEL_MAP[state] || '未知状态';
}

export function getStageLabel(stage: ProcessStage): string {
  return STAGE_LABEL_MAP[stage] || '未知阶段';
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
