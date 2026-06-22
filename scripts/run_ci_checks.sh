#!/bin/bash
# CI 校验脚本：串联 Schema 静态校验 + 全链路动态验证
# 退出码：0=全部通过，非 0=失败
#
# 使用方式：
#     # 本地运行
#     bash scripts/run_ci_checks.sh
#
#     # GitHub Actions 接入示例：
#     # - name: Run Log Schema and Chain Checks
#     #   run: bash scripts/run_ci_checks.sh
#
#     # GitLab CI 接入示例：
#     # log_checks:
#     #   script:
#     #     - bash scripts/run_ci_checks.sh
#
#     # pre-commit 接入（.pre-commit-config.yaml）：
#     # - repo: local
#     #   hooks:
#     #     - id: validate-log-schema
#     #       name: Validate Log Schema
#     #       entry: python scripts/validate_log_schema.py
#     #       language: system
#     #       pass_filenames: false

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "============================================================"
echo "  CI 校验：日志 Schema + 全链路 Request ID"
echo "============================================================"

echo ""
echo "▶ Step 1: Schema 静态校验（扫描所有 s_*_logger 调用）"
python scripts/validate_log_schema.py
STEP1_EXIT=$?

echo ""
echo "▶ Step 2: 全链路动态验证（60 个测试点）"
python scripts/verify_request_id_chain.py
STEP2_EXIT=$?

echo ""
echo "============================================================"
if [ $STEP1_EXIT -eq 0 ] && [ $STEP2_EXIT -eq 0 ]; then
    echo "  ✅ 所有 CI 校验通过"
    echo "============================================================"
    exit 0
else
    echo "  ❌ CI 校验失败，请修复后再提交"
    echo "  - Schema 校验退出码: $STEP1_EXIT"
    echo "  - 链路验证退出码: $STEP2_EXIT"
    echo "============================================================"
    exit 1
fi
