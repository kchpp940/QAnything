import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from qanything_kernel.utils.general_utils import format_source_documents as _format_source_documents, format_time_record as _format_time_record

logger = logging.getLogger(__name__)


class BaseSerializer:
    """基础序列化器，提供通用的序列化和字段处理能力"""

    fields: List[str] = []
    defaults: Dict[str, Any] = {}
    json_fields: List[str] = []

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        """
        序列化数据，统一字段格式
        :param data: 原始数据，可以是 dict 或对象
        :param kwargs: 额外的字段值
        :return: 序列化后的字典
        """
        result = {}

        if isinstance(data, dict):
            raw_data = data
        else:
            raw_data = cls._object_to_dict(data)

        for field in cls.fields:
            value = kwargs.get(field, raw_data.get(field))
            result[field] = cls._process_field(field, value, raw_data, **kwargs)

        return result

    @classmethod
    def _object_to_dict(cls, obj: Any) -> Dict[str, Any]:
        """将对象转换为字典"""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return {}

    @classmethod
    def _process_field(cls, field: str, value: Any, raw_data: Dict[str, Any], **kwargs) -> Any:
        """处理单个字段，应用默认值、JSON 解析等"""
        if value is None:
            value = cls.defaults.get(field)

        if field in cls.json_fields and isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse JSON field {field}: {value}")
                value = cls.defaults.get(field, {})

        if hasattr(cls, f'_process_{field}'):
            processor = getattr(cls, f'_process_{field}')
            value = processor(value, raw_data, **kwargs)

        return value

    @classmethod
    def serialize_list(cls, items: List[Any], **kwargs) -> List[Dict[str, Any]]:
        """序列化列表数据"""
        return [cls.serialize(item, **kwargs) for item in items]


