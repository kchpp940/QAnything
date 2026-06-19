import sys
import os

# 获取当前脚本的绝对路径
current_script_path = os.path.abspath(__file__)

# 将项目根目录添加到sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_script_path))))

sys.path.append(root_dir)
print(root_dir)

from sanic import Sanic, response
from qanything_kernel.utils.custom_log import insert_logger
from qanything_kernel.utils.general_utils import get_time_async
from qanything_kernel.core.retriever.general_document import LocalFileForInsert
from qanything_kernel.core.retriever.vectorstore import VectorStoreMilvusClient
from qanything_kernel.connector.database.mysql.mysql_client import KnowledgeBaseManager
from qanything_kernel.core.retriever.elasticsearchstore import StoreElasticSearchClient
from qanything_kernel.core.retriever.parent_retriever import ParentRetriever
from qanything_kernel.configs.model_config import MYSQL_HOST_LOCAL, MYSQL_PORT_LOCAL, \
    MYSQL_USER_LOCAL, MYSQL_PASSWORD_LOCAL, MYSQL_DATABASE_LOCAL, MAX_CHARS
from qanything_kernel.utils.file_progress_tracker import (
    FileProgressTracker, FileStage, FileStageStatus, ErrorCode, RETRYABLE_ERRORS
)
from sanic.worker.manager import WorkerManager
import asyncio
import traceback
import time
import random
import aiomysql
import argparse
import json

WorkerManager.THRESHOLD = 6000

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8110, help='port')
parser.add_argument('--workers', type=int, default=4, help='workers')
# 检查是否是local或online，不是则报错
args = parser.parse_args()

INSERT_WORKERS = args.workers
insert_logger.info(f"INSERT_WORKERS: {INSERT_WORKERS}")

# 创建 Sanic 应用
app = Sanic("InsertFileService")

# 数据库配置
db_config = {
    'host': MYSQL_HOST_LOCAL,
    'port': MYSQL_PORT_LOCAL,
    'user': MYSQL_USER_LOCAL,
    'password': MYSQL_PASSWORD_LOCAL,
    'db': MYSQL_DATABASE_LOCAL,
}


