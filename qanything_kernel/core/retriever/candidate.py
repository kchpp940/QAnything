from dataclasses import dataclass, field
from typing import List, Dict, Optional
from langchain.schema import Document
import time


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

    def to_trace_candidate(self) -> dict:
        return {
            'doc_id': self.doc_id,
            'file_id': self.file_id,
            'file_name': self.file_name,
            'retrieval_source': self.retrieval_source,
            'retrieval_query': self.retrieval_query,
            'embed_version': self.embed_version,
            'stage': self.stage,
            'is_filtered': self.is_filtered,
            'filter_reasons': list(self.filter_reasons),
            'scores': dict(self.scores),
            'current_score': self.current_score,
            'content': self.page_content,
            'metadata': {
                'file_url': self.document.metadata.get('file_url', ''),
                'nos_keys': self.document.metadata.get('nos_keys', ''),
                'headers': self.document.metadata.get('headers', {}),
                'page_id': self.document.metadata.get('page_id', 0),
            }
        }

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


@dataclass
class RetrievalTrace:
    retrieval_candidates: List[dict] = field(default_factory=list)
    rerank_candidates: List[dict] = field(default_factory=list)
    filter_candidates: List[dict] = field(default_factory=list)
    selected_candidates: List[dict] = field(default_factory=list)
    diagnostics: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: time.time())

    def set_stage_candidates(self, stage: str, candidates: List['CandidateDocument']):
        stage_map = {
            'retrieval': 'retrieval_candidates',
            'rerank': 'rerank_candidates',
            'filter': 'filter_candidates',
            'selected': 'selected_candidates'
        }
        attr = stage_map.get(stage)
        if attr:
            snapshot = [c.to_trace_candidate() for c in candidates]
            setattr(self, attr, snapshot)

    def set_diagnostics(self, diagnostics: Dict):
        self.diagnostics = dict(diagnostics)

    def to_dict(self) -> dict:
        return {
            'retrieval_candidates': list(self.retrieval_candidates),
            'rerank_candidates': list(self.rerank_candidates),
            'filter_candidates': list(self.filter_candidates),
            'selected_candidates': list(self.selected_candidates),
            'diagnostics': dict(self.diagnostics),
            'created_at': self.created_at
        }

    def get_stage_snapshot(self, stage: str) -> List[dict]:
        stage_map = {
            'retrieval': self.retrieval_candidates,
            'rerank': self.rerank_candidates,
            'filter': self.filter_candidates,
            'selected': self.selected_candidates
        }
        return list(stage_map.get(stage, []))

    def get_active_by_stage(self, stage: str) -> List[dict]:
        return [c for c in self.get_stage_snapshot(stage) if not c.get('is_filtered', False)]


class RetrievalDiagnosis:
    STAGE_ORDER = ['retrieval', 'rerank', 'filter', 'selected']

    @classmethod
    def from_retrieval_trace(cls, retrieval_trace, user_id: str = '', kb_ids: List[str] = None,
                             query: str = '', qa_id: str = '') -> dict:
        trace_dict = retrieval_trace.to_dict() if hasattr(retrieval_trace, 'to_dict') else dict(retrieval_trace)
        diagnosis = trace_dict.get('diagnostics', {})

        stage_stats = {}
        for stage in cls.STAGE_ORDER:
            key = f'{stage}_candidates'
            candidates = trace_dict.get(key, [])
            total = len(candidates)
            active = len([c for c in candidates if not c.get('is_filtered', False)])
            filtered = total - active
            scores = [c.get('current_score', 0.0) for c in candidates]
            sources = {}
            for c in candidates:
                src = c.get('retrieval_source') or 'unknown'
                sources[src] = sources.get(src, 0) + 1
            filter_reason_counts = {}
            for c in candidates:
                if c.get('is_filtered'):
                    for r in c.get('filter_reasons', []):
                        filter_reason_counts[r] = filter_reason_counts.get(r, 0) + 1

            stage_stats[stage] = {
                'total_count': total,
                'active_count': active,
                'filtered_count': filtered,
                'avg_score': round(sum(scores) / len(scores), 4) if scores else 0.0,
                'max_score': round(max(scores), 4) if scores else 0.0,
                'min_score': round(min(scores), 4) if scores else 0.0,
                'source_distribution': sources,
                'filter_reason_counts': filter_reason_counts,
            }

        diagnosis_record = {
            'qa_id': qa_id,
            'user_id': user_id,
            'kb_ids': kb_ids or [],
            'query': query,
            'stage_stats': stage_stats,
            'diagnostics': diagnosis,
            'created_at': trace_dict.get('created_at', time.time())
        }
        return diagnosis_record
