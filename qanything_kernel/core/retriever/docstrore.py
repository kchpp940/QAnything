from qanything_kernel.utils.custom_log import insert_logger
from qanything_kernel.connector.database.mysql.mysql_client import KnowledgeBaseManager
from qanything_kernel.configs.model_config import UPLOAD_ROOT_PATH
from qanything_kernel.utils.custom_log import debug_logger
from qanything_kernel.utils.general_utils import normalize_document_metadata
from langchain_core.documents import Document
from langchain.storage import InMemoryStore
from typing import (
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar
)
import os
import json
import asyncio
from tqdm import tqdm


V = TypeVar("V")


def _build_doc_from_json(doc_id: str, doc_json: dict, mysql_client: KnowledgeBaseManager,
                         idx: int = 0, total: int = 1) -> Optional[Document]:
    if doc_json is None:
        return None
    user_id = doc_json['kwargs']['metadata'].get('user_id', '')
    file_id = doc_json['kwargs']['metadata'].get('file_id', '')
    file_name = doc_json['kwargs']['metadata'].get('file_name', '')
    kb_id = doc_json['kwargs']['metadata'].get('kb_id', '')
    doc_idx = doc_id.split('_')[-1] if '_' in doc_id else '0'
    upload_path = os.path.join(UPLOAD_ROOT_PATH, user_id)
    if file_id and file_name and kb_id:
        local_path = os.path.join(upload_path, kb_id, file_id, file_name.rsplit('.', 1)[0] + '_' + doc_idx + '.json')
        if not os.path.exists(local_path):
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'w') as f:
                f.write(json.dumps(doc_json, ensure_ascii=False))
    doc = Document(page_content=doc_json['kwargs']['page_content'], metadata=doc_json['kwargs']['metadata'])
    doc.metadata['doc_id'] = doc_id
    if file_name.endswith('.faq'):
        faq_dict = doc.metadata.get('faq_dict', {})
        if faq_dict:
            page_content = f"{faq_dict.get('question', '')}：{faq_dict.get('answer', '')}"
            nos_keys = faq_dict.get('nos_keys')
            doc.page_content = page_content
            doc.metadata['nos_keys'] = nos_keys
            if 'retrieval_source' not in doc.metadata:
                doc.metadata['retrieval_source'] = 'faq'
    normalize_document_metadata(doc, idx_for_fallback=idx, total_docs=total, default_kb_id=kb_id)
    return doc


class MysqlStore(InMemoryStore):
    def __init__(self, mysql_client: KnowledgeBaseManager):
        self.mysql_client = mysql_client
        super().__init__()

    def mset(self, key_value_pairs: Sequence[Tuple[str, V]]) -> None:
        doc_ids = [doc_id for doc_id, _ in key_value_pairs]
        insert_logger.info(f"add documents: {len(doc_ids)}")
        for doc_id, doc in tqdm(key_value_pairs):
            doc_json = doc.to_json()
            if doc_json['kwargs'].get('metadata') is None:
                doc_json['kwargs']['metadata'] = doc.metadata
            self.mysql_client.add_document(doc_id, doc_json)

    async def amset(self, key_value_pairs: Sequence[Tuple[str, V]]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.mset, key_value_pairs)

    def mget(self, keys: Sequence[str]) -> List[Optional[V]]:
        total = len(keys)
        docs = []
        for idx, doc_id in enumerate(keys):
            doc_json = self.mysql_client.get_document_by_doc_id(doc_id)
            doc = _build_doc_from_json(doc_id, doc_json, self.mysql_client, idx=idx, total=total)
            docs.append(doc)
        return docs

    async def amget(self, keys: Sequence[str]) -> List[Optional[V]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.mget, keys)
