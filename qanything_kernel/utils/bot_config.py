import json
import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from copy import deepcopy

from qanything_kernel.configs.model_config import (
    BOT_DESC, BOT_IMAGE, BOT_PROMPT, BOT_WELCOME,
    VECTOR_SEARCH_TOP_K, DEFAULT_PARENT_CHUNK_SIZE
)

try:
    from qanything_kernel.utils.custom_log import debug_logger
except Exception:
    debug_logger = logging.getLogger("bot_config")


SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "shared_configs", "llm_param_schema.json"
)


def _load_schema() -> Dict[str, Any]:
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        debug_logger.error(f"Failed to load llm_param_schema.json: {e}")
        return {}


SCHEMA = _load_schema()
LLM_FIELDS = SCHEMA.get("fields", {})
POST_PROCESS = SCHEMA.get("post_process", {})


def _coerce_value(value: Any, field_type: str) -> Any:
    if value is None:
        return None
    if field_type == "str":
        return str(value)
    if field_type == "int":
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if field_type == "float":
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    if field_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    return value


def _apply_field_defaults(target: Dict[str, Any], fill_missing_only: bool = True) -> None:
    for field_name, field_spec in LLM_FIELDS.items():
        if fill_missing_only and field_name in target and target[field_name] is not None:
            continue
        if field_spec.get("fill_default_for_bot", False):
            default = field_spec.get("default")
            target[field_name] = default


def _validate_field_ranges(llm_setting: Dict[str, Any]) -> Tuple[bool, str]:
    for field_name, field_spec in LLM_FIELDS.items():
        value = llm_setting.get(field_name)
        if value is None and not field_spec.get("allow_null", False):
            continue
        if "min" in field_spec and value is not None and value < field_spec["min"]:
            return False, f"fail, {field_name} must be >= {field_spec['min']}"
        if "max" in field_spec and value is not None and value > field_spec["max"]:
            return False, f"fail, {field_name} must be <= {field_spec['max']}"
    return True, "success"


def _apply_post_process(llm_setting: Dict[str, Any]) -> None:
    top_p_correction = POST_PROCESS.get("top_p_1_0_correction", {})
    if top_p_correction.get("enabled", False):
        from_val = top_p_correction.get("from", 1.0)
        to_val = top_p_correction.get("to", 0.99)
        if llm_setting.get("top_p") == from_val:
            llm_setting["top_p"] = to_val


def _validate_required_llm_fields(llm_setting: Dict[str, Any]) -> Tuple[bool, List[str]]:
    missing = []
    for field_name, field_spec in LLM_FIELDS.items():
        if field_spec.get("required_for_request", False):
            value = llm_setting.get(field_name)
            if value is None or (isinstance(value, str) and value == ""):
                missing.append(field_name)
    return len(missing) == 0, missing


