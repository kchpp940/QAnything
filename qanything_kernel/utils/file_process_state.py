from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import json
import time


class FileProcessState(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    SPLITTING = "splitting"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ProcessStage(str, Enum):
    UPLOAD = "upload"
    PARSE = "parse"
    SPLIT = "split"
    EMBED = "embed"
    INDEX = "index"
    COMPLETE = "complete"


STAGE_ORDER = [
    ProcessStage.UPLOAD,
    ProcessStage.PARSE,
    ProcessStage.SPLIT,
    ProcessStage.EMBED,
    ProcessStage.INDEX,
    ProcessStage.COMPLETE,
]

STAGE_TO_STATE_MAP = {
    ProcessStage.UPLOAD: FileProcessState.PENDING,
    ProcessStage.PARSE: FileProcessState.PARSING,
    ProcessStage.SPLIT: FileProcessState.SPLITTING,
    ProcessStage.EMBED: FileProcessState.EMBEDDING,
    ProcessStage.INDEX: FileProcessState.INDEXING,
    ProcessStage.COMPLETE: FileProcessState.COMPLETED,
}


class ErrorCategory(str, Enum):
    PARSE_ERROR = "parse_error"
    SPLIT_ERROR = "split_error"
    EMBEDDING_ERROR = "embedding_error"
    MILVUS_ERROR = "milvus_error"
    ES_ERROR = "es_error"
    MYSQL_ERROR = "mysql_error"
    TIMEOUT_ERROR = "timeout_error"
    CONTENT_TOO_LARGE = "content_too_large"
    CONTENT_EMPTY = "content_empty"
    UNKNOWN_ERROR = "unknown_error"


RETRYABLE_ERRORS = {
    ErrorCategory.MILVUS_ERROR,
    ErrorCategory.ES_ERROR,
    ErrorCategory.MYSQL_ERROR,
    ErrorCategory.TIMEOUT_ERROR,
    ErrorCategory.EMBEDDING_ERROR,
    ErrorCategory.UNKNOWN_ERROR,
}


STAGE_PROGRESS_MAP = {
    ProcessStage.UPLOAD: 0.0,
    ProcessStage.PARSE: 0.2,
    ProcessStage.SPLIT: 0.4,
    ProcessStage.EMBED: 0.6,
    ProcessStage.INDEX: 0.8,
    ProcessStage.COMPLETE: 1.0,
}


LEGACY_STATUS_MAP = {
    "gray": FileProcessState.PENDING,
    "yellow": FileProcessState.PARSING,
    "green": FileProcessState.COMPLETED,
    "red": FileProcessState.FAILED,
}


STATE_TO_LEGACY_MAP = {v: k for k, v in LEGACY_STATUS_MAP.items()}


@dataclass
class StageEvent:
    stage: ProcessStage
    timestamp: float = field(default_factory=time.time)
    progress: float = 0.0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "timestamp": self.timestamp,
            "progress": self.progress,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageEvent":
        return cls(
            stage=ProcessStage(data["stage"]),
            timestamp=data.get("timestamp", time.time()),
            progress=data.get("progress", 0.0),
            message=data.get("message", ""),
        )


@dataclass
class ErrorInfo:
    error_category: ErrorCategory
    error_message: str
    stage: ProcessStage
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    stack_trace: Optional[str] = None

    @property
    def is_retryable(self) -> bool:
        return self.error_category in RETRYABLE_ERRORS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_category": self.error_category.value,
            "error_message": self.error_message,
            "stage": self.stage.value,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "stack_trace": self.stack_trace,
            "is_retryable": self.is_retryable,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorInfo":
        return cls(
            error_category=ErrorCategory(data["error_category"]),
            error_message=data["error_message"],
            stage=ProcessStage(data["stage"]),
            timestamp=data.get("timestamp", time.time()),
            retry_count=data.get("retry_count", 0),
            stack_trace=data.get("stack_trace"),
        )


@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_factor: float = 2.0
    retryable_errors: set = field(default_factory=lambda: RETRYABLE_ERRORS.copy())

    def get_delay(self, retry_count: int) -> float:
        delay = self.base_delay_seconds * (self.backoff_factor ** retry_count)
        return min(delay, self.max_delay_seconds)

    def can_retry(self, error_info: ErrorInfo) -> bool:
        return (
            error_info.is_retryable
            and error_info.retry_count < self.max_retries
            and error_info.error_category in self.retryable_errors
        )


@dataclass
class FileProcessContext:
    file_id: str
    state: FileProcessState = FileProcessState.PENDING
    current_stage: ProcessStage = ProcessStage.UPLOAD
    stage_events: List[StageEvent] = field(default_factory=list)
    error_history: List[ErrorInfo] = field(default_factory=list)
    progress: float = 0.0
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def transition_to(self, new_state: FileProcessState, stage: Optional[ProcessStage] = None,
                      message: str = "") -> None:
        self.state = new_state
        if stage:
            self.current_stage = stage
            self.progress = STAGE_PROGRESS_MAP.get(stage, self.progress)
            event = StageEvent(stage=stage, progress=self.progress, message=message)
            self.stage_events.append(event)

    def record_error(self, error_info: ErrorInfo) -> None:
        self.error_history.append(error_info)
        self.state = FileProcessState.FAILED

    def can_retry(self, policy: Optional[RetryPolicy] = None) -> bool:
        policy = policy or RetryPolicy()
        if not self.error_history:
            return False
        latest_error = self.error_history[-1]
        return policy.can_retry(latest_error)

    def mark_for_retry(self) -> None:
        if self.error_history:
            self.error_history[-1].retry_count += 1
            self.retry_count += 1
            self.state = FileProcessState.RETRYING

    def get_retry_stage(self) -> ProcessStage:
        if not self.error_history:
            return ProcessStage.UPLOAD
        latest_error = self.error_history[-1]
        error_stage = latest_error.stage
        stage_index = STAGE_ORDER.index(error_stage)
        if stage_index > 0:
            return STAGE_ORDER[stage_index - 1]
        return ProcessStage.UPLOAD

    def rollback_to(self, stage: ProcessStage, message: str = "") -> None:
        if stage not in STAGE_ORDER:
            raise ValueError(f"Invalid stage: {stage}")
        self.current_stage = stage
        self.state = STAGE_TO_STATE_MAP.get(stage, FileProcessState.PENDING)
        self.progress = STAGE_PROGRESS_MAP.get(stage, 0.0)
        event = StageEvent(stage=stage, progress=self.progress, message=message or f"回滚到 {stage.value} 阶段")
        self.stage_events.append(event)

    def reset_for_retry(self, policy: Optional[RetryPolicy] = None) -> bool:
        if not self.can_retry(policy):
            return False
        retry_stage = self.get_retry_stage()
        self.mark_for_retry()
        self.rollback_to(retry_stage, f"准备第 {self.retry_count} 次重试")
        return True

    def get_completed_stages(self) -> List[ProcessStage]:
        completed = []
        for stage in STAGE_ORDER:
            if stage == self.current_stage:
                break
            if any(e.stage == stage for e in self.stage_events):
                completed.append(stage)
        return completed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "state": self.state.value,
            "current_stage": self.current_stage.value,
            "stage_events": [e.to_dict() for e in self.stage_events],
            "error_history": [e.to_dict() for e in self.error_history],
            "progress": self.progress,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileProcessContext":
        ctx = cls(file_id=data["file_id"])
        ctx.state = FileProcessState(data.get("state", FileProcessState.PENDING.value))
        ctx.current_stage = ProcessStage(data.get("current_stage", ProcessStage.UPLOAD.value))
        ctx.stage_events = [StageEvent.from_dict(e) for e in data.get("stage_events", [])]
        ctx.error_history = [ErrorInfo.from_dict(e) for e in data.get("error_history", [])]
        ctx.progress = data.get("progress", 0.0)
        ctx.retry_count = data.get("retry_count", 0)
        ctx.metadata = data.get("metadata", {})
        return ctx

    @classmethod
    def from_json(cls, json_str: str) -> "FileProcessContext":
        return cls.from_dict(json.loads(json_str))

    def get_display_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "current_stage": self.current_stage.value,
            "progress": self.progress,
            "progress_percent": int(self.progress * 100),
            "is_completed": self.state == FileProcessState.COMPLETED,
            "is_failed": self.state == FileProcessState.FAILED,
            "is_processing": self.state in [
                FileProcessState.PARSING,
                FileProcessState.SPLITTING,
                FileProcessState.EMBEDDING,
                FileProcessState.INDEXING,
                FileProcessState.RETRYING,
            ],
            "is_pending": self.state == FileProcessState.PENDING,
            "is_retrying": self.state == FileProcessState.RETRYING,
            "can_retry": self.can_retry(),
            "retry_count": self.retry_count,
            "retry_stage": self.get_retry_stage().value if self.error_history else None,
            "stage_events": [e.to_dict() for e in self.stage_events],
            "error_history": [e.to_dict() for e in self.error_history],
            "latest_error": self.error_history[-1].to_dict() if self.error_history else None,
            "completed_stages": [s.value for s in self.get_completed_stages()],
            "metadata": self.metadata,
            "legacy_status": STATE_TO_LEGACY_MAP.get(self.state, "red"),
        }


