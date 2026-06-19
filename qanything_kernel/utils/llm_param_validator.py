import json
import os
from typing import Dict, List, Tuple, Any, Optional

_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'shared_configs', 'llm_param_schema.json')
_SCHEMA_CACHE: Optional[Dict[str, Any]] = None


def _load_schema() -> Dict[str, Any]:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        with open(_SCHEMA_PATH, 'r', encoding='utf-8') as f:
            _SCHEMA_CACHE = json.load(f)
    return _SCHEMA_CACHE


def _coerce_bool(value: Any) -> Tuple[Any, Optional[str]]:
    if isinstance(value, bool):
        return value, None
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ('true', '1', 'yes', 'on'):
            return True, None
        if low in ('false', '0', 'no', 'off', ''):
            return False, None
        return None, f"cannot cast string '{value}' to bool"
    if isinstance(value, (int, float)):
        if value == 1:
            return True, None
        if value == 0:
            return False, None
    return None, f"cannot cast type '{type(value).__name__}' to bool"


def _coerce_int(value: Any) -> Tuple[Any, Optional[str]]:
    if isinstance(value, bool):
        return None, f"bool cannot be cast to int"
    if isinstance(value, int):
        return value, None
    if isinstance(value, float):
        if value.is_integer():
            return int(value), None
        return None, f"float '{value}' is not integral, cannot cast to int"
    if isinstance(value, str):
        s = value.strip()
        try:
            return int(s), None
        except ValueError:
            return None, f"cannot cast string '{value}' to int"
    return None, f"cannot cast type '{type(value).__name__}' to int"


def _coerce_float(value: Any) -> Tuple[Any, Optional[str]]:
    if isinstance(value, bool):
        return None, f"bool cannot be cast to float"
    if isinstance(value, (int, float)):
        return float(value), None
    if isinstance(value, str):
        s = value.strip()
        try:
            return float(s), None
        except ValueError:
            return None, f"cannot cast string '{value}' to float"
    return None, f"cannot cast type '{type(value).__name__}' to float"


def _coerce_str(value: Any) -> Tuple[Any, Optional[str]]:
    if isinstance(value, str):
        return value, None
    return None, f"expected str, got type '{type(value).__name__}'"


_COERCERS = {
    'bool': _coerce_bool,
    'int': _coerce_int,
    'float': _coerce_float,
    'str': _coerce_str,
}


def _validate_range(name: str, value: Any, field_schema: Dict[str, Any]) -> Optional[str]:
    if field_schema.get('type') in ('int', 'float') and value is not None:
        fmin = field_schema.get('min')
        fmax = field_schema.get('max')
        if fmin is not None and value < fmin:
            return f"{name}={value} is less than min={fmin}"
        if fmax is not None and value > fmax:
            return f"{name}={value} is greater than max={fmax}"
    return None


