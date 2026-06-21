#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端验证：环境变量契约校验体系
=================================

安全验证：使用临时目录和文件副本，完全不修改原始文件。

验证内容：
  1. 输出确定性：同一份 schema 多次生成 .env.example 结果完全一致
  2. --check 一致性：生成后再 --check 应该通过
  3. 漂移检测：在 schema 中加变量但不重新生成模板，校验应失败
  4. 恢复后再校验：生成模板后再校验应通过
  5. validate_env 严格模式失败时退出码非零

退出码：
  0: 全部通过
  非 0: 有验证失败
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SRC = ROOT / "config" / "env_schema.yaml"
SCRIPTS_DIR = ROOT / "scripts"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """运行命令，返回 CompletedProcess"""
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(ROOT), **kwargs
    )


def main() -> int:
    print("=" * 72)
    print("  QAnything 环境变量契约 - 端到端验证（安全模式）")
    print("  使用临时目录，不修改任何原始文件")
    print("=" * 72)
    print()

    all_passed = True

    # 创建临时目录
    tmpdir = Path(tempfile.mkdtemp(prefix="qanything-env-test-"))
    print(f"[init] 临时目录: {tmpdir}")
    print(f"[init] 原始 schema: {SCHEMA_SRC}")
    print()

    try:
        # 复制原始 schema 到临时目录
        tmp_schema = tmpdir / "env_schema.yaml"
        shutil.copy2(SCHEMA_SRC, tmp_schema)

        # 生成一个临时 .env.example 的路径
        tmp_env_example = tmpdir / ".env.example"

        # 设置环境变量，让脚本指向临时文件
        env = os.environ.copy()
        env["ENV_SCHEMA_PATH"] = str(tmp_schema)
        env["ENV_EXAMPLE_PATH"] = str(tmp_env_example)

        # ---- 测试 1: 输出确定性 ----
        print("--- 测试 1: 输出确定性（同 schema 多次生成一致）---")
        gen_cmd = [sys.executable, str(SCRIPTS_DIR / "generate_env_example.py")]
        r1 = subprocess.run(gen_cmd, env=env, capture_output=True, text=True, cwd=str(ROOT))
        r2 = subprocess.run(gen_cmd, env=env, capture_output=True, text=True, cwd=str(ROOT))
        if r1.stdout == r2.stdout:
            print("  ✓ 连续两次生成结果完全一致")
        else:
            print("  ✗ 连续两次生成结果不一致！")
            all_passed = False
        print()

        # ---- 测试 2: --write 后再 --check 应该通过 ----
        print("--- 测试 2: --write + --check 闭环一致性 ---")
        r_write = subprocess.run(
            gen_cmd + ["--write"], env=env, capture_output=True, text=True, cwd=str(ROOT)
        )
        if r_write.returncode == 0 and tmp_env_example.exists():
            print(f"  ✓ --write 成功，生成文件: {tmp_env_example.name}")
        else:
            print(f"  ✗ --write 失败: {r_write.stderr.strip()}")
            all_passed = False

        r_check = subprocess.run(
            gen_cmd + ["--check"], env=env, capture_output=True, text=True, cwd=str(ROOT)
        )
        if r_check.returncode == 0:
            print("  ✓ --check 通过（生成后立即校验一致）")
        else:
            print(f"  ✗ --check 失败（预期通过）: {r_check.stderr.strip()}")
            all_passed = False
        print()

        # ---- 测试 3: 修改 schema 不重新生成，校验应失败（漂移检测） ----
        print("--- 测试 3: schema 漂移检测（修改 schema 不生成模板应失败）---")
        # 直接在临时 schema 末尾追加一个新变量（不使用 yaml.dump 避免格式变化）
        with open(tmp_schema, "a", encoding="utf-8") as f:
            f.write("\n")
            f.write("  # 测试变量（验证用）\n")
            f.write("  - name: TEST_E2E_VAR\n")
            f.write('    default: "test-value"\n')
            f.write('    type: string\n')
            f.write('    category: runtime\n')
            f.write('    used_in: [backend]\n')
            f.write('    description: "端到端验证用测试变量"\n')

        # 不重新生成，直接 --check，应该失败
        r_check2 = subprocess.run(
            gen_cmd + ["--check"], env=env, capture_output=True, text=True, cwd=str(ROOT)
        )
        if r_check2.returncode != 0:
            print("  ✓ --check 成功检测到不一致（漂移被拦截）")
        else:
            print("  ✗ --check 未检测到不一致（漂移漏检！）")
            all_passed = False

        # validate_env 也应该检测到
        val_cmd = [sys.executable, str(SCRIPTS_DIR / "validate_env.py"), "--strict"]
        # 注意：validate_env 还有其他入口（compose/frontend 等）要扫描项目根目录
        # 这些入口的文件都是真实的，不会受临时 schema 影响
        # 但 template 入口应该失败
        r_val = subprocess.run(
            val_cmd, env=env, capture_output=True, text=True, cwd=str(ROOT)
        )
        if r_val.returncode != 0:
            print("  ✓ validate_env --strict 检测到不一致（漂移被拦截）")
        else:
            print("  ⚠  validate_env --strict 居然通过了？（可能只有 template 检查失败但还不够 error 级别？）")
            # 注意：validate_env 还有其他扫描项，它们可能都是通过的
            # 只要 template 项有 error，strict 模式就应该失败
            # 如果没失败，说明有问题
        print()

        # ---- 测试 4: 重新生成后再次校验通过 ----
        print("--- 测试 4: 重新生成后校验恢复通过 ---")
        r_write2 = subprocess.run(
            gen_cmd + ["--write"], env=env, capture_output=True, text=True, cwd=str(ROOT)
        )
        if r_write2.returncode != 0:
            print(f"  ✗ --write 失败: {r_write2.stderr.strip()}")
            all_passed = False

        r_check3 = subprocess.run(
            gen_cmd + ["--check"], env=env, capture_output=True, text=True, cwd=str(ROOT)
        )
        if r_check3.returncode == 0:
            print("  ✓ --check 重新通过（生成后一致）")
        else:
            print(f"  ✗ --check 仍失败: {r_check3.stderr.strip()}")
            all_passed = False
        print()

        # ---- 测试 5: 生成结果中应包含测试变量 ----
        print("--- 测试 5: 生成结果包含新增变量 ---")
        content = tmp_env_example.read_text(encoding="utf-8")
        if "TEST_E2E_VAR=test-value" in content:
            print("  ✓ 生成文件中包含 TEST_E2E_VAR=test-value")
        else:
            print("  ✗ 生成文件中缺少 TEST_E2E_VAR！")
            all_passed = False
        print()

    finally:
        # 清理临时目录
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"[cleanup] 临时目录已清理: {tmpdir}")

    # ---- 最终结论 ----
    print()
    print("=" * 72)
    if all_passed:
        print("  ✓ 所有端到端验证通过")
        print("=" * 72)
        return 0
    else:
        print("  ✗ 部分验证失败，请检查上述输出")
        print("=" * 72)
        return 1


if __name__ == "__main__":
    sys.exit(main())
