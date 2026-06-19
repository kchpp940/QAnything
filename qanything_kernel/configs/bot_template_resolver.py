import json
import copy
from typing import Any, Dict, Optional, Tuple

from qanything_kernel.configs.scene_templates import (
    SCENE_TEMPLATES,
    NO_TEMPLATE_DEFAULTS,
    TEMPLATE_OVERRIDABLE_FIELDS,
    ALL_TEMPLATE_IDS,
    ANSWER_STYLES,
    SCENE_TEMPLATE_SCHEMA_VERSION,
)


def parse_user_overrides(user_overrides_raw: Any) -> Dict[str, Any]:
    if user_overrides_raw is None or user_overrides_raw == '':
        return {}
    if isinstance(user_overrides_raw, dict):
        return user_overrides_raw
    if isinstance(user_overrides_raw, str):
        try:
            parsed = json.loads(user_overrides_raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def get_template_defaults(template_id: Optional[str]) -> Dict[str, Any]:
    if template_id and template_id in SCENE_TEMPLATES:
        return copy.deepcopy(SCENE_TEMPLATES[template_id]['defaults'])
    return copy.deepcopy(NO_TEMPLATE_DEFAULTS)


def validate_user_overrides(
    user_overrides: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Validate user overrides.
    Returns (cleaned_overrides, errors) tuple.
    """
    cleaned: Dict[str, Any] = {}
    errors: Dict[str, Any] = {}

    for field in TEMPLATE_OVERRIDABLE_FIELDS:
        if field not in user_overrides:
            continue
        value = user_overrides[field]
        if field in ('prompt_setting', 'welcome_message', 'answer_style'):
            if value is None:
                cleaned[field] = ''
            else:
                cleaned[field] = str(value)
            if field == 'answer_style' and cleaned[field] and cleaned[field] not in ANSWER_STYLES:
                errors[field] = f'invalid answer_style: {cleaned[field]}'
                del cleaned[field]
        elif field in ('top_K',):
            try:
                ival = int(value)
                cleaned[field] = max(1, min(ival, 100))
            except (TypeError, ValueError):
                errors[field] = f'invalid top_K: {value}'
        elif field in ('temperature', 'top_P'):
            try:
                fval = float(value)
                cleaned[field] = max(0.0, min(fval, 2.0))
            except (TypeError, ValueError):
                errors[field] = f'invalid {field}: {value}'
        elif field in ('rerank', 'networking', 'hybrid_search', 'only_need_search_results'):
            if isinstance(value, str):
                cleaned[field] = value.lower() in ('true', '1', 'yes', 'on')
            else:
                cleaned[field] = bool(value)
    return cleaned, errors


def compute_user_overrides(
    template_id: Optional[str],
    current_values: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute diff between current_values and template defaults.
    Only fields that differ are kept as overrides.
    """
    defaults = get_template_defaults(template_id)
    overrides: Dict[str, Any] = {}
    for field in TEMPLATE_OVERRIDABLE_FIELDS:
        if field not in current_values:
            continue
        cur_val = current_values[field]
        def_val = defaults.get(field)
        if cur_val != def_val:
            overrides[field] = cur_val
    return overrides


def resolve_bot_values(
    template_id: Optional[str],
    user_overrides_raw: Any,
) -> Dict[str, Any]:
    """
    Core resolver: merge template_defaults + validated user_overrides.
    Always returns ALL overridable fields with concrete values.
    """
    defaults = get_template_defaults(template_id)
    parsed_overrides = parse_user_overrides(user_overrides_raw)
    cleaned_overrides, _ = validate_user_overrides(parsed_overrides)
    merged = copy.deepcopy(defaults)
    for field, value in cleaned_overrides.items():
        merged[field] = value
    return merged


def compute_overridden_fields(
    template_id: Optional[str],
    user_overrides_raw: Any,
) -> list:
    """
    Compute which fields are explicitly overridden by the user (not equal to template defaults).
    """
    parsed_overrides = parse_user_overrides(user_overrides_raw)
    cleaned_overrides, _ = validate_user_overrides(parsed_overrides)
    defaults = get_template_defaults(template_id)
    overridden: list = []
    for field in TEMPLATE_OVERRIDABLE_FIELDS:
        if field in cleaned_overrides:
            if cleaned_overrides[field] != defaults.get(field):
                overridden.append(field)
    return overridden


def is_valid_template_id(template_id: Optional[str]) -> bool:
    return template_id in ALL_TEMPLATE_IDS


def new_bot_build_persist_values(
    template_id: Optional[str],
    user_provided_overrides: Dict[str, Any],
    existing_raw_prompt: Optional[str] = None,
    existing_raw_welcome: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    For new_bot: Given template_id + user-provided overrides, compute:
      - merged_values: concrete values to actually use
      - cleaned_overrides: validated overrides to persist in DB
      - resolved_prompt_welcome: extracted prompt/welcome for legacy columns
    """
    if template_id and not is_valid_template_id(template_id):
        raise ValueError(f'invalid template_id: {template_id}')

    defaults = get_template_defaults(template_id)
    parsed_override = {}
    if isinstance(user_provided_overrides, str):
        parsed_override = parse_user_overrides(user_provided_overrides)
    elif isinstance(user_provided_overrides, dict):
        parsed_override = user_provided_overrides

    if existing_raw_prompt is not None and 'prompt_setting' not in parsed_override:
        if existing_raw_prompt != defaults.get('prompt_setting', ''):
            parsed_override['prompt_setting'] = existing_raw_prompt
    if existing_raw_welcome is not None and 'welcome_message' not in parsed_override:
        if existing_raw_welcome != defaults.get('welcome_message', ''):
            parsed_override['welcome_message'] = existing_raw_welcome

    cleaned_overrides, _errors = validate_user_overrides(parsed_override)
    overrides_to_persist = compute_user_overrides(template_id, cleaned_overrides)

    merged = copy.deepcopy(defaults)
    for field, value in cleaned_overrides.items():
        merged[field] = value

    resolved_prompt_welcome = {
        'prompt_setting': merged.get('prompt_setting', ''),
        'welcome_message': merged.get('welcome_message', ''),
    }

    return merged, overrides_to_persist, resolved_prompt_welcome


def update_bot_build_persist_values(
    old_template_id: Optional[str],
    new_template_id: Optional[str],
    user_provided_overrides: Any,
    old_merged_values: Optional[Dict[str, Any]] = None,
    raw_field_updates: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    For update_bot: rebuilds overrides when template changes (migrate custom overrides),
    or when user submits field-level overrides.
    """
    if new_template_id and not is_valid_template_id(new_template_id):
        raise ValueError(f'invalid template_id: {new_template_id}')

    new_defaults = get_template_defaults(new_template_id)
    parsed = parse_user_overrides(user_provided_overrides)

    explicit_overrides: Dict[str, Any] = {}
    if isinstance(raw_field_updates, dict):
        for field in TEMPLATE_OVERRIDABLE_FIELDS:
            if field in raw_field_updates and raw_field_updates[field] is not None:
                explicit_overrides[field] = raw_field_updates[field]
    if isinstance(parsed, dict):
        for field in TEMPLATE_OVERRIDABLE_FIELDS:
            if field in parsed:
                explicit_overrides[field] = parsed[field]

    if old_merged_values and old_template_id != new_template_id:
        old_defaults = get_template_defaults(old_template_id)
        for field in TEMPLATE_OVERRIDABLE_FIELDS:
            if field in explicit_overrides:
                continue
            old_val = old_merged_values.get(field)
            old_def = old_defaults.get(field)
            if old_val is not None and old_val != old_def:
                explicit_overrides[field] = old_val

    cleaned, _ = validate_user_overrides(explicit_overrides)
    overrides_to_persist = compute_user_overrides(new_template_id, cleaned)

    merged = copy.deepcopy(new_defaults)
    for field, value in cleaned.items():
        merged[field] = value

    resolved_prompt_welcome = {
        'prompt_setting': merged.get('prompt_setting', ''),
        'welcome_message': merged.get('welcome_message', ''),
    }

    return merged, overrides_to_persist, resolved_prompt_welcome


def build_llm_setting_with_answer_style(
    existing_llm_setting_str: Any,
    answer_style: Optional[str],
) -> str:
    """
    Re-encode llm_setting JSON, adding (or preserving) answer_style.
    """
    if existing_llm_setting_str:
        if isinstance(existing_llm_setting_str, str):
            try:
                llm = json.loads(existing_llm_setting_str)
            except (json.JSONDecodeError, ValueError):
                llm = {}
        elif isinstance(existing_llm_setting_str, dict):
            llm = dict(existing_llm_setting_str)
        else:
            llm = {}
    else:
        llm = {}
    if answer_style is not None:
        llm['answer_style'] = answer_style
    return json.dumps(llm, ensure_ascii=False)


def get_schema_version() -> str:
    return SCENE_TEMPLATE_SCHEMA_VERSION