class BotConfig:
    """
    Bot 配置的统一契约层。

    职责：
    1. 统一默认值（基于 shared_configs/llm_param_schema.json）
    2. 旧字段兼容（散字段 -> 结构化 config）
    3. JSON 解析/序列化
    4. 字段合法性校验
    5. 最终运行配置输出

    所有 new_bot / update_bot / get_bot_info / local_doc_chat 都必须经过此层，
    确保保存、回显、执行路径一致。
    """

    def __init__(
        self,
        bot_name: str,
        description: str = BOT_DESC,
        head_image: str = BOT_IMAGE,
        prompt_setting: str = BOT_PROMPT,
        welcome_message: str = BOT_WELCOME,
        kb_ids: Optional[List[str]] = None,
        llm_setting: Optional[Dict[str, Any]] = None,
    ):
        self.bot_name = bot_name
        self.description = description or BOT_DESC
        self.head_image = head_image or BOT_IMAGE
        self.prompt_setting = prompt_setting or BOT_PROMPT
        self.welcome_message = welcome_message or BOT_WELCOME
        self.kb_ids = kb_ids or []
        self.llm_setting = llm_setting or {}
        _apply_field_defaults(self.llm_setting, fill_missing_only=True)
        for k, v in list(self.llm_setting.items()):
            spec = LLM_FIELDS.get(k)
            if spec:
                coerced = _coerce_value(v, spec.get("type", "str"))
                if coerced is not None or spec.get("allow_null", False):
                    self.llm_setting[k] = coerced
        _apply_field_defaults(self.llm_setting, fill_missing_only=True)
        _apply_post_process(self.llm_setting)

    @classmethod
    def from_db_row(cls, row: tuple) -> "BotConfig":
        """
        从数据库 SELECT 行（get_bot 返回格式）构造 BotConfig。

        row 格式：
        (bot_id, bot_name, description, head_image, prompt_setting, welcome_message,
         kb_ids_str, update_time, user_id, llm_setting_json_str)
        """
        bot_name = row[1]
        description = row[2] if row[2] else BOT_DESC
        head_image = row[3] if row[3] else BOT_IMAGE
        prompt_setting = row[4] if row[4] else BOT_PROMPT
        welcome_message = row[5] if row[5] else BOT_WELCOME
        kb_ids_str = row[6] or ""
        kb_ids = [kb for kb in kb_ids_str.split(",") if kb] if kb_ids_str else []
        llm_setting_raw = row[9] if len(row) > 9 else "{}"
        try:
            llm_setting = json.loads(llm_setting_raw) if llm_setting_raw else {}
        except (json.JSONDecodeError, TypeError):
            debug_logger.warning(f"Failed to parse llm_setting from DB: {llm_setting_raw}")
            llm_setting = {}
        return cls(
            bot_name=bot_name,
            description=description,
            head_image=head_image,
            prompt_setting=prompt_setting,
            welcome_message=welcome_message,
            kb_ids=kb_ids,
            llm_setting=llm_setting,
        )

    @classmethod
    def from_request(cls, req_data: Dict[str, Any], existing: Optional["BotConfig"] = None) -> "BotConfig":
        """
        从 HTTP 请求参数构造 BotConfig。

        支持两种格式：
        1. 结构化：{ bot_config: { basic: {...}, llm_setting: {...}, kb_ids: [...] } }
        2. 散字段（兼容旧前端）：{ bot_name, description, prompt_setting, ..., api_base, api_key, ... }

        当 existing 不为空时（update_bot 场景），缺失的字段从 existing 继承。
        """
        base = existing

        structured = req_data.get("bot_config")
        if structured:
            basic = structured.get("basic", {})
            llm_setting = structured.get("llm_setting", {})
            kb_ids = structured.get("kb_ids")
        else:
            basic = {
                "bot_name": req_data.get("bot_name"),
                "description": req_data.get("description"),
                "head_image": req_data.get("head_image"),
                "prompt_setting": req_data.get("prompt_setting"),
                "welcome_message": req_data.get("welcome_message"),
            }
            llm_setting = {}
            for field_name in LLM_FIELDS.keys():
                if field_name in req_data and req_data[field_name] is not None:
                    llm_setting[field_name] = req_data[field_name]
            kb_ids = req_data.get("kb_ids")

        if base:
            merged_llm = deepcopy(base.llm_setting)
            merged_llm.update(llm_setting)
            llm_setting = merged_llm
            bot_name = basic.get("bot_name") or base.bot_name
            description = basic.get("description") if basic.get("description") is not None else base.description
            head_image = basic.get("head_image") if basic.get("head_image") is not None else base.head_image
            prompt_setting = basic.get("prompt_setting") if basic.get("prompt_setting") is not None else base.prompt_setting
            welcome_message = basic.get("welcome_message") if basic.get("welcome_message") is not None else base.welcome_message
            final_kb_ids = kb_ids if kb_ids is not None else base.kb_ids
        else:
            bot_name = basic.get("bot_name", "")
            description = basic.get("description")
            head_image = basic.get("head_image")
            prompt_setting = basic.get("prompt_setting")
            welcome_message = basic.get("welcome_message")
            final_kb_ids = kb_ids if kb_ids is not None else []

        return cls(
            bot_name=bot_name,
            description=description,
            head_image=head_image,
            prompt_setting=prompt_setting,
            welcome_message=welcome_message,
            kb_ids=final_kb_ids,
            llm_setting=llm_setting,
        )

    @classmethod
    def from_chat_request(cls, req_data: Dict[str, Any], db_row: Optional[tuple] = None) -> "BotConfig":
        """
        从 local_doc_chat 请求构造 BotConfig。

        优先级：
        1. 如果提供 bot_id 且 db_row 存在，以 DB 配置为准
        2. 散字段覆盖（兼容临时参数）
        """
        if db_row is not None:
            config = cls.from_db_row(db_row)
        else:
            config = cls(bot_name="__chat_tmp__")
        override_llm = {}
        for field_name in LLM_FIELDS.keys():
            if field_name in req_data and req_data[field_name] is not None:
                override_llm[field_name] = req_data[field_name]
        if override_llm:
            merged = deepcopy(config.llm_setting)
            merged.update(override_llm)
            config.llm_setting = merged
            _apply_field_defaults(config.llm_setting, fill_missing_only=True)
            _apply_post_process(config.llm_setting)
        kb_ids_override = req_data.get("kb_ids")
        if kb_ids_override is not None:
            config.kb_ids = kb_ids_override
        prompt_override = req_data.get("custom_prompt")
        if prompt_override is not None:
            config.prompt_setting = prompt_override
        return config

    def to_db_fields(self) -> Dict[str, Any]:
        """序列化为数据库写入字段。"""
        return {
            "bot_name": self.bot_name,
            "description": self.description,
            "head_image": self.head_image,
            "prompt_setting": self.prompt_setting,
            "welcome_message": self.welcome_message,
            "kb_ids_str": ",".join(self.kb_ids),
            "llm_setting_json": json.dumps(self.llm_setting, ensure_ascii=False),
        }

    def to_api_response(self, bot_id: str, user_id: str, update_time_str: str,
                        kb_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """序列化为 get_bot_info API 返回格式。"""
        return {
            "bot_id": bot_id,
            "user_id": user_id,
            "bot_name": self.bot_name,
            "description": self.description,
            "head_image": self.head_image,
            "prompt_setting": self.prompt_setting,
            "welcome_message": self.welcome_message,
            "kb_ids": self.kb_ids,
            "kb_names": kb_names or [],
            "update_time": update_time_str,
            "llm_setting": deepcopy(self.llm_setting),
            "bot_config": {
                "basic": {
                    "bot_name": self.bot_name,
                    "description": self.description,
                    "head_image": self.head_image,
                    "prompt_setting": self.prompt_setting,
                    "welcome_message": self.welcome_message,
                },
                "llm_setting": deepcopy(self.llm_setting),
                "kb_ids": self.kb_ids,
            },
        }

    def to_runtime_config(self) -> Dict[str, Any]:
        """输出 local_doc_chat 运行时需要的扁平化配置。"""
        llm = self.llm_setting
        return {
            "kb_ids": self.kb_ids,
            "custom_prompt": self.prompt_setting,
            "rerank": llm.get("rerank", True),
            "only_need_search_results": llm.get("only_need_search_results", False),
            "need_web_search": llm.get("networking", False),
            "api_base": llm.get("api_base", ""),
            "api_key": llm.get("api_key", "ollama"),
            "api_context_length": llm.get("api_context_length", 4096),
            "top_p": llm.get("top_p", 0.99),
            "temperature": llm.get("temperature", 0.5),
            "top_k": llm.get("top_k", VECTOR_SEARCH_TOP_K),
            "model": llm.get("model", "gpt-4o-mini"),
            "max_token": llm.get("max_token"),
            "hybrid_search": llm.get("hybrid_search", False),
            "chunk_size": llm.get("chunk_size", DEFAULT_PARENT_CHUNK_SIZE),
        }

    def validate(self) -> Tuple[bool, str]:
        """校验配置合法性，返回 (是否通过, 错误信息)。"""
        if not self.bot_name:
            return False, "fail, bot_name is required"
        ok, msg = _validate_field_ranges(self.llm_setting)
        if not ok:
            return False, msg
        return True, "success"

    def validate_for_chat(self) -> Tuple[bool, str]:
        """校验聊天时必填字段。"""
        ok, missing = _validate_required_llm_fields(self.llm_setting)
        if not ok:
            missing_str = " and ".join(missing) if len(missing) > 1 else missing[0]
            return False, f"fail, {missing_str} is required"
        if not self.kb_ids:
            return False, "fail, Bot unbound knowledge base."
        return True, "success"