class SourceDocumentSerializer(BaseSerializer):
    """来源文档序列化器，统一 source_documents 和 retrieval_documents 格式"""

    fields = [
        'file_id', 'file_name', 'content', 'score', 'file_url',
        'retrieval_query', 'embed_version', 'doc_id', 'retrieval_source',
        'headers', 'page_id', 'nos_keys', 'detail_data_source'
    ]

    defaults = {
        'file_id': '',
        'file_name': '',
        'content': '',
        'score': '0',
        'file_url': '',
        'retrieval_query': '',
        'embed_version': '',
        'doc_id': '',
        'retrieval_source': '',
        'headers': {},
        'page_id': 0,
        'nos_keys': '',
        'detail_data_source': ''
    }

    @classmethod
    def _process_score(cls, value: Any, raw_data: Dict[str, Any], **kwargs) -> str:
        """确保 score 是字符串格式"""
        return str(value) if value is not None else cls.defaults['score']

    @classmethod
    def _process_headers(cls, value: Any, raw_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """确保 headers 是字典格式"""
        if isinstance(value, dict):
            return value
        return cls.defaults['headers']


class TimeRecordSerializer(BaseSerializer):
    """时间记录序列化器，统一 time_record 格式"""

    fields = ['time_usage', 'token_usage']

    defaults = {
        'time_usage': {
            'preprocess': 0,
            'condense_q_chain': 0,
            'retriever_search': 0,
            'web_search': 0,
            'rerank': 0,
            'reprocess': 0,
            'llm_first_return': 0,
            'first_return': 0,
            'llm_completed': 0,
            'chat_completed': 0,
            'obtain_images_time': 0,
            'rollback_length': 0,
            'tokens_per_second': 0
        },
        'token_usage': {
            'total_tokens': 0,
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'rewrite_prompt_tokens': 0,
            'rewrite_completion_tokens': 0
        }
    }

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        """
        序列化时间记录，接受原始 time_record dict 或已格式化的 dict
        """
        if data is None:
            return {
                'time_usage': cls.defaults['time_usage'].copy(),
                'token_usage': cls.defaults['token_usage'].copy()
            }

        if isinstance(data, dict) and 'time_usage' in data and 'token_usage' in data:
            formatted = data
        else:
            formatted = _format_time_record(data)

        time_usage = formatted.get('time_usage', {})
        token_usage = formatted.get('token_usage', {})

        merged_time_usage = cls.defaults['time_usage'].copy()
        merged_time_usage.update({k: round(v, 2) if isinstance(v, (int, float)) else v
                                  for k, v in time_usage.items()})

        merged_token_usage = cls.defaults['token_usage'].copy()
        merged_token_usage.update({k: round(v) if isinstance(v, (int, float)) else v
                                    for k, v in token_usage.items()})

        return {
            'time_usage': merged_time_usage,
            'token_usage': merged_token_usage
        }


class LLMSettingSerializer(BaseSerializer):
    """LLM 配置序列化器，统一 llm_setting 格式"""

    fields = [
        'model', 'api_base', 'api_key', 'api_context_length',
        'max_token', 'temperature', 'top_p', 'top_k',
        'chunk_size', 'rerank', 'hybrid_search', 'networking',
        'only_need_search_results', 'prompt_template'
    ]

    defaults = {
        'model': 'gpt-4o-mini',
        'api_base': '',
        'api_key': '',
        'api_context_length': 4096,
        'max_token': 1024,
        'temperature': 0.5,
        'top_p': 0.99,
        'top_k': 8,
        'chunk_size': 500,
        'rerank': True,
        'hybrid_search': False,
        'networking': False,
        'only_need_search_results': False,
        'prompt_template': ''
    }

    json_fields = []

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        """
        序列化 LLM 配置，接受 JSON 字符串或 dict
        """
        if data is None:
            return cls.defaults.copy()

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse LLM setting JSON: {data}")
                return cls.defaults.copy()

        if not isinstance(data, dict):
            return cls.defaults.copy()

        field_mapping = {
            'apiModelName': 'model',
            'apiBase': 'api_base',
            'apiKey': 'api_key',
            'apiContextLength': 'api_context_length',
            'maxToken': 'max_token',
            'top_P': 'top_p',
            'top_K': 'top_k',
            'chunkSize': 'chunk_size',
            'networkSearch': 'networking',
            'mixedSearch': 'hybrid_search',
            'onlySearch': 'only_need_search_results',
        }

        normalized = {}
        for key, value in data.items():
            normalized_key = field_mapping.get(key, key)
            if normalized_key in cls.fields:
                normalized[normalized_key] = value

        result = cls.defaults.copy()
        for key, value in normalized.items():
            if value is not None:
                if key == 'temperature' and isinstance(value, (int, float)):
                    if value == 1.0:
                        value = 0.99
                result[key] = value

        return result


class RetrievalTraceSerializer(BaseSerializer):
    """检索追踪序列化器"""

    fields = [
        'query', 'retrieval_method', 'total_results',
        'filtered_results', 'stage', 'timestamp'
    ]

    defaults = {
        'query': '',
        'retrieval_method': '',
        'total_results': 0,
        'filtered_results': 0,
        'stage': '',
        'timestamp': ''
    }


class WebSearchTraceSerializer(BaseSerializer):
    """联网搜索追踪序列化器"""

    fields = [
        'query', 'search_engine', 'result_count',
        'selected_urls', 'timestamp'
    ]

    defaults = {
        'query': '',
        'search_engine': '',
        'result_count': 0,
        'selected_urls': [],
        'timestamp': ''
    }


class ChatResponseSerializer(BaseSerializer):
    """聊天响应序列化器，统一流式和非流式聊天响应格式"""

    fields = [
        'code', 'msg', 'question', 'response', 'model',
        'history', 'condense_question', 'source_documents',
        'retrieval_documents', 'time_record', 'llm_setting',
        'retrieval_trace', 'web_search_trace', 'show_images',
        'bot_id', 'qa_id', 'timestamp'
    ]

    defaults = {
        'code': 200,
        'msg': 'success',
        'question': '',
        'response': '',
        'model': '',
        'history': [],
        'condense_question': '',
        'source_documents': [],
        'retrieval_documents': [],
        'time_record': TimeRecordSerializer.defaults,
        'llm_setting': LLMSettingSerializer.defaults,
        'retrieval_trace': [],
        'web_search_trace': [],
        'show_images': [],
        'bot_id': '',
        'qa_id': '',
        'timestamp': ''
    }

    json_fields = ['history', 'source_documents', 'retrieval_documents',
                   'retrieval_trace', 'web_search_trace', 'show_images']

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        """
        序列化聊天响应，支持流式和非流式
        """
        if isinstance(data, dict):
            raw_data = data
        else:
            raw_data = cls._object_to_dict(data)

        result = {}

        for field in cls.fields:
            value = kwargs.get(field, raw_data.get(field))
            if value is None:
                value = cls.defaults.get(field)

            if field == 'source_documents' and value:
                if isinstance(value, list) and len(value) > 0 and not isinstance(value[0], dict):
                    value = _format_source_documents(value)
                value = SourceDocumentSerializer.serialize_list(value)

            elif field == 'retrieval_documents' and value:
                if isinstance(value, list) and len(value) > 0 and not isinstance(value[0], dict):
                    value = _format_source_documents(value)
                value = SourceDocumentSerializer.serialize_list(value)

            elif field == 'time_record':
                value = TimeRecordSerializer.serialize(value)

            elif field == 'llm_setting':
                value = LLMSettingSerializer.serialize(value)

            elif field == 'retrieval_trace':
                if isinstance(value, list) and value:
                    value = RetrievalTraceSerializer.serialize_list(value)

            elif field == 'web_search_trace':
                if isinstance(value, list) and value:
                    value = WebSearchTraceSerializer.serialize_list(value)

            elif field == 'timestamp':
                if not value:
                    value = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            result[field] = value

        return result


class BotInfoSerializer(BaseSerializer):
    """Bot 信息序列化器"""

    fields = [
        'bot_id', 'bot_name', 'description', 'head_image',
        'prompt_setting', 'welcome_message', 'kb_ids',
        'kb_names', 'update_time', 'llm_setting', 'user_id'
    ]

    defaults = {
        'bot_id': '',
        'bot_name': '',
        'description': '',
        'head_image': '',
        'prompt_setting': '',
        'welcome_message': '',
        'kb_ids': [],
        'kb_names': [],
        'update_time': '',
        'llm_setting': LLMSettingSerializer.defaults,
        'user_id': ''
    }

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        """
        序列化 Bot 信息，从数据库 tuple 或 dict 转换
        """
        if data is None:
            return cls.defaults.copy()

        if isinstance(data, tuple):
            raw_dict = {
                'bot_id': data[0] if len(data) > 0 else '',
                'user_id': data[8] if len(data) > 8 else kwargs.get('user_id', ''),
                'bot_name': data[1] if len(data) > 1 else '',
                'description': data[2] if len(data) > 2 else '',
                'head_image': data[3] if len(data) > 3 else '',
                'prompt_setting': data[4] if len(data) > 4 else '',
                'welcome_message': data[5] if len(data) > 5 else '',
                'kb_ids_str': data[6] if len(data) > 6 else '',
                'update_time': data[7].strftime('%Y-%m-%d %H:%M:%S') if len(data) > 7 and hasattr(data[7], 'strftime') else '',
                'llm_setting_str': data[9] if len(data) > 9 else '{}'
            }
        elif isinstance(data, dict):
            raw_dict = data
        else:
            raw_dict = cls._object_to_dict(data)

        result = cls.defaults.copy()
        kb_ids_str = raw_dict.get('kb_ids_str', '')
        if kb_ids_str and isinstance(kb_ids_str, str):
            result['kb_ids'] = [kid for kid in kb_ids_str.split(',') if kid]
        elif 'kb_ids' in raw_dict and isinstance(raw_dict['kb_ids'], list):
            result['kb_ids'] = raw_dict['kb_ids']

        llm_setting_str = raw_dict.get('llm_setting_str', '{}')
        result['llm_setting'] = LLMSettingSerializer.serialize(llm_setting_str)

        for field in ['bot_id', 'bot_name', 'description', 'head_image',
                      'prompt_setting', 'welcome_message', 'update_time', 'user_id']:
            if field in raw_dict and raw_dict[field] is not None:
                result[field] = raw_dict[field]

        if 'kb_names' in raw_dict and isinstance(raw_dict['kb_names'], list):
            result['kb_names'] = raw_dict['kb_names']

        if 'update_time' in raw_dict and hasattr(raw_dict['update_time'], 'strftime'):
            result['update_time'] = raw_dict['update_time'].strftime('%Y-%m-%d %H:%M:%S')

        return result


class KnowledgeFileSerializer(BaseSerializer):
    """知识库文件序列化器"""

    fields = [
        'file_id', 'file_name', 'status', 'bytes', 'content_length',
        'timestamp', 'file_location', 'file_url', 'chunks_number',
        'msg', 'question', 'answer', 'estimated_chars'
    ]

    defaults = {
        'file_id': '',
        'file_name': '',
        'status': 'gray',
        'bytes': 0,
        'content_length': 0,
        'timestamp': '',
        'file_location': '',
        'file_url': '',
        'chunks_number': 0,
        'msg': '',
        'question': '',
        'answer': '',
        'estimated_chars': 0
    }

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        """
        序列化文件信息，从数据库 tuple 或 dict 转换
        """
        if data is None:
            return cls.defaults.copy()

        if isinstance(data, tuple):
            raw_dict = {
                'file_id': data[0] if len(data) > 0 else '',
                'file_name': data[1] if len(data) > 1 else '',
                'status': data[2] if len(data) > 2 else 'gray',
                'bytes': data[3] if len(data) > 3 else 0,
                'content_length': data[4] if len(data) > 4 else 0,
                'timestamp': data[5] if len(data) > 5 else '',
                'file_location': data[6] if len(data) > 6 else '',
                'file_url': data[7] if len(data) > 7 else '',
                'chunks_number': data[8] if len(data) > 8 else 0,
                'msg': data[9] if len(data) > 9 else ''
            }
        elif isinstance(data, dict):
            raw_dict = data
        else:
            raw_dict = cls._object_to_dict(data)

        result = cls.defaults.copy()
        for field in cls.fields:
            if field in raw_dict and raw_dict[field] is not None:
                result[field] = raw_dict[field]

        return result


class QARecordSerializer(BaseSerializer):
    """历史 QA 记录序列化器"""

    fields = [
        'qa_id', 'user_id', 'bot_id', 'kb_ids', 'query', 'model',
        'product_source', 'time_record', 'history', 'condense_question',
        'prompt', 'result', 'retrieval_documents', 'source_documents',
        'timestamp', 'retrieval_trace', 'web_search_trace', 'kb_names'
    ]

    defaults = {
        'qa_id': '',
        'user_id': '',
        'bot_id': '',
        'kb_ids': [],
        'query': '',
        'model': '',
        'product_source': '',
        'time_record': TimeRecordSerializer.defaults,
        'history': [],
        'condense_question': '',
        'prompt': '',
        'result': '',
        'retrieval_documents': [],
        'source_documents': [],
        'timestamp': '',
        'retrieval_trace': [],
        'web_search_trace': [],
        'kb_names': ''
    }

    json_fields = ['kb_ids', 'time_record', 'history',
                   'retrieval_documents', 'source_documents']

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        """
        序列化 QA 记录，从数据库 dict 转换
        """
        if data is None:
            return cls.defaults.copy()

        if isinstance(data, dict):
            raw_data = data
        else:
            raw_data = cls._object_to_dict(data)

        result = cls.defaults.copy()

        for field in cls.fields:
            value = kwargs.get(field, raw_data.get(field))
            if value is None:
                continue

            if field == 'time_record':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = {}
                value = TimeRecordSerializer.serialize(value)

            elif field == 'source_documents':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if isinstance(value, list):
                    value = SourceDocumentSerializer.serialize_list(value)

            elif field == 'retrieval_documents':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if isinstance(value, list):
                    value = SourceDocumentSerializer.serialize_list(value)

            elif field in ['kb_ids', 'history']:
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = cls.defaults[field]

            elif field == 'timestamp':
                if hasattr(value, 'strftime'):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')

            elif field == 'retrieval_trace':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if not isinstance(value, list):
                    value = []

            elif field == 'web_search_trace':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if not isinstance(value, list):
                    value = []

            result[field] = value

        return result


class DiagnosisRecordSerializer(BaseSerializer):
    """诊断记录序列化器，用于 get_related_qa 接口返回的单条 qa_info 和关联 section 中的 log"""

    fields = [
        'qa_id', 'user_id', 'bot_id', 'kb_ids', 'query', 'model',
        'product_source', 'time_record', 'history', 'condense_question',
        'prompt', 'result', 'retrieval_documents', 'source_documents',
        'timestamp', 'retrieval_trace', 'web_search_trace', 'kb_names'
    ]

    defaults = {
        'qa_id': '',
        'user_id': '',
        'bot_id': '',
        'kb_ids': [],
        'query': '',
        'model': '',
        'product_source': '',
        'time_record': TimeRecordSerializer.defaults,
        'history': [],
        'condense_question': '',
        'prompt': '',
        'result': '',
        'retrieval_documents': [],
        'source_documents': [],
        'timestamp': '',
        'retrieval_trace': [],
        'web_search_trace': [],
        'kb_names': ''
    }

    json_fields = ['kb_ids', 'time_record', 'history',
                   'retrieval_documents', 'source_documents']

    @classmethod
    def serialize(cls, data: Any, **kwargs) -> Dict[str, Any]:
        if data is None:
            return cls.defaults.copy()

        if isinstance(data, dict):
            raw_data = data
        else:
            raw_data = cls._object_to_dict(data)

        result = cls.defaults.copy()

        for field in cls.fields:
            value = kwargs.get(field, raw_data.get(field))
            if value is None:
                continue

            if field == 'time_record':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = {}
                value = TimeRecordSerializer.serialize(value)

            elif field == 'source_documents':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if isinstance(value, list):
                    value = SourceDocumentSerializer.serialize_list(value)

            elif field == 'retrieval_documents':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if isinstance(value, list):
                    value = SourceDocumentSerializer.serialize_list(value)

            elif field in ['kb_ids', 'history']:
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = cls.defaults[field]

            elif field == 'timestamp':
                if hasattr(value, 'strftime'):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')

            elif field == 'retrieval_trace':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if not isinstance(value, list):
                    value = []

            elif field == 'web_search_trace':
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        value = []
                if not isinstance(value, list):
                    value = []

            result[field] = value

        return result


class PaginatedResponseSerializer(BaseSerializer):
    """分页响应序列化器"""

    fields = ['total', 'total_page', 'page_id', 'page_limit', 'status_count', 'details']

    defaults = {
        'total': 0,
        'total_page': 0,
        'page_id': 1,
        'page_limit': 10,
        'status_count': {},
        'details': []
    }

    @classmethod
    def serialize(cls, data: Any, item_serializer: Optional[BaseSerializer] = None, **kwargs) -> Dict[str, Any]:
        """
        序列化分页响应
        :param data: 原始数据
        :param item_serializer: 列表项的序列化器类
        :param kwargs: 额外参数
        """
        if isinstance(data, dict):
            raw_data = data
        else:
            raw_data = cls._object_to_dict(data)

        result = {}
        for field in cls.fields:
            value = kwargs.get(field, raw_data.get(field, cls.defaults[field]))
            result[field] = value if value is not None else cls.defaults[field]

        if item_serializer and isinstance(result['details'], list):
            result['details'] = item_serializer.serialize_list(result['details'])

        return result


class ApiResponseSerializer:
    """统一 API 响应包装器"""

    @staticmethod
    def success(data: Any = None, msg: str = 'success', code: int = 200, **kwargs) -> Dict[str, Any]:
        """成功响应"""
        response = {
            'code': code,
            'msg': msg,
            'data': data if data is not None else kwargs
        }
        return response

    @staticmethod
    def error(msg: str, code: int = 2001, **kwargs) -> Dict[str, Any]:
        """错误响应"""
        response = {
            'code': code,
            'msg': msg
        }
        if kwargs:
            response.update(kwargs)
        return response
