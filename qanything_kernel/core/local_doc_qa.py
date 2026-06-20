from qanything_kernel.configs.model_config import VECTOR_SEARCH_TOP_K, VECTOR_SEARCH_SCORE_THRESHOLD, \
    PROMPT_TEMPLATE, STREAMING, SYSTEM, INSTRUCTIONS, SIMPLE_PROMPT_TEMPLATE, CUSTOM_PROMPT_TEMPLATE, \
    LOCAL_RERANK_MODEL_NAME, LOCAL_EMBED_MAX_LENGTH, SEPARATORS
from typing import List, Tuple, Union, Dict
import time
from scipy.spatial import cKDTree
from scipy.spatial.distance import cosine
from scipy.stats import gmean
from qanything_kernel.connector.embedding.embedding_for_online_client import YouDaoEmbeddings
from qanything_kernel.connector.rerank.rerank_for_online_client import YouDaoRerank
from qanything_kernel.connector.llm import OpenAILLM
from langchain.schema import Document
from langchain.schema.messages import AIMessage, HumanMessage
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from qanything_kernel.connector.database.mysql.mysql_client import KnowledgeBaseManager
from qanything_kernel.core.retriever.vectorstore import VectorStoreMilvusClient
from qanything_kernel.core.retriever.elasticsearchstore import StoreElasticSearchClient
from qanything_kernel.core.retriever.parent_retriever import ParentRetriever
from qanything_kernel.core.retriever.candidate import CandidateDocument, RetrievalStageResult, RetrievalSource, CandidateStage
from qanything_kernel.utils.general_utils import (get_time, clear_string, get_time_async, num_tokens,
                                                  cosine_similarity, clear_string_is_equal, num_tokens_embed,
                                                  num_tokens_rerank, deduplicate_documents, replace_image_references)
from qanything_kernel.utils.custom_log import debug_logger, qa_logger, rerank_logger
from qanything_kernel.core.chains.condense_q_chain import RewriteQuestionChain
from qanything_kernel.core.tools.web_search_tool import duckduckgo_search
import copy
import requests
import json
import numpy as np
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import traceback
import re