async def rollback_file_data(progress_tracker, progress_data, file_id, file_name, kb_id,
                             milvus_kb, es_client, mysql_client, failed_stage, chunks_number=0):
    has_failure = False
    try:
        progress_data = progress_tracker.update_rollback_start(progress_data, failed_stage)
        progress_tracker.save_progress(file_id, progress_data)

        try:
            existing_file_ids = milvus_kb.get_files([file_id])
            has_milvus_data = len(existing_file_ids) > 0
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "milvus_checked", "success",
                f"found {len(existing_file_ids)} residual entries in Milvus" if has_milvus_data else "no residual Milvus data"
            )
            if has_milvus_data:
                milvus_kb.delete_files([file_id])
                verify_ids = milvus_kb.get_files([file_id])
                if len(verify_ids) == 0:
                    progress_data = progress_tracker.update_rollback_step(
                        progress_data, "milvus_cleared", "success",
                        "Milvus data cleared and verified"
                    )
                    insert_logger.info(f"Rollback: Milvus data cleared for file {file_id}")
                else:
                    has_failure = True
                    progress_data = progress_tracker.update_rollback_step(
                        progress_data, "milvus_cleared", "failed",
                        f"Milvus still has {len(verify_ids)} entries after deletion"
                    )
                    insert_logger.error(f"Rollback: Milvus verification failed for file {file_id}")
            else:
                progress_data = progress_tracker.update_rollback_step(
                    progress_data, "milvus_cleared", "success", "no residual Milvus data"
                )
        except Exception as e:
            has_failure = True
            error_detail = f"Milvus rollback error: {str(e)}"
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "milvus_checked", "failed", error_detail
            )
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "milvus_cleared", "failed", error_detail
            )
            insert_logger.error(f"Rollback Milvus error for file {file_id}: {error_detail}")

        try:
            es_doc_ids = es_client.search_by_file_id(file_id)
            has_es_data = len(es_doc_ids) > 0
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "es_checked", "success",
                f"found {len(es_doc_ids)} residual docs in ES" if has_es_data else "no residual ES data"
            )
            if has_es_data:
                es_client.delete(es_doc_ids)
                verify_ids = es_client.search_by_file_id(file_id)
                if len(verify_ids) == 0:
                    progress_data = progress_tracker.update_rollback_step(
                        progress_data, "es_cleared", "success",
                        f"ES data cleared and verified ({len(es_doc_ids)} docs deleted)"
                    )
                    insert_logger.info(f"Rollback: ES data cleared for file {file_id}, {len(es_doc_ids)} docs")
                else:
                    has_failure = True
                    progress_data = progress_tracker.update_rollback_step(
                        progress_data, "es_cleared", "failed",
                        f"ES still has {len(verify_ids)} docs after deletion"
                    )
                    insert_logger.error(f"Rollback: ES verification failed for file {file_id}")
            else:
                progress_data = progress_tracker.update_rollback_step(
                    progress_data, "es_cleared", "success", "no residual ES data"
                )
        except Exception as e:
            has_failure = True
            error_detail = f"ES rollback error: {str(e)}"
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "es_checked", "failed", error_detail
            )
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "es_cleared", "failed", error_detail
            )
            insert_logger.error(f"Rollback ES error for file {file_id}: {error_detail}")

        try:
            mysql_docs = mysql_client.get_document_by_file_id(file_id)
            mysql_count = len(mysql_docs) if mysql_docs else 0
            has_mysql_data = mysql_count > 0
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "mysql_checked", "success",
                f"found {mysql_count} residual docs in MySQL" if has_mysql_data else "no residual MySQL data"
            )
            if has_mysql_data:
                mysql_client.delete_documents([file_id])
                try:
                    mysql_client.update_chunks_number(file_id, 0)
                except Exception:
                    pass
                verify_docs = mysql_client.get_document_by_file_id(file_id)
                verify_count = len(verify_docs) if verify_docs else 0
                if verify_count == 0:
                    progress_data = progress_tracker.update_rollback_step(
                        progress_data, "mysql_cleared", "success",
                        f"MySQL data cleared and verified ({mysql_count} docs deleted)"
                    )
                    insert_logger.info(f"Rollback: MySQL Documents cleared for file {file_id}")
                else:
                    has_failure = True
                    progress_data = progress_tracker.update_rollback_step(
                        progress_data, "mysql_cleared", "failed",
                        f"MySQL still has {verify_count} docs after deletion"
                    )
                    insert_logger.error(f"Rollback: MySQL verification failed for file {file_id}")
            else:
                progress_data = progress_tracker.update_rollback_step(
                    progress_data, "mysql_cleared", "success", "no residual MySQL data"
                )
        except Exception as e:
            has_failure = True
            error_detail = f"MySQL rollback error: {str(e)}"
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "mysql_checked", "failed", error_detail
            )
            progress_data = progress_tracker.update_rollback_step(
                progress_data, "mysql_cleared", "failed", error_detail
            )
            insert_logger.error(f"Rollback MySQL error for file {file_id}: {error_detail}")

        if has_failure:
            progress_data = progress_tracker.update_rollback_failed(
                progress_data, "One or more rollback steps failed, manual intervention may be required"
            )
        else:
            progress_data = progress_tracker.update_rollback_success(progress_data)
        progress_tracker.save_progress(file_id, progress_data)
        return progress_data

    except Exception as e:
        rollback_error = f"Rollback exception: {str(e)}"
        insert_logger.error(f"Rollback critical error for file {file_id}: {rollback_error}")
        progress_data = progress_tracker.update_rollback_failed(progress_data, rollback_error)
        progress_tracker.save_progress(file_id, progress_data)
        return progress_data


