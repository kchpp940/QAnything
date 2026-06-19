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
        self._es_client = self._init_es_client()
        debug_logger.info(f"Init ElasticSearchStore with index_name: {ES_INDEX_NAME}")

    def _init_es_client(self):
        try:
            from elasticsearch import Elasticsearch
            return Elasticsearch(
                ES_URL, basic_auth=(ES_USER, ES_PASSWORD) if ES_USER else None
            )
        except ImportError:
            try:
                return self.es_store.client
            except Exception:
                debug_logger.warning("Could not get native ES client, search_by_file_id will be unavailable")
                return None

    def search_by_file_id(self, file_id, max_results=10000):
        if self._es_client is None:
            debug_logger.warning("ES native client unavailable, cannot search by file_id")
            return []
        try:
            query = {
                "query": {
                    "prefix": {
                        "_id": file_id + "_"
                    }
                },
                "_source": False,
                "size": max_results
            }
            res = self._es_client.search(index=ES_INDEX_NAME, body=query)
            hits = res.get("hits", {}).get("hits", [])
            doc_ids = [hit["_id"] for hit in hits]
            total = res.get("hits", {}).get("total", {}).get("value", len(doc_ids))
            debug_logger.info(f"ES search by file_id {file_id}: found {total} docs, fetched {len(doc_ids)} ids")
            return doc_ids
        except Exception as e:
            debug_logger.error(f"ES search by file_id failed for {file_id}: {e}")
            return []

    def delete_by_file_id(self, file_id):
        doc_ids = self.search_by_file_id(file_id)
        if doc_ids:
            self.delete(doc_ids)
            debug_logger.info(f"ES delete_by_file_id {file_id}: deleted {len(doc_ids)} docs")
        else:
            debug_logger.info(f"ES delete_by_file_id {file_id}: no docs to delete")
        return len(doc_ids)

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