class LocalDocQA:
    def __init__(self, port):
        self.port = port
        self.milvus_cache = None
        self.embeddings: YouDaoEmbeddings = None
        self.rerank: YouDaoRerank = None
        self.chunk_conent: bool = True
        self.score_threshold: int = VECTOR_SEARCH_SCORE_THRESHOLD
        self.milvus_kb: VectorStoreMilvusClient = None
        self.retriever: ParentRetriever = None
        self.milvus_summary: KnowledgeBaseManager = None
        self.es_client: StoreElasticSearchClient = None
        self.session = self.create_retry_session(retries=3, backoff_factor=1)
        self.doc_splitter = CharacterTextSplitter(
            chunk_size=LOCAL_EMBED_MAX_LENGTH / 2,
            chunk_overlap=0,
            length_function=len
        )

    @staticmethod
    def create_retry_session(retries, backoff_factor):
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def init_cfg(self, args=None):
        self.embeddings = YouDaoEmbeddings()
        self.rerank = YouDaoRerank()
        self.milvus_summary = KnowledgeBaseManager()
        self.milvus_kb = VectorStoreMilvusClient()
        self.es_client = StoreElasticSearchClient()
        self.retriever = ParentRetriever(self.milvus_kb, self.milvus_summary, self.es_client)

    @get_time
    def get_web_search(self, queries, top_k):
        query = queries[0]
        web_content, web_documents = duckduckgo_search(query, top_k)
        candidates = []
        for idx, doc in enumerate(web_documents):
            if 'title' not in doc.metadata:
                continue
            file_name = re.sub(r'[\uFF01-\uFF5E\u3000-\u303F]', '', doc.metadata['title'])
            doc.metadata['file_name'] = file_name + '.web'
            doc.metadata['file_url'] = doc.metadata['source']
            doc.metadata['embed_version'] = self.embeddings.embed_version
            doc.metadata['score'] = 1 - (idx / len(web_documents))
            doc.metadata['file_id'] = 'websearch' + str(idx)
            doc.metadata['headers'] = {"新闻标题": file_name}
            score = 1 - (idx / len(web_documents))
            candidate = CandidateDocument(
                document=doc,
                retrieval_source=RetrievalSource.WEB,
                retrieval_query=query,
                scores={'web_rank': score},
                embed_version=self.embeddings.embed_version,
            )
            if 'description' in doc.metadata:
                desc_doc = Document(page_content=doc.metadata['description'], metadata=doc.metadata)
                desc_candidate = CandidateDocument(
                    document=desc_doc,
                    retrieval_source=RetrievalSource.WEB,
                    retrieval_query=query,
                    scores={'web_rank': score},
                    embed_version=self.embeddings.embed_version,
                )
                candidates.append(desc_candidate)
            candidates.append(candidate)
        return web_content, candidates

    def web_page_search(self, query, top_k=None):
        try:
            web_content, candidates = self.get_web_search([query], top_k)
        except Exception as e:
            debug_logger.error(f"web search error: {traceback.format_exc()}")
            return []

        return candidates

    @get_time_async
    async def _retrieve_candidates(self, query, retriever: ParentRetriever, kb_ids, time_record, hybrid_search, top_k):
        start_time = time.perf_counter()
        candidates = await retriever.get_retrieved_documents(query, partition_keys=kb_ids, time_record=time_record,
                                                             hybrid_search=hybrid_search, top_k=top_k)
        if len(candidates) == 0:
            debug_logger.warning("MILVUS SEARCH ERROR, RESTARTING MILVUS CLIENT!")
            retriever.vectorstore_client = VectorStoreMilvusClient()
            debug_logger.warning("MILVUS CLIENT RESTARTED!")
            candidates = await retriever.get_retrieved_documents(query, partition_keys=kb_ids, time_record=time_record,
                                                                  hybrid_search=hybrid_search, top_k=top_k)
        end_time = time.perf_counter()
        time_record['retriever_search'] = round(end_time - start_time, 2)
        debug_logger.info(f"retriever_search time: {time_record['retriever_search']}s")

        for idx, candidate in enumerate(candidates):
            candidate.retrieval_query = query
            candidate.embed_version = self.embeddings.embed_version
            if not candidate.scores:
                candidate.update_score('embed', 1 - (idx / len(candidates)))
            if retriever.mysql_client.is_deleted_file(candidate.file_id):
                debug_logger.warning(f"file_id: {candidate.file_id} is deleted")
                candidate.mark_filtered('file_deleted')

        debug_logger.info(f"embed scores: {[c.current_score for c in candidates if not c.is_filtered]}")

        return RetrievalStageResult(
            stage_name='retrieval',
            candidates=candidates,
            elapsed_time=time_record.get('retriever_search', 0.0)
        )

    def _select_by_token_limit(self, custom_llm: OpenAILLM, query: str,
                               candidates: List[CandidateDocument],
                               history: List[str],
                               prompt_template: str) -> Tuple[List[CandidateDocument], int, str]:
        query_token_num = int(custom_llm.num_tokens_from_messages([query]) * 4)
        history_token_num = int(custom_llm.num_tokens_from_messages([x for sublist in history for x in sublist]))
        template_token_num = int(custom_llm.num_tokens_from_messages([prompt_template]))

        reference_field_token_num = int(custom_llm.num_tokens_from_messages(
            [f"<reference>[{idx + 1}]</reference>" for idx in range(len(candidates))]))
        limited_token_nums = custom_llm.token_window - custom_llm.max_token - custom_llm.offcut_token - query_token_num - history_token_num - template_token_num - reference_field_token_num

        debug_logger.info(f"=============================================")
        debug_logger.info(f"token_window = {custom_llm.token_window}")
        debug_logger.info(f"max_token = {custom_llm.max_token}")
        debug_logger.info(f"offcut_token = {custom_llm.offcut_token}")
        debug_logger.info(f"limited token nums: {limited_token_nums}")
        debug_logger.info(f"template token nums: {template_token_num}")
        debug_logger.info(f"reference_field token nums: {reference_field_token_num}")
        debug_logger.info(f"query token nums: {query_token_num}")
        debug_logger.info(f"history token nums: {history_token_num}")
        debug_logger.info(f"=============================================")

        tokens_msg = """
        token_window = {custom_llm.token_window}, max_token = {custom_llm.max_token},       
        offcut_token = {custom_llm.offcut_token}, docs_available_token_nums: {limited_token_nums}, 
        template token nums: {template_token_num}, reference_field token nums: {reference_field_token_num}, 
        query token nums: {query_token_num}, history token nums: {history_token_num}
        docs_available_token_nums = token_window - max_token - offcut_token - query_token_num * 4 - history_token_num - template_token_num - reference_field_token_num
        """.format(custom_llm=custom_llm, limited_token_nums=limited_token_nums, template_token_num=template_token_num,
                     reference_field_token_num=reference_field_token_num, query_token_num=query_token_num // 4,
                     history_token_num=history_token_num)

        new_candidates = []
        total_token_num = 0

        not_repeated_file_ids = []
        for candidate in candidates:
            headers_token_num = 0
            file_id = candidate.file_id
            if file_id not in not_repeated_file_ids:
                not_repeated_file_ids.append(file_id)
                if 'headers' in candidate.metadata:
                    headers = f"headers={candidate.metadata['headers']}"
                    headers_token_num = custom_llm.num_tokens_from_messages([headers])
            doc_valid_content = re.sub(r'!\[figure]\(.*?\)', '', candidate.page_content)
            doc_token_num = custom_llm.num_tokens_from_messages([doc_valid_content])
            doc_token_num += headers_token_num
            if total_token_num + doc_token_num <= limited_token_nums:
                new_candidates.append(candidate)
                total_token_num += doc_token_num
            else:
                candidate.mark_filtered('token_limit_exceeded')

        debug_logger.info(f"new_candidates token nums: {custom_llm.num_tokens_from_docs([c.document for c in new_candidates])}")
        return new_candidates, limited_token_nums, tokens_msg

    def generate_prompt(self, query, candidates: List[CandidateDocument], prompt_template):
        if candidates:
            context = ''
            not_repeated_file_ids = []
            for candidate in candidates:
                doc_valid_content = re.sub(r'!\[figure]\(.*?\)', '', candidate.page_content)
                file_id = candidate.file_id
                if file_id not in not_repeated_file_ids:
                    if len(not_repeated_file_ids) != 0:
                        context += '</reference>\n'
                    not_repeated_file_ids.append(file_id)
                    if 'headers' in candidate.metadata:
                        headers = f"headers={candidate.metadata['headers']}"
                        context += f"<reference {headers}>[{len(not_repeated_file_ids)}]" + '\n' + doc_valid_content + '\n'
                    else:
                        context += f"<reference>[{len(not_repeated_file_ids)}]" + '\n' + doc_valid_content + '\n'
                else:
                    context += doc_valid_content + '\n'
            context += '</reference>\n'

            prompt = prompt_template.replace("{{context}}", context).replace("{{question}}", query)
        else:
            prompt = prompt_template.replace("{{question}}", query)
        return prompt

    async def _rerank_candidates(self, candidates: List[CandidateDocument], query: str,
                                 time_record: dict, use_rerank: bool) -> RetrievalStageResult:
        active = [c for c in candidates if not c.is_filtered]
        if not use_rerank or len(active) <= 1 or num_tokens_rerank(query) > 300:
            return RetrievalStageResult(stage_name='rerank', candidates=candidates)

        docs = [c.document for c in active]
        try:
            t1 = time.perf_counter()
            debug_logger.info(f"use rerank, rerank docs num: {len(docs)}")
            reranked_docs = await self.rerank.arerank_documents(query, docs)
            t2 = time.perf_counter()
            time_record['rerank'] = round(t2 - t1, 2)

            doc_score_map = {}
            for doc in reranked_docs:
                doc_score_map[id(doc)] = doc.metadata.get('score', 0)

            for candidate in active:
                rerank_score = doc_score_map.get(id(candidate.document))
                if rerank_score is not None:
                    candidate.update_score('rerank', rerank_score)
                    candidate.stage = CandidateStage.RERANKED

            active.sort(key=lambda c: c.scores.get('rerank', 0), reverse=True)

            debug_logger.info(f"rerank step1 num: {len(active)}")
            debug_logger.info(f"rerank step1 scores: {[c.scores.get('rerank', 0) for c in active]}")
        except Exception as e:
            time_record['rerank'] = 0.0
            debug_logger.error(f"query {query}: rerank error: {traceback.format_exc()}")
            try:
                embed1 = await self.embeddings.aembed_query(query)
                for candidate in active:
                    embed2 = await self.embeddings.aembed_query(candidate.page_content)
                    fallback_score = cosine_similarity(embed1, embed2)
                    candidate.update_score('cosine_fallback', fallback_score)
                    candidate.stage = CandidateStage.RERANKED
                active.sort(key=lambda c: c.scores.get('cosine_fallback', 0), reverse=True)
            except Exception as e2:
                debug_logger.error(f"cosine fallback error: {e2}")

        return RetrievalStageResult(
            stage_name='rerank',
            candidates=candidates,
            elapsed_time=time_record.get('rerank', 0.0)
        )

    async def get_rerank_results(self, query, doc_ids=None, doc_strs=None):
        docs = []
        if doc_strs:
            docs = [Document(page_content=doc_str) for doc_str in doc_strs]
        else:
            for doc_id in doc_ids:
                doc_json = self.milvus_summary.get_document_by_doc_id(doc_id)
                if doc_json is None:
                    docs.append(None)
                    continue
                _user_id, _file_id, file_name, _kb_id = doc_json['kwargs']['metadata']['user_id'], \
                    doc_json['kwargs']['metadata']['file_id'], doc_json['kwargs']['metadata']['file_name'], \
                    doc_json['kwargs']['metadata']['kb_id']
                doc = Document(page_content=doc_json['kwargs']['page_content'], metadata=doc_json['kwargs']['metadata'])
                doc.metadata['doc_id'] = doc_id
                doc.metadata['retrieval_query'] = query
                doc.metadata['embed_version'] = self.embeddings.embed_version
                if file_name.endswith('.faq'):
                    faq_dict = doc.metadata['faq_dict']
                    page_content = f"{faq_dict['question']}：{faq_dict['answer']}"
                    nos_keys = faq_dict.get('nos_keys')
                    doc.page_content = page_content
                    doc.metadata['nos_keys'] = nos_keys
                docs.append(doc)

        candidates = [CandidateDocument.from_document(doc, retrieval_query=query,
                         embed_version=self.embeddings.embed_version) for doc in docs if doc is not None]

        if len(candidates) > 1 and num_tokens_rerank(query) <= 300:
            try:
                debug_logger.info(f"use rerank, rerank docs num: {len(candidates)}")
                reranked_docs = await self.rerank.arerank_documents(query, [c.document for c in candidates])
                doc_score_map = {id(doc): doc.metadata.get('score', 0) for doc in reranked_docs}
                for candidate in candidates:
                    rerank_score = doc_score_map.get(id(candidate.document))
                    if rerank_score is not None:
                        candidate.update_score('rerank', rerank_score)
                candidates.sort(key=lambda c: c.scores.get('rerank', 0), reverse=True)
                if len(candidates) > 1:
                    candidates = [c for c in candidates if c.scores.get('rerank', 0) >= 0.28]
                return candidates
            except Exception as e:
                debug_logger.error(f"query tokens: {num_tokens_rerank(query)}, rerank error: {e}")
                embed1 = await self.embeddings.aembed_query(query)
                for candidate in candidates:
                    embed2 = await self.embeddings.aembed_query(candidate.page_content)
                    candidate.update_score('cosine_fallback', cosine_similarity(embed1, embed2))
                return candidates
        else:
            if candidates:
                embed1 = await self.embeddings.aembed_query(query)
                for candidate in candidates:
                    embed2 = await self.embeddings.aembed_query(candidate.page_content)
                    candidate.update_score('cosine_fallback', cosine_similarity(embed1, embed2))
            return candidates

    def _filter_candidates(self, candidates: List[CandidateDocument], top_k: int) -> RetrievalStageResult:
        active = [c for c in candidates if not c.is_filtered]

        if len(active) > 1:
            passing = [c for c in active if c.scores.get('rerank', c.current_score) >= 0.28]
            if passing:
                for c in active:
                    if c not in passing:
                        c.mark_filtered('rerank_score_below_threshold')
                active = passing
            debug_logger.info(f"rerank step2 num: {len(active)}")

        if len(active) > 1:
            top_score = active[0].scores.get('rerank', active[0].current_score)
            saved = [active[0]]
            for c in active[1:]:
                c_score = c.scores.get('rerank', c.current_score)
                relative_diff = (top_score - c_score) / top_score if top_score > 0 else 0
                if relative_diff > 0.5:
                    remaining = active[active.index(c):]
                    for dropped in remaining:
                        dropped.mark_filtered('rerank_score_drop_off')
                    break
                saved.append(c)
            active = saved
            debug_logger.info(f"rerank step3 num: {len(active)}")

        if len(active) > top_k:
            for c in active[top_k:]:
                c.mark_filtered('top_k_truncated')
            active = active[:top_k]

        return RetrievalStageResult(stage_name='filter', candidates=candidates)

    async def _aggregate_candidates(self, custom_llm: OpenAILLM, candidates: List[CandidateDocument],
                                     limited_token_nums: int, use_rerank: bool) -> Tuple[List[CandidateDocument], List[CandidateDocument]]:
        return candidates, candidates
        debug_logger.info(f"retrieval_candidates len: {len(candidates)}")
        try:
            new_docs = self.aggregate_documents(candidates, limited_token_nums, custom_llm, use_rerank)
            if new_docs:
                source_candidates = new_docs
            else:
                merged_documents_file_ids = []
                for candidate in candidates:
                    if candidate.file_id not in merged_documents_file_ids:
                        merged_documents_file_ids.append(candidate.file_id)
                source_candidates = []
                for file_id in merged_documents_file_ids:
                    file_candidates = [c for c in candidates if c.file_id == file_id]
                    file_candidates = sorted(file_candidates, key=lambda x: int(x.doc_id.split('_')[-1]))
                    source_candidates.extend(file_candidates)
        except Exception as e:
            debug_logger.error(f"aggregate_documents error w/ {e}: {traceback.format_exc()}")
            source_candidates = candidates

        debug_logger.info(f"source_candidates len: {len(source_candidates)}")
        return source_candidates, candidates

    async def calculate_relevance_optimized(
            self,
            question: str,
            llm_answer: str,
            reference_candidates: List[CandidateDocument],
            top_k: int = 5
    ) -> List[Dict]:
        reference_docs = [c.document for c in reference_candidates]
        question_scores = [c.current_score for c in reference_candidates]

        # 计算LLM回答的embedding
        llm_answer_embedding = await self.embeddings.aembed_query(llm_answer)

        # 计算所有引用文档分段的embeddings
        all_segments_docs = self.doc_splitter.split_documents(reference_docs)
        all_segments = [doc.page_content for doc in all_segments_docs]
        reference_embeddings = await self.embeddings.aembed_documents(all_segments)

        # 将嵌入向量转换为numpy数组以便使用scipy的cosine函数
        llm_answer_embedding = np.array(llm_answer_embedding)
        reference_embeddings = np.array(reference_embeddings)

        # 构建KD树
        tree = cKDTree(reference_embeddings)

        # 使用KD树找到最相似的分段
        _, indices = tree.query(llm_answer_embedding.reshape(1, -1), k=top_k)
        if isinstance(indices[0], np.int64):
            indices = [indices]

        # 计算每个文档的分段数量，以便根据索引找到对应的文档
        doc_segment_lengths = [len(self.doc_splitter.split_documents([doc])) for doc in reference_docs]

        # 创建一个累积的段落索引，用于根据段落找到文档ID
        cumulative_lengths = np.cumsum([0] + doc_segment_lengths)

        # 定义加权几何平均函数
        def weighted_geometric_mean(scores, weights):
            return gmean([score ** weight for score, weight in zip(scores, weights)])

        # 计算相似度和综合得分
        relevant_docs = []
        for doc_index in indices[0]:
            # 根据doc_index找到对应的文档ID
            doc_id = np.searchsorted(cumulative_lengths, doc_index, side='right') - 1

            # 获取该文档内的实际分段索引
            segment_index_in_doc = doc_index - cumulative_lengths[doc_id]

            # 计算1 - cosine距离来计算相似度
            similarity_llm = 1 - cosine(llm_answer_embedding, reference_embeddings[doc_index])
            rerank_score = question_scores[doc_id]

            # 设置rerank分数和LLM回答与文档余弦相似度的权重
            weights = [0.5, 0.5]  # 分别对应similarity_llm和rerank_score
            combined_score = weighted_geometric_mean([similarity_llm, rerank_score], weights)

            relevant_docs.append({
                'document': reference_docs[doc_id],
                'segment': all_segments_docs[doc_index],
                'similarity_llm': float(similarity_llm),
                'question_score': question_scores[doc_id],
                'combined_score': float(combined_score)
            })

        # 按综合得分降序排序
        relevant_docs.sort(key=lambda x: x['combined_score'], reverse=True)

        return relevant_docs

    @staticmethod
    async def generate_response(query, res, condense_question, source_candidates: List[CandidateDocument],
                                retrieval_candidates: List[CandidateDocument],
                                time_record, chat_history, streaming, prompt):
        history = chat_history + [[query, res]]

        if streaming:
            res = 'data: ' + json.dumps({'answer': res}, ensure_ascii=False)

        response = {
            "query": query,
            "prompt": prompt,
            "result": res,
            "condense_question": condense_question,
            "retrieval_documents": retrieval_candidates,
            "source_documents": source_candidates
        }

        if 'llm_completed' not in time_record:
            time_record['llm_completed'] = 0.0
        if 'total_tokens' not in time_record:
            time_record['total_tokens'] = 0
        if 'prompt_tokens' not in time_record:
            time_record['prompt_tokens'] = 0
        if 'completion_tokens' not in time_record:
            time_record['completion_tokens'] = 0

        # 使用yield返回response和history
        yield response, history

        # 如果是流式输出，发送结束标志
        if streaming:
            response['result'] = "data: [DONE]\n\n"
            yield response, history

    async def get_knowledge_based_answer(self, model, max_token, kb_ids, query, retriever, custom_prompt, time_record,
                                         temperature, api_base, api_key, api_context_length, top_p, top_k, web_chunk_size,
                                         chat_history=None, streaming: bool = STREAMING, rerank: bool = False,
                                         only_need_search_results: bool = False, need_web_search=False,
                                         hybrid_search=False):
        custom_llm = OpenAILLM(model, max_token, api_base, api_key, api_context_length, top_p, temperature)
        if chat_history is None:
            chat_history = []
        retrieval_query = query
        condense_question = query
        if chat_history:
            formatted_chat_history = []
            for msg in chat_history:
                formatted_chat_history += [
                    HumanMessage(content=msg[0]),
                    AIMessage(content=msg[1]),
                ]
            debug_logger.info(f"formatted_chat_history: {formatted_chat_history}")

            rewrite_q_chain = RewriteQuestionChain(model_name=model, openai_api_base=api_base, openai_api_key=api_key)
            full_prompt = rewrite_q_chain.condense_q_prompt.format(
                chat_history=formatted_chat_history,
                question=query
            )
            while custom_llm.num_tokens_from_messages([full_prompt]) >= 4096 - 256:
                formatted_chat_history = formatted_chat_history[2:]
                full_prompt = rewrite_q_chain.condense_q_prompt.format(
                    chat_history=formatted_chat_history,
                    question=query
                )
            debug_logger.info(
                f"Subtract formatted_chat_history: {len(chat_history) * 2} -> {len(formatted_chat_history)}")
            try:
                t1 = time.perf_counter()
                condense_question = await rewrite_q_chain.condense_q_chain.ainvoke(
                    {
                        "chat_history": formatted_chat_history,
                        "question": query,
                    },
                )
                t2 = time.perf_counter()
                time_record['condense_q_chain'] = round(t2 - t1, 2)
                time_record['rewrite_completion_tokens'] = custom_llm.num_tokens_from_messages([condense_question])
                debug_logger.info(f"condense_q_chain time: {time_record['condense_q_chain']}s")
            except Exception as e:
                debug_logger.error(f"condense_q_chain error: {e}")
                condense_question = query
            debug_logger.info(f"condense_question: {condense_question}")
            time_record['rewrite_prompt_tokens'] = custom_llm.num_tokens_from_messages([full_prompt, condense_question])
            if clear_string(condense_question) != clear_string(query):
                retrieval_query = condense_question

        # === Stage 1: Retrieval ===
        if kb_ids:
            retrieval_result = await self._retrieve_candidates(retrieval_query, retriever, kb_ids, time_record,
                                                                hybrid_search, top_k)
            all_candidates = list(retrieval_result.active_candidates)
        else:
            all_candidates = []

        # === Web search integration ===
        if need_web_search:
            t1 = time.perf_counter()
            web_candidates = self.web_page_search(query, top_k=3)
            web_splitter = RecursiveCharacterTextSplitter(
                separators=SEPARATORS,
                chunk_size=web_chunk_size,
                chunk_overlap=int(web_chunk_size / 4),
                length_function=num_tokens_embed,
            )
            if web_candidates:
                web_docs = web_splitter.split_documents([c.document for c in web_candidates])
                new_web_candidates = []
                current_doc_id = 0
                current_file_id = web_docs[0].metadata['file_id'] if web_docs else ''
                for doc in web_docs:
                    if doc.metadata['file_id'] == current_file_id:
                        doc.metadata['doc_id'] = current_file_id + '_' + str(current_doc_id)
                        current_doc_id += 1
                    else:
                        current_file_id = doc.metadata['file_id']
                        current_doc_id = 0
                        doc.metadata['doc_id'] = current_file_id + '_' + str(current_doc_id)
                        current_doc_id += 1
                    doc_json = doc.to_json()
                    if doc_json['kwargs'].get('metadata') is None:
                        doc_json['kwargs']['metadata'] = doc.metadata
                    self.milvus_summary.add_document(doc_id=doc.metadata['doc_id'], json_data=doc_json)
                    web_candidate = CandidateDocument.from_document(
                        doc, retrieval_source=RetrievalSource.WEB,
                        retrieval_query=query, embed_version=self.embeddings.embed_version,
                        score_type='web_rank'
                    )
                    new_web_candidates.append(web_candidate)
                all_candidates.extend(new_web_candidates)
            t2 = time.perf_counter()
            time_record['web_search'] = round(t2 - t1, 2)

        # === Stage 2: Deduplicate ===
        seen_contents = set()
        deduped_candidates = []
        for candidate in all_candidates:
            if candidate.page_content not in seen_contents:
                seen_contents.add(candidate.page_content)
                deduped_candidates.append(candidate)
        all_candidates = deduped_candidates

        # === Stage 3: Rerank ===
        rerank_result = await self._rerank_candidates(all_candidates, condense_question, time_record, rerank)
        all_candidates = rerank_result.candidates

        # === Stage 4: Filter ===
        filter_result = self._filter_candidates(all_candidates, top_k)
        active_candidates = [c for c in filter_result.candidates if not c.is_filtered]

        # Strip headers after rerank
        for candidate in active_candidates:
            candidate.page_content = re.sub(r'^\[headers]\(.*?\)\n', '', candidate.page_content)

        # FAQ high-score handling
        high_score_faq = [c for c in active_candidates
                          if c.file_name.endswith('.faq') and c.current_score >= 0.9]
        if high_score_faq:
            active_candidates = high_score_faq

        # FAQ exact match
        for candidate in active_candidates:
            if candidate.file_name.endswith('.faq') and clear_string_is_equal(
                    candidate.metadata['faq_dict']['question'], query):
                debug_logger.info(f"match faq question: {query}")
                if only_need_search_results:
                    yield active_candidates, None
                    return
                res = candidate.metadata['faq_dict']['answer']
                async for response, history in self.generate_response(query, res, condense_question,
                                                                      active_candidates, active_candidates,
                                                                      time_record, chat_history, streaming, 'MATCH_FAQ'):
                    yield response, history
                return

        # === Prompt and token selection ===
        today = time.strftime("%Y-%m-%d", time.localtime())
        now = time.strftime("%H:%M:%S", time.localtime())

        extra_msg = None
        total_images_number = 0
        retrieval_candidates = []
        if active_candidates:
            if custom_prompt:
                prompt_template = CUSTOM_PROMPT_TEMPLATE.replace("{{custom_prompt}}", custom_prompt)
            else:
                system_prompt = SYSTEM.replace("{{today_date}}", today).replace("{{current_time}}", now)
                prompt_template = PROMPT_TEMPLATE.replace("{{system}}", system_prompt).replace("{{instructions}}",
                                                                                               INSTRUCTIONS)

            t1 = time.perf_counter()
            retrieval_candidates, limited_token_nums, tokens_msg = self._select_by_token_limit(
                custom_llm=custom_llm, query=query,
                candidates=active_candidates,
                history=chat_history,
                prompt_template=prompt_template)

            if len(retrieval_candidates) < len(active_candidates):
                if len(retrieval_candidates) == 0:
                    debug_logger.error(f"limited_token_nums: {limited_token_nums} < {web_chunk_size}!")
                    res = (
                        f"抱歉，由于留给相关文档使用的token数量不足(docs_available_token_nums: {limited_token_nums} < 文本分片大小: {web_chunk_size})，"
                        f"\n无法保证回答质量，请在模型配置中提高【总Token数量】或减少【输出Tokens数量】或减少【上下文消息数量】再继续提问。"
                        f"\n计算方式：{tokens_msg}")
                    async for response, history in self.generate_response(query, res, condense_question,
                                                                          active_candidates, active_candidates,
                                                                          time_record, chat_history, streaming,
                                                                          'TOKENS_NOT_ENOUGH'):
                        yield response, history
                    return

                extra_msg = (
                    f"\n\nWARNING: 由于留给相关文档使用的token数量不足(docs_available_token_nums: {limited_token_nums})，"
                    f"\n检索到的部分文档chunk被裁切，原始来源数量：{len(active_candidates)}，裁切后数量：{len(retrieval_candidates)}，"
                    f"\n可能会影响回答质量，尤其是问题涉及的相关内容较多时。"
                    f"\n可在模型配置中提高【总Token数量】或减少【输出Tokens数量】或减少【上下文消息数量】再继续提问。\n")

            source_candidates, retrieval_candidates = await self._aggregate_candidates(custom_llm,
                                                                                       retrieval_candidates,
                                                                                       limited_token_nums,
                                                                                       rerank)

            for candidate in source_candidates:
                if candidate.metadata.get('images', []):
                    total_images_number += len(candidate.metadata['images'])
                    candidate.page_content = replace_image_references(candidate.page_content, candidate.file_id)
            debug_logger.info(f"total_images_number: {total_images_number}")

            t2 = time.perf_counter()
            time_record['reprocess'] = round(t2 - t1, 2)
        else:
            source_candidates = []
            if custom_prompt:
                prompt_template = SIMPLE_PROMPT_TEMPLATE.replace("{{today}}", today).replace("{{now}}", now).replace(
                    "{{custom_prompt}}", custom_prompt)
            else:
                simple_custom_prompt = """
                - If you cannot answer based on the given information, you will return the sentence \"抱歉，已知的信息不足，因此无法回答。\". 
                """
                prompt_template = SIMPLE_PROMPT_TEMPLATE.replace("{{today}}", today).replace("{{now}}", now).replace(
                    "{{custom_prompt}}", simple_custom_prompt)

        if only_need_search_results:
            yield source_candidates, None
            return

        t1 = time.perf_counter()
        has_first_return = False

        acc_resp = ''
        prompt = self.generate_prompt(query=query,
                                      candidates=source_candidates,
                                      prompt_template=prompt_template)
        est_prompt_tokens = num_tokens(prompt) + num_tokens(str(chat_history))
        async for answer_result in custom_llm.generatorAnswer(prompt=prompt, history=chat_history, streaming=streaming):
            resp = answer_result.llm_output["answer"]
            if 'answer' in resp:
                acc_resp += json.loads(resp[6:])['answer']
            prompt = answer_result.prompt
            history = answer_result.history
            total_tokens = answer_result.total_tokens
            prompt_tokens = answer_result.prompt_tokens
            completion_tokens = answer_result.completion_tokens
            history[-1][0] = query
            response = {"query": query,
                        "prompt": prompt,
                        "result": resp,
                        "condense_question": condense_question,
                        "retrieval_documents": retrieval_candidates,
                        "source_documents": source_candidates}
            time_record['prompt_tokens'] = prompt_tokens if prompt_tokens != 0 else est_prompt_tokens
            time_record['completion_tokens'] = completion_tokens if completion_tokens != 0 else num_tokens(acc_resp)
            time_record['total_tokens'] = total_tokens if total_tokens != 0 else time_record['prompt_tokens'] + \
                                                                                 time_record['completion_tokens']
            if has_first_return is False:
                first_return_time = time.perf_counter()
                has_first_return = True
                time_record['llm_first_return'] = round(first_return_time - t1, 2)
            if resp[6:].startswith("[DONE]"):
                if extra_msg is not None:
                    msg_response = {"query": query,
                                "prompt": prompt,
                                "result": f"data: {json.dumps({'answer': extra_msg}, ensure_ascii=False)}",
                                "condense_question": condense_question,
                                "retrieval_documents": retrieval_candidates,
                                "source_documents": source_candidates}
                    yield msg_response, history
                last_return_time = time.perf_counter()
                time_record['llm_completed'] = round(last_return_time - t1, 2) - time_record['llm_first_return']
                history[-1][1] = acc_resp
                if total_images_number != 0:
                    candidates_with_images = [c for c in source_candidates if c.metadata.get('images', [])]
                    time1 = time.perf_counter()
                    relevant_docs = await self.calculate_relevance_optimized(
                        question=query,
                        llm_answer=acc_resp,
                        reference_candidates=candidates_with_images,
                        top_k=1
                    )
                    show_images = ["\n### 引用图文如下：\n"]
                    for doc in relevant_docs:
                        for image in doc['document'].metadata.get('images', []):
                            image_str = replace_image_references(image, doc['document'].metadata['file_id'])
                            debug_logger.info(f"image_str: {image} -> {image_str}")
                            show_images.append(image_str + '\n')
                    debug_logger.info(f"show_images: {show_images}")
                    time_record['obtain_images'] = round(time.perf_counter() - last_return_time, 2)
                    time2 = time.perf_counter()
                    debug_logger.info(f"obtain_images time: {time2 - time1}s")
                    time_record["obtain_images_time"] = round(time2 - time1, 2)
                    if len(show_images) > 1:
                        response['show_images'] = show_images
            yield response, history

    def get_completed_document(self, file_id, limit=None):
        sorted_json_datas = self.milvus_summary.get_document_by_file_id(file_id)
        if limit:
            sorted_json_datas = sorted_json_datas[limit[0]: limit[1] + 1]

        completed_content_with_figure = ''
        completed_content = ''
        for doc_json in sorted_json_datas:
            doc = Document(page_content=doc_json['kwargs']['page_content'], metadata=doc_json['kwargs']['metadata'])
            # rerank之后删除headers，只保留文本内容，用于后续处理
            doc.page_content = re.sub(r'^\[headers]\(.*?\)\n', '', doc.page_content)
            # if filter_figures:
            #     doc.page_content = re.sub(r'!\[figure]\(.*?\)', '', doc.page_content)  # 删除图片
            if doc_json['kwargs']['metadata']['file_name'].endswith('.faq'):
                faq_dict = doc_json['kwargs']['metadata']['faq_dict']
                doc.page_content = f"{faq_dict['question']}：{faq_dict['answer']}"
            completed_content_with_figure += doc.page_content + '\n\n'
            completed_content += re.sub(r'!\[figure]\(.*?\)', '', doc.page_content) + '\n\n' # 删除图片
        completed_doc_with_figure = Document(page_content=completed_content_with_figure, metadata=sorted_json_datas[0]['kwargs']['metadata'])
        completed_doc = Document(page_content=completed_content, metadata=sorted_json_datas[0]['kwargs']['metadata'])
        # FIX metadata
        has_table = False
        images = []
        for doc_json in sorted_json_datas:
            if doc_json['kwargs']['metadata'].get('has_table'):
                has_table = True
                break
            if doc_json['kwargs']['metadata'].get('images'):
                images.extend(doc_json['kwargs']['metadata']['images'])
        completed_doc.metadata['has_table'] = has_table
        completed_doc.metadata['images'] = images
        completed_doc_with_figure.metadata['has_table'] = has_table
        completed_doc_with_figure.metadata['images'] = images

        # completed_content = ''
        # for doc_json in sorted_json_datas:
        #     doc = Document(page_content=doc_json['kwargs']['page_content'], metadata=doc_json['kwargs']['metadata'])
        #     # rerank之后删除headers，只保留文本内容，用于后续处理
        #     doc.page_content = re.sub(r'^\[headers]\(.*?\)\n', '', doc.page_content)
        #     if filter_figures:
        #         doc.page_content = re.sub(r'!\[figure]\(.*?\)', '', doc.page_content)  # 删除图片
        #     completed_content += doc.page_content + '\n\n'
        # completed_doc = Document(page_content=completed_content, metadata=sorted_json_datas[0]['kwargs']['metadata'])
        return completed_doc, completed_doc_with_figure

    def aggregate_documents(self, source_documents, limited_token_nums, custom_llm, rerank):
        # 聚合文档，具体逻辑是帮我判断所有候选是否集中在一个或两个文件中，是的话直接返回这一个或两个完整文档，如果tokens不够则截取文档中的完整上下文
        first_file_dict = {}
        ori_first_docs = []
        second_file_dict = {}
        ori_second_docs = []
        for doc in source_documents:
            file_id = doc.metadata['file_id']
            if not first_file_dict:
                first_file_dict['file_id'] = file_id
                first_file_dict['doc_ids'] = [int(doc.metadata['doc_id'].split('_')[-1])]
                ori_first_docs.append(doc)
                if rerank:
                    first_file_dict['score'] = max(
                        [doc.metadata['score'] for doc in source_documents if doc.metadata['file_id'] == file_id])
                else:
                    first_file_dict['score'] = min(
                        [doc.metadata['score'] for doc in source_documents if doc.metadata['file_id'] == file_id])
            elif first_file_dict['file_id'] == file_id:
                first_file_dict['doc_ids'].append(int(doc.metadata['doc_id'].split('_')[-1]))
                ori_first_docs.append(doc)
            elif not second_file_dict:
                second_file_dict['file_id'] = file_id
                second_file_dict['doc_ids'] = [int(doc.metadata['doc_id'].split('_')[-1])]
                ori_second_docs.append(doc)
                if rerank:
                    second_file_dict['score'] = max(
                        [doc.metadata['score'] for doc in source_documents if doc.metadata['file_id'] == file_id])
                else:
                    second_file_dict['score'] = min(
                        [doc.metadata['score'] for doc in source_documents if doc.metadata['file_id'] == file_id])
            elif second_file_dict['file_id'] == file_id:
                second_file_dict['doc_ids'].append(int(doc.metadata['doc_id'].split('_')[-1]))
                ori_second_docs.append(doc)
            else:  # 如果有第三个文件，直接返回
                return []

        ori_first_docs_tokens = custom_llm.num_tokens_from_docs(ori_first_docs)
        ori_second_docs_tokens = custom_llm.num_tokens_from_docs(ori_second_docs)

        new_docs = []
        first_completed_doc, first_completed_doc_with_figure = self.get_completed_document(first_file_dict['file_id'])
        first_completed_doc.metadata['score'] = first_file_dict['score']
        first_doc_tokens = custom_llm.num_tokens_from_docs([first_completed_doc])
        if first_doc_tokens + ori_second_docs_tokens > limited_token_nums:
            if len(ori_first_docs) == 1:
                debug_logger.info(f"first_file_docs number is one")
                return new_docs
            # 获取first_file_dict['doc_ids']的最小值和最大值
            doc_limit = [min(first_file_dict['doc_ids']), max(first_file_dict['doc_ids'])]
            first_completed_doc_limit, first_completed_doc_limit_with_figure = self.get_completed_document(
                first_file_dict['file_id'], doc_limit)
            first_completed_doc_limit.metadata['score'] = first_file_dict['score']
            first_doc_tokens = custom_llm.num_tokens_from_docs([first_completed_doc_limit])
            if first_doc_tokens + ori_second_docs_tokens > limited_token_nums:
                debug_logger.info(
                    f"first_limit_doc_tokens {doc_limit}: {first_doc_tokens} + ori_second_docs_tokens: {ori_second_docs_tokens} > limited_token_nums: {limited_token_nums}")
                return new_docs
            else:
                debug_logger.info(
                    f"first_limit_doc_tokens {doc_limit}: {first_doc_tokens} + ori_second_docs_tokens: {ori_second_docs_tokens} <= limited_token_nums: {limited_token_nums}")
                new_docs.append(first_completed_doc_limit_with_figure)
        else:
            debug_logger.info(
                f"first_doc_tokens: {first_doc_tokens} + ori_second_docs_tokens: {ori_second_docs_tokens} <= limited_token_nums: {limited_token_nums}")
            new_docs.append(first_completed_doc_with_figure)
        if second_file_dict:
            second_completed_doc, second_completed_doc_with_figure = self.get_completed_document(second_file_dict['file_id'])
            second_completed_doc.metadata['score'] = second_file_dict['score']
            second_doc_tokens = custom_llm.num_tokens_from_docs([second_completed_doc])
            if first_doc_tokens + second_doc_tokens > limited_token_nums:
                if len(ori_second_docs) == 1:
                    debug_logger.info(f"second_file_docs number is one")
                    new_docs.extend(ori_second_docs)
                    return new_docs
                doc_limit = [min(second_file_dict['doc_ids']), max(second_file_dict['doc_ids'])]
                second_completed_doc_limit, second_completed_doc_limit_with_figure = self.get_completed_document(
                    second_file_dict['file_id'], doc_limit)
                second_completed_doc_limit.metadata['score'] = second_file_dict['score']
                second_doc_tokens = custom_llm.num_tokens_from_docs([second_completed_doc_limit])
                if first_doc_tokens + second_doc_tokens > limited_token_nums:
                    debug_logger.info(
                        f"first_doc_tokens: {first_doc_tokens} + second_limit_doc_tokens {doc_limit}: {second_doc_tokens} > limited_token_nums: {limited_token_nums}")
                    new_docs.extend(ori_second_docs)
                    return new_docs
                else:
                    debug_logger.info(
                        f"first_doc_tokens: {first_doc_tokens} + second_limit_doc_tokens {doc_limit}: {second_doc_tokens} <= limited_token_nums: {limited_token_nums}")
                    new_docs.append(second_completed_doc_limit_with_figure)
            else:
                debug_logger.info(
                    f"first_doc_tokens: {first_doc_tokens} + second_doc_tokens: {second_doc_tokens} <= limited_token_nums: {limited_token_nums}")
                new_docs.append(second_completed_doc_with_figure)
        return new_docs

    def incomplete_table(self, source_documents, limited_token_nums, custom_llm):
        # 若某个doc里包含表格的一部分，则扩展为整个表格
        existing_table_docs = [doc for doc in source_documents if doc.metadata.get('has_table', False)]
        if not existing_table_docs:
            return source_documents
        new_docs = []
        existing_table_ids = []
        verified_table_ids = []
        current_doc_tokens = custom_llm.num_tokens_from_docs(source_documents)
        for doc in source_documents:
            if 'doc_id' not in doc.metadata:
                new_docs.append(doc)
                continue
            if table_doc_id := doc.metadata.get('table_doc_id', None):
                if table_doc_id in existing_table_ids:  # 已经不全了完整表格
                    continue
                if table_doc_id in verified_table_ids:  # 已经确认了完整表格太大放不大
                    new_docs.append(doc)
                    continue
                doc_json = self.milvus_summary.get_document_by_doc_id(table_doc_id)
                if doc_json is None:
                    new_docs.append(doc)
                    continue
                table_doc = Document(page_content=doc_json['kwargs']['page_content'],
                                     metadata=doc_json['kwargs']['metadata'])
                table_doc.metadata['score'] = doc.metadata['score']
                table_doc_tokens = custom_llm.num_tokens_from_docs([table_doc])
                current_table_docs = [doc for doc in source_documents if
                                      doc.metadata.get('table_doc_id', None) == table_doc_id]
                subtract_table_doc_tokens = custom_llm.num_tokens_from_docs(current_table_docs)
                if current_doc_tokens + table_doc_tokens - subtract_table_doc_tokens > limited_token_nums:
                    debug_logger.info(
                        f"Add table_doc_tokens: {table_doc_tokens} > limited_token_nums: {limited_token_nums}")
                    new_docs.append(doc)
                    verified_table_ids.append(table_doc_id)
                    continue
                else:
                    debug_logger.info(f"Incomplete table_doc: {table_doc_id}")
                    new_docs.append(table_doc)
                    existing_table_ids.append(table_doc_id)
                    current_doc_tokens = current_doc_tokens + table_doc_tokens - subtract_table_doc_tokens
        return new_docs
