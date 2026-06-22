#!/usr/bin/env python3
"""
Log Schema 合规性校验脚本
- 扫描 qanything_kernel 下所有 Python 文件
- 检查 s_*_logger 调用中的 keyword 参数是否在 LogSchema 白名单内
- 检查 stage/stage_start/stage_success/stage_fail 的 stage 参数值是否来自 Stage 常量
- 退出码：0=全部合规，非 0=存在不合规
"""
import ast
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = PROJECT_ROOT / "qanything_kernel"

LOGGER_NAMES = {"s_debug_logger", "s_qa_logger", "s_rerank_logger", "s_embed_logger", "s_insert_logger"}
STAGE_METHODS = {"stage_start", "stage_success", "stage_fail"}
COMMON_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical"}

# 从 LogSchema/Stage/Status 动态加载合法字段与 stage 值
sys.path.insert(0, str(PROJECT_ROOT))
from qanything_kernel.utils.request_context import LogSchema, Stage, Status, _find_similar_core_field

SCHEMA_FIELDS = LogSchema.get_all_fields()
CORE_FIELDS = LogSchema.get_core_fields()
STAGE_VALUES = {v for k, v in Stage.__dict__.items() if not k.startswith('_') and isinstance(v, str)}
STATUS_VALUES = {v for k, v in Status.__dict__.items() if not k.startswith('_') and isinstance(v, str)}

# 真正的业务扩展字段（运行时落入 extra_fields）
# 命名规范：使用 X_ 前缀标识扩展字段，例如 X_MSG, X_CUSTOM_FIELD
# 核心字段必须在 LogSchema 中定义，不允许放入此列表
# 当前原则：所有常用字段已归入明确分类，此列表原则上应保持为空
ALLOWED_EXTRA_FIELDS = set()

# 允许的参数名（s_*_logger 方法的位置参数和显式 keyword 参数）
EXPLICIT_PARAMS = {"stage", "status", "duration_ms", "error", "error_category", "message"}


class LogSchemaChecker(ast.NodeVisitor):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations = []  # (line, col, severity, message)
        self.total_calls = 0

    def _add(self, node, severity, msg):
        self.violations.append((node.lineno, node.col_offset, severity, msg))

    def visit_Call(self, node: ast.Call):
        # 只看 s_*_logger.xxx() 调用
        if not isinstance(node.func, ast.Attribute):
            self.generic_visit(node)
            return
        attr = node.func
        if not isinstance(attr.value, ast.Name):
            self.generic_visit(node)
            return
        if attr.value.id not in LOGGER_NAMES:
            self.generic_visit(node)
            return

        self.total_calls += 1
        method = attr.attr

        # 位置参数第一个是 message，跳过
        kw = {kw.arg: kw for kw in node.keywords if kw.arg is not None}

        # ---- 检查所有 keyword 参数名 ----
        for key, kw_node in kw.items():
            if key in EXPLICIT_PARAMS:
                continue
            if key in SCHEMA_FIELDS:
                continue
            if key in ALLOWED_EXTRA_FIELDS:
                continue
            # 检查是否是核心字段拼写错误（编辑距离 <= 2）
            suggestion = _find_similar_core_field(key, CORE_FIELDS)
            if suggestion:
                self._add(kw_node, "ERROR",
                          f"字段 '{key}' 疑似核心字段拼写错误，建议改为 LogSchema.{suggestion.upper()} ('{suggestion}')")
            else:
                self._add(kw_node, "WARN",
                          f"字段 '{key}' 不在 LogSchema 白名单也不在允许扩展列表，"
                          f"运行时会落入 extra_fields 命名空间")

        # ---- stage_* 方法特殊检查 ----
        if method in STAGE_METHODS:
            # 第一个位置参数（或 stage kw）必须是 Stage.XXX 常量
            stage_expr = None
            if node.args:
                stage_expr = node.args[0]
            elif "stage" in kw:
                stage_expr = kw["stage"].value

            if stage_expr is not None:
                if isinstance(stage_expr, ast.Attribute) and isinstance(stage_expr.value, ast.Name):
                    if stage_expr.value.id != "Stage":
                        self._add(stage_expr, "ERROR",
                                  f"stage 参数必须是 Stage.XXX 常量，当前是 {stage_expr.value.id}.{stage_expr.attr}")
                elif isinstance(stage_expr, ast.Constant) and isinstance(stage_expr.value, str):
                    if stage_expr.value not in STAGE_VALUES:
                        self._add(stage_expr, "ERROR",
                                  f"stage 字符串值 '{stage_expr.value}' 不在 Stage 常量列表中")
                    else:
                        self._add(stage_expr, "WARN",
                                  f"stage 建议用 Stage.XXX 常量而非硬编码字符串 '{stage_expr.value}'")

            # status 不建议显式传（stage_* 方法会自动填）
            if "status" in kw:
                self._add(kw["status"], "WARN",
                          "stage_* 方法会自动设置 status，无需显式传递")

        # ---- error 参数建议是异常对象 ----
        if "error" in kw and method in ("info", "debug", "warning"):
            self._add(kw["error"], "WARN",
                      "普通 info/debug/warning 不建议传 error，异常请用 error() 或 exception()")

        self.generic_visit(node)


def check_file(path: Path) -> list:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        return [(e.lineno, 0, "ERROR", f"语法错误: {e.msg}")]
    checker = LogSchemaChecker(str(path))
    checker.visit(tree)
    return checker.violations


def main():
    errors = 0
    warnings = 0
    scanned_files = 0
    violation_files = 0

    for pyfile in sorted(TARGET_DIR.rglob("*.py")):
        rel = pyfile.relative_to(PROJECT_ROOT)
        violations = check_file(pyfile)
        scanned_files += 1
        if not violations:
            continue
        violation_files += 1
        for ln, col, sev, msg in violations:
            if sev == "ERROR":
                errors += 1
            else:
                warnings += 1
            icon = "❌" if sev == "ERROR" else "⚠️ "
            print(f"{icon} {rel}:L{ln}:{col}  [{sev}]  {msg}")

    print(f"\n{'='*60}")
    print(f"扫描目录: {TARGET_DIR.relative_to(PROJECT_ROOT)}")
    print(f"扫描文件数: {scanned_files}")
    print(f"不合规文件数: {violation_files}")
    print(f"Schema 字段数: {len(SCHEMA_FIELDS)}")
    print(f"Stage 常量数: {len(STAGE_VALUES)}")
    print(f"允许扩展字段数: {len(ALLOWED_EXTRA_FIELDS)}")
    print(f"ERROR: {errors}  |  WARNING: {warnings}")

    if errors > 0:
        print("\n❌ 存在不合规调用，请修复后再提交")
        sys.exit(1)
    elif warnings > 0:
        print("\n⚠️  存在告警字段，建议补充到 LogSchema 或 ALLOWED_EXTRA_FIELDS")
        sys.exit(0)
    else:
        print("\n✅ 所有 s_*_logger 调用均符合 Schema 规范")
        sys.exit(0)


if __name__ == "__main__":
    main()