async def cleanup_before_retry(progress_tracker, progress_data, file_id, file_name, kb_id,
                               milvus_kb, es_client, mysql_client):
    has_cleanup_failure = False
    needs_wait = False
    try:
        progress_data = progress_tracker.update_cleanup_start(progress_data)
        progress_tracker.save_progress(file_id, progress_data)

        try:
            existing_file_ids = milvus_kb.get_files([file_id])
            has_milvus_data = len(existing_file_ids) > 0
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "milvus_checked", "success",
                f"found {len(existing_file_ids)} residual entries in Milvus" if has_milvus_data else "no residual Milvus data"
            )
            if has_milvus_data:
                milvus_kb.delete_files([file_id])
                needs_wait = True
                verify_ids = milvus_kb.get_files([file_id])
                if len(verify_ids) == 0:
                    progress_data = progress_tracker.update_cleanup_step(
                        progress_data, "milvus_cleared", "success",
                        "Milvus data cleared and verified"
                    )
                    insert_logger.info(f"Cleanup: Milvus data cleared for retry file {file_id}")
                else:
                    has_cleanup_failure = True
                    progress_data = progress_tracker.update_cleanup_step(
                        progress_data, "milvus_cleared", "failed",
                        f"Milvus still has {len(verify_ids)} entries after deletion"
                    )
                    insert_logger.error(f"Cleanup: Milvus verification failed for retry file {file_id}")
            else:
                progress_data = progress_tracker.update_cleanup_step(
                    progress_data, "milvus_cleared", "success", "no residual Milvus data"
                )
        except Exception as e:
            has_cleanup_failure = True
            error_detail = f"Milvus cleanup error: {str(e)}"
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "milvus_checked", "failed", error_detail
            )
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "milvus_cleared", "failed", error_detail
            )
            insert_logger.error(f"Cleanup Milvus error for file {file_id}: {error_detail}")

        try:
            es_doc_ids = es_client.search_by_file_id(file_id)
            has_es_data = len(es_doc_ids) > 0
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "es_checked", "success",
                f"found {len(es_doc_ids)} residual docs in ES" if has_es_data else "no residual ES data"
            )
            if has_es_data:
                es_client.delete(es_doc_ids)
                needs_wait = True
                verify_ids = es_client.search_by_file_id(file_id)
                if len(verify_ids) == 0:
                    progress_data = progress_tracker.update_cleanup_step(
                        progress_data, "es_cleared", "success",
                        f"ES data cleared and verified ({len(es_doc_ids)} docs deleted)"
                    )
                    insert_logger.info(f"Cleanup: ES data cleared for retry file {file_id}, {len(es_doc_ids)} docs")
                else:
                    has_cleanup_failure = True
                    progress_data = progress_tracker.update_cleanup_step(
                        progress_data, "es_cleared", "failed",
                        f"ES still has {len(verify_ids)} docs after deletion"
                    )
                    insert_logger.error(f"Cleanup: ES verification failed for retry file {file_id}")
            else:
                progress_data = progress_tracker.update_cleanup_step(
                    progress_data, "es_cleared", "success", "no residual ES data"
                )
        except Exception as e:
            has_cleanup_failure = True
            error_detail = f"ES cleanup error: {str(e)}"
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "es_checked", "failed", error_detail
            )
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "es_cleared", "failed", error_detail
            )
            insert_logger.error(f"Cleanup ES error for file {file_id}: {error_detail}")

        try:
            mysql_docs = mysql_client.get_document_by_file_id(file_id)
            mysql_count = len(mysql_docs) if mysql_docs else 0
            has_mysql_data = mysql_count > 0
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "mysql_checked", "success",
                f"found {mysql_count} residual docs in MySQL" if has_mysql_data else "no residual MySQL data"
            )
            if has_mysql_data:
                mysql_client.delete_documents([file_id])
                try:
                    mysql_client.update_chunks_number(file_id, 0)
                except Exception:
                    pass
                needs_wait = True
                verify_docs = mysql_client.get_document_by_file_id(file_id)
                verify_count = len(verify_docs) if verify_docs else 0
                if verify_count == 0:
                    progress_data = progress_tracker.update_cleanup_step(
                        progress_data, "mysql_cleared", "success",
                        f"MySQL data cleared and verified ({mysql_count} docs deleted)"
                    )
                    insert_logger.info(f"Cleanup: MySQL data cleared for retry file {file_id}")
                else:
                    has_cleanup_failure = True
                    progress_data = progress_tracker.update_cleanup_step(
                        progress_data, "mysql_cleared", "failed",
                        f"MySQL still has {verify_count} docs after deletion"
                    )
                    insert_logger.error(f"Cleanup: MySQL verification failed for retry file {file_id}")
            else:
                progress_data = progress_tracker.update_cleanup_step(
                    progress_data, "mysql_cleared", "success", "no residual MySQL data"
                )
        except Exception as e:
            has_cleanup_failure = True
            error_detail = f"MySQL cleanup error: {str(e)}"
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "mysql_checked", "failed", error_detail
            )
            progress_data = progress_tracker.update_cleanup_step(
                progress_data, "mysql_cleared", "failed", error_detail
            )
            insert_logger.error(f"Cleanup MySQL error for file {file_id}: {error_detail}")

        if has_cleanup_failure:
            progress_data = progress_tracker.update_cleanup_failed(
                progress_data, "One or more cleanup steps failed, file cannot be retried safely"
            )
        else:
            progress_data = progress_tracker.update_cleanup_success(progress_data)
        progress_tracker.save_progress(file_id, progress_data)

        if needs_wait and not has_cleanup_failure:
            insert_logger.info(f"Cleanup completed for retry file {file_id}, waiting 2s for data consistency...")
            await asyncio.sleep(2)

    except Exception as e:
        cleanup_error = f"Cleanup exception: {str(e)}"
        insert_logger.error(f"Cleanup critical error for file {file_id}: {cleanup_error}")
        progress_data = progress_tracker.update_cleanup_failed(progress_data, cleanup_error)
        progress_tracker.save_progress(file_id, progress_data)

    return progress_data