def _run_post_process(setting: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    schema = _load_schema()
    pp = schema.get('post_process', {})
    for rule_name, rule in pp.items():
        if not rule.get('enabled'):
            continue
        if 'top_p' in rule_name and 'top_p' in setting:
            current = setting['top_p']
            if current is not None and current == rule.get('from'):
                setting['top_p'] = rule.get('to')
                warnings.append(f"post_process {rule_name}: top_p corrected from {rule.get('from')} to {rule.get('to')}")
    return warnings


def process_bot_llm_setting(setting: Optional[Dict[str, Any]], lenient: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    if setting is None:
        setting = {}
    if not isinstance(setting, dict):
        if lenient:
            setting = {}
        else:
            return {}, ["llm_setting must be a dict/object"]

    schema = _load_schema()
    fields = schema.get('fields', {})
    result: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []

    for field_name, field_schema in fields.items():
        ftype = field_schema.get('type')
        coercer = _COERCERS.get(ftype)
        if coercer is None:
            errors.append(f"unsupported type '{ftype}' for field '{field_name}'")
            continue

        allow_null = field_schema.get('allow_null', False)
        fill_default = field_schema.get('fill_default_for_bot', False)
        default_value = field_schema.get('default', None)

        if field_name not in setting or setting[field_name] is None:
            if allow_null and field_name in setting and setting[field_name] is None:
                result[field_name] = None
            elif fill_default:
                result[field_name] = default_value
            elif allow_null:
                result[field_name] = None
            continue

        raw = setting[field_name]
        casted, cast_err = coercer(raw)
        if cast_err is not None:
            if lenient and fill_default:
                warnings.append(f"field '{field_name}': {cast_err}; falling back to default={default_value}")
                result[field_name] = default_value
                continue
            errors.append(f"field '{field_name}': {cast_err}")
            continue
        if casted is None and not allow_null:
            if lenient and fill_default:
                warnings.append(f"field '{field_name}': null not allowed; falling back to default={default_value}")
                result[field_name] = default_value
                continue
            errors.append(f"field '{field_name}': null value is not allowed")
            continue

        result[field_name] = casted

    for key in setting.keys():
        if key not in fields:
            result[key] = setting[key]

    if not errors:
        _run_post_process(result)
        for field_name, field_schema in fields.items():
            if field_name not in result:
                continue
            val = result[field_name]
            if val is None:
                continue
            range_err = _validate_range(field_name, val, field_schema)
            if range_err is not None:
                if lenient and field_schema.get('fill_default_for_bot', False):
                    default_value = field_schema.get('default', None)
                    warnings.append(f"{range_err}; falling back to default={default_value}")
                    result[field_name] = default_value
                else:
                    errors.append(range_err)

    if lenient:
        for w in warnings:
            errors.append(w)

    return result, errors


def process_chat_request_llm_setting(setting: Optional[Dict[str, Any]], lenient: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    if setting is None:
        setting = {}
    if not isinstance(setting, dict):
        if lenient:
            setting = {}
        else:
            return {}, ["llm_setting must be a dict/object"]

    schema = _load_schema()
    fields = schema.get('fields', {})
    result: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []

    for field_name, field_schema in fields.items():
        ftype = field_schema.get('type')
        coercer = _COERCERS.get(ftype)
        if coercer is None:
            continue

        allow_null = field_schema.get('allow_null', False)
        required = field_schema.get('required_for_request', False)
        default_value = field_schema.get('default', None)

        if field_name not in setting or setting[field_name] is None:
            if required and (field_name not in setting or setting[field_name] is None):
                if default_value is not None or (allow_null and default_value is None):
                    result[field_name] = default_value
                    continue
                if lenient:
                    warnings.append(f"field '{field_name}' is required; falling back to default={default_value}")
                    result[field_name] = default_value
                    continue
                errors.append(f"field '{field_name}' is required")
            elif allow_null and field_name in setting and setting[field_name] is None:
                result[field_name] = None
            continue

        raw = setting[field_name]
        casted, cast_err = coercer(raw)
        if cast_err is not None:
            if lenient and default_value is not None:
                warnings.append(f"field '{field_name}': {cast_err}; falling back to default={default_value}")
                result[field_name] = default_value
                continue
            errors.append(f"field '{field_name}': {cast_err}")
            continue
        if casted is None and not allow_null:
            if lenient and default_value is not None:
                warnings.append(f"field '{field_name}': null not allowed; falling back to default={default_value}")
                result[field_name] = default_value
                continue
            errors.append(f"field '{field_name}': null value is not allowed")
            continue

        result[field_name] = casted

    for key in setting.keys():
        if key not in fields:
            result[key] = setting[key]

    if not errors:
        _run_post_process(result)
        for field_name, field_schema in fields.items():
            if field_name not in result:
                continue
            val = result[field_name]
            if val is None:
                continue
            range_err = _validate_range(field_name, val, field_schema)
            if range_err is not None:
                default_value = field_schema.get('default', None)
                if lenient and default_value is not None:
                    warnings.append(f"{range_err}; falling back to default={default_value}")
                    result[field_name] = default_value
                else:
                    errors.append(range_err)

    if lenient:
        for w in warnings:
            errors.append(w)

    return result, errors


def normalize_llm_setting(setting: Optional[Dict[str, Any]], lenient: bool = True) -> Tuple[Dict[str, Any], List[str]]:
    if setting is None:
        return {}, []
    if not isinstance(setting, dict):
        if lenient:
            setting = {}
        else:
            return {}, []

    schema = _load_schema()
    fields = schema.get('fields', {})
    result = dict(setting)
    errors: List[str] = []
    warnings: List[str] = []

    for field_name, field_schema in fields.items():
        if field_name not in result:
            continue
        ftype = field_schema.get('type')
        coercer = _COERCERS.get(ftype)
        if coercer is None:
            continue
        allow_null = field_schema.get('allow_null', False)
        default_value = field_schema.get('default', None)
        if result[field_name] is None:
            continue
        casted, cast_err = coercer(result[field_name])
        if cast_err is not None:
            if lenient and field_schema.get('fill_default_for_bot', False):
                warnings.append(f"field '{field_name}': {cast_err}; falling back to default={default_value}")
                result[field_name] = default_value
                continue
            errors.append(f"field '{field_name}': {cast_err}")
            continue
        if casted is None and not allow_null:
            if lenient and field_schema.get('fill_default_for_bot', False):
                warnings.append(f"field '{field_name}': null not allowed; falling back to default={default_value}")
                result[field_name] = default_value
                continue
            continue
        result[field_name] = casted

    if not errors:
        _run_post_process(result)
        for field_name, field_schema in fields.items():
            if field_name not in result:
                continue
            val = result[field_name]
            if val is None:
                continue
            range_err = _validate_range(field_name, val, field_schema)
            if range_err is not None:
                default_value = field_schema.get('default', None)
                if lenient and field_schema.get('fill_default_for_bot', False):
                    warnings.append(f"{range_err}; falling back to default={default_value}")
                    result[field_name] = default_value
                else:
                    errors.append(range_err)

    if lenient:
        for w in warnings:
            errors.append(w)

    return result, errors
