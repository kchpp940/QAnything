from typing import List, Dict
import time


class RetrievalDiagnosisSerializer:
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
            stage_stats[stage] = cls._compute_stage_stats(candidates)

        return {
            'qa_id': qa_id,
            'user_id': user_id,
            'kb_ids': kb_ids or [],
            'query': query,
            'stage_stats': stage_stats,
            'diagnostics': diagnosis,
            'created_at': trace_dict.get('created_at', time.time())
        }

    @classmethod
    def _compute_stage_stats(cls, candidates: list) -> dict:
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
        return {
            'total_count': total,
            'active_count': active,
            'filtered_count': filtered,
            'avg_score': round(sum(scores) / len(scores), 4) if scores else 0.0,
            'max_score': round(max(scores), 4) if scores else 0.0,
            'min_score': round(min(scores), 4) if scores else 0.0,
            'source_distribution': sources,
            'filter_reason_counts': filter_reason_counts,
        }
