import sys
import os

# 获取当前脚本的绝对路径
current_script_path = os.path.abspath(__file__)

# 将项目根目录添加到sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_script_path))))

sys.path.append(root_dir)
print(root_dir)

from sanic import Sanic, response
from qanything_kernel.utils.custom_log import insert_logger, s_insert_logger
from qanything_kernel.utils.request_context import (init_context, set_context, reset_context, Stage, generate_request_id)
from qanything_kernel.utils.general_utils import get_time_async
from qanything_kernel.core.retriever.general_document import LocalFileForInsert
from qanything_kernel.core.retriever.vectorstore import VectorStoreMilvusClient
from qanything_kernel.connector.database.mysql.mysql_client import KnowledgeBaseManager
from qanything_kernel.core.retriever.elasticsearchstore import StoreElasticSearchClient
from qanything_kernel.core.retriever.parent_retriever import ParentRetriever
from qanything_kernel.configs.model_config import MYSQL_HOST_LOCAL, MYSQL_PORT_LOCAL, \
    MYSQL_USER_LOCAL, MYSQL_PASSWORD_LOCAL, MYSQL_DATABASE_LOCAL, MAX_CHARS
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


@get_time_async
async def process_data(retriever, milvus_kb, mysql_client, file_info, time_record):
    parse_timeout_seconds = 300
    insert_timeout_seconds = 300
    content_length = -1
    status = 'green'
    process_start = time.perf_counter()
    s_insert_logger.info("Start insert file", file_info=str(file_info))
    _, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, chunk_size, _ = file_info
    # 获取格式为'2021-08-01 00:00:00'的时间戳
    insert_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    mysql_client.update_knowlegde_base_latest_insert_time(kb_id, insert_timestamp)
    local_file = LocalFileForInsert(user_id, kb_id, file_id, file_location, file_name, file_url, chunk_size, mysql_client)
    msg = "success"
    chunks_number = 0
    mysql_client.update_file_msg(file_id, f'Processing:{random.randint(1, 5)}%')
    # 这里是把文件做向量化，然后写入Milvus的逻辑
    s_insert_logger.stage_start(Stage.FILE_PARSE, "start file parse")
    start = time.perf_counter()
    try:
        await asyncio.wait_for(
            asyncio.to_thread(local_file.split_file_to_docs),
            timeout=parse_timeout_seconds
        )
        content_length = sum([len(doc.page_content) for doc in local_file.docs])
        if content_length > MAX_CHARS:
            duration_ms = (time.perf_counter() - start) * 1000
            status = 'red'
            msg = f"{file_name} content_length too large, {content_length} >= MaxLength({MAX_CHARS})"
            s_insert_logger.stage_fail(Stage.FILE_PARSE, f"file parse failed: content_length too large", duration_ms=duration_ms)
            return status, content_length, chunks_number, msg
        elif content_length == 0:
            duration_ms = (time.perf_counter() - start) * 1000
            status = 'red'
            msg = f"{file_name} content_length is 0, file content is empty or The URL exists anti-crawling or requires login."
            s_insert_logger.stage_fail(Stage.FILE_PARSE, "file parse failed: content_length is 0", duration_ms=duration_ms)
            return status, content_length, chunks_number, msg
    except asyncio.TimeoutError as te:
        duration_ms = (time.perf_counter() - start) * 1000
        local_file.event.set()
        s_insert_logger.error("split_file_to_docs timeout", timeout_seconds=parse_timeout_seconds)
        status = 'red'
        msg = f"split_file_to_docs timeout: {parse_timeout_seconds}s"
        s_insert_logger.stage_fail(Stage.FILE_PARSE, f"file parse timeout: {parse_timeout_seconds}s", error=te, duration_ms=duration_ms)
        return status, content_length, chunks_number, msg
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        error_info = f'split_file_to_docs error: {traceback.format_exc()}'
        msg = error_info
        s_insert_logger.error("split_file_to_docs error", error_info=error_info)
        status = 'red'
        msg = f"split_file_to_docs error"
        s_insert_logger.stage_fail(Stage.FILE_PARSE, "file parse exception", error=e, duration_ms=duration_ms)
        return status, content_length, chunks_number, msg
    end = time.perf_counter()
    duration_ms = (end - start) * 1000
    time_record['parse_time'] = round(end - start, 2)
    s_insert_logger.info("parse time", parse_seconds=round(end - start, 2), docs_count=len(local_file.docs))
    s_insert_logger.stage_success(Stage.FILE_PARSE, "file parse success", duration_ms=duration_ms)
    mysql_client.update_file_msg(file_id, f'Processing:{random.randint(5, 75)}%')

    s_insert_logger.stage_start(Stage.FILE_INSERT, "start milvus insert")
    try:
        start = time.perf_counter()
        chunks_number, insert_time_record = await asyncio.wait_for(
            retriever.insert_documents(local_file.docs, chunk_size),
            timeout=insert_timeout_seconds)
        insert_time = time.perf_counter()
        duration_ms = (insert_time - start) * 1000
        time_record.update(insert_time_record)
        s_insert_logger.info("insert time", insert_seconds=round(insert_time - start, 2))
        mysql_client.update_chunks_number(local_file.file_id, chunks_number)
        s_insert_logger.stage_success(Stage.FILE_INSERT, "milvus insert success", duration_ms=duration_ms, chunks_number=chunks_number)
    except asyncio.TimeoutError as te:
        duration_ms = (time.perf_counter() - start) * 1000
        s_insert_logger.error("milvus insert timeout", timeout_seconds=insert_timeout_seconds)
        expr = f'file_id == \"{local_file.file_id}\"'
        milvus_kb.delete_expr(expr)
        status = 'red'
        time_record['insert_timeout'] = True
        msg = f"milvus insert timeout: {insert_timeout_seconds}s"
        s_insert_logger.stage_fail(Stage.FILE_INSERT, f"milvus insert timeout: {insert_timeout_seconds}s", error=te, duration_ms=duration_ms, chunks_number=chunks_number)
        return status, content_length, chunks_number, msg
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        error_info = f'milvus insert error: {traceback.format_exc()}'
        s_insert_logger.error("milvus insert error", error_info=error_info)
        status = 'red'
        time_record['insert_error'] = True
        msg = f"milvus insert error"
        s_insert_logger.stage_fail(Stage.FILE_INSERT, "milvus insert exception", error=e, duration_ms=duration_ms, chunks_number=chunks_number)
        return status, content_length, chunks_number, msg

    mysql_client.update_file_msg(file_id, f'Processing:{random.randint(75, 100)}%')
    time_record['upload_total_time'] = round(time.perf_counter() - process_start, 2)
    mysql_client.update_file_upload_infos(file_id, time_record)
    s_insert_logger.info("insert_files_to_milvus", user_id=user_id, kb_id=kb_id, file_id=file_id, file_name=file_name, status=status)
    msg = json.dumps(time_record, ensure_ascii=False)
    return status, content_length, chunks_number, msg


