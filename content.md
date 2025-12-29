好的，我完全理解。这是一个典型的开发者体验（DX）优化，通过统一的视觉语言（前缀、表情符号、缩进）来增强命令行工具的可读性和专业性。不一致的格式会让用户感到困惑，并使输出难以解析。

我们现在就来执行这个“视觉风格统一”任务。我将系统性地审查并更新所有 `en` 和 `zh` 目录下的 JSON 消息文件，确保它们遵循一套统一的设计规范。

首先，这是执行此项改进的计划。

## [WIP] style: 统一 CLI 输出消息的视觉风格

### 用户需求
统一所有 `stitcher-common` 包中的 `needle` 消息文件（`.json`），确保命令行输出（特别是 `stitcher check`）在格式、缩进和表情符号使用上保持一致，以提升可读性和专业性。

### 评论
这是一个非常有价值的润色工作。统一的 CLI 输出风格能显著提升用户体验，让工具感觉更加可靠和精心设计。通过建立一套清晰的视觉规范（例如，所有问题详情都使用相同的缩进和标签格式），用户可以更快地识别和分类信息，从而提高效率。

### 目标
1.  **审查**：全面审查 `packages/stitcher-common/src/stitcher/common/assets/needle/` 目录下的所有 `en` 和 `zh` 语言的 JSON 文件。
2.  **规范化 `check` 输出**：
    *   为所有文件级的状态消息（`check/file.json`）添加一致的表情符号前缀（`❌`, `⚠️`, `✅`）。
    *   为所有问题详情消息（`check/issue.json` 和 `check/state.json`）添加统一的 `   - [TAG] ` 前缀和缩进，确保视觉对齐。
3.  **全局表情符号**：在所有命令的输出消息中，根据消息的性质（成功、错误、警告、信息等）应用一套一致的表情符号。
4.  **更新文件**：使用 `write_file` 操作，将格式化和内容更新后的 JSON 写回文件系统。

### 基本原理
我们将直接覆盖现有的 JSON 文件。通过仔细地重新设计每个消息模板，我们可以建立一个全局一致的视觉语言。对于 `check` 命令，关键在于区分“文件级摘要”和“问题级详情”。摘要将以表情符号开头，而详情将以固定的缩进和方括号标签开头，从而在视觉上形成清晰的层级结构，直接解决用户反馈的问题。

### 标签
#intent/tune #flow/ready #priority/medium #comp/common #scope/ux #ai/instruct #task/domain/ui #task/object/cli-messages #task/action/refactor #task/state/begin

---
### Script

#### Acts 1: 统一英文 (en) 消息文件

