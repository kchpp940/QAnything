from dataclasses import dataclass, field
from typing import List, Dict, Optional
from langchain.schema import Document


class RetrievalSource:
    MILVUS = 'milvus'
    ES = 'es'
    WEB = 'web'


class CandidateStage:
    RETRIEVED = 'retrieved'
    RERANKED = 'reranked'
    FILTERED = 'filtered'
    SELECTED = 'selected'


@dataclass
class CandidateDocument:
    document: Document
    retrieval_source: str = ''
    retrieval_query: str = ''
    scores: Dict[str, float] = field(default_factory=dict)
    stage: str = CandidateStage.RETRIEVED
    filter_reasons: List[str] = field(default_factory=list)
    embed_version: str = ''
    is_filtered: bool = False

    @property
    def current_score(self) -> float:
        for key in ('rerank', 'embed', 'web_rank', 'cosine_fallback'):
            if key in self.scores:
                return self.scores[key]
        return 0.0

    @property
    def file_id(self) -> str:
        return self.document.metadata.get('file_id', '')

    @property
    def file_name(self) -> str:
        return self.document.metadata.get('file_name', '')

    @property
    def doc_id(self) -> str:
        return self.document.metadata.get('doc_id', '')

    @property
    def page_content(self) -> str:
        return self.document.page_content

    @page_content.setter
    def page_content(self, value: str):
        self.document.page_content = value

    @property
    def metadata(self) -> dict:
        return self.document.metadata

    def mark_filtered(self, reason: str):
        self.is_filtered = True
        self.stage = CandidateStage.FILTERED
        if reason not in self.filter_reasons:
            self.filter_reasons.append(reason)

    def update_score(self, score_type: str, score: float):
        self.scores[score_type] = score

    def to_source_dict(self) -> dict:
        return {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'content': self.page_content,
            'retrieval_query': self.retrieval_query,
            'file_url': self.document.metadata.get('file_url', ''),
            'score': str(self.current_score),
            'embed_version': self.embed_version,
            'nos_keys': self.document.metadata.get('nos_keys', ''),
            'doc_id': self.doc_id,
            'retrieval_source': self.retrieval_source,
            'headers': self.document.metadata.get('headers', {}),
            'page_id': self.document.metadata.get('page_id', 0),
        }

    @classmethod
    def from_document(cls, doc: Document, retrieval_source: str = '',
                      retrieval_query: str = '', embed_version: str = '',
                      score: Optional[float] = None, score_type: str = 'embed') -> 'CandidateDocument':
        scores = {}
        if score is not None:
            scores[score_type] = score
        elif 'score' in doc.metadata:
            scores[score_type] = doc.metadata['score']
        return cls(
            document=doc,
            retrieval_source=retrieval_source,
            retrieval_query=retrieval_query,
            scores=scores,
            embed_version=embed_version,
        )


@dataclass
class RetrievalStageResult:
    stage_name: str
    candidates: List[CandidateDocument]
    elapsed_time: float = 0.0
    metadata: Dict = field(default_factory=dict)

    @property
    def active_candidates(self) -> List[CandidateDocument]:
        return [c for c in self.candidates if not c.is_filtered]

    @property
    def filtered_candidates(self) -> List[CandidateDocument]:
        return [c for c in self.candidates if c.is_filtered]

    def get_documents(self) -> List[Document]:
        return [c.document for c in self.active_candidates]