def legacy_status_to_state(legacy_status: str) -> FileProcessState:
    return LEGACY_STATUS_MAP.get(legacy_status.lower(), FileProcessState.FAILED)


def state_to_legacy_status(state: FileProcessState) -> str:
    return STATE_TO_LEGACY_MAP.get(state, "red")


def categorize_error(exception: Exception, stage: ProcessStage) -> ErrorCategory:
    error_msg = str(exception).lower()

    if "timeout" in error_msg:
        return ErrorCategory.TIMEOUT_ERROR
    elif "milvus" in error_msg or "vector" in error_msg:
        return ErrorCategory.MILVUS_ERROR
    elif "elasticsearch" in error_msg or "es_" in error_msg:
        return ErrorCategory.ES_ERROR
    elif "mysql" in error_msg or "duplicate" in error_msg:
        return ErrorCategory.MYSQL_ERROR
    elif "parse" in error_msg or "decode" in error_msg:
        return ErrorCategory.PARSE_ERROR
    elif "split" in error_msg or "chunk" in error_msg:
        return ErrorCategory.SPLIT_ERROR
    elif "embedding" in error_msg or "embed" in error_msg:
        return ErrorCategory.EMBEDDING_ERROR
    else:
        return ErrorCategory.UNKNOWN_ERROR
