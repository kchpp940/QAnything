#!/usr/bin/env node
/**
 * check-api-boundary.mjs
 *
 * 轻量 API 边界扫描脚本。
 *
 * 作用：在 components / views / store 目录中检查是否出现：
 *   1. 直接导入旧入口：`@/services/urlConfig` 或 `@/interface`
 *   2. 直接导入 Raw 类型（`*Raw`），这些类型仅限 services/api 内部使用
 *   3. 直接调用旧请求对象：`urlResquest.xxx(...)`
 *   4. 直接导入已迁移的旧类型（utils/types.ts 中带 @deprecated 的那些）：
 *      IDataSourceItem / IChatItem / ITimeInfo / ITokenInfo / IChatSetting /
 *      IFileListItem / IUrlListItem / IAajxRes
 *
 * 豁免：
 *   - src/services/api/** 内部目录（Raw 类型只允许在 adapter/client/types 内部）
 *   - 行内注释 `// eslint-disable-next-line no-restricted-imports` 或 `// @ts-ignore`
 *   - 注释掉的代码（行首为 `//` 或块注释）
 *
 * 退出码：
 *   0 - 没有违规
 *   1 - 有违规（将阻止 lint-staged / pre-commit 或 CI）
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';
import { pathToFileURL } from 'node:url';

const ROOT = resolve(import.meta.dirname, '..');
const SRC = join(ROOT, 'src');

const TARGET_DIRS = ['components', 'views', 'store'];

const EXCLUDED_DIRS = new Set(['node_modules', 'dist', '.git']);

const IMPORT_URLCONFIG_RE = /from\s+['"](@\/services\/urlConfig)['"]/;
const IMPORT_INTERFACE_RE = /from\s+['"](@\/interface)['"]/;

const IMPORT_RAW_TYPE_RE =
  /import\s+(?:type\s+)?(?:\{[^}]*\b(\w+Raw)\b[^}]*\}|\*\s+as\s+\w+|\w+Raw)\s+from\s+['"][^'"]+['"]/;
const IMPORT_RAW_TYPE_GROUP_RE = /\b(\w+Raw)\b/g;

const URLREQUEST_CALL_RE = /\burlResquest\s*\.\s*\w+\s*\(/;

const DEPRECATED_TYPE_IMPORT_RE =
  /import\s+(?:type\s+)?\{[^}]*\b(IDataSourceItem|IChatItem|ITimeInfo|ITokenInfo|IChatSetting|IFileListItem|IUrlListItem|IAajxRes)\b[^}]*\}\s+from\s+['"](@\/utils\/types|@\/interface)['"]/;
const DEPRECATED_TYPE_GROUP_RE =
  /\b(IDataSourceItem|IChatItem|ITimeInfo|ITokenInfo|IChatSetting|IFileListItem|IUrlListItem|IAajxRes)\b/g;

function walk(dir, out = []) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    if (EXCLUDED_DIRS.has(entry.name)) continue;
    if (entry.name.startsWith('.')) continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, out);
    } else if (/\.(ts|tsx|js|jsx|vue)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

function isLineDisabled(line) {
  if (/^\s*\/\//.test(line)) return true;
  if (/^\s*\*/.test(line)) return true;
  if (/\/\/\s*eslint-disable-next-line/.test(line)) return true;
  if (/\/\/\s*@ts-ignore/.test(line)) return true;
  return false;
}

function collectFiles() {
  const files = [];
  for (const dirName of TARGET_DIRS) {
    const dir = join(SRC, dirName);
    try {
      if (statSync(dir).isDirectory()) walk(dir, files);
    } catch {
      // 目录不存在就跳过
    }
  }
  return files;
}

