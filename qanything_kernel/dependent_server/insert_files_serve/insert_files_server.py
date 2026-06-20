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
from qanything_kernel.utils.file_process_state import (FileProcessState, ProcessStage, ErrorCategory,
                                                      FileProcessContext, RetryPolicy, categorize_error)
from qanything_kernel.utils.stage_rollback_handler import StageRollbackHandler
from sanic.worker.manager import WorkerManager
import asyncio
import traceback
import time
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


async def update_process_context_async(pool, file_id, context):
    context_json = context.to_json()
    legacy_status = 'green' if context.state == FileProcessState.COMPLETED else (
        'red' if context.state == FileProcessState.FAILED else 'yellow'
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE File SET process_context = %s, status = %s WHERE file_id = %s",
                (context_json, legacy_status, file_id)
            )
            await conn.commit()


async def rollback_stage_data_async(milvus_kb, es_client, mysql_client, file_id, to_stage, context=None, extra=None):
    rollback_handler = StageRollbackHandler(
        milvus_client=milvus_kb,
        es_client=es_client,
        mysql_client=mysql_client,
    )
    result = rollback_handler.rollback_to_stage(file_id, to_stage, context, extra)
    return result


@get_time_async
async def process_data(retriever, milvus_kb, mysql_client, pool, file_info, time_record):
    parse_timeout_seconds = 300
    insert_timeout_seconds = 300
    content_length = -1
    process_start = time.perf_counter()
    insert_logger.info(f'Start insert file: {file_info}')

    if len(file_info) == 10:
        id_val, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, chunk_size, process_context_json = file_info
    else:
        id_val, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, chunk_size = file_info
        process_context_json = None

    extra = {"file_location": file_location}

    if process_context_json:
        try:
            context = FileProcessContext.from_json(process_context_json)
            insert_logger.info(f"Resuming file {file_id} from state: {context.state.value}, stage: {context.current_stage.value}")
            if context.state == FileProcessState.RETRYING:
                insert_logger.info(f"Retry: running rollback for {file_id} to stage {context.current_stage.value}")
                await asyncio.to_thread(
                    rollback_stage_data_async,
                    milvus_kb, retriever.es_client, mysql_client,
                    file_id, context.current_stage, context, extra
                )
        except Exception as e:
            insert_logger.warning(f"Failed to parse process_context for {file_id}: {e}, starting fresh")
            context = FileProcessContext(file_id=file_id)
    else:
        context = FileProcessContext(file_id=file_id)

    context.transition_to(FileProcessState.PARSING, ProcessStage.PARSE, "开始解析文件")
    await update_process_context_async(pool, file_id, context)

    insert_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    mysql_client.update_knowlegde_base_latest_insert_time(kb_id, insert_timestamp)
    local_file = LocalFileForInsert(user_id, kb_id, file_id, file_location, file_name, file_url, chunk_size, mysql_client)
    chunks_number = 0

    start = time.perf_counter()
    try:
        await asyncio.wait_for(
            asyncio.to_thread(local_file.split_file_to_docs),
            timeout=parse_timeout_seconds
        )
        content_length = sum([len(doc.page_content) for doc in local_file.docs])
        if content_length > MAX_CHARS:
            error_msg = f"{file_name} content_length too large, {content_length} >= MaxLength({MAX_CHARS})"
            context.record_error(ErrorInfo(
                error_category=ErrorCategory.CONTENT_TOO_LARGE,
                error_message=error_msg,
                stage=ProcessStage.PARSE,
            ))
            await update_process_context_async(pool, file_id, context)
            return context, content_length, chunks_number
        elif content_length == 0:
            error_msg = f"{file_name} content_length is 0, file content is empty or The URL exists anti-crawling or requires login."
            context.record_error(ErrorInfo(
                error_category=ErrorCategory.CONTENT_EMPTY,
                error_message=error_msg,
                stage=ProcessStage.PARSE,
            ))
            await update_process_context_async(pool, file_id, context)
            return context, content_length, chunks_number
    except asyncio.TimeoutError:
        local_file.event.set()
        error_msg = f"split_file_to_docs timeout: {parse_timeout_seconds}s"
        insert_logger.error(f'Timeout: {error_msg}')
        context.record_error(ErrorInfo(
            error_category=ErrorCategory.TIMEOUT_ERROR,
            error_message=error_msg,
            stage=ProcessStage.PARSE,
            stack_trace=traceback.format_exc(),
        ))
        await update_process_context_async(pool, file_id, context)
        return context, content_length, chunks_number
    except Exception as e:
        error_msg = f"split_file_to_docs error: {str(e)}"
        insert_logger.error(f'{error_msg}\n{traceback.format_exc()}')
        context.record_error(ErrorInfo(
            error_category=categorize_error(e, ProcessStage.PARSE),
            error_message=error_msg,
            stage=ProcessStage.PARSE,
            stack_trace=traceback.format_exc(),
        ))
        await update_process_context_async(pool, file_id, context)
        return context, content_length, chunks_number

    end = time.perf_counter()
    time_record['parse_time'] = round(end - start, 2)
    insert_logger.info(f'parse time: {end - start} {len(local_file.docs)}')

    context.transition_to(FileProcessState.SPLITTING, ProcessStage.SPLIT, "文件切分完成，开始向量化")
    await update_process_context_async(pool, file_id, context)

    try:
        start = time.perf_counter()
        context.transition_to(FileProcessState.EMBEDDING, ProcessStage.EMBED, "开始向量化处理")
        await update_process_context_async(pool, file_id, context)

        chunks_number, insert_time_record = await asyncio.wait_for(
            retriever.insert_documents(local_file.docs, chunk_size),
            timeout=insert_timeout_seconds)
        insert_time = time.perf_counter()
        time_record.update(insert_time_record)
        insert_logger.info(f'insert time: {insert_time - start}')
        mysql_client.update_chunks_number(local_file.file_id, chunks_number)
    except asyncio.TimeoutError:
        insert_logger.error(f'Timeout: milvus insert took longer than {insert_timeout_seconds} seconds')
        await asyncio.to_thread(
            rollback_stage_data_async,
            milvus_kb, retriever.es_client, mysql_client,
            file_id, ProcessStage.EMBED, context, extra
        )
        error_msg = f"milvus insert timeout: {insert_timeout_seconds}s"
        time_record['insert_timeout'] = True
        context.record_error(ErrorInfo(
            error_category=ErrorCategory.TIMEOUT_ERROR,
            error_message=error_msg,
            stage=ProcessStage.INDEX,
            stack_trace=traceback.format_exc(),
        ))
        await update_process_context_async(pool, file_id, context)
        return context, content_length, chunks_number
    except Exception as e:
        error_msg = f"milvus insert error: {str(e)}"
        insert_logger.error(f'{error_msg}\n{traceback.format_exc()}')
        time_record['insert_error'] = True
        await asyncio.to_thread(
            rollback_stage_data_async,
            milvus_kb, retriever.es_client, mysql_client,
            file_id, ProcessStage.EMBED, context, extra
        )
        context.record_error(ErrorInfo(
            error_category=categorize_error(e, ProcessStage.INDEX),
            error_message=error_msg,
            stage=ProcessStage.INDEX,
            stack_trace=traceback.format_exc(),
        ))
        await update_process_context_async(pool, file_id, context)
        return context, content_length, chunks_number

    context.transition_to(FileProcessState.INDEXING, ProcessStage.INDEX, "索引构建完成")
    await update_process_context_async(pool, file_id, context)

    context.transition_to(FileProcessState.COMPLETED, ProcessStage.COMPLETE, "文件处理完成")
    time_record['upload_total_time'] = round(time.perf_counter() - process_start, 2)
    mysql_client.update_file_upload_infos(file_id, time_record)
    context.metadata['time_record'] = time_record
    context.metadata['chunks_number'] = chunks_number
    context.metadata['content_length'] = content_length
    await update_process_context_async(pool, file_id, context)

    insert_logger.info(f'insert_files_to_milvus: {user_id}, {kb_id}, {file_id}, {file_name}, completed')
    return context, content_length, chunks_number


