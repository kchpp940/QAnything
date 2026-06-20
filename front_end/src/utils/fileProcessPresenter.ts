import {
  FileProcessState,
  ProcessStage,
  ErrorCategory,
  StageEvent,
  ErrorInfo,
  ProcessStateDisplay,
  STAGE_ORDER,
  STAGE_LABEL_MAP,
  STATE_LABEL_MAP,
  ERROR_CATEGORY_LABEL_MAP,
  getStageLabel,
  getErrorCategoryLabel,
  getStatusFromProcessState,
} from '@/utils/fileProcessState';

export type StatusIconType = 'loading' | 'success' | 'error' | 'pending';

export interface FileProcessPresentation {
  iconType: StatusIconType;
  statusText: string;
  legacyStatus: string;
  progress: number;
  progressPercent: number;
  showProgress: boolean;
  recentEvents: StageEvent[];
  showEvents: boolean;
  hasError: boolean;
  errorCategoryText: string;
  errorMessage: string;
  errorStageText: string;
  isRetryable: boolean;
  retryCount: number;
  retryStageText: string | null;
  canView: boolean;
  canRetry: boolean;
  isProcessing: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  isPending: boolean;
  completedStages: ProcessStage[];
  allStages: ProcessStage[];
}

const DEFAULT_PRESENTATION: FileProcessPresentation = {
  iconType: 'pending',
  statusText: '等待处理',
  legacyStatus: 'gray',
  progress: 0,
  progressPercent: 0,
  showProgress: false,
  recentEvents: [],
  showEvents: false,
  hasError: false,
  errorCategoryText: '',
  errorMessage: '',
  errorStageText: '',
  isRetryable: false,
  retryCount: 0,
  retryStageText: null,
  canView: false,
  canRetry: false,
  isProcessing: false,
  isCompleted: false,
  isFailed: false,
  isPending: true,
  completedStages: [],
  allStages: [...STAGE_ORDER],
};

export function createFileProcessPresentation(
  processState: ProcessStateDisplay | null | undefined,
  fallbackLegacyStatus?: string | null,
): FileProcessPresentation {
  if (!processState && !fallbackLegacyStatus) {
    return { ...DEFAULT_PRESENTATION };
  }

  if (!processState) {
    return presentationFromLegacy(fallbackLegacyStatus!);
  }

  const iconType = resolveIconType(processState);
  const statusText = resolveStatusText(processState);
  const progress = processState.progress || 0;
  const progressPercent = processState.progress_percent || 0;
  const showProgress = processState.is_processing || processState.is_pending;
  const recentEvents = (processState.stage_events || []).slice(-3);
  const showEvents = recentEvents.length > 0 && !processState.is_completed;
  const hasError = !!processState.latest_error && processState.is_failed;

  let errorCategoryText = '';
  let errorMessage = '';
  let errorStageText = '';
  if (processState.latest_error) {
    errorCategoryText = getErrorCategoryLabel(processState.latest_error.error_category as any);
    errorMessage = processState.latest_error.error_message || '';
    errorStageText = getStageLabel(processState.latest_error.stage as any);
  }

  const isRetryable = !!(
    processState.can_retry ||
    (processState.latest_error && (processState.latest_error as any).is_retryable)
  );

  return {
    iconType,
    statusText,
    legacyStatus: processState.legacy_status || 'gray',
    progress,
    progressPercent,
    showProgress,
    recentEvents,
    showEvents,
    hasError,
    errorCategoryText,
    errorMessage,
    errorStageText,
    isRetryable,
    retryCount: processState.retry_count || 0,
    retryStageText: processState.retry_stage ? getStageLabel(processState.retry_stage as any) : null,
    canView: !!processState.is_completed,
    canRetry: processState.is_failed && isRetryable,
    isProcessing: !!processState.is_processing,
    isCompleted: !!processState.is_completed,
    isFailed: !!processState.is_failed,
    isPending: !!processState.is_pending,
    completedStages: (processState.completed_stages || []) as ProcessStage[],
    allStages: [...STAGE_ORDER],
  };
}

