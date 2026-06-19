SCENE_TEMPLATE_SCHEMA_VERSION = '1.0.0'

ANSWER_STYLES = {'concise', 'detailed', 'technical', 'strict_citation'}

TEMPLATE_OVERRIDABLE_FIELDS = [
    'prompt_setting',
    'welcome_message',
    'top_K',
    'rerank',
    'networking',
    'hybrid_search',
    'only_need_search_results',
    'temperature',
    'top_P',
    'answer_style',
]

SCENE_TEMPLATES = {
    'customer_service': {
        'name': '客服问答',
        'name_en': 'Customer Service',
        'description': '适用于客服场景，回答简洁、准确，优先检索已有问答对，强调服务礼仪',
        'description_en': 'For customer service scenarios. Concise, accurate answers with service etiquette.',
        'icon': '🧑‍💼',
        'defaults': {
            'prompt_setting': '你是一位专业的客服代表，请根据知识库内容准确、简洁地回答用户问题。回答时请注意：1. 保持礼貌和耐心；2. 优先引用知识库中的标准答案；3. 如遇不确定的问题，建议用户联系人工客服；4. 回答尽量简短，不超过3句话。',
            'welcome_message': '您好！欢迎使用智能客服，请问有什么可以帮助您的？',
            'top_K': 5,
            'rerank': True,
            'networking': False,
            'hybrid_search': False,
            'only_need_search_results': False,
            'temperature': 0.3,
            'top_P': 0.85,
            'answer_style': 'concise',
        },
    },
    'enterprise_knowledge': {
        'name': '企业知识助手',
        'name_en': 'Enterprise Knowledge Assistant',
        'description': '适用于企业内部知识查询，回答详尽、专业，结合多个知识源给出综合回答',
        'description_en': 'For enterprise knowledge queries. Detailed, professional answers combining multiple sources.',
        'icon': '🏢',
        'defaults': {
            'prompt_setting': '你是一位企业知识助手，请根据知识库内容全面、专业地回答用户问题。回答时请注意：1. 尽可能详尽地回答问题，引用相关资料；2. 对复杂问题进行条理清晰的分点说明；3. 如知识库中存在多个相关文档，综合整理后给出回答；4. 标注信息来源便于用户追溯。',
            'welcome_message': '您好！我是企业知识助手，可以帮您查询公司内部资料和知识库内容，请输入您的问题。',
            'top_K': 10,
            'rerank': True,
            'networking': False,
            'hybrid_search': True,
            'only_need_search_results': False,
            'temperature': 0.5,
            'top_P': 0.9,
            'answer_style': 'detailed',
        },
    },
    'code_doc_assistant': {
        'name': '代码文档助手',
        'name_en': 'Code Documentation Assistant',
        'description': '适用于代码和API文档查询，提供精确的技术说明和代码示例',
        'description_en': 'For code and API documentation queries. Precise technical explanations with code examples.',
        'icon': '💻',
        'defaults': {
            'prompt_setting': '你是一位代码文档助手，请根据知识库中的技术文档准确回答问题。回答时请注意：1. 提供准确的代码示例和使用方法；2. 说明API参数、返回值和注意事项；3. 如有版本差异需特别说明；4. 使用代码块格式展示代码片段；5. 如文档中未找到相关内容，明确告知用户。',
            'welcome_message': '您好！我是代码文档助手，可以帮您查询API文档和技术资料，请描述您的问题。',
            'top_K': 8,
            'rerank': True,
            'networking': False,
            'hybrid_search': True,
            'only_need_search_results': False,
            'temperature': 0.2,
            'top_P': 0.8,
            'answer_style': 'technical',
        },
    },
    'strict_citation': {
        'name': '严谨引用模式',
        'name_en': 'Strict Citation Mode',
        'description': '适用于需要严格引用来源的场景，所有回答必须标注出处，不编造信息',
        'description_en': 'For scenarios requiring strict citation. All answers must reference sources, no fabrication.',
        'icon': '📋',
        'defaults': {
            'prompt_setting': '你是一位严谨的知识问答助手。回答规则：1. 所有回答必须基于知识库中的内容，不得编造信息；2. 每个论点必须标注来源文档名称或段落；3. 如知识库中无相关内容，必须明确回答"根据现有知识库未找到相关信息"，不得推测；4. 区分事实陈述与推理，推理部分需标注"根据以上信息推断"；5. 引用原文时使用引号标注。',
            'welcome_message': '您好！我将在严格引用模式下为您服务，所有回答均会标注信息来源，确保信息可追溯。',
            'top_K': 15,
            'rerank': True,
            'networking': False,
            'hybrid_search': True,
            'only_need_search_results': False,
            'temperature': 0.1,
            'top_P': 0.7,
            'answer_style': 'strict_citation',
        },
    },
}

NO_TEMPLATE_DEFAULTS = {
    'prompt_setting': '',
    'welcome_message': '',
    'top_K': 8,
    'rerank': True,
    'networking': False,
    'hybrid_search': False,
    'only_need_search_results': False,
    'temperature': 0.7,
    'top_P': 0.9,
    'answer_style': '',
}

ALL_TEMPLATE_IDS = set(SCENE_TEMPLATES.keys())


def get_template_meta(template_id, is_zh=True):
    if not template_id or template_id not in SCENE_TEMPLATES:
        return None
    tpl = SCENE_TEMPLATES[template_id]
    return {
        'id': template_id,
        'name': tpl['name'] if is_zh else tpl['name_en'],
        'description': tpl['description'] if is_zh else tpl['description_en'],
        'icon': tpl['icon'],
    }


def list_templates(is_zh=True):
    return [
        {
            'id': tid,
            'name': SCENE_TEMPLATES[tid]['name'] if is_zh else SCENE_TEMPLATES[tid]['name_en'],
            'description': SCENE_TEMPLATES[tid]['description'] if is_zh else SCENE_TEMPLATES[tid]['description_en'],
            'icon': SCENE_TEMPLATES[tid]['icon'],
        }
        for tid in SCENE_TEMPLATES
    ]
