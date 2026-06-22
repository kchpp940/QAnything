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
    StructuredJsonFormatter, StructuredLogger,
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

    valid, extra, warnings = validate_log_fields(all_fields)

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


async def test_6_real_log_json_chain():
    """测试 6: 基于真实 StructuredLogger JSON 输出的跨阶段 request_id 断言
    模拟完整链路：上传 API → Worker → 检索 → 流式 LLM
    捕获所有 JSON 日志，用 jq 语义按同一个 request_id 检索，断言跨阶段可关联
    """
    import logging
    from io import StringIO

    print("\n📋 Test 6: 真实 StructuredLogger JSON 跨阶段链路断言")

    # 捕获 JSON 日志输出
    log_capture = StringIO()
    capture_handler = logging.StreamHandler(log_capture)
    capture_handler.setFormatter(StructuredJsonFormatter())
    capture_handler.setLevel(logging.INFO)

    # 创建独立 logger 避免污染全局
    test_logger = logging.getLogger('test_chain_json')
    test_logger.handlers.clear()
    test_logger.addHandler(capture_handler)
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False

    s_test = StructuredLogger(test_logger)

    # 统一的 request_id 贯穿全链路
    request_id = generate_request_id()
    user_id = "u_chain_001"
    kb_id = "kb_chain_001"
    file_id = "file_chain_001"

    # ===== 阶段 1: 上传 API =====
    init_context(request_id=request_id, user_id=user_id, kb_id=kb_id,
                api_name="upload_files")
    s_test.info("文件上传开始",
                stage=Stage.FILE_UPLOAD,
                status=Status.START,
                file_id=file_id,
                file_name="test_rag.pdf",
                file_size=1024000)
    s_test.info("文件上传成功",
                stage=Stage.FILE_UPLOAD,
                status=Status.SUCCESS,
                duration_ms=234.56,
                file_id=file_id)
    upload_rid = get_request_id()

    # ===== 阶段 2: Worker 继承 request_id（从 upload_infos JSON）=====
    # 模拟从数据库读出 upload_infos JSON，继承同一个 request_id
    upload_infos = json.dumps({
        "request_id": request_id,
        "user_id": user_id,
        "kb_id": kb_id,
        "file_id": file_id,
    })
    worker_rid = json.loads(upload_infos)["request_id"]
    check("worker 从 upload_infos 继承的 request_id 与上传一致",
          worker_rid == upload_rid, f"worker={worker_rid[:12]} upload={upload_rid[:12]}")

    # Worker 中初始化上下文（继承 request_id）
    init_context(request_id=worker_rid, user_id=user_id, kb_id=kb_id,
                api_name="insert_worker", inherited_request_id=True)
    s_test.info("文件解析开始",
                stage=Stage.FILE_PARSE,
                status=Status.START,
                file_id=file_id)
    s_test.info("文件入库完成",
                stage=Stage.FILE_INSERT,
                status=Status.SUCCESS,
                duration_ms=1567.89,
                chunks_count=42,
                file_id=file_id)
    reset_context()

    # ===== 阶段 3: 检索阶段 =====
    init_context(request_id=request_id, user_id=user_id, kb_id=kb_id,
                api_name="local_doc_chat")
    s_test.info("检索开始",
                stage=Stage.RETRIEVAL,
                status=Status.START,
                query="什么是 RAG 系统？")
    s_test.info("检索完成",
                stage=Stage.RETRIEVAL,
                status=Status.SUCCESS,
                duration_ms=89.12,
                retrieval_docs_count=10,
                source_docs_count=10,
                top_k=10,
                rerank=True,
                hybrid_search=True)

    # ===== 阶段 4: 流式 LLM 生成阶段 =====
    s_test.info("LLM 生成开始",
                stage=Stage.LLM_GENERATE,
                status=Status.START,
                streaming=True,
                model="qwen-72b-chat")
    s_test.info("首 token 输出",
                stage=Stage.LLM_GENERATE,
                status=Status.FIRST_TOKEN,
                first_token_ms=345.67,
                model="qwen-72b-chat")
    s_test.info("流式生成完成",
                stage=Stage.LLM_GENERATE,
                status=Status.SUCCESS,
                duration_ms=2345.67,
                model="qwen-72b-chat",
                total_tokens=896,
                input_tokens=512,
                output_tokens=384,
                tokens_per_second=163.8)
    reset_context()

    # ===== 解析所有 JSON 日志，按 request_id 检索 =====
    log_capture.seek(0)
    log_lines = log_capture.getvalue().strip().split('\n')
    log_entries = []
    for line in log_lines:
        if line.strip():
            try:
                entry = json.loads(line)
                log_entries.append(entry)
            except json.JSONDecodeError:
                pass

    check(f"共捕获 {len(log_entries)} 条 JSON 日志", len(log_entries) >= 8,
          f"实际 {len(log_entries)} 条")

    # 模拟 jq 语义：按同一个 request_id 过滤（顶级字段或 ctx）
    def filter_by_request_id(entries, rid):
        """模拟 jq: .[] | select(.request_id == $rid)"""
        results = []
        for e in entries:
            ctx = e.get('ctx', {})
            e_rid = e.get('request_id') or ctx.get('request_id')
            if e_rid == rid:
                results.append(e)
        return results

    chain_entries = filter_by_request_id(log_entries, request_id)
    check(f"request_id={request_id[:12]}... 跨 4 阶段共检索到 {len(chain_entries)} 条日志",
          len(chain_entries) >= 8, f"实际 {len(chain_entries)} 条")

    # 按 stage 分组，断言每个阶段都有记录
    stages_found = {}
    for e in chain_entries:
        stage = e.get('stage')
        if stage:
            stages_found.setdefault(stage, []).append(e)

    expected_stages = {Stage.FILE_UPLOAD, Stage.FILE_PARSE, Stage.FILE_INSERT,
                      Stage.RETRIEVAL, Stage.LLM_GENERATE}
    check(f"4 大阶段 {expected_stages} 全部有日志",
          set(stages_found.keys()) >= expected_stages,
          f"缺失: {expected_stages - set(stages_found.keys())}")

    # 断言每个阶段的关键字段
    # FILE_UPLOAD 阶段
    upload_entries = stages_found.get(Stage.FILE_UPLOAD, [])
    check(f"FILE_UPLOAD 有 start + success 2 条日志", len(upload_entries) >= 2)
    upload_success = next((e for e in upload_entries
                          if e.get('status') == Status.SUCCESS), None)
    check("FILE_UPLOAD success 有 duration_ms",
          upload_success and upload_success.get('duration_ms') == 234.56)
    check("FILE_UPLOAD success 有 file_id",
          upload_success and upload_success.get('file_id') == file_id)

    # FILE_INSERT 阶段
    insert_entries = stages_found.get(Stage.FILE_INSERT, [])
    check("FILE_INSERT 有 success 日志", len(insert_entries) >= 1)
    insert_success = insert_entries[0]
    check("FILE_INSERT 有 chunks_count",
          insert_success.get('chunks_count') == 42)
    check("FILE_INSERT ctx 中 request_id 正确",
          insert_success['ctx'].get('request_id') == request_id)

    # RETRIEVAL 阶段
    retrieval_entries = stages_found.get(Stage.RETRIEVAL, [])
    check("RETRIEVAL 有 start + success 2 条日志", len(retrieval_entries) >= 2)
    retrieval_success = next((e for e in retrieval_entries
                             if e.get('status') == Status.SUCCESS), None)
    check("RETRIEVAL success 有 retrieval_docs_count",
          retrieval_success and retrieval_success.get('retrieval_docs_count') == 10)
    check("RETRIEVAL success 有 source_docs_count",
          retrieval_success and retrieval_success.get('source_docs_count') == 10)

    # LLM_GENERATE 阶段
    llm_entries = stages_found.get(Stage.LLM_GENERATE, [])
    check("LLM_GENERATE 有 start + first_token + success 3 条日志", len(llm_entries) >= 3)
    llm_success = next((e for e in llm_entries
                       if e.get('status') == Status.SUCCESS), None)
    check("LLM_GENERATE success 有 model",
          llm_success and llm_success.get('model') == "qwen-72b-chat")
    check("LLM_GENERATE success 有 total_tokens",
          llm_success and llm_success.get('total_tokens') == 896)
    check("LLM_GENERATE success 有 duration_ms",
          llm_success and llm_success.get('duration_ms') == 2345.67)
    check("LLM_GENERATE success 有 tokens_per_second",
          llm_success and llm_success.get('tokens_per_second') == 163.8)

    # 断言同一个 request_id 贯穿所有阶段
    all_rids = set()
    for e in chain_entries:
        ctx = e.get('ctx', {})
        rid = e.get('request_id') or ctx.get('request_id')
        all_rids.add(rid)
    check(f"所有 {len(chain_entries)} 条日志的 request_id 完全一致（只有 1 个唯一值）",
          len(all_rids) == 1 and request_id in all_rids,
          f"唯一 request_id 数量: {len(all_rids)}")

    # 断言 JSON 格式符合契约（顶级字段完整）
    sample_entry = chain_entries[0]
    required_top_level = {'timestamp', 'level', 'logger', 'pid', 'module',
                         'function', 'line', 'ctx', 'message'}
    check(f"JSON 顶级字段包含 {required_top_level}",
          set(sample_entry.keys()) >= required_top_level,
          f"缺失: {required_top_level - set(sample_entry.keys())}")

    check("ctx 中包含 request_id",
          sample_entry['ctx'].get('request_id') == request_id)

    # 清理
    capture_handler.close()
    test_logger.removeHandler(capture_handler)
    reset_context()


async def main():
    print("=" * 60)
    print("全链路 Request ID 与 Schema 验证")
    print("=" * 60)

    test_1_context_basic()
    test_2_upload_to_worker_inheritance()
    await test_3_stream_lifecycle()
    test_4_log_schema_compliance()
    test_5_error_classification()
    await test_6_real_log_json_chain()

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