function resolveIconType(ps: ProcessStateDisplay): StatusIconType {
  if (ps.is_completed) return 'success';
  if (ps.is_failed) return 'error';
  if (ps.is_processing) return 'loading';
  return 'pending';
}

function resolveStatusText(ps: ProcessStateDisplay): string {
  if (ps.state === FileProcessState.RETRYING) {
    return `重试中(${ps.retry_count})`;
  }
  if (ps.is_processing) {
    const stageLabel = getStageLabel(ps.current_stage as any);
    return `${stageLabel}中`;
  }
  if (ps.state === FileProcessState.PENDING) {
    return '等待处理';
  }
  return STATE_LABEL_MAP[ps.state as FileProcessState] || '未知状态';
}

function presentationFromLegacy(legacyStatus: string): FileProcessPresentation {
  const base = { ...DEFAULT_PRESENTATION, legacyStatus };

  switch (legacyStatus) {
    case 'green':
      return {
        ...base,
        iconType: 'success',
        statusText: '处理完成',
        canView: true,
        isCompleted: true,
        isPending: false,
      };
    case 'yellow':
      return {
        ...base,
        iconType: 'loading',
        statusText: '处理中',
        showProgress: true,
        isProcessing: true,
        isPending: false,
      };
    case 'red':
      return {
        ...base,
        iconType: 'error',
        statusText: '处理失败',
        hasError: true,
        isFailed: true,
        isPending: false,
      };
    case 'gray':
    default:
      return {
        ...base,
        iconType: 'pending',
        statusText: '排队中',
      };
  }
}

export interface RetryPresentation {
  visible: boolean;
  disabled: boolean;
  btnText: string;
  tooltip: string;
}

export function getRetryPresentation(
  presentation: FileProcessPresentation,
): RetryPresentation {
  if (!presentation.canRetry) {
    return {
      visible: presentation.isFailed,
      disabled: true,
      btnText: '不支持重试',
      tooltip: presentation.isRetryable ? '' : '该错误类型不支持重试，请删除后重新上传',
    };
  }
  return {
    visible: true,
    disabled: false,
    btnText: '重试',
    tooltip: presentation.retryStageText
      ? `将从「${presentation.retryStageText}」阶段开始重试`
      : '重试此文件处理',
  };
}

export interface StageProgressPresentation {
  stage: ProcessStage;
  label: string;
  status: 'completed' | 'current' | 'pending';
  index: number;
}

export function getStageProgressPresentation(
  presentation: FileProcessPresentation,
): StageProgressPresentation[] {
  return presentation.allStages.map((stage, idx) => {
    const completedIdx = presentation.completedStages.indexOf(stage);
    let status: 'completed' | 'current' | 'pending' = 'pending';
    if (completedIdx >= 0) {
      status = 'completed';
    } else if (presentation.isProcessing && presentation.completedStages.length === idx) {
      status = 'current';
    }
    return {
      stage,
      label: STAGE_LABEL_MAP[stage] || stage,
      status,
      index: idx,
    };
  });
}

export function isFileProcessing(
  presentation: FileProcessPresentation,
  fallbackLegacyStatus?: string | null,
): boolean {
  if (presentation.isProcessing || presentation.isPending) return true;
  if (fallbackLegacyStatus === 'gray' || fallbackLegacyStatus === 'yellow') return true;
  return false;
}

export function mergeLegacyAndPresentation(
  processState: ProcessStateDisplay | null | undefined,
  legacyStatus: string | null | undefined,
): { isProcessing: boolean; legacyStatus: string } {
  const presentation = createFileProcessPresentation(processState, legacyStatus || undefined);
  const isProcessing = isFileProcessing(presentation, legacyStatus || undefined);
  const finalLegacyStatus = processState
    ? getStatusFromProcessState(processState)
    : (legacyStatus || 'gray');
  return { isProcessing, legacyStatus: finalLegacyStatus };
}