@get_time_async
async def process_data(retriever, milvus_kb, mysql_client, es_client, file_info, time_record):
    parse_timeout_seconds = 300
    insert_timeout_seconds = 300
    content_length = -1
    status = 'green'
    process_start = time.perf_counter()
    insert_logger.info(f'Start insert file: {file_info}')
    _, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, chunk_size = file_info
    # 获取格式为'2021-08-01 00:00:00'的时间戳
    insert_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    mysql_client.update_knowlegde_base_latest_insert_time(kb_id, insert_timestamp)
    local_file = LocalFileForInsert(user_id, kb_id, file_id, file_location, file_name, file_url, chunk_size, mysql_client)
    msg = "success"
    chunks_number = 0

    progress_tracker = FileProgressTracker(mysql_client)
    progress_data = progress_tracker.load_progress(file_id)

    is_retry = False
    if progress_data and progress_data.get("retry_count", 0) > 0:
        is_retry = True

    if not progress_data:
        progress_data = progress_tracker.create_initial_progress(file_id, file_name)
        progress_data = progress_tracker.update_stage_start(progress_data, FileStage.UPLOAD)
        progress_data = progress_tracker.update_stage_progress(progress_data, FileStage.UPLOAD, 100)
        progress_data = progress_tracker.update_stage_success(progress_data, FileStage.UPLOAD)

    if is_retry or progress_tracker.needs_rollback(progress_data):
        insert_logger.info(f"File {file_id} is retry or has residual data, running cleanup_before_retry")
        progress_data = await cleanup_before_retry(
            progress_tracker, progress_data, file_id, file_name, kb_id,
            milvus_kb, es_client, mysql_client
        )

        cleanup_info = progress_data.get("cleanup_info", {})
        milvus_clear_ok = cleanup_info.get("milvus_cleared") is True
        es_clear_ok = cleanup_info.get("es_cleared") is True
        mysql_clear_ok = cleanup_info.get("mysql_cleared") is True

        if not (milvus_clear_ok and es_clear_ok and mysql_clear_ok):
            failed_targets = []
            if not milvus_clear_ok:
                failed_targets.append("Milvus")
            if not es_clear_ok:
                failed_targets.append("ES")
            if not mysql_clear_ok:
                failed_targets.append("MySQL")
            block_msg = f"Retry blocked: residual data in {', '.join(failed_targets)} could not be cleared"
            insert_logger.error(f"File {file_id}: {block_msg}")
            progress_data = progress_tracker.update_stage_failed(
                progress_data, FileStage.CLEANUP, ErrorCode.CLEANUP_ERROR, block_msg
            )
            progress_data["retryable"] = False
            progress_tracker.save_progress(file_id, progress_data)
            status = 'red'
            msg = block_msg
            return status, content_length, chunks_number, msg

    try:
        progress_data = progress_tracker.update_stage_start(progress_data, FileStage.PARSE)
        progress_tracker.save_progress(file_id, progress_data)

        start = time.perf_counter()
        await asyncio.wait_for(
            asyncio.to_thread(local_file.split_file_to_docs),
            timeout=parse_timeout_seconds
        )
        content_length = sum([len(doc.page_content) for doc in local_file.docs])

        if content_length > MAX_CHARS:
            error_msg = f"{file_name} content_length too large, {content_length} >= MaxLength({MAX_CHARS})"
            progress_data = progress_tracker.update_stage_failed(
                progress_data, FileStage.PARSE, ErrorCode.PARSE_CONTENT_TOO_LARGE, error_msg
            )
            progress_tracker.save_progress(file_id, progress_data)
            status = 'red'
            msg = error_msg
            return status, content_length, chunks_number, msg

        elif content_length == 0:
            error_msg = f"{file_name} content_length is 0, file content is empty or The URL exists anti-crawling or requires login."
            progress_data = progress_tracker.update_stage_failed(
                progress_data, FileStage.PARSE, ErrorCode.PARSE_ANTI_CRAWL, error_msg
            )
            progress_tracker.save_progress(file_id, progress_data)
            status = 'red'
            msg = error_msg
            return status, content_length, chunks_number, msg

        progress_data = progress_tracker.update_stage_success(progress_data, FileStage.PARSE)
        progress_data = progress_tracker.update_stage_start(progress_data, FileStage.CHUNK)
        progress_data = progress_tracker.update_stage_progress(progress_data, FileStage.CHUNK, 100)
        progress_data = progress_tracker.update_stage_success(progress_data, FileStage.CHUNK)
        progress_tracker.save_progress(file_id, progress_data)

        end = time.perf_counter()
        time_record['parse_time'] = round(end - start, 2)
        insert_logger.info(f'parse time: {end - start} {len(local_file.docs)}')

        progress_data = progress_tracker.update_stage_start(progress_data, FileStage.MILVUS_INSERT)
        progress_tracker.save_progress(file_id, progress_data)

        start = time.perf_counter()
        chunks_number, insert_time_record = await asyncio.wait_for(
            retriever.insert_documents(local_file.docs, chunk_size),
            timeout=insert_timeout_seconds)
        insert_time = time.perf_counter()
        time_record.update(insert_time_record)
        insert_logger.info(f'insert time: {insert_time - start}')
        mysql_client.update_chunks_number(local_file.file_id, chunks_number)

        progress_data = progress_tracker.update_stage_progress(progress_data, FileStage.MILVUS_INSERT, 100)
        progress_data = progress_tracker.update_stage_success(progress_data, FileStage.MILVUS_INSERT)
        progress_tracker.save_progress(file_id, progress_data)

        progress_data = progress_tracker.update_stage_start(progress_data, FileStage.ES_INDEX)
        progress_data = progress_tracker.update_stage_progress(progress_data, FileStage.ES_INDEX, 100)
        progress_data = progress_tracker.update_stage_success(progress_data, FileStage.ES_INDEX)
        progress_data = progress_tracker.mark_completed(progress_data)
        progress_tracker.save_progress(file_id, progress_data)

    except asyncio.TimeoutError:
        local_file.event.set()
        timeout_stage = FileStage.PARSE if 'parse_time' not in time_record else FileStage.MILVUS_INSERT
        timeout_error = ErrorCode.PARSE_TIMEOUT if timeout_stage == FileStage.PARSE else ErrorCode.MILVUS_TIMEOUT
        error_msg = f"{timeout_stage.value} timeout: {parse_timeout_seconds if timeout_stage == FileStage.PARSE else insert_timeout_seconds}s"
        insert_logger.error(f'Timeout: {timeout_stage.value} took longer than expected')

        partial_info = {}
        if timeout_stage == FileStage.MILVUS_INSERT and chunks_number > 0:
            partial_info["chunks_inserted"] = chunks_number
            progress_data = progress_tracker.update_stage_partial_success(
                progress_data, FileStage.MILVUS_INSERT, partial_info
            )

        progress_data = progress_tracker.update_stage_failed(
            progress_data, timeout_stage, timeout_error, error_msg
        )
        progress_tracker.save_progress(file_id, progress_data)

        progress_data = await rollback_file_data(
            progress_tracker, progress_data, file_id, file_name, kb_id,
            milvus_kb, es_client, mysql_client, timeout_stage, chunks_number
        )

        status = 'red'
        time_record['insert_timeout'] = True
        msg = error_msg
        return status, content_length, chunks_number, msg

    except Exception as e:
        error_info = f'error: {traceback.format_exc()}'
        insert_logger.error(error_info)

        failed_stage = FileStage.PARSE
        error_code = ErrorCode.PARSE_ERROR
        if 'parse_time' in time_record:
            failed_stage = FileStage.MILVUS_INSERT
            error_code = ErrorCode.MILVUS_INSERT_ERROR

        error_msg = f"{failed_stage.value} error: {str(e)}"

        partial_info = {}
        if failed_stage == FileStage.MILVUS_INSERT and chunks_number > 0:
            partial_info["chunks_inserted"] = chunks_number
            progress_data = progress_tracker.update_stage_partial_success(
                progress_data, FileStage.MILVUS_INSERT, partial_info
            )

        progress_data = progress_tracker.update_stage_failed(
            progress_data, failed_stage, error_code, error_msg
        )
        progress_tracker.save_progress(file_id, progress_data)

        progress_data = await rollback_file_data(
            progress_tracker, progress_data, file_id, file_name, kb_id,
            milvus_kb, es_client, mysql_client, failed_stage, chunks_number
        )

        status = 'red'
        time_record['insert_error'] = True
        msg = error_msg
        return status, content_length, chunks_number, msg

    time_record['upload_total_time'] = round(time.perf_counter() - process_start, 2)
    mysql_client.update_file_upload_infos(file_id, time_record)
    insert_logger.info(f'insert_files_to_milvus: {user_id}, {kb_id}, {file_id}, {file_name}, {status}')
    msg = json.dumps(time_record, ensure_ascii=False)
    return status, content_length, chunks_number, msg


