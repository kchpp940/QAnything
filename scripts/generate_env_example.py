#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 config/env_schema.yaml 生成 .env.example

使用方法：
  python scripts/generate_env_example.py            # 生成到标准输出，可预览
  python scripts/generate_env_example.py --write    # 写入 .env.example 文件
  python scripts/generate_env_example.py --check    # 仅检查当前 .env.example 是否与生成结果一致
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[FATAL] 需要 PyYAML，请先执行: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "config" / "env_schema.yaml"
OUTPUT_FILE = ROOT / ".env.example"


# category -> (中文分类名, 中文描述)
CATEGORY_META = {
    "runtime":  ("基础运行配置", "服务启动模式、监听地址、Worker 数等基础参数"),
    "mysql":    ("MySQL 数据库连接", "本地 MySQL / MariaDB 连接参数"),
    "milvus":   ("Milvus 向量数据库连接", "Milvus、Etcd、MinIO 连接参数"),
    "es":       ("Elasticsearch 连接", "Elasticsearch 连接和检索参数"),
    "services": ("本地依赖服务端口", "Embedding、Rerank、OCR、PDF 解析等依赖服务"),
    "kb":       ("知识库与检索配置", "向量检索阈值、分块大小、句子长度等"),
    "paths":    ("文件存储路径", "上传文件、Docker 卷、缓存目录等"),
    "frontend": ("前端相关", "Vite 开发模式、API 地址、路径前缀等"),
    "images":   ("Docker 镜像配置", "各组件 Docker 镜像版本标签"),
    "other":    ("其他配置", "杂项参数"),
}


def format_default(value) -> str:
    """将 schema 中的 default 值格式化为 .env 文件中的字符串"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def load_schema():
    if not SCHEMA_FILE.exists():
        print(f"[FATAL] Schema 文件不存在: {SCHEMA_FILE}", file=sys.stderr)
        sys.exit(2)

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    schema_version = raw.get("schema_version", "1.0")
    variables = raw.get("variables", []) or []

    # 按 category 分组，保留原 order
    by_category: dict[str, list[dict]] = {}
    for item in variables:
        cat = item.get("category", "other")
        by_category.setdefault(cat, []).append(item)

    return schema_version, by_category


def generate_content(schema_version: str, by_category: dict[str, list[dict]]) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 文件头
    lines.append("# ============================================================")
    lines.append("# QAnything 统一环境变量契约")
    lines.append("# ============================================================")
    lines.append("#")
    lines.append(f"# ⚠️   此文件由 scripts/generate_env_example.py 自动生成，请勿手动修改！")
    lines.append(f"# 📋 来源配置：config/env_schema.yaml  (schema_version={schema_version})")
    lines.append(f"# 🔧 生成时间：{now}")
    lines.append("#")
    lines.append("# 使用方法：")
    lines.append("#   cp .env.example .env        # 复制为本地配置")
    lines.append("#   vim .env                     # 按需修改本地值")
    lines.append("#")
    lines.append("# 新增/修改变量：")
    lines.append("#   1) 编辑 config/env_schema.yaml")
    lines.append("#   2) 运行 python scripts/generate_env_example.py --write")
    lines.append("#   3) 运行 python scripts/validate_env.py 做一致性校验")
    lines.append("#")
    lines.append("")

    # 按 CATEGORY_META 顺序生成分类
    categories_to_emit = list(CATEGORY_META.keys()) + [
        c for c in by_category.keys() if c not in CATEGORY_META
    ]

    for idx, cat in enumerate(categories_to_emit, start=1):
        if cat not in by_category:
            continue

        cat_vars = by_category[cat]
        cat_name, cat_desc = CATEGORY_META.get(cat, (f"分类 {cat}", ""))

        lines.append("# ------------------------------------------------------------")
        lines.append(f"# {idx}、{cat_name}")
        if cat_desc:
            lines.append(f"#     {cat_desc}")
        lines.append("# ------------------------------------------------------------")
        lines.append("")

        for var in cat_vars:
            name = var.get("name", "")
            default = var.get("default")
            desc = var.get("description", "")
            required = var.get("required", False)
            deprecated = var.get("deprecated", False)

            if not name:
                continue

            # 变量说明注释
            prefix_parts = []
            if deprecated:
                prefix_parts.append("【已弃用】")
            if required:
                prefix_parts.append("【必填】")
            label = " ".join(prefix_parts)
            if desc:
                if label:
                    lines.append(f"# {label}{desc}")
                else:
                    lines.append(f"# {desc}")
            elif label:
                lines.append(f"# {label}")

            # TYPE 提示
            var_type = var.get("type", "string")
            lines.append(f"#   └─ 类型: {var_type}{'  默认值=' + repr(format_default(default)) if default is not None else ''}")

            # VAR=value 行
            lines.append(f"{name}={format_default(default)}")
            lines.append("")

    # 结尾注释
    lines.append("# ============================================================")
    lines.append("# 生成结束")
    lines.append("# ============================================================")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="从 config/env_schema.yaml 生成 .env.example")
    parser.add_argument("--write", action="store_true",
                        help="将生成内容写入 .env.example 文件（默认仅输出到 stdout）")
    parser.add_argument("--check", action="store_true",
                        help="不写入，仅检查当前 .env.example 是否与 schema 生成结果一致")
    args = parser.parse_args()

    schema_version, by_category = load_schema()
    content = generate_content(schema_version, by_category)

    if args.check:
        if not OUTPUT_FILE.exists():
            print("[FAIL] .env.example 文件不存在", file=sys.stderr)
            sys.exit(1)
        existing = OUTPUT_FILE.read_text(encoding="utf-8")
        # 逐行比较，忽略换行符差异和时间戳行
        gen_lines = [l for l in content.splitlines()
                     if not l.startswith("# 🔧 生成时间：")]
        cur_lines = [l for l in existing.splitlines()
                     if not l.startswith("# 🔧 生成时间：")]
        if gen_lines == cur_lines:
            print("[OK] .env.example 与 schema 生成结果一致 ✓")
            sys.exit(0)
        else:
            print("[FAIL] .env.example 与 schema 生成结果不一致 ✗", file=sys.stderr)
            print("       请执行: python scripts/generate_env_example.py --write", file=sys.stderr)
            sys.exit(1)

    if args.write:
        OUTPUT_FILE.write_text(content, encoding="utf-8")
        print(f"[OK] 已生成: {OUTPUT_FILE}")
        print(f"     变量数: {sum(len(v) for v in by_category.values())} 个")
        print(f"     分类数: {len(by_category)} 个")
        sys.exit(0)

    # 默认输出到 stdout
    sys.stdout.write(content)


if __name__ == "__main__":
    main()
