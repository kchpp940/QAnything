from qanything_kernel.utils.custom_log import debug_logger, insert_logger
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
        debug_logger.info(f"Init ElasticSearchStore with index_name: {ES_INDEX_NAME}")

    def delete(self, docs_ids):
        try:
            res = self.es_store.delete(docs_ids, timeout=60)
            debug_logger.info(f"Delete ES document with number: {len(docs_ids)}, {docs_ids[0]}, res: {res}")
        except Exception as e:
            debug_logger.error(f"Delete ES document failed with error: {e}")

    def delete_files(self, file_ids, file_chunks):
        docs_ids = []
        for file_id, file_chunk in zip(file_ids, file_chunks):
            docs_ids.extend([file_id + '_' + str(i) for i in range(file_chunk)])
        if docs_ids:
            self.delete(docs_ids)

    def delete_files_by_file_id(self, file_ids):
        try:
            es_client = getattr(self.es_store, 'client', None)
            index_name = getattr(self.es_store, 'index_name', ES_INDEX_NAME)
            if es_client is None:
                debug_logger.error("ES client not available, skip delete by file_id")
                return
            for file_id in file_ids:
                query = {
                    "query": {
                        "term": {
                            "metadata.file_id.keyword": file_id
                        }
                    }
                }
                res = es_client.delete_by_query(index=index_name, body=query, timeout="60s")
                debug_logger.info(f"Delete ES documents by file_id {file_id}: deleted={res.get('deleted', 0)}, total={res.get('total', 0)}")
        except Exception as e:
            debug_logger.error(f"Delete ES documents by file_id failed: {e}")
