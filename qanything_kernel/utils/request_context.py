import uuid
import time
from contextvars import ContextVar, Token
from typing import Optional, Dict, Any


class ErrorCategory:
    VALIDATION_ERROR = "validation_error"
    AUTH_ERROR = "auth_error"
    NOT_FOUND = "not_found"
    DB_ERROR = "db_error"
    VECTOR_DB_ERROR = "vector_db_error"
    SEARCH_ENGINE_ERROR = "search_engine_error"
    LLM_ERROR = "llm_error"
    EMBEDDING_ERROR = "embedding_error"
    RERANK_ERROR = "rerank_error"
    FILE_PARSE_ERROR = "file_parse_error"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"


class Stage:
    REQUEST_RECEIVED = "request_received"
    PARAMS_VALIDATED = "params_validated"
    KB_OPERATION = "kb_operation"
    FILE_UPLOAD = "file_upload"
    FILE_PARSE = "file_parse"
    FILE_INSERT = "file_insert"
    RETRIEVAL = "retrieval"
    RERANK = "rerank"
    LLM_GENERATE = "llm_generate"
    RESPONSE_SENT = "response_sent"
    DB_OPERATION = "db_operation"
    VECTOR_DB_OPERATION = "vector_db_operation"
    ES_OPERATION = "es_operation"
    BOT_OPERATION = "bot_operation"


class RequestContext:
    def __init__(self):
        self._request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
        self._user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
        self._kb_id: ContextVar[Optional[str]] = ContextVar('kb_id', default=None)
        self._file_id: ContextVar[Optional[str]] = ContextVar('file_id', default=None)
        self._bot_id: ContextVar[Optional[str]] = ContextVar('bot_id', default=None)
        self._extra: ContextVar[Dict[str, Any]] = ContextVar('extra', default={})
        self._start_time: ContextVar[Optional[float]] = ContextVar('start_time', default=None)
        self._stage: ContextVar[Optional[str]] = ContextVar('stage', default=None)
        self._api_name: ContextVar[Optional[str]] = ContextVar('api_name', default=None)

    def generate_request_id(self) -> str:
        return "REQ" + uuid.uuid4().hex[:16].upper()

    def init_context(self, request_id: Optional[str] = None,
                     user_id: Optional[str] = None,
                     kb_id: Optional[str] = None,
                     file_id: Optional[str] = None,
                     bot_id: Optional[str] = None,
                     api_name: Optional[str] = None,
                     **extra) -> None:
        self._request_id.set(request_id or self.generate_request_id())
        self._user_id.set(user_id)
        self._kb_id.set(kb_id)
        self._file_id.set(file_id)
        self._bot_id.set(bot_id)
        self._api_name.set(api_name)
        self._start_time.set(time.perf_counter())
        self._extra.set(extra.copy())

    def set(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if key == 'request_id':
                self._request_id.set(value)
            elif key == 'user_id':
                self._user_id.set(value)
            elif key == 'kb_id':
                self._kb_id.set(value)
            elif key == 'file_id':
                self._file_id.set(value)
            elif key == 'bot_id':
                self._bot_id.set(value)
            elif key == 'api_name':
                self._api_name.set(value)
            elif key == 'stage':
                self._stage.set(value)
            else:
                current_extra = self._extra.get().copy()
                current_extra[key] = value
                self._extra.set(current_extra)

    def update_extra(self, **kwargs) -> None:
        current_extra = self._extra.get().copy()
        current_extra.update(kwargs)
        self._extra.set(current_extra)

    def clear_extra(self, *keys) -> None:
        if not keys:
            self._extra.set({})
            return
        current_extra = self._extra.get().copy()
        for key in keys:
            current_extra.pop(key, None)
        self._extra.set(current_extra)

    def get(self) -> Dict[str, Any]:
        ctx = {
            'request_id': self._request_id.get(),
            'user_id': self._user_id.get(),
            'kb_id': self._kb_id.get(),
            'file_id': self._file_id.get(),
            'bot_id': self._bot_id.get(),
            'api_name': self._api_name.get(),
            'stage': self._stage.get(),
        }
        elapsed = self.get_elapsed_ms()
        if elapsed is not None:
            ctx['elapsed_ms'] = elapsed
        ctx.update(self._extra.get())
        return {k: v for k, v in ctx.items() if v is not None}

    def get_elapsed_ms(self) -> Optional[float]:
        start = self._start_time.get()
        if start is None:
            return None
        return round((time.perf_counter() - start) * 1000, 2)

    def reset(self) -> None:
        self._request_id.set(None)
        self._user_id.set(None)
        self._kb_id.set(None)
        self._file_id.set(None)
        self._bot_id.set(None)
        self._extra.set({})
        self._start_time.set(None)
        self._stage.set(None)
        self._api_name.set(None)


_ctx = RequestContext()


def init_context(**kwargs) -> None:
    _ctx.init_context(**kwargs)


def set_context(**kwargs) -> None:
    _ctx.set(**kwargs)


def update_extra(**kwargs) -> None:
    _ctx.update_extra(**kwargs)


def clear_extra(*keys) -> None:
    _ctx.clear_extra(*keys)


def get_context() -> Dict[str, Any]:
    return _ctx.get()


def get_request_id() -> Optional[str]:
    return _ctx.get().get('request_id')


def generate_request_id() -> str:
    return _ctx.generate_request_id()


def get_elapsed_ms() -> Optional[float]:
    return _ctx.get_elapsed_ms()


def reset_context() -> None:
    _ctx.reset()
