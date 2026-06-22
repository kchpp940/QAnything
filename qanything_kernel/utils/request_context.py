import uuid
import time
from contextvars import ContextVar, Token
from typing import Optional, Dict, Any, Tuple


class LogSchema:
    REQUEST_ID = "request_id"
    USER_ID = "user_id"
    KB_ID = "kb_id"
    FILE_ID = "file_id"
    BOT_ID = "bot_id"
    KB_NAME = "kb_name"
    FILE_NAME = "file_name"
    API_NAME = "api_name"
    STAGE = "stage"
    STATUS = "status"
    DURATION_MS = "duration_ms"
    ELAPSED_MS = "elapsed_ms"
    MESSAGE = "message"
    ERROR = "error"
    ERROR_CATEGORY = "error_category"
    ERROR_MSG = "error_msg"
    ERROR_CODE = "error_code"
    STACKTRACE = "stacktrace"
    SUB_STAGE = "sub_stage"
    METHOD = "method"
    PATH = "path"
    CLIENT_IP = "client_ip"
    USER_AGENT = "user_agent"
    STATUS_CODE = "status_code"
    RESPONSE_SIZE = "response_size"
    MODEL = "model"
    STREAMING = "streaming"
    RERANK = "rerank"
    HYBRID_SEARCH = "hybrid_search"
    FIRST_TOKEN_MS = "first_token_ms"
    TOKENS_PER_SECOND = "tokens_per_second"
    OUTPUT_TOKENS = "output_tokens"
    INPUT_TOKENS = "input_tokens"
    TOTAL_TOKENS = "total_tokens"
    RETRIEVAL_DOCS_COUNT = "retrieval_docs_count"
    SOURCE_DOCS_COUNT = "source_docs_count"
    QUERY = "query"
    KB_IDS_COUNT = "kb_ids_count"
    CHUNK_SIZE = "chunk_size"
    MODE = "mode"
    TOTAL_FILES = "total_files"
    SUCCESS_COUNT = "success_count"
    SKIPPED_COUNT = "skipped_count"
    FAILED_COUNT = "failed_count"
    FILE_IDS = "file_ids"
    IS_QUICK = "is_quick"
    FUNC_NAME = "func_name"
    SQL_QUERY = "sql_query"
    SQL_PARAMS = "sql_params"
    DB_ERRNO = "db_errno"
    MYSQL_ERRNO = "mysql_errno"
    DB_POOL_SIZE = "db_pool_size"
    VECTOR_QUERY = "vector_query"
    TOP_K = "top_k"
    VECTOR_RESULT_COUNT = "vector_result_count"
    VECTOR_RETRY_COUNT = "vector_retry_count"
    ES_INDEX = "es_index"
    ES_DOC_ID = "es_doc_id"
    ES_RESULT_COUNT = "es_result_count"
    FILE_SIZE = "file_size"
    PAGES_COUNT = "pages_count"
    CHUNKS_COUNT = "chunks_count"
    REQUEST_SOURCE = "request_source"
    VALID_FILES_COUNT = "valid_files_count"
    TOTAL_KB_SIZE = "total_kbs"
    INVALID_FIELDS = "invalid_fields"
    MAX_NEW_TOKENS = "max_new_tokens"
    # ===== 从业务扩展提升的核心字段 =====
    KB_IDS = "kb_ids"
    TIMESTAMP = "timestamp"
    RESULT = "result"
    RESULT_COUNT = "result_count"
    FILE_URL = "file_url"
    FILE_INFO = "file_info"
    DOC_ID = "doc_id"
    DOC_COUNT = "doc_count"
    TOTAL_DELETED = "total_deleted"
    QUERIES = "queries"
    SCORE = "score"
    METADATA = "metadata"
    TRACEBACK = "traceback"
    RETRY_COUNT = "retry_count"
    MAX_RETRIES = "max_retries"
    EXPR = "expr"
    PID = "pid"
    ORIGINAL_LEN = "original_len"
    FINAL_LEN = "final_len"
    FREE_CNX = "free_cnx"
    USED_CNX = "used_cnx"
    POOL_SIZE = "pool_size"
    DATABASE = "database"
    DATABASE_NAME = "database_name"
    IMAGE_ID = "image_id"
    NOS_KEY = "nos_key"
    ANY_KB_ID = "any_kb_id"
    TIME_RANGE = "time_range"
    USER_NAME = "user_name"
    DOC_IDS_COUNT = "doc_ids_count"
    FAQ_ID = "faq_id"
    BATCH_INDEX = "batch_index"
    BATCH_COUNT = "batch_count"
    COLLECTION_NAME = "collection_name"
    DELETED_CHUNKS_COUNT = "deleted_chunks_count"
    FILES_ID = "files_id"
    GROUPS_COUNT = "groups_count"
    HOST = "host"
    PORT = "port"
    INDEX_NAME = "index_name"
    ES_URL = "es_url"
    ES_USER = "es_user"
    CHUNKS_NUMBER = "chunks_number"
    PARSE_SECONDS = "parse_seconds"
    INSERT_SECONDS = "insert_seconds"
    TIMEOUT_SECONDS = "timeout_seconds"
    FILE_TO_UPDATE = "file_to_update"
    TARGET_STATUS = "target_status"
    INHERITED_REQUEST_ID = "inherited_request_id"
    RETRIEVER_SEARCH_TIME_S = "retriever_search_time_s"
    DOCS_LEN = "docs_len"
    QUERY_TOKENS = "query_tokens"
    CONDENSE_QUESTION = "condense_question"
    FORMATTED_CHAT_HISTORY = "formatted_chat_history"
    WEB_CHUNK_SIZE = "web_chunk_size"
    TOTAL_IMAGES_NUMBER = "total_images_number"
    ORIGINAL = "original"
    REPLACED = "replaced"
    FIRST_DOC_TOKENS = "first_doc_tokens"
    SECOND_DOC_TOKENS = "second_doc_tokens"
    SECOND_LIMIT_DOC_TOKENS = "second_limit_doc_tokens"
    TABLE_DOC_ID = "table_doc_id"
    TABLE_DOC_TOKENS = "table_doc_tokens"
    TOKEN_NUMS = "token_nums"
    TOKEN_WINDOW = "token_window"
    OFFCUT_TOKEN = "offcut_token"
    LIMITED_TOKEN = "limited_token"
    ROLLBACK_LENGTH = "rollback_length"
    RERANK_TIME = "rerank_time"
    LLM_TIME = "llm_time"
    PREPROCESS_TIME = "preprocess_time"
    RETRIEVE_TIME = "retrieve_time"
    TOTAL_TIME = "total_time"

    # ===== 业务扩展字段（允许落入 extra_fields）=====
    ADD_MSG = "add_msg"
    EST_ROWS = "est_rows"
    IDX_NAME = "idx_name"
    TBL_NAME = "tbl_name"
    TABLE_NAME = "table_name"
    BOT_NAME = "bot_name"
    BOT_PROMPT = "bot_prompt"
    BOT_WELCOME = "bot_welcome"
    BOT_DESC = "bot_desc"
    BOT_IMAGE = "bot_image"
    SOURCE = "source"
    DESCRIPTION = "description"
    PROMPT_LENGTH = "prompt_length"
    RESULT_LENGTH = "result_length"
    CONDENSE_QUESTION_LENGTH = "condense_question_length"
    DOCS_NUM = "docs_num"
    SCORES = "scores"
    TIME_S = "time_s"
    DOC_LIMIT = "doc_limit"
    FIRST_LIMIT_DOC_TOKENS = "first_limit_doc_tokens"
    ORI_SECOND_DOCS_TOKENS = "ori_second_docs_tokens"
    LIMITED_TOKEN_NUMS = "limited_token_nums"
    TEMPLATE_TOKEN_NUMS = "template_token_nums"
    REFERENCE_FIELD_TOKEN_NUMS = "reference_field_token_nums"
    QUERY_TOKEN_NUMS = "query_token_nums"
    HISTORY_TOKEN_NUMS = "history_token_nums"
    MAX_TOKEN = "max_token"
    WORKER_ID = "worker_id"
    ERROR_INFO = "error_info"
    DOCS_COUNT = "docs_count"
    FIRST_DOC_ID = "first_doc_id"
    DELETE_RESULT = "delete_result"
    BATCH_RESULT_COUNT = "batch_result_count"
    RETRY_COUNT = "retry_count"
    MAX_RETRIES = "max_retries"
    EXPR = "expr"
    IS_STREAM = "is_stream"
    SHOW_IMAGES = "show_images"
    TOTAL_FILES_COUNT = "total_files_count"
    SKIPPED_FILES = "skipped_files"
    SKIPPED_URLS = "skipped_urls"
    SKIPPED_FAQS = "skipped_faqs"
    INSERTED_FILES = "inserted_files"
    ESTIMATED_CHARS = "estimated_chars"
    URL_TYPE = "url_type"
    USER_SIZE = "user_size"
    KB_SIZE = "kb_size"
    IS_QUICK_MODE = "is_quick_mode"
    FILE_CONTENT_LENGTH = "file_content_length"
    FILE_TYPE_COUNT = "file_type_count"
    TOTAL_KB = "total_kb"
    TOTAL_QA = "total_qa"
    QAS_SIZE_KB = "qas_size_kb"
    PRODUCT_SOURCE = "product_source"
    SYSTEM_PROMPT_LEN = "system_prompt_len"
    MAX_CONTEXT_LEN = "max_context_len"
    TRUNCATED = "truncated"
    TRUNCATED_HISTORY = "truncated_history"
    DOCS_TOKEN_LENGTH = "docs_token_length"
    REFERENCE_DOCS = "reference_docs"
    REMAINING_TOKENS = "remaining_tokens"
    SELECTED_DOCS = "selected_docs"
    DOC_TOKENS = "doc_tokens"
    RESULT_TOKENS = "result_tokens"
    ANSWER_TOKENS = "answer_tokens"
    NEED_WEB_SEARCH = "need_web_search"
    TIME_RECORD = "time_record"
    ADD_SIZE = "add_size"
    DEL_SIZE = "del_size"
    MSG = "msg"
    TRACEBACK_INFO = "traceback_info"
    STACK_INFO = "stack_info"
    USER_MSG = "user_msg"
    DOCS = "docs"
    INDEX = "index"
    TABLE_MD = "table_md"
    NEXT_CELLS = "next_cells"
    TEXT_BEFORE_TABLE = "text_before_table"
    TEXT_AFTER_TABLE = "text_after_table"
    TABLES_MD = "tables_md"
    CELL_CONTENT = "cell_content"
    ROW = "row"
    COL = "col"
    MAX_ADD_TOKENS = "max_add_tokens"
    TOKEN_DIFF = "token_diff"
    TABLE_DOC = "table_doc"
    TOTAL_TABLES = "total_tables"
    INCOMPLETE_TABLES = "incomplete_tables"
    MISSING_PARAMS = "missing_params"
    NOT_EXIST_KB_IDS = "not_exist_kb_ids"
    KB_IDS_INVALID = "kb_ids_invalid"
    EXIST_FILES = "exist_files"
    NEW_FILES = "new_files"
    EXIST_FAQ_KB_IDS = "exist_faq_kb_ids"
    FAQS_COUNT = "faqs_count"
    CONTENT_LENGTH = "content_length"
    FILE_INFO = "file_info"
    INVALID_FIELDS = "invalid_fields"

    # ===== 分层分类集合 =====
    CORE_TRACKING_FIELDS = {
        REQUEST_ID, USER_ID, KB_ID, FILE_ID, BOT_ID, API_NAME,
        STAGE, STATUS, DURATION_MS, ELAPSED_MS, ERROR_CATEGORY,
    }

    CORE_METRICS_FIELDS = {
        MODEL, TOKENS_PER_SECOND, OUTPUT_TOKENS, INPUT_TOKENS, TOTAL_TOKENS,
        RETRIEVAL_DOCS_COUNT, SOURCE_DOCS_COUNT, FIRST_TOKEN_MS,
        STREAMING, RERANK, HYBRID_SEARCH, TOP_K, CHUNK_SIZE,
        DOCS_NUM, DOC_LIMIT, DOCS_COUNT, FIRST_DOC_ID,
    }

    CORE_RESOURCE_FIELDS = {
        KB_NAME, FILE_NAME, KB_IDS, FILE_IDS, KB_IDS_COUNT, FILE_SIZE,
        PAGES_COUNT, CHUNKS_COUNT, VALID_FILES_COUNT, TOTAL_FILES,
        SUCCESS_COUNT, SKIPPED_COUNT, FAILED_COUNT, QUERY,
        REQUEST_SOURCE, SUB_STAGE, SKIPPED_FILES, SKIPPED_URLS,
        SKIPPED_FAQS, INSERTED_FILES, ESTIMATED_CHARS, URL_TYPE,
        FILE_CONTENT_LENGTH, FILE_TYPE_COUNT, TOTAL_QA, QAS_SIZE_KB,
        TOTAL_KB_SIZE,
    }

    HTTP_REQUEST_FIELDS = {
        METHOD, PATH, CLIENT_IP, USER_AGENT, STATUS_CODE, RESPONSE_SIZE,
    }

    DB_FIELDS = {
        SQL_QUERY, SQL_PARAMS, DB_ERRNO, DB_POOL_SIZE, FREE_CNX, USED_CNX,
        POOL_SIZE, DATABASE, DATABASE_NAME, ANY_KB_ID, TIME_RANGE,
        BATCH_INDEX, BATCH_COUNT, USER_NAME, DOC_ID, DOC_COUNT,
        DOC_IDS_COUNT, FAQ_ID, TOTAL_DELETED, TIMESTAMP, MYSQL_ERRNO,
        EST_ROWS, IDX_NAME, TBL_NAME, TABLE_NAME, SOURCE, DESCRIPTION,
    }

    VECTOR_DB_FIELDS = {
        VECTOR_QUERY, VECTOR_RESULT_COUNT, VECTOR_RETRY_COUNT,
        COLLECTION_NAME, DELETED_CHUNKS_COUNT, FILES_ID, GROUPS_COUNT,
        HOST, PORT, RETRY_COUNT, MAX_RETRIES, EXPR, RESULT_COUNT,
    }

    SEARCH_ENGINE_FIELDS = {
        ES_INDEX, ES_DOC_ID, ES_RESULT_COUNT, INDEX_NAME, ES_URL, ES_USER,
    }

    FILE_PROCESSING_FIELDS = {
        FILE_URL, FILE_INFO, FILE_TO_UPDATE, TARGET_STATUS,
        INHERITED_REQUEST_ID, PARSE_SECONDS, INSERT_SECONDS, TIMEOUT_SECONDS,
        CHUNKS_NUMBER, IMAGE_ID, NOS_KEY,
    }

    BOT_FIELDS = {
        BOT_NAME, BOT_PROMPT, BOT_WELCOME, BOT_DESC, BOT_IMAGE,
    }

    VALIDATION_FIELDS = {
        MISSING_PARAMS, NOT_EXIST_KB_IDS, KB_IDS_INVALID,
        EXIST_FILES, NEW_FILES, EXIST_FAQ_KB_IDS, FAQS_COUNT,
        CONTENT_LENGTH, INVALID_FIELDS,
    }

    LLM_FIELDS = {
        QUERIES, SCORE, SCORES, METADATA, RESULT, TRACEBACK, PID,
        ORIGINAL_LEN, FINAL_LEN, RETRIEVER_SEARCH_TIME_S,
        DOCS_LEN, QUERY_TOKENS, CONDENSE_QUESTION, FORMATTED_CHAT_HISTORY,
        WEB_CHUNK_SIZE, TOTAL_IMAGES_NUMBER, ORIGINAL, REPLACED,
        FIRST_DOC_TOKENS, SECOND_DOC_TOKENS, SECOND_LIMIT_DOC_TOKENS,
        TABLE_DOC_ID, TABLE_DOC_TOKENS, TOKEN_NUMS, TOKEN_WINDOW,
        OFFCUT_TOKEN, LIMITED_TOKEN, ROLLBACK_LENGTH, RERANK_TIME,
        LLM_TIME, PREPROCESS_TIME, RETRIEVE_TIME, TOTAL_TIME,
        PROMPT_LENGTH, RESULT_LENGTH, CONDENSE_QUESTION_LENGTH,
        FIRST_LIMIT_DOC_TOKENS, LIMITED_TOKEN_NUMS, TEMPLATE_TOKEN_NUMS,
        REFERENCE_FIELD_TOKEN_NUMS, QUERY_TOKEN_NUMS, HISTORY_TOKEN_NUMS,
        MAX_TOKEN, MAX_NEW_TOKENS, DOC_TOKENS, RESULT_TOKENS, ANSWER_TOKENS,
        DOCS_TOKEN_LENGTH, REMAINING_TOKENS, SELECTED_DOCS, REFERENCE_DOCS,
        SYSTEM_PROMPT_LEN, MAX_CONTEXT_LEN, MAX_ADD_TOKENS,
        TOTAL_TABLES, INCOMPLETE_TABLES, TABLE_DOC, TABLE_MD,
        TABLES_MD, TEXT_BEFORE_TABLE, TEXT_AFTER_TABLE,
        NEXT_CELLS, CELL_CONTENT, ROW, COL, TOKEN_DIFF,
        TRUNCATED, TRUNCATED_HISTORY, NEED_WEB_SEARCH,
        ORI_SECOND_DOCS_TOKENS,
    }

    DEBUG_PERF_FIELDS = {
        FUNC_NAME, IS_QUICK, MODE, ERROR_CODE, ERROR_MSG, STACKTRACE,
        MESSAGE, ERROR, TIME_S, TIME_RECORD, ADD_SIZE, DEL_SIZE,
        TRACEBACK_INFO, STACK_INFO, WORKER_ID, BATCH_RESULT_COUNT,
        DELETE_RESULT, IS_STREAM, SHOW_IMAGES, TOTAL_FILES_COUNT,
        PRODUCT_SOURCE, USER_SIZE, KB_SIZE, USER_MSG, MSG,
        DOCS, INDEX, ADD_MSG, ERROR_INFO, IS_QUICK_MODE,
    }

    # 真正的扩展字段（以 X_ 前缀标识，落入 extra_fields）
    # 原则：新增字段必须先归入明确分类，只有临时/调试字段允许放此处
    # 使用方式：代码中传入 X_ 前缀，如 X_MSG, X_BOT_NAME, X_CUSTOM_FIELD
    BUSINESS_EXTENSION_FIELDS = set()

    @classmethod
    def is_core_field(cls, field: str) -> bool:
        return (field in cls.CORE_TRACKING_FIELDS or
                field in cls.CORE_METRICS_FIELDS or
                field in cls.CORE_RESOURCE_FIELDS)

    @classmethod
    def is_allowed_field(cls, field: str) -> bool:
        return (field in cls.CORE_TRACKING_FIELDS or
                field in cls.CORE_METRICS_FIELDS or
                field in cls.CORE_RESOURCE_FIELDS or
                field in cls.HTTP_REQUEST_FIELDS or
                field in cls.DB_FIELDS or
                field in cls.VECTOR_DB_FIELDS or
                field in cls.SEARCH_ENGINE_FIELDS or
                field in cls.FILE_PROCESSING_FIELDS or
                field in cls.BOT_FIELDS or
                field in cls.VALIDATION_FIELDS or
                field in cls.LLM_FIELDS or
                field in cls.DEBUG_PERF_FIELDS or
                field in cls.BUSINESS_EXTENSION_FIELDS)

    @classmethod
    def get_core_fields(cls) -> set:
        return set.union(
            cls.CORE_TRACKING_FIELDS, cls.CORE_METRICS_FIELDS, cls.CORE_RESOURCE_FIELDS
        )

    @classmethod
    def get_all_fields(cls) -> set:
        return {v for k, v in cls.__dict__.items()
                if not k.startswith('_') and isinstance(v, str)
                and not k.startswith('is_') and not k.startswith('get_')
                and not k.endswith('_FIELDS')}




