import logging
import json
import traceback
from concurrent_log_handler import ConcurrentRotatingFileHandler
from logging import Formatter, LogRecord
import time
import os
import sys
from typing import Dict, Any, Optional, Tuple

from qanything_kernel.utils.request_context import (
    get_context, get_request_id, ErrorCategory,
    validate_log_fields, get_log_schema_fields, LogSchema
)


process_type = 'MainProcess' if 'SANIC_WORKER_NAME' not in os.environ else os.environ['SANIC_WORKER_NAME']


class CustomConcurrentRotatingFileHandler(ConcurrentRotatingFileHandler):
    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        current_time = time.strftime("%Y%m%d_%H%M%S")
        dfn = self.rotation_filename(f"{self.baseFilename}.{current_time}")

        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)

        if not self.delay:
            self.stream = self._open()


class StructuredJsonFormatter(Formatter):
    RESERVED_ATTRS = {
        'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
        'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs',
        'message', 'msg', 'name', 'pathname', 'process', 'processName',
        'relativeCreated', 'stack_info', 'thread', 'threadName'
    }

    def format(self, record: LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(record.created)) +
                         f'.{int(record.msecs):03d}',
            'level': record.levelname,
            'logger': record.name,
            'pid': record.process,
            'process_type': process_type,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.threadName,
        }

        ctx = get_context()
        if ctx:
            log_obj['ctx'] = ctx

        structured_fields = getattr(record, 'structured_fields', {})
        if structured_fields:
            log_obj.update(structured_fields)

        error_info = getattr(record, 'error_info', None)
        if error_info:
            log_obj[LogSchema.ERROR] = error_info

        extra = {k: v for k, v in record.__dict__.items()
                 if k not in self.RESERVED_ATTRS
                 and k not in ('structured_fields', 'error_info')
                 and not k.startswith('_')}
        if extra:
            log_obj['extra'] = extra

        msg = record.getMessage()
        if msg:
            try:
                parsed = json.loads(msg)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if k not in log_obj:
                            log_obj[k] = v
                else:
                    log_obj[LogSchema.MESSAGE] = msg
            except (json.JSONDecodeError, ValueError):
                log_obj[LogSchema.MESSAGE] = msg

        if record.exc_info:
            if not log_obj.get(LogSchema.ERROR):
                log_obj[LogSchema.ERROR] = {}
            exc_type, exc_value, _ = record.exc_info
            log_obj[LogSchema.ERROR].update({
                'type': exc_type.__name__ if exc_type else None,
                'message': str(exc_value) if exc_value else None,
                LogSchema.STACKTRACE: self.formatException(record.exc_info),
            })

        if hasattr(record, 'stack_info') and record.stack_info:
            log_obj['stack_info'] = self.formatStack(record.stack_info)

        try:
            return json.dumps(log_obj, ensure_ascii=False, default=str)
        except (TypeError, ValueError, OverflowError):
            log_obj['message'] = f"[Serialization failed] {log_obj.get('message', '')}"
            if 'error' in log_obj:
                log_obj['error'] = {'message': str(log_obj['error'])}
            if 'ctx' in log_obj:
                log_obj['ctx'] = {'request_id': log_obj['ctx'].get('request_id')}
            return json.dumps(log_obj, ensure_ascii=False, default=str)


class StructuredLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log(self, level: int, message: str,
             stage: Optional[str] = None,
             status: Optional[str] = None,
             duration_ms: Optional[float] = None,
             error: Optional[BaseException] = None,
             error_category: Optional[str] = None,
             **fields: Any) -> None:
        raw_fields = {}
        if stage:
            raw_fields[LogSchema.STAGE] = stage
        if status is not None:
            raw_fields[LogSchema.STATUS] = status
        if duration_ms is not None:
            raw_fields[LogSchema.DURATION_MS] = round(duration_ms, 2)

        valid_fields, extra_fields = validate_log_fields(fields)
        raw_fields.update(valid_fields)

        structured = dict(raw_fields)
        if extra_fields:
            structured['extra_fields'] = extra_fields

        error_info = None
        if error is not None:
            error_info = {
                LogSchema.ERROR_CATEGORY: error_category or self._classify_error(error),
                'type': type(error).__name__,
                LogSchema.ERROR_MSG: str(error),
                LogSchema.STACKTRACE: ''.join(traceback.format_exception(
                    type(error), error, error.__traceback__
                )),
            }

        extra = {'structured_fields': structured}
        if error_info:
            extra['error_info'] = error_info

        self._logger.log(level, message, exc_info=error, extra=extra)

    @staticmethod
    def _classify_error(err: BaseException) -> str:
        try:
            import mysql.connector.errors as mysql_errs
            mysql_error_types = (mysql_errs.Error, mysql_errs.InterfaceError)
        except (ImportError, AttributeError):
            mysql_error_types = ()
        err_name = type(err).__name__.lower()
        err_msg = str(err).lower()

        if 'timeout' in err_name or 'timeout' in err_msg:
            return ErrorCategory.TIMEOUT_ERROR
        if 'mysql' in err_name or isinstance(err, mysql_error_types):
            return ErrorCategory.DB_ERROR
        if 'milvus' in err_name:
            return ErrorCategory.VECTOR_DB_ERROR
        if 'elastic' in err_name or 'elasticsearch' in err_msg:
            return ErrorCategory.SEARCH_ENGINE_ERROR
        if any(k in err_name for k in ['parse', 'pdf', 'docx', 'ppt', 'excel', 'file']):
            return ErrorCategory.FILE_PARSE_ERROR
        if 'auth' in err_name or 'unauthorized' in err_msg or 'forbidden' in err_msg:
            return ErrorCategory.AUTH_ERROR
        if 'notfound' in err_name or 'not found' in err_msg:
            return ErrorCategory.NOT_FOUND
        if any(k in err_msg for k in ['connection', 'network', 'socket', ' refused']):
            return ErrorCategory.NETWORK_ERROR
        if any(k in err_name for k in ['validation', 'value', 'type']) or 'invalid' in err_msg:
            return ErrorCategory.VALIDATION_ERROR
        if any(k in err_name for k in ['llm', 'openai', 'chat']):
            return ErrorCategory.LLM_ERROR
        if 'embed' in err_name:
            return ErrorCategory.EMBEDDING_ERROR
        if 'rerank' in err_name:
            return ErrorCategory.RERANK_ERROR
        return ErrorCategory.UNKNOWN_ERROR

    def debug(self, message: str, **kwargs) -> None:
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._log(logging.WARNING, message, **kwargs)

    def warn(self, message: str, **kwargs) -> None:
        self.warning(message, **kwargs)

    def error(self, message: str, error: Optional[BaseException] = None, **kwargs) -> None:
        self._log(logging.ERROR, message, error=error, **kwargs)

    def exception(self, message: str, error: Optional[BaseException] = None, **kwargs) -> None:
        if error is None:
            exc_info = sys.exc_info()
            if exc_info and exc_info[0] is not None:
                error = exc_info[1]
        self._log(logging.ERROR, message, error=error, **kwargs)

    def critical(self, message: str, error: Optional[BaseException] = None, **kwargs) -> None:
        self._log(logging.CRITICAL, message, error=error, **kwargs)

    def stage_start(self, stage: str, message: str = "", **fields) -> None:
        self.info(message or f"Stage start: {stage}", stage=stage, status="start", **fields)

    def stage_success(self, stage: str, message: str = "", duration_ms: Optional[float] = None, **fields) -> None:
        self.info(message or f"Stage success: {stage}", stage=stage, status="success",
                  duration_ms=duration_ms, **fields)

    def stage_fail(self, stage: str, message: str = "",
                   error: Optional[BaseException] = None,
                   duration_ms: Optional[float] = None,
                   error_category: Optional[str] = None,
                   **fields) -> None:
        self.error(message or f"Stage failed: {stage}", stage=stage, status="fail",
                   error=error, error_category=error_category,
                   duration_ms=duration_ms, **fields)

    @property
    def logger(self) -> logging.Logger:
        return self._logger


def _setup_logger(name: str, log_folder: str, filename: str,
                  use_json: bool = True,
                  include_func: bool = True,
                  max_bytes: int = 64 * 1024 * 1024,
                  backup_count: int = 256) -> Tuple[logging.Logger, StructuredLogger]:
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    logger = logging.getLogger(name)
    if logger.handlers:
        structured = StructuredLogger(logger)
        return logger, structured

    logger.setLevel(logging.INFO)

    handler = CustomConcurrentRotatingFileHandler(
        os.path.join(log_folder, filename), "a", max_bytes, backup_count
    )

    if use_json:
        formatter = StructuredJsonFormatter()
    else:
        base_fmt = f"%(asctime)s - [PID: %(process)d][{process_type}]"
        if include_func:
            base_fmt += " - [Function: %(funcName)s]"
        base_fmt += " - %(levelname)s - %(message)s"
        formatter = logging.Formatter(base_fmt)

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    structured = StructuredLogger(logger)
    return logger, structured


current_time = time.strftime("%Y%m%d_%H%M%S")
debug_log_folder = './logs/debug_logs'
qa_log_folder = './logs/qa_logs'
rerank_log_folder = './logs/rerank_logs'
embed_log_folder = './logs/embed_logs'
insert_log_folder = './logs/insert_logs'

debug_logger, s_debug_logger = _setup_logger(
    'debug_logger', debug_log_folder, 'debug.log', use_json=True, include_func=True
)
qa_logger, s_qa_logger = _setup_logger(
    'qa_logger', qa_log_folder, 'qa.log', use_json=True, include_func=False
)
rerank_logger, s_rerank_logger = _setup_logger(
    'rerank_logger', rerank_log_folder, 'rerank.log', use_json=True, include_func=False
)
embed_logger, s_embed_logger = _setup_logger(
    'embed_logger', embed_log_folder, 'embed.log', use_json=True, include_func=False
)
insert_logger, s_insert_logger = _setup_logger(
    'insert_logger', insert_log_folder, 'insert.log', use_json=True, include_func=True
)

print(s_debug_logger, s_qa_logger, s_rerank_logger, s_embed_logger, s_insert_logger, flush=True)
