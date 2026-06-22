from qanything_kernel.utils.custom_log import debug_logger, insert_logger, s_debug_logger
from qanything_kernel.utils.request_context import Stage
from qanything_kernel.configs.model_config import ES_USER, ES_PASSWORD, ES_URL, ES_INDEX_NAME
from langchain_elasticsearch import ElasticsearchStore


class StoreElasticSearchClient:
    def __init__(self):
        self.es_store = ElasticsearchStore(
            es_url=ES_URL,
            index_name=ES_INDEX_NAME,
            es_user=ES_USER,
            es_password=ES_PASSWORD,
            strategy=ElasticsearchStore.BM25RetrievalStrategy()
        )
        s_debug_logger.info("ElasticSearchStore初始化完成", index_name=ES_INDEX_NAME, es_url=ES_URL, es_user=ES_USER)

    def delete(self, docs_ids):
        docs_count = len(docs_ids)
        s_debug_logger.stage_start(Stage.ES_OPERATION, "ES delete start",
                                   docs_count=docs_count)
        try:
            res = self.es_store.delete(docs_ids, timeout=60)
            s_debug_logger.info("ES文档删除完成",
                                docs_count=docs_count,
                                first_doc_id=docs_ids[0] if docs_ids else None,
                                delete_result=res)
            s_debug_logger.stage_success(Stage.ES_OPERATION, "ES delete success",
                                         docs_count=docs_count,
                                         delete_result=res)
        except Exception as e:
            s_debug_logger.error("ES文档删除失败",
                                 error=e,
                                 docs_count=docs_count,
                                 stage=Stage.ES_OPERATION,
                                 error_category="search_engine_error")
            s_debug_logger.stage_fail(Stage.ES_OPERATION, "ES delete failed",
                                      error=e,
                                      error_category="search_engine_error",
                                      docs_count=docs_count)

    def delete_files(self, file_ids, file_chunks):
        docs_ids = []
        for file_id, file_chunk in zip(file_ids, file_chunks):
            # doc_id 是file_id + '_' + i，其中i是range(file_chunk)
            docs_ids.extend([file_id + '_' + str(i) for i in range(file_chunk)])
        if docs_ids:
            self.delete(docs_ids)