class Status:
    START = "start"
    SUCCESS = "success"
    FAIL = "fail"
    FIRST_TOKEN = "first_token"


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



def get_log_schema_fields() -> set:
    return LogSchema.get_all_fields()


def is_valid_log_field(field: str) -> bool:
    return LogSchema.is_allowed_field(field)


def validate_log_fields(fields: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], list]:
    """
    校验日志字段，返回 (合法字段, 扩展字段, 警告列表)
    - 核心字段拼错会触发 WARNING，返回建议修正
    """
    valid = {}
    extra = {}
    warnings = []
    core_fields = LogSchema.get_core_fields()
    all_allowed = LogSchema.get_all_fields()

    for k, v in fields.items():
        if LogSchema.is_allowed_field(k):
            # 去掉 X_ 前缀后存储
            store_key = k[2:] if k.startswith('X_') else k
            valid[store_key] = v
        else:
            suggestion = _find_similar_core_field(k, core_fields)
            if suggestion:
                warnings.append(
                    f"字段 '{k}' 疑似核心字段拼写错误，建议改为 LogSchema.{suggestion.upper()} ('{suggestion}')"
                )
            extra[k] = v
    return valid, extra, warnings


def _find_similar_core_field(field: str, core_fields: set, max_distance: int = 2) -> Optional[str]:
    """
    用编辑距离检测疑似拼写错误的核心字段
    例：requestid → request_id, userid → user_id
    """
    best_match = None
    best_distance = max_distance + 1

    for core in core_fields:
        dist = _levenshtein_distance(field.lower(), core.lower())
        if dist <= max_distance and dist < best_distance:
            best_distance = dist
            best_match = core

    return best_match


def _levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串的编辑距离"""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