我们将从英文消息开始，系统性地更新每一个 JSON 文件。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/file.json
~~~~~
~~~~~json
{
  "fail": "❌ {path}: Found {count} error(s).",
  "warn": "⚠️  {path}: Found {count} warning(s).",
  "pass": "✅ {path}: Synced.",
  "untracked": "⚠️  {path}: Untracked (no .stitcher.yaml file found; run `stitcher init` or `pump`)",
  "untracked_with_details": "⚠️  {path}: Untracked and needs documentation for {count} public APIs:"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/issue.json
~~~~~
~~~~~json
{
  "conflict": "   - [CONFLICT]  {key} (content differs between code and YAML)",
  "extra": "   - [EXTRA DOC] {key} (in docs but not in code)",
  "missing": "   - [MISSING]   {key} (entity exists, but no docstring in code or YAML)",
  "pending": "   - [PENDING]   {key} (new docstring in code, please run `stitcher pump`)",
  "redundant": "   - [REDUNDANT] {key} (docstring exists in both code and YAML; please run `stitcher strip`)",
  "untracked_missing_key": "   - [MISSING]   {key} (please add a docstring in the source code)"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/state.json
~~~~~
~~~~~json
{
  "co_evolution": "   - [CO-EVOLUTION] {key} (both code and docs changed; intent unclear)",
  "doc_updated": "   - [DOC UPDATED]  {key} (documentation was improved and auto-reconciled)",
  "reconciled": "   ✅ [RECONCILED]  {key} in {path}",
  "relinked": "   ✅ [RE-LINKED]   {key} in {path}",
  "signature_drift": "   - [SIG DRIFT]   {key} (code changed, docs may be stale)"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/option.json
~~~~~
~~~~~json
{
  "force": {
    "help": "Code-first: Overwrite YAML content if it differs from source code."
  },
  "non_interactive": {
    "help": "Force non-interactive mode, failing on unresolved conflicts."
  },
  "reconcile": {
    "help": "YAML-first: Ignore source docstrings if they conflict with existing YAML."
  },
  "strip": {
    "help": "Remove docstrings from source code after pumping."
  },
  "verbose": {
    "help": "Enable debug logging."
  }
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/init/__init__.json
~~~~~
~~~~~json
{
  "no_docs_found": "🤔 No docstrings found in source files. No .stitcher.yaml files were created."
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/inject/__init__.json
~~~~~
~~~~~json
{
  "no_docs_found": "🤔 No docstrings found in any .stitcher.yaml files. Nothing to inject."
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/pump/error.json
~~~~~
~~~~~json
{
  "conflict": "❌ Conflict in {path} for '{key}': Docstrings differ. Use --force (code-first) or --reconcile (YAML-first), or run interactively to resolve."
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/pump/info.json
~~~~~
~~~~~json
{
  "reconciled": "ℹ️  Reconciled {count} conflict(s) in {path} by keeping existing YAML content."
}
~~~~~

#### Acts 2: 统一中文 (zh) 消息文件

现在，我们将对中文消息文件应用相同的结构和风格更改。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/file.json
~~~~~
~~~~~json
{
  "fail": "❌ {path}: 发现 {count} 个错误。",
  "warn": "⚠️  {path}: 发现 {count} 个警告。",
  "pass": "✅ {path}: 已同步。",
  "untracked": "⚠️  {path}: 未被追踪 (缺少 .stitcher.yaml 文件；请运行 `stitcher init` 或 `pump`)",
  "untracked_with_details": "⚠️  {path}: 未被追踪，且有 {count} 个公开 API 需要文档:"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/issue.json
~~~~~
~~~~~json
{
  "conflict": "   - [内容冲突]  {key} (代码和 YAML 中的文档内容不一致)",
  "extra": "   - [悬空文档]  {key} (在文档中存在但在代码中缺失)",
  "missing": "   - [文档缺失]  {key} (代码实体存在，但代码和 YAML 中均无文档)",
  "pending": "   - [等待同步]  {key} (代码中有新文档，请运行 `stitcher pump`)",
  "redundant": "   - [文档冗余]  {key} (代码和 YAML 中存在重复文档，请运行 `stitcher strip`)",
  "untracked_missing_key": "   - [文档缺失]  {key} (请在代码中为其添加文档字符串)"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/state.json
~~~~~
~~~~~json
{
  "co_evolution": "   - [协同演进]  {key} (代码和文档均已变更，意图不明确)",
  "doc_updated": "   - [文档更新]  {key} (文档已改进并自动调和)",
  "reconciled": "   ✅ [已调和]    {key} (位于 {path})",
  "relinked": "   ✅ [已重链接]  {key} (位于 {path})",
  "signature_drift": "   - [签名漂移]  {key} (代码已变更，文档可能已过时)"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/option.json
~~~~~
~~~~~json
{
  "force": {
    "help": "代码优先：如果内容不一致，使用代码中的文档覆盖 YAML 内容。"
  },
  "non_interactive": {
    "help": "强制使用非交互模式，在遇到无法解决的冲突时将直接失败。"
  },
  "reconcile": {
    "help": "YAML 优先：当与现有 YAML 冲突时，保留 YAML 的文档内容。"
  },
  "strip": {
    "help": "在抽取文档后立即从源代码中移除它们。"
  },
  "verbose": {
    "help": "启用调试级别的日志输出。"
  }
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/init/__init__.json
~~~~~
~~~~~json
{
  "no_docs_found": "🤔 在源文件中未找到任何文档字符串，因此未创建 .stitcher.yaml 文件。"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/inject/__init__.json
~~~~~
~~~~~json
{
  "no_docs_found": "🤔 在 .stitcher.yaml 文件中未找到任何文档字符串，无可注入内容。"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/pump/error.json
~~~~~
~~~~~json
{
  "conflict": "❌ {path} 中 '{key}' 存在内容冲突。请使用 --force (代码优先) 或 --reconcile (YAML优先)，或在交互模式下运行以解决。"
}
~~~~~
~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/pump/info.json
~~~~~
~~~~~json
{
  "reconciled": "ℹ️  因处于 --reconcile 模式，已在 {path} 中忽略 {count} 个冲突（保留了现有的 YAML 内容）。"
}
~~~~~

### 下一步建议
我们已经完成了对所有消息文件的风格统一。现在，我将生成一个 `[COMMIT]` 计划，将这些改进和上一阶段的功能添加一起提交。如果你同意，请告诉我。
