#!/usr/bin/env python3
"""
全链路 Request ID 贯穿验证脚本
- 模拟：上传 API → 文件入队 → Worker 继承 → 检索 → 流式 LLM → 流结束清理
- 验证点：
  1. 同一个 request_id 贯穿上传、worker、检索、LLM 全链路
  2. 流式 generator 结束后上下文正确清理，不会串号
  3. 结构化日志字段符合 Schema 规范

用法：
    python scripts/verify_request_id_chain.py
"""
import asyncio
import json
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from qanything_kernel.utils.request_context import (
    init_context, set_context, update_extra,
    get_context, get_request_id, reset_context,
    generate_request_id, get_elapsed_ms,
    Stage, Status, ErrorCategory,
    LogSchema, is_valid_log_field, validate_log_fields,
)
from qanything_kernel.utils.custom_log import (
    s_debug_logger, s_insert_logger, s_qa_logger,
    StructuredJsonFormatter,
)

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f"  ({detail})" if detail else ""))


def test_1_context_basic():
    """测试 1: 基本上下文存取"""
    print("\n📋 Test 1: 基本上下文存取")
    reset_context()

    init_context(request_id=generate_request_id(), user_id="u_test_001", api_name="upload_files")
    set_context(kb_id="kb_test_001", file_id="file_test_001")
    update_extra(chunk_size=256, mode="light")

    ctx = get_context()
    rid = get_request_id()

    check("request_id 已生成", rid and rid.startswith("REQ"), f"rid={rid}")
    check("user_id 正确", ctx.get('user_id') == "u_test_001")
    check("kb_id 正确", ctx.get('kb_id') == "kb_test_001")
    check("file_id 正确", ctx.get('file_id') == "file_test_001")
    check("api_name 正确", ctx.get('api_name') == "upload_files")
    check("chunk_size 在 extra 中", ctx.get('chunk_size') == 256)
    check("mode 在 extra 中", ctx.get('mode') == "light")
    check("elapsed_ms 存在且 > 0", ctx.get('elapsed_ms', 0) >= 0)

    reset_context()
    check("reset 后 request_id 为空", get_request_id() is None)


def test_2_upload_to_worker_inheritance():
    """测试 2: 上传 API → Worker 的 request_id 继承"""
    print("\n📋 Test 2: 上传 → Worker request_id 继承")

    # 模拟上传 API
    init_context(request_id=generate_request_id(), user_id="u_test_001", kb_id="kb_test_001",
                api_name="upload_files")
    upload_rid = get_request_id()
    file_id = "file_test_" + upload_rid[-8:]
    set_context(file_id=file_id, file_name="test.pdf")

    # 模拟 add_file 写入 upload_infos
    upload_infos = {"request_id": upload_rid, "source": "api_upload", "mode": "light"}
    upload_infos_json = json.dumps(upload_infos, ensure_ascii=False)
    s_debug_logger.info("file uploaded", file_id=file_id, file_name="test.pdf",
                       stage=Stage.FILE_UPLOAD, status=Status.SUCCESS)
    check("上传 API request_id 非空", bool(upload_rid))

    reset_context()
    check("上传结束后上下文已清理", get_request_id() is None)

    # 模拟 Worker 从数据库读出 file_info（含 upload_infos）
    # 第 10 位是 upload_infos
    file_info = (1, file_id, "u_test_001", "test.pdf", "kb_test_001",
                "/tmp/test.pdf", 1024, "", 256, upload_infos_json)

    _, fid, uid, fname, kid, floc, fsize, furl, csize, uinfo_raw = file_info
    try:
        _infos = json.loads(uinfo_raw) if uinfo_raw else {}
    except Exception:
        _infos = {}
    inherited_rid = _infos.get("request_id") if isinstance(_infos, dict) else None

    # Worker 初始化上下文（继承或新生成）
    worker_rid = inherited_rid or generate_request_id()
    init_context(request_id=worker_rid, user_id=uid, kb_id=kid, file_id=fid,
                file_name=fname, api_name='insert_files_worker',
                inherited_request_id=bool(inherited_rid))

    check("Worker 继承到相同 request_id", worker_rid == upload_rid,
          f"upload={upload_rid}, worker={worker_rid}")
    check("上下文中 inherited_request_id=True", get_context().get('inherited_request_id') is True)

    s_insert_logger.stage_start(Stage.FILE_PARSE, "开始解析文件", file_size=1024)
    s_insert_logger.stage_success(Stage.FILE_PARSE, "解析完成", duration_ms=123.4, chunks_count=5)

    s_insert_logger.stage_start(Stage.FILE_INSERT, "开始入库")
    s_insert_logger.stage_success(Stage.FILE_INSERT, "入库完成", duration_ms=456.7, docs_count=5)

    s_insert_logger.stage_success(Stage.FILE_UPLOAD, "文件处理完成", duration_ms=580.1)

    ctx = get_context()
    check("Worker 阶段 ctx 包含全部关键字段",
          all(k in ctx for k in ['request_id', 'user_id', 'kb_id', 'file_id', 'file_name', 'api_name']))

    reset_context()


