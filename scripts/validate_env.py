#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QAnything 环境变量契约校验器
============================

从 config/env_schema.yaml 读取契约，校验所有配置入口：

  ✓ docker-compose-*.yaml  (compose)
  ✓ build_images/Dockerfile (dockerfile)
  ✓ qanything_kernel/configs/model_config.py (backend)
  ✓ front_end/.env.*        (frontend)
  ✓ .env.example           (template)

校验内容：
  1. 引用一致性：所有文件中出现的变量都在 schema 注册过
  2. 默认值一致性：默认值与 schema 中声明的 default 一致

使用：
  python scripts/validate_env.py            # 普通校验，输出报告
  python scripts/validate_env.py --strict # 有任何不一致就退出码非零
  python scripts/validate_env.py --json    # 输出 JSON 格式

退出码：
  0: 全部通过
  1: 有错误（strict模式或严重问题
  2: 有警告（仅 warn,默认允许通过
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    print("[FATAL] 需要 PyYAML，请先执行: pip install pyyaml", file=sys.stderr)
    print("        或: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = Path(os.environ.get("ENV_SCHEMA_PATH", ROOT / "config" / "env_schema.yaml"))
ENV_EXAMPLE = Path(os.environ.get("ENV_EXAMPLE_PATH", ROOT / ".env.example"))
GENERATE_SCRIPT = ROOT / "scripts" / "generate_env_example.py"


# ------------------------------------------------------------
# 生成一致性校验：复用 generate_env_example.py 生成内容比对
# ------------------------------------------------------------
def _generate_expected_content() -> Optional[str]:
    """通过 import generate_env_example 生成期望的 .env.example 内容"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import generate_env_example as ge
    except ImportError:
        return None
    finally:
        if str(Path(__file__).resolve().parent) in sys.path:
            sys.path.remove(str(Path(__file__).resolve().parent))
    try:
        schema_version, by_category = ge.load_schema()
        return ge.generate_content(schema_version, by_category)
    except Exception:
        return None


def scan_env_example_generated(schema: Dict[str, EnvVar]) -> List[Issue]:
    """校验 .env.example 是否与 schema 生成结果一致（取代原手写一致性检查）"""
    issues: List[Issue] = []

    if not ENV_EXAMPLE.exists():
        issues.append(Issue(
            "error", "template",
            str(ENV_EXAMPLE.relative_to(ROOT)),
            "文件不存在，请执行: python scripts/generate_env_example.py --write",
        ))
        return issues

    expected = _generate_expected_content()
    if expected is None:
        # 回退方案：基本变量存在性检查
        with open(ENV_EXAMPLE, "r", encoding="utf-8") as f:
            content = f.read()
        cnt_vars = 0
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                cnt_vars += 1
        schema_cnt = len(schema)
        if cnt_vars != schema_cnt:
            issues.append(Issue(
                "warning", "template",
                str(ENV_EXAMPLE.relative_to(ROOT)),
                f"无法调用生成脚本做严格校验。粗略计数: .env.example 中有 {cnt_vars} 个变量，schema 中有 {schema_cnt} 个变量。"
                "建议运行: python scripts/generate_env_example.py --check",
            ))
        return issues

    # 完全逐行比较（生成结果已无动态内容，输出完全确定）
    actual = ENV_EXAMPLE.read_text(encoding="utf-8")
    if actual == expected:
        return issues

    # 差异定位：找出前 6 处不同行号
    actual_lines = actual.splitlines()
    expected_lines = expected.splitlines()
    diffs = []
    max_lines = max(len(actual_lines), len(expected_lines))
    for i in range(max_lines):
        if i >= len(actual_lines):
            diffs.append(f"第 {i+1} 行缺失 (期望: {expected_lines[i][:60]}...)")
        elif i >= len(expected_lines):
            diffs.append(f"第 {i+1} 行多余 (实际: {actual_lines[i][:60]}...)")
        elif actual_lines[i] != expected_lines[i]:
            diffs.append(f"第 {i+1} 行不同")
            diffs.append(f"  期望: {expected_lines[i][:80]}")
            diffs.append(f"  实际: {actual_lines[i][:80]}")
        if len(diffs) >= 18:
            break

    issues.append(Issue(
        "error", "template",
        str(ENV_EXAMPLE.relative_to(ROOT)),
        ".env.example 与 schema 生成结果不一致。请执行:\n"
        "         python scripts/generate_env_example.py --write\n"
        "       前 6 处差异:\n           " + "\n           ".join(diffs[:18]),
    ))
    return issues

# ------------------------------------------------------------
# 数据结构
# ------------------------------------------------------------
@dataclass
class EnvVar:
    name: str
    default: object
    type: str = "string"
    required: bool = False
    category: str = "other"
    used_in: List[str] = field(default_factory=list)
    description: str = ""
    deprecated: bool = False


@dataclass
class Issue:
    level: str          # 'error' | 'warning' | 'info'
    source: str            # 来源类别
    file: str            # 发生的文件
    message: str          # 具体内容
    var_name: Optional[str] = None


# ------------------------------------------------------------
# 工具：加载 schema
# ------------------------------------------------------------
def load_schema() -> Dict[str, EnvVar]:
    if not SCHEMA_FILE.exists():
        print(f"[FATAL] Schema 文件不存在: {SCHEMA_FILE}", file=sys.stderr)
        sys.exit(2)

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    vars_raw = raw.get("variables", [])
    schema: Dict[str, EnvVar] = {}
    for item in vars_raw:
        name = item.get("name")
        if not name:
            continue
        schema[name] = EnvVar(
            name=name,
            default=item.get("default"),
            type=item.get("type", "string"),
            required=bool(item.get("required", False)),
            category=item.get("category", "other"),
            used_in=list(item.get("used_in", []) or []),
            description=item.get("description", ""),
            deprecated=bool(item.get("deprecated", False)),
        )
    return schema


# ------------------------------------------------------------
# 工具：正则提取
# ------------------------------------------------------------
# ${VAR_NAME:-default}  $VAR_NAME
ENV_REF_RE = re.compile(r'\$\{?(\w+)(?::-([^}]*))?\}?')
ENV_ASSIGN_RE = re.compile(r'^(\w+)=(.*)$')


def extract_env_refs(text: str) -> Set[str]:
    """从字符串中提取所有 ${VAR} 和 $VAR 引用"""
    refs = set()
    for match in ENV_REF_RE.findall(text):
        refs.add(match[0])
    return refs


def extract_env_assignments(text: str) -> Dict[str, str]:
    """提取 VAR=value 赋值（.env 文件）"""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = ENV_ASSIGN_RE.match(line)
        if m:
            result[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return result


def extract_backend_os_getenv(text: str) -> Dict[str, str]:
    """提取 Python 代码中 os.getenv('VAR', default) 读取"""
    pattern = re.compile(
        r"os\.getenv\s*\(\s*['\"](\w+)['\"]"
        r"(?:\s*,\s*(['\"]([^'\"]*)['\"]|([^)]+)))?"
    )
    result = {}
    for m in pattern.finditer(text):
        var = m.group(1)
        default = None
        if m.group(3):
            default = m.group(3).strip().strip('"').strip("'")
        elif m.group(4):
            default = m.group(4).strip()
        result[var] = default
    return result


def extract_dockerfile_env(text: str) -> Dict[str, str]:
    """提取 Dockerfile 中 ENV 定义"""
    result = {}
    # 匹配：ENV VAR=value  或  ENV VAR value  或  ENV VAR1=val1 VAR2=val2
    env_line_re = re.compile(
        r'^\s*ENV\s+(.+)', re.MULTILINE)
    for line_match in env_line_re.finditer(text):
        body = line_match.group(1).strip()
        # 支持反斜杠续行: VAR1=val1\ VAR2=val2...
        tokens = []
        buf = ""
        in_quote = False
        i = 0
        chars = list(body)
        while i < len(chars):
            c = chars[i]
            if c == "\\":
                if i + 1 < len(chars) and chars[i+1] in ('\n'):
                    i += 2
                    continue
            elif c in ('"', "'"):
                in_quote = not in_quote
            elif c.isspace() and not in_quote:
                if buf:
                    tokens.append(buf)
                    buf = ""
                i += 1
                continue
            buf += c
            i += 1
        if buf:
            tokens.append(buf)
        for tok in tokens:
            if "=" in tok:
                k, v = tok.split("=", 1)
                result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def strip_bash_default(v: str) -> str:
    """去除 bash 默认值语法:${VAR:-default} -> VAR, default"""
    m = re.fullmatch(r'\$\{(\w+)(?::-(.+))?\}', v.strip())
    if m:
        return m.group(2) or ""
    return v


# ------------------------------------------------------------
# 默认值归一化比较
# ------------------------------------------------------------
def normalize(value: str | None, expected_type: str) -> str:
    if value is None:
        return None
    s = str(value).strip()
    # 去除引号
    s = s.strip('"').strip("'")
    # bash 默认值语法展开
    s = strip_bash_default(s)
    if expected_type == "bool":
        return s.lower() in ("1", "true", "True", "yes")
    elif expected_type == "int":
        try:
            return int(s) if s != "" else None
        except (ValueError, TypeError):
            return s
    elif expected_type == "float":
        try:
            return float(s) if s != "" else None
        except (ValueError, TypeError):
            return s
    return s


def defaults_match(schema_val, actual: str) -> bool:
    """判断 schema 默认值和实际值是否相等（宽松比较）"""
    if schema_val == actual:
        return True
    # None 和 "" 视为等价
    if schema_val is None and actual in ("", "None", None):
        return True
    if isinstance(schema_val, bool):
        return normalize(actual, "bool") == schema_val
    if isinstance(schema_val, int):
        return normalize(actual, "int") == schema_val
    if isinstance(schema_val, float):
        return normalize(actual, "float") == schema_val
    # 字符串宽松比较
    return str(schema_val).strip() == str(actual).strip()


# ------------------------------------------------------------
# 各入口扫描函数
# ------------------------------------------------------------
def scan_compose(schema: Dict[str, EnvVar]) -> List[Issue]:
    issues: List[Issue] = []
    compose_files = sorted(ROOT.glob("docker-compose*.yaml")) + \
                         list(ROOT.glob("docker-compose*.yml"))
    for cf in compose_files:
        try:
            with open(cf, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            issues.append(Issue("error", "compose", str(cf.relative_to(ROOT)),
                          "无法读取文件"))
            continue
        # 1) 所有 ${VAR} 引用
        refs = extract_env_refs(text)
        for var in sorted(refs):
            if var == "DOCKER_VOLUME_DIRECTORY":
                continue
            if var not in schema:
                issues.append(Issue(
                    "error", "compose",
                    str(cf.relative_to(ROOT)),
                    f"变量 ${var} 在 compose 文件中引用，但未在 env_schema.yaml 注册",
                    var_name=var,
                ))
        # 2) environment 列表里显式赋值默认值检查
        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            issues.append(Issue("warning", "compose", str(cf.relative_to(ROOT)),
                          "YAML 解析失败，跳过 environment 默认值检查"))
            continue
        services = data.get("services", {}) or {}
        for svc_name, svc_cfg in services.items():
            if not isinstance(svc_cfg, dict):
                continue
            environment = svc_cfg.get("environment") or []
            env_dict = {}
            if isinstance(environment, list):
                for item in environment:
                    if "=" in item:
                        k, v = item.split("=", 1)
                        env_dict[k] = v
            elif isinstance(environment, dict):
                env_dict = dict(environment)
            for var_name, actual_default in env_dict.items():
                actual_stripped = strip_bash_default(str(actual_default))
                # 某些 compose 特有值是合理的：
                # - 容器内部端口（3306、19530、9200）不同于宿主机映射端口
                # - 使用容器服务名（mysql/standalone/elasticsearch 等）代替 localhost
                # - USER_IP=0.0.0.0 是容器内部监听地址
                compose_overrides = {
                    "MYSQL_HOST": ("mysql",),
                    "MYSQL_PORT": ("3306",),
                    "MILVUS_HOST": ("standalone",),
                    "MILVUS_PORT": ("19530",),
                    "ES_HOST": ("elasticsearch",),
                    "ES_PORT": ("9200",),
                    "USER_IP": ("0.0.0.0",),
                    "ETCD_ENDPOINTS": ("etcd:2379",),
                    "MINIO_ADDRESS": ("minio:9000",),
                    "GATEWAY_IP": ("127.0.0.1", "host.docker.internal"),
                }
                is_compose_specific = (
                    var_name in compose_overrides
                    and actual_stripped in compose_overrides[var_name]
                )
                if var_name in schema and not is_compose_specific and not defaults_match(
                    schema[var_name].default, actual_stripped):
                    issues.append(Issue(
                        "warning", "compose",
                        str(cf.relative_to(ROOT)),
                        f"{svc_name}.environment.{var_name}: 默认值与 schema 不一致 "
                        f"(schema={schema[var_name].default!r} actual={actual_stripped!r}",
                        var_name=var_name,
                    ))
    return issues


def scan_dockerfile(schema: Dict[str, EnvVar]) -> List[Issue]:
    issues: List[Issue] = []
    dockerfiles = ROOT / "build_images" / "Dockerfile"
    if dockerfiles.exists():
        with open(dockerfiles, "r", encoding="utf-8") as f:
            text = f.read()
        envs = extract_dockerfile_env(text)
        for var, actual in sorted(envs.items()):
            if var not in schema:
                issues.append(Issue(
                    "warning", "dockerfile",
                    str(dockerfiles.relative_to(ROOT)),
                    f"ENV {var} 在 Dockerfile 中定义，但未在 env_schema.yaml 注册",
                    var_name=var,
                ))
            # 特殊情况：TIKTOKEN_CACHE_DIR 在 Dockerfile 中有具体路径是合理的（schema 中 null 表示不指定）
            elif var == "TIKTOKEN_CACHE_DIR" and actual.startswith("/"):
                pass  # Dockerfile 设定具体路径是合理行为
            elif not defaults_match(schema[var].default, actual):
                issues.append(Issue(
                    "warning", "dockerfile",
                    str(dockerfiles.relative_to(ROOT)),
                    f"ENV {var}: 默认值与 schema 不一致 "
                    f"(schema={schema[var].default!r} actual={actual!r})",
                    var_name=var,
                ))
    return issues


def scan_backend(schema: Dict[str, EnvVar]) -> List[Issue]:
    issues: List[Issue] = []
    model_config = ROOT / "qanything_kernel" / "configs" / "model_config.py"
    if model_config.exists():
        with open(model_config, "r", encoding="utf-8") as f:
            text = f.read()
        envs = extract_backend_os_getenv(text)
        for var, actual_default in sorted(envs.items()):
            if var not in schema:
                issues.append(Issue(
                    "error", "backend",
                    str(model_config.relative_to(ROOT)),
                    f"os.getenv('{var}') 在 model_config.py 中读取，但未在 env_schema.yaml 注册",
                    var_name=var,
                ))
            elif actual_default is not None:
                stripped = strip_bash_default(str(actual_default))
                # 特殊情况：后端使用 GATEWAY_IP 作为 Milvus/ES/MySQL 的默认 host 是合理设计
                backend_gateway_fallback = ("MYSQL_HOST", "MILVUS_HOST", "ES_HOST")
                is_gateway_fallback = (
                    var in backend_gateway_fallback and "GATEWAY_IP" in stripped
                )
                if not is_gateway_fallback and not defaults_match(schema[var].default, stripped):
                    issues.append(Issue(
                        "warning", "backend",
                        str(model_config.relative_to(ROOT)),
                        f"os.getenv('{var}'): 默认值与 schema 不一致 "
                        f"(schema={schema[var].default!r} actual={stripped!r})",
                        var_name=var,
                    ))
    return issues


def scan_frontend(schema: Dict[str, EnvVar]) -> List[Issue]:
    issues: List[Issue] = []
    fe_dir = ROOT / "front_end"
    env_files = sorted(fe_dir.glob(".env.*"))
    for ef in env_files:
        with open(ef, "r", encoding="utf-8") as f:
            text = f.read()
        envs = extract_env_assignments(text)
        for var, actual in sorted(envs.items()):
            # 特殊情况：.env.production 中 VITE_APP_MODE=prod 是合理的
            is_prod_mode_ok = (
                ef.name == ".env.production"
                and var == "VITE_APP_MODE"
                and actual in ("prod", "production")
            )
            if var not in schema:
                issues.append(Issue(
                    "warning", "frontend",
                    str(ef.relative_to(ROOT)),
                    f"{var}= 在前端 env 文件中定义，但未在 env_schema.yaml 注册",
                    var_name=var,
                ))
            elif not is_prod_mode_ok and not defaults_match(schema[var].default, actual):
                issues.append(Issue(
                    "info", "frontend",
                    str(ef.relative_to(ROOT)),
                    f"{var}: 默认值与 schema 不一致 "
                    f"(schema={schema[var].default!r} actual={actual!r})",
                    var_name=var,
                ))
    # 检查 vite.config.ts - 只匹配 import.meta.env.VAR_NAME 或 process.env.VAR_NAME 形式
    vite_cfg = fe_dir / "vite.config.ts"
    if vite_cfg.exists():
        with open(vite_cfg, "r", encoding="utf-8") as f:
            text = f.read()
        env_pattern = re.compile(r'(?:import\.meta\.env|process\.env)\.(\w+)')
        refs = set(env_pattern.findall(text))
        for var in sorted(refs):
            if var in ("", "import", "process", "meta", "NODE_ENV"):
                continue
            if var not in schema:
                issues.append(Issue(
                    "error", "frontend",
                    str(vite_cfg.relative_to(ROOT)),
                    f"引用 {var} 在 vite.config.ts 中，但未在 env_schema.yaml 注册",
                    var_name=var,
                ))
    return issues


def scan_env_example(schema: Dict[str, EnvVar]) -> List[Issue]:
    issues: List[Issue] = []
    env_example = ROOT / ".env.example"
    if env_example.exists():
        with open(env_example, "r", encoding="utf-8") as f:
            text = f.read()
        envs = extract_env_assignments(text)
        schema_required = {v.name for v in schema.values() if not v.deprecated}
        example_vars = set(envs.keys())
        # 检查 schema 中的变量有没有漏在 .env.example
        missing = schema_required - example_vars
        for var in sorted(missing):
            issues.append(Issue(
                "warning", "template",
                str(env_example.relative_to(ROOT)),
                f"变量 {var} 在 env_schema.yaml 中定义，但未在 .env.example 中列出",
                var_name=var,
            ))
        # 检查 .env.example 的默认值一致性
        for var, actual in sorted(envs.items()):
            if var in schema and not defaults_match(schema[var].default, actual):
                issues.append(Issue(
                    "warning", "template",
                    str(env_example.relative_to(ROOT)),
                    f"{var}: 默认值与 schema 不一致 "
                    f"(schema={schema[var].default!r} actual={actual!r})",
                    var_name=var,
                ))
    return issues


# ------------------------------------------------------------
# 报告输出
# ------------------------------------------------------------
def print_report(all_issues: List[Issue], show_json: bool, schema: Dict[str, EnvVar]):
    errors = sum(1 for i in all_issues if i.level == "error")
    warnings = sum(1 for i in all_issues if i.level == "warning")

    if show_json:
        report = {
            "summary": {
                "total": len(all_issues),
                "errors": errors,
                "warnings": warnings,
                "infos": sum(1 for i in all_issues if i.level == "info"),
            },
            "issues": [
                {
                    "level": i.level,
                    "source": i.source,
                    "file": i.file,
                    "var_name": i.var_name,
                    "message": i.message,
                }
                for i in all_issues
            ],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return errors, warnings

    # 彩色终端报告
    colors = {
        "error": "\033[31m",
        "warning": "\033[33m",
        "info": "\033[36m",
        "ok": "\033[32m",
        "reset": "\033[0m",
    }
    icons = {"error": "✗", "warning": "⚠", "info": "ℹ", "ok": "✓"}

    by_source = defaultdict(list)
    for i in all_issues:
        by_source[i.source].append(i)

    print("=" * 72)
    print("  QAnything 环境变量契约校验报告")
    print("=" * 72)

    infos = sum(1 for i in all_issues if i.level == "info")

    print(f"  Schema: config/env_schema.yaml")
    print(f"  变量数: {len(schema)} 个注册变量")
    print()

    if not all_issues:
        print(f"  {colors['ok']}{icons['ok']} 全部通过: 0 错误 / 0 警告 / 0 信息{colors['reset']}")
    else:
        status_parts = []
        if errors:
            status_parts.append(f"{colors['error']}{errors} 错误{colors['reset']}")
        if warnings:
            status_parts.append(f"{colors['warning']}{warnings} 警告{colors['reset']}")
        if infos:
            status_parts.append(f"{colors['info']}{infos} 信息{colors['reset']}")
        print(f"  结果: {' / '.join(status_parts)}")
    print()

    source_names = {
        "compose": "Docker Compose 文件",
        "dockerfile": "Dockerfile",
        "backend": "后端 Python 代码",
        "frontend": "前端配置",
        "template": ".env.example 模板",
    }

    for source in sorted(by_source.keys()):
        source_issues = sorted(
            [i for i in all_issues if i.source == source], key=lambda x: (x.level, x.file, x.var_name or "")
        )
        src_label = source_names.get(source, source)
        src_errors = sum(1 for i in source_issues if i.level == "error")
        src_warnings = sum(1 for i in source_issues if i.level == "warning")

        header = f"--- {src_label}"
        if src_errors or src_warnings:
            parts = []
            if src_errors:
                parts.append(f"{colors['error']}{src_errors}E{colors['reset']}")
            if src_warnings:
                parts.append(f"{colors['warning']}{src_warnings}W{colors['reset']}")
            header += f" ({' '.join(parts)})"
        print(header)

        current_file = None
        for i in source_issues:
            if i.file != current_file:
                print(f"  📄 {i.file}")
                current_file = i.file
            color = colors[i.level]
            icon = icons[i.level]
            prefix = f"    {color}{icon}{colors['reset']}"
            if i.var_name:
                print(f"{prefix} [{i.var_name}] {i.message}")
            else:
                print(f"{prefix} {i.message}")
        print()

    print("=" * 72)
    if errors == 0 and warnings == 0:
        print(f"  {colors['ok']}环境变量契约校验全部通过 ✓{colors['reset']}")
    else:
        print("  提示: 修复后重新运行: python scripts/validate_env.py")
        print("        新增变量请编辑: config/env_schema.yaml")
    print("=" * 72)
    return errors, warnings


# ------------------------------------------------------------
# 主函数
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="QAnything 环境变量契约校验")
    parser.add_argument("--strict", action="store_true",
                        help="严格模式: 警告也视为失败")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="以 JSON 格式输出报告")
    parser.add_argument("--skip-ok", action="store_true",
                        help="仅显示有问题的项")
    args = parser.parse_args()

    schema = load_schema()
    all_issues: List[Issue] = []

    scanners = [
        scan_compose,
        scan_dockerfile,
        scan_backend,
        scan_frontend,
        scan_env_example_generated,
    ]

    for sc in scanners:
        try:
            all_issues.extend(sc(schema))
        except Exception as exc:
            all_issues.append(Issue(
                "error", "internal", "validate_env.py",
                f"扫描器 {sc.__name__} 异常: {exc}",
            ))

    errors, warnings = print_report(all_issues, args.json_out, schema)

    # 退出码
    if args.strict:
        sys.exit(1 if (errors or warnings) else 0)
    else:
        sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
