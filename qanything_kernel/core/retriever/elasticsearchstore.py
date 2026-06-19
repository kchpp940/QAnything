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
            metadata_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"metadata.file_id.keyword": file_id}}
                        ]
                    }
                },
                "_source": False,
                "size": max_results
            }
            fallback_query = {
                "query": {
                    "prefix": {"_id": file_id + "_"}
                },
                "_source": False,
                "size": max_results
            }

            try:
                meta_res = self._es_client.search(index=ES_INDEX_NAME, body=metadata_query)
                meta_hits = meta_res.get("hits", {}).get("hits", [])
                meta_total = meta_res.get("hits", {}).get("total", {}).get("value", len(meta_hits))
                meta_ids = [hit["_id"] for hit in meta_hits]
                debug_logger.info(
                    f"ES metadata search for {file_id}: total={meta_total}, fetched={len(meta_ids)} ids"
                )
            except Exception as meta_err:
                debug_logger.warning(
                    f"ES metadata.file_id query failed for {file_id}: {meta_err}, fallback to _id prefix"
                )
                meta_ids = []
                meta_total = 0

            fallback_ids = []
            fallback_total = 0
            try:
                fb_res = self._es_client.search(index=ES_INDEX_NAME, body=fallback_query)
                fb_hits = fb_res.get("hits", {}).get("hits", [])
                fallback_total = fb_res.get("hits", {}).get("total", {}).get("value", len(fb_hits))
                fallback_ids = [hit["_id"] for hit in fb_hits]
                debug_logger.info(
                    f"ES _id-prefix fallback for {file_id}: total={fallback_total}, fetched={len(fallback_ids)} ids"
                )
            except Exception as fb_err:
                debug_logger.warning(
                    f"ES _id prefix fallback failed for {file_id}: {fb_err}"
                )

            all_ids = list(dict.fromkeys(meta_ids + fallback_ids))
            debug_logger.info(
                f"ES combined search for {file_id}: "
                f"metadata={meta_total}, prefix={fallback_total}, unique_total={len(all_ids)}"
            )
            return all_ids
        except Exception as e:
            debug_logger.error(f"ES search_by_file_id failed for {file_id}: {e}")
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