async def get_pending_file(pool, worker_id):
    minutes = int(int(time.strftime("%M", time.localtime())) / INSERT_WORKERS)
    dynamic_worker_id = (worker_id + minutes) % INSERT_WORKERS

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            query = """
                SELECT id, timestamp, file_id, file_name, status, process_context FROM File
                WHERE (status = 'gray' OR (process_context IS NOT NULL AND JSON_EXTRACT(process_context, '$.state') IN ('pending', 'retrying')))
                AND MOD(id, %s) = %s AND deleted = 0
                ORDER BY timestamp ASC LIMIT 1;
            """
            await cur.execute(query, (INSERT_WORKERS, dynamic_worker_id))
            file_to_update = await cur.fetchone()

            if file_to_update:
                id_val, timestamp, file_id, file_name, status, process_context_json = file_to_update
                await cur.execute("UPDATE File SET status='yellow' WHERE id=%s", (id_val,))
                await conn.commit()
                insert_logger.info(f"UPDATE FILE: {timestamp}, {file_id}, {file_name}, yellow")

                await cur.execute(
                    "SELECT id, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, "
                    "chunk_size, process_context FROM File WHERE id=%s", (id_val,))
                file_info = await cur.fetchone()
                return file_info
    return None


async def check_and_process(pool):
    process_type = 'MainProcess' if 'SANIC_WORKER_NAME' not in os.environ else os.environ['SANIC_WORKER_NAME']
    worker_id = int(process_type.split('-')[-2])
    insert_logger.info(f"{os.getpid()} worker_id is {worker_id}")
    mysql_client = KnowledgeBaseManager()
    milvus_kb = VectorStoreMilvusClient()
    es_client = StoreElasticSearchClient()
    retriever = ParentRetriever(milvus_kb, mysql_client, es_client)
    retry_policy = RetryPolicy(max_retries=3)

    while True:
        sleep_time = 3
        file_info = None
        file_id = None
        id_val = None
        try:
            file_info = await get_pending_file(pool, worker_id)
            if file_info:
                id_val, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, chunk_size = file_info
                time_record = {}

                context, content_length, chunks_number = await process_data(
                    retriever, milvus_kb, mysql_client, pool, file_info, time_record
                )

                insert_logger.info('time_record: ' + json.dumps(time_record, ensure_ascii=False))

                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        msg = context.error_history[-1].error_message if context.error_history else json.dumps(time_record, ensure_ascii=False)
                        status = 'green' if context.state == FileProcessState.COMPLETED else 'red'
                        await cur.execute(
                            "UPDATE File SET status=%s, content_length=%s, chunks_number=%s, msg=%s WHERE id=%s",
                            (status, content_length, chunks_number, msg, id_val))
                        await conn.commit()

                insert_logger.info(f"UPDATE FILE: {file_id}, {file_name}, {context.state.value}")
                sleep_time = 0.1
        except Exception as e:
            insert_logger.error(f'处理文件异常: {str(e)}\n{traceback.format_exc()}')
            if file_id:
                try:
                    context = FileProcessContext(file_id=file_id)
                    context.record_error(ErrorInfo(
                        error_category=categorize_error(e, ProcessStage.INDEX),
                        error_message=str(e),
                        stage=ProcessStage.INDEX,
                        stack_trace=traceback.format_exc(),
                    ))
                    await update_process_context_async(pool, file_id, context)

                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            if id_val is not None:
                                await cur.execute("UPDATE File SET status='red' WHERE id=%s AND status='yellow'", (id_val,))
                                await conn.commit()
                except Exception as inner_e:
                    insert_logger.error(f'MySQL 二次连接异常：{str(inner_e)}')
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
