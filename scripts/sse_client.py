import json
import requests
from typing import Optional, Dict, Any, Iterator


def parse_sse_message(raw_data: str) -> Optional[Dict[str, Any]]:
    trimmed = raw_data.strip()

    if not trimmed:
        return None

    if trimmed == '[DONE]':
        return {'event': 'done', 'data': {}, 'is_legacy': True}

    try:
        parsed = json.loads(trimmed)

        if isinstance(parsed, dict) and 'event' in parsed and 'data' in parsed:
            event = parsed.get('event')
            if event in ('delta', 'final', 'error', 'done'):
                return {'event': event, 'data': parsed.get('data', {}), 'is_legacy': False}

        if isinstance(parsed, dict):
            code = parsed.get('code')
            msg = parsed.get('msg')
            if code and code != 200 and msg:
                return {'event': 'error', 'data': {'code': code, 'msg': msg}, 'is_legacy': True}

            time_record = parsed.get('time_record') or {}
            has_time_usage = bool(time_record and time_record.get('time_usage'))
            is_delta_shape = (
                parsed.get('code') == 200
                and parsed.get('msg') == 'success'
                and 'response' in parsed
            )

            if is_delta_shape and not has_time_usage:
                return {
                    'event': 'delta',
                    'data': {
                        'response': parsed.get('response'),
                        'time_record': parsed.get('time_record'),
                    },
                    'is_legacy': True,
                }

            if 'response' in parsed or has_time_usage:
                return {
                    'event': 'final',
                    'data': {
                        'response': parsed.get('response', ''),
                        'question': parsed.get('question'),
                        'model': parsed.get('model'),
                        'history': parsed.get('history'),
                        'condense_question': parsed.get('condense_question'),
                        'source_documents': parsed.get('source_documents'),
                        'retrieval_documents': parsed.get('retrieval_documents'),
                        'time_record': parsed.get('time_record'),
                        'show_images': parsed.get('show_images'),
                    },
                    'is_legacy': True,
                }

        return None
    except (ValueError, TypeError) as e:
        print(f'SSE message parse error: {e}, raw: {raw_data}')
        return None


def stream_chat_request(url: str, data: Dict[str, Any], timeout: int = 60) -> Iterator[Dict[str, Any]]:
    response = requests.post(url, json=data, timeout=timeout, stream=True)
    for line in response.iter_lines(decode_unicode=False, delimiter=b'\n\n'):
        if line:
            chunk_str = line.decode('utf-8')
            if chunk_str.startswith('data: '):
                chunk_str = chunk_str[6:]
            parsed = parse_sse_message(chunk_str)
            if parsed:
                yield parsed