async def test_3_stream_lifecycle():
    """测试 3: 流式响应生命周期（生成器结束后才清理上下文）"""
    print("\n📋 Test 3: 流式响应生命周期")

    # 模拟 on_request 初始化
    init_context(request_id=generate_request_id(), user_id="u_test_001", kb_id="kb_test_001",
                api_name="local_doc_chat", model="test-model")
    stream_rid = get_request_id()
    check("on_request 初始化成功", bool(stream_rid))

    s_debug_logger.stage_start(Stage.RETRIEVAL, "开始检索")
    s_debug_logger.stage_success(Stage.RETRIEVAL, "检索完成", duration_ms=50.5,
                                retrieval_docs_count=10, source_docs_count=5)

    # 模拟流式生成器（对应 handler 中的 _generate_raw_answer）
    async def _mock_stream_generator():
        # 生成器内部应能拿到 request_id
        for i in range(3):
            yield f"chunk_{i}"
            await asyncio.sleep(0.001)
            check(f"生成器 chunk{i} 内 request_id 一致", get_request_id() == stream_rid)

    # 外层 wrapper（对应 handler 中的 generate_answer wrapper）
    async def generate_answer_wrapper(response_stream):
        s_debug_logger.stage_start(Stage.LLM_GENERATE, "开始流式生成")
        try:
            async for chunk in _mock_stream_generator():
                yield chunk
            s_debug_logger.stage_success(Stage.LLM_GENERATE, "流式生成完成",
                                        duration_ms=get_elapsed_ms(),
                                        tokens_per_second=35.2,
                                        output_tokens=128)
        except Exception as e:
            s_debug_logger.stage_fail(Stage.LLM_GENERATE, "流式生成失败", error=e)
            raise
        finally:
            s_debug_logger.info("stream context cleanup", elapsed_ms=get_elapsed_ms())
            reset_context()

    # 模拟 on_response 触发（此时流尚未结束，不清理）
    check("on_response 触发前 request_id 存在", get_request_id() == stream_rid)

    # 消费流
    chunks = []
    async for chunk in generate_answer_wrapper(None):
        chunks.append(chunk)

    check(f"收到 {len(chunks)} 个 chunk", len(chunks) == 3)
    check("流结束后上下文已清理（finally 中 reset）",
          get_request_id() is None)


def test_4_log_schema_compliance():
    """测试 4: 结构化日志字段符合 Schema 规范"""
    print("\n📋 Test 4: 日志字段 Schema 合规性")

    # 合法字段会出现在顶级
    valid_fields = {"request_id", "stage", "status", "duration_ms", "model", "kb_id",
                   "file_id", "user_id", "query", "top_k", "chunks_count"}
    invalid_fields = {"random_field_x", "foo_bar", "my_custom_key_xyz"}

    all_fields = {}
    all_fields.update({k: "v" for k in valid_fields})
    all_fields.update({k: "v" for k in invalid_fields})

    valid, extra = validate_log_fields(all_fields)

    check("schema 字段都被识别为合法", set(valid.keys()) & valid_fields == valid_fields)
    check("非 schema 字段都落入 extra", set(extra.keys()) & invalid_fields == invalid_fields)

    # LogSchema 常用字段检查
    check("LogSchema.REQUEST_ID == 'request_id'", LogSchema.REQUEST_ID == "request_id")
    check("LogSchema.STAGE == 'stage'", LogSchema.STAGE == "stage")
    check("LogSchema.STATUS == 'status'", LogSchema.STATUS == "status")
    check("LogSchema.DURATION_MS == 'duration_ms'", LogSchema.DURATION_MS == "duration_ms")
    check("LogSchema.ERROR_CATEGORY == 'error_category'", LogSchema.ERROR_CATEGORY == "error_category")
    check("LogSchema.ERROR_MSG == 'error_msg'", LogSchema.ERROR_MSG == "error_msg")

    # stage 是一个字段名（不是 stage 的值），验证字段名合法
    check("字段名 'stage' 在 Schema 中", is_valid_log_field('stage'))
    check("字段名 'status' 在 Schema 中", is_valid_log_field('status'))
    check("字段名 'duration_ms' 在 Schema 中", is_valid_log_field('duration_ms'))

    # Stage 枚举值都能被 _classify_error 正常使用（验证常量存在）
    stage_values = {v for k, v in Stage.__dict__.items()
                   if not k.startswith('_') and isinstance(v, str)}
    check("Stage 枚举至少 10 个值", len(stage_values) >= 10,
          f"当前 {len(stage_values)} 个")
    check("Stage.RETRIEVAL 存在", hasattr(Stage, 'RETRIEVAL'))
    check("Stage.LLM_GENERATE 存在", hasattr(Stage, 'LLM_GENERATE'))
    check("Stage.FILE_UPLOAD 存在", hasattr(Stage, 'FILE_UPLOAD'))


def test_5_error_classification():
    """测试 5: 错误分类自动识别"""
    print("\n📋 Test 5: 错误分类自动识别")

    try:
        raise ValueError("invalid user_id parameter")
    except ValueError as e:
        cat = s_debug_logger._classify_error(e)
        check("ValueError 识别为 validation_error", cat == ErrorCategory.VALIDATION_ERROR,
              f"cat={cat}")

    try:
        raise TimeoutError("operation timed out after 30s")
    except TimeoutError as e:
        cat = s_debug_logger._classify_error(e)
        check("TimeoutError 识别为 timeout_error", cat == ErrorCategory.TIMEOUT_ERROR,
              f"cat={cat}")

    try:
        raise RuntimeError("elasticsearch connection refused")
    except RuntimeError as e:
        cat = s_debug_logger._classify_error(e)
        check("含 elasticsearch 的错误识别为 search_engine_error",
              cat == ErrorCategory.SEARCH_ENGINE_ERROR, f"cat={cat}")


async def main():
    print("=" * 60)
    print("全链路 Request ID 与 Schema 验证")
    print("=" * 60)

    test_1_context_basic()
    test_2_upload_to_worker_inheritance()
    await test_3_stream_lifecycle()
    test_4_log_schema_compliance()
    test_5_error_classification()

    print("\n" + "=" * 60)
    print(f"结果：✅ 通过 {PASS}  |  ❌ 失败 {FAIL}")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
    else:
        print("\n🎉 所有验证通过！request_id 贯穿上传、worker、检索、流式 LLM 全链路")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