function checkFile(filePath) {
  const content = readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/);
  const offenses = [];

  let inBlockComment = false;

  lines.forEach((rawLine, i) => {
    const lineNo = i + 1;
    const trimmed = rawLine.trim();

    if (trimmed.startsWith('/*')) inBlockComment = true;
    if (inBlockComment) {
      if (trimmed.includes('*/')) inBlockComment = false;
      return;
    }

    if (isLineDisabled(rawLine)) return;

    const relFile = relative(ROOT, filePath).split(sep).join('/');

    let m;

    m = rawLine.match(IMPORT_URLCONFIG_RE);
    if (m) {
      offenses.push({
        file: relFile,
        line: lineNo,
        code: 'no-old-url-config',
        message: `禁止导入旧接口入口 ${m[1]}，请改用 @/services/api 或 @/utils/session`,
      });
    }

    m = rawLine.match(IMPORT_INTERFACE_RE);
    if (m) {
      offenses.push({
        file: relFile,
        line: lineNo,
        code: 'no-old-interface',
        message: `禁止导入旧类型入口 ${m[1]}，请改用 @/services/api/types 下的业务对象类型`,
      });
    }

    if (IMPORT_RAW_TYPE_RE.test(rawLine)) {
      const names = [];
      let nm;
      const clone = new RegExp(IMPORT_RAW_TYPE_GROUP_RE.source, 'g');
      while ((nm = clone.exec(rawLine)) !== null) {
        if (!nm[1].endsWith('RouteRecordRaw')) names.push(nm[1]);
      }
      if (names.length) {
        offenses.push({
          file: relFile,
          line: lineNo,
          code: 'no-raw-type',
          message: `禁止直接导入 Raw 类型：${names.join(', ')}。请消费 adapter 后的业务对象；确有需要请通过业务对象的 .raw 属性访问原始字段`,
        });
      }
    }

    m = rawLine.match(URLREQUEST_CALL_RE);
    if (m) {
      offenses.push({
        file: relFile,
        line: lineNo,
        code: 'no-urlResquest-call',
        message: `禁止调用 urlResquest，请改用 @/services/api 中对应业务域的 api.xxx 方法`,
      });
    }

    if (DEPRECATED_TYPE_IMPORT_RE.test(rawLine)) {
      const names = [];
      let nm;
      const clone = new RegExp(DEPRECATED_TYPE_GROUP_RE.source, 'g');
      while ((nm = clone.exec(rawLine)) !== null) names.push(nm[1]);
      if (names.length) {
        offenses.push({
          file: relFile,
          line: lineNo,
          code: 'no-deprecated-type',
          message: `禁止使用已废弃类型 ${names.join(', ')}，请改用 @/services/api/types 中对应的规范化业务对象`,
        });
      }
    }
  });

  return offenses;
}

function main() {
  const files = collectFiles();
  const blocking = [];
  const warnings = [];

  for (const file of files) {
    for (const off of checkFile(file)) {
      if (off.code === 'no-deprecated-type') {
        warnings.push(off);
      } else {
        blocking.push(off);
      }
    }
  }

  if (warnings.length) {
    process.stdout.write(
      `⚠️  API 边界扫描告警：发现 ${warnings.length} 处对已废弃类型的引用（不阻断提交，建议逐步迁移）\n\n`
    );
    for (const off of warnings) {
      process.stdout.write(
        `  ${off.file}:${off.line}  [${off.code}]\n` +
          `      ${off.message}\n`
      );
    }
    process.stdout.write('\n');
  }

  if (blocking.length === 0) {
    process.stdout.write('✅ API 边界扫描通过：未发现阻断级违规引用\n');
    process.exit(0);
  }

  process.stderr.write(
    `❌ API 边界扫描失败：发现 ${blocking.length} 处阻断级违规引用\n\n`
  );

  for (const off of blocking) {
    process.stderr.write(
      `  ${off.file}:${off.line}  [${off.code}]\n` +
        `      ${off.message}\n\n`
    );
  }

  process.stderr.write(
    '修复指引：\n' +
      '  · 旧请求入口   →  使用 @/services/api 中的 api.{knowledge,chat,bot,statistics,upload}.xxx()\n' +
      '  · 用户上下文   →  使用 @/utils/session 中的 userId / getUserPhone() / getUserContext()\n' +
      '  · Raw 类型     →  使用 adapter 后的业务对象（IKnowledgeBase / IKbFile / IBot / IQARecord ...）\n' +
      '  · 已废弃类型   →  对应关系见 utils/types.ts 顶部说明\n\n'
  );

  process.exit(1);
}

main();
