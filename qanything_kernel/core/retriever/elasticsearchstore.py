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
        self._es_client = None
        self._index_name = None
        self._init_es_client()

    def _init_es_client(self):
        for attr in ('client', 'es_client', '_client', '_es_client'):
            c = getattr(self.es_store, attr, None)
            if c is not None:
                self._es_client = c
                debug_logger.info(f"Found ES client via es_store.{attr}")
                break
        for attr in ('index_name', '_index_name'):
            n = getattr(self.es_store, attr, None)
            if n is not None:
                self._index_name = n
                break
        if self._index_name is None:
            self._index_name = ES_INDEX_NAME

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
        if not file_ids:
            return 0
        total_deleted = 0
        if self._es_client is not None:
            total_deleted = self._delete_by_query(file_ids)
            if total_deleted >= 0:
                return total_deleted
            debug_logger.warning("ES delete_by_query failed, try search+delete fallback")
        total_deleted = self._delete_by_search(file_ids)
        if total_deleted >= 0:
            return total_deleted
        debug_logger.warning(
            f"ES delete_files_by_file_id all paths failed for {len(file_ids)} files, "
            f"caller should fall back to delete_files with known chunks_number"
        )
        return -1

    def _delete_by_query(self, file_ids):
        try:
            total_deleted = 0
            for file_id in file_ids:
                query = {
                    "query": {
                        "term": {
                            "metadata.file_id.keyword": file_id
                        }
                    }
                }
                res = self._es_client.delete_by_query(
                    index=self._index_name,
                    body=query,
                    timeout="120s",
                    conflicts="proceed"
                )
                deleted = res.get("deleted", 0)
                total = res.get("total", 0)
                total_deleted += deleted
                debug_logger.info(
                    f"ES delete_by_query file_id={file_id}: deleted={deleted}, total={total}, "
                    f"version_conflicts={res.get('version_conflicts', 0)}"
                )
            debug_logger.info(
                f"ES delete_by_query done: {len(file_ids)} files, {total_deleted} documents deleted"
            )
            return total_deleted
        except Exception as e:
            debug_logger.error(f"ES delete_by_query failed: {e}")
            return -1

    def _delete_by_search(self, file_ids):
        if self._es_client is None:
            debug_logger.error("ES client not available, cannot do search+delete")
            return -1
        try:
            all_doc_ids = []
            for file_id in file_ids:
                search_query = {
                    "query": {
                        "term": {
                            "metadata.file_id.keyword": file_id
                        }
                    },
                    "_source": False,
                    "size": 10000
                }
                res = self._es_client.search(
                    index=self._index_name, body=search_query, scroll="2m")
                scroll_id = res.get("_scroll_id")
                hits = res.get("hits", {}).get("hits", [])
                doc_ids = [hit["_id"] for hit in hits]
                all_doc_ids.extend(doc_ids)
                while len(hits) > 0:
                    res = self._es_client.scroll(scroll_id=scroll_id, scroll="2m")
                    scroll_id = res.get("_scroll_id")
                    hits = res.get("hits", {}).get("hits", [])
                    doc_ids = [hit["_id"] for hit in hits]
                    all_doc_ids.extend(doc_ids)
                if scroll_id:
                    try:
                        self._es_client.clear_scroll(scroll_id=scroll_id)
                    except Exception:
                        pass
            if all_doc_ids:
                debug_logger.info(
                    f"ES search found {len(all_doc_ids)} docs to delete for {len(file_ids)} files"
                )
                self.delete(all_doc_ids)
                return len(all_doc_ids)
            else:
                debug_logger.info(
                    f"ES search found 0 docs for {len(file_ids)} files, nothing to delete"
                )
                return 0
        except Exception as e:
            debug_logger.error(f"ES search+delete failed: {e}")
            return -1