async def check_and_process(pool):
    process_type = 'MainProcess' if 'SANIC_WORKER_NAME' not in os.environ else os.environ['SANIC_WORKER_NAME']
    worker_id = int(process_type.split('-')[-2])
    insert_logger.info(f"{os.getpid()} worker_id is {worker_id}")
    mysql_client = KnowledgeBaseManager()
    milvus_kb = VectorStoreMilvusClient()
    es_client = StoreElasticSearchClient()
    retriever = ParentRetriever(milvus_kb, mysql_client, es_client)
    while True:
        sleep_time = 3
        # worker_id 根据时间变化，每x分钟变一次，获取当前时间的分钟数
        minutes = int(int(time.strftime("%M", time.localtime())) / INSERT_WORKERS)
        dynamic_worker_id = (worker_id + minutes) % INSERT_WORKERS
        id = None
        try:
            async with pool.acquire() as conn:  # 获取连接
                async with conn.cursor() as cur:  # 创建游标
                    query = f"""
                        SELECT id, timestamp, file_id, file_name FROM File
                        WHERE status = 'gray' AND MOD(id, %s) = %s AND deleted = 0
                        ORDER BY timestamp ASC LIMIT 1;
                    """

                    await cur.execute(query, (INSERT_WORKERS, dynamic_worker_id))

                    file_to_update = await cur.fetchone()

                    if file_to_update:
                        insert_logger.info(f"{worker_id}, file_to_update: {file_to_update}")
                        # 把files_to_update按照timestamp排序, 获取时间最早的那条记录的id
                        # file_to_update = sorted(files_to_update, key=lambda x: x[1])[0]

                        id, timestamp, file_id, file_name = file_to_update
                        # 更新这条记录的状态
                        await cur.execute("""
                            UPDATE File SET status='yellow'
                            WHERE id=%s;
                        """, (id,))
                        await conn.commit()
                        insert_logger.info(f"UPDATE FILE: {timestamp}, {file_id}, {file_name}, yellow")

                        await cur.execute(
                            "SELECT id, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, "
                            "chunk_size FROM File WHERE id=%s", (id,))
                        file_info = await cur.fetchone()

                        time_record = {}
                        # 现在处理数据
                        status, content_length, chunks_number, msg = await process_data(retriever, milvus_kb,
                                                                                        mysql_client, es_client,
                                                                                        file_info, time_record)

                        insert_logger.info('time_record: ' + json.dumps(time_record, ensure_ascii=False))
                        # 更新文件处理后的状态和相关信息
                        await cur.execute(
                            "UPDATE File SET status=%s, content_length=%s, chunks_number=%s, msg=%s WHERE id=%s",
                            (status, content_length, chunks_number, msg, file_info[0]))
                        await conn.commit()
                        insert_logger.info(f"UPDATE FILE: {timestamp}, {file_id}, {file_name}, {status}")
                        sleep_time = 0.1
                    else:
                        await conn.commit()
        except Exception as e:
            insert_logger.error('MySQL或Milvus 连接异常：' + str(e))
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        insert_logger.error(f"process_files Error {traceback.format_exc()}")
                        # 如果file的status是yellow，就改为red
                        if id is not None:
                            await cur.execute("UPDATE File SET status='red' WHERE id=%s AND status='yellow'", (id,))
                            await conn.commit()

                            await cur.execute(
                                "SELECT id, file_id, user_id, file_name, kb_id, file_location, file_size FROM File WHERE id=%s",
                                (id,))
                            file_info = await cur.fetchone()

                            insert_logger.info(f"UPDATE FILE: {timestamp}, {file_id}, {file_name}, yellow2red")
                            _, file_id, user_id, file_name, kb_id, file_location, file_size = file_info
                            # await post_data(user_id=user_id, charsize=-1, docid=file_id, status='red', msg="Milvus service exception")
            except Exception as e:
                insert_logger.error('MySQL 二次连接异常：' + str(e))
        finally:
            await asyncio.sleep(sleep_time)


@app.listener('after_server_stop')
async def close_db(app, loop):
    # 关闭数据库连接池
    app.ctx.pool.close()
    await app.ctx.pool.wait_closed()


@app.listener('before_server_start')
async def setup_workers(app, loop):
    # 创建数据库连接池
    app.ctx.pool = await aiomysql.create_pool(**db_config, minsize=1, maxsize=16, loop=loop, autocommit=False,
                                              init_command='SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED')  # 更改事务隔离级别
    app.add_task(check_and_process(app.ctx.pool))


# 启动服务
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=args.port, workers=INSERT_WORKERS, access_log=False)