async def check_and_process(pool):
    process_type = 'MainProcess' if 'SANIC_WORKER_NAME' not in os.environ else os.environ['SANIC_WORKER_NAME']
    worker_id = int(process_type.split('-')[-2])
    s_insert_logger.info("worker started", pid=os.getpid(), worker_id=worker_id)
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
                        s_insert_logger.info("file_to_update picked", worker_id=worker_id, file_to_update=str(file_to_update))
                        # 把files_to_update按照timestamp排序, 获取时间最早的那条记录的id
                        # file_to_update = sorted(files_to_update, key=lambda x: x[1])[0]

                        id, timestamp, file_id, file_name = file_to_update
                        # 更新这条记录的状态
                        await cur.execute("""
                            UPDATE File SET status='yellow'
                            WHERE id=%s;
                        """, (id,))
                        await conn.commit()
                        s_insert_logger.info("file status yellow", timestamp=timestamp, file_id=file_id, file_name=file_name)

                        await cur.execute(
                            "SELECT id, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, "
                            "chunk_size, upload_infos FROM File WHERE id=%s", (id,))
                        file_info = await cur.fetchone()
                        _, file_id, user_id, file_name, kb_id, file_location, file_size, file_url, chunk_size, upload_infos_raw = file_info
                        try:
                            _infos = json.loads(upload_infos_raw) if upload_infos_raw else {}
                        except Exception:
                            _infos = {}
                        _inherited_req_id = _infos.get("request_id") if isinstance(_infos, dict) else None
                        init_context(request_id=_inherited_req_id or generate_request_id(),
                                     user_id=user_id, kb_id=kb_id, file_id=file_id, file_name=file_name,
                                     api_name='insert_files_worker', inherited_request_id=bool(_inherited_req_id))

                        time_record = {}
                        process_start = time.perf_counter()
                        try:
                            # 现在处理数据
                            status, content_length, chunks_number, msg = await process_data(retriever, milvus_kb,
                                                                                            mysql_client,
                                                                                            file_info, time_record)

                            duration_ms = (time.perf_counter() - process_start) * 1000
                            if status == 'green':
                                s_insert_logger.stage_success(Stage.FILE_UPLOAD, "file upload success", duration_ms=duration_ms)
                            else:
                                s_insert_logger.stage_fail(Stage.FILE_UPLOAD, f"file upload failed: {msg}", duration_ms=duration_ms)

                            s_insert_logger.info("file process time_record", time_record=time_record)
                            # 更新文件处理后的状态和相关信息
                            await cur.execute(
                                "UPDATE File SET status=%s, content_length=%s, chunks_number=%s, msg=%s WHERE id=%s",
                                (status, content_length, chunks_number, msg, file_info[0]))
                            await conn.commit()
                            s_insert_logger.info("file status updated", timestamp=timestamp, file_id=file_id, file_name=file_name, target_status=status)
                            sleep_time = 0.1
                        except Exception as process_e:
                            duration_ms = (time.perf_counter() - process_start) * 1000
                            s_insert_logger.stage_fail(Stage.FILE_UPLOAD, f"file upload exception: {str(process_e)}", error=process_e, duration_ms=duration_ms)
                            raise
                        finally:
                            reset_context()
                    else:
                        await conn.commit()
        except Exception as e:
            s_insert_logger.exception("mysql milvus connection error", error=e)
            try:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        s_insert_logger.exception("process_files inner error", error_category=ErrorCategory.INTERNAL_ERROR)
                        # 如果file的status是yellow，就改为red
                        if id is not None:
                            await cur.execute("UPDATE File SET status='red' WHERE id=%s AND status='yellow'", (id,))
                            await conn.commit()

                            await cur.execute(
                                "SELECT id, file_id, user_id, file_name, kb_id, file_location, file_size FROM File WHERE id=%s",
                                (id,))
                            file_info = await cur.fetchone()

                            s_insert_logger.warning("file status yellow2red", timestamp=timestamp, file_id=file_id, file_name=file_name)
                            _, file_id, user_id, file_name, kb_id, file_location, file_size = file_info
                            # await post_data(user_id=user_id, charsize=-1, docid=file_id, status='red', msg="Milvus service exception")
            except Exception as e:
                s_insert_logger.exception("mysql secondary connection error", error=e)
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
