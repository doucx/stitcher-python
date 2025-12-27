我理解你的要求。统一用户界面 (UI) 的文案风格对于提升用户体验 (UX) 至关重要。一个清晰、一致且具备引导性的术语体系可以显著降低用户的认知负荷，并让他们对工具的行为建立起精确的心智模型。

你指出的 “缺失” 与 “代办” 的语义模糊问题非常关键。这正是我要解决的核心：确保每个状态信息都有一个唯一的、可操作的含义，从而引导用户完成从初始化 (`init`)、文档提取 (`hydrate`) 到代码检查 (`check`) 的完整工作流。

以下是我的计划，旨在全面审查和统一所有 `needle` 本地化文件的风格。

## [WIP] refactor(cli): 统一并优化 CLI 的用户反馈文案

### 用户需求
审查所有 `needle` JSON 本地化文件，统一其文案风格和术语，特别是 `stitcher check` 命令的输出，使其对用户更清晰、更具指导性，从而形成一个无缝闭环的工作流。

### 评论
这是一个非常有价值的改进。通过建立一套一致的词汇表（例如，明确区分“文档缺失”和“等待同步”），我们可以将 `stitcher check` 的输出从一个简单的“问题报告”转变为一个智能的“下一步行动建议”，这极大地提升了开发者体验 (DX)。

### 目标
1.  **分析工作流**：梳理用户使用 `stitcher` 的核心工作流，确保文案能够引导用户从一个状态正确地迁移到下一个状态。
2.  **统一术语**：为 `check` 命令报告的五种核心问题（`missing`, `pending`, `redundant`, `extra`, `conflict`）以及签名不匹配问题（`mismatch`）定义一套清晰、一致的中英文术语和状态标签。
3.  **增强可操作性**：在提示信息中直接嵌入解决问题的建议（例如，“请运行 `stitcher hydrate`”）。
4.  **实施修改**：使用 `write_file` 更新所有相关的中英文 JSON 文件以应用新的文案风格。

### 基本原理
我们将以 `stitcher check` 的输出为中心进行重构，因为它承载了最复杂的状态信息。

1.  **重新定义状态标签**：
    *   `untracked_missing_key` 和 `missing` 都指向同一个用户动作：**在代码中编写文档**。我们将统一它们的标签为 `[文档缺失]` / `[MISSING]`。
    *   `pending` 意味着文档已在代码中，需要同步到 YAML。这是一个明确的**等待同步**状态，提示用户运行 `hydrate`。
    *   `extra` 指的是 YAML 中的文档定义在代码中已不存在，这是一个**定义缺失**或“悬空”的状态。
    *   其余状态（`redundant`, `conflict`, `mismatch`）的现有定义是清晰的，但其呈现方式将被优化。

2.  **格式对齐**：为了提升可扫描性，所有状态标签（如 `[状态]`) 将被格式化为统一的视觉风格。

3.  **全局应用**：此原则将被应用到所有相关的 JSON 文件中，以确保整个应用的“声音和语调”保持一致。

### 标签
#intent/refine #flow/ready #priority/medium #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/localization #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 优化 `check` 命令的英文反馈文案

我们将统一 `check` 命令的英文输出，使其更具指导性。`DANGLING` 比 `EXTRA` 更能准确描述问题。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/main.json
~~~~~
~~~~~json
{
    "check.file.pass": "✅ {path}: Synced.",
    "check.file.fail": "❌ {path}: Found {count} errors.",
    "check.file.warn": "⚠️  {path}: Found {count} warnings.",
    "check.file.untracked": "⚠️  {path}: Untracked (no .stitcher.yaml file found; run `stitcher init` or `hydrate`)",
    "check.file.untracked_with_details": "⚠️  {path}: Untracked and needs documentation for {count} public APIs:",
    "check.issue.untracked_missing_key": "   - [MISSING]   {key} (please add a docstring in the source code)",
    "check.issue.missing": "   - [MISSING]   {key} (entity exists, but no docstring in code or YAML)",
    "check.issue.pending": "   - [PENDING]   {key} (new docstring in code, please run `stitcher hydrate`)",
    "check.issue.redundant": "   - [REDUNDANT] {key} (docstring exists in both code and YAML; please run `stitcher strip`)",
    "check.issue.extra": "   - [DANGLING]  {key} (docstring in YAML, but entity is missing in code)",
    "check.issue.conflict": "   - [CONFLICT]  {key} (content differs between code and YAML)",
    "check.run.success": "✨ All checks passed. Documentation is in sync.",
    "check.run.success_with_warnings": "⚠️  Check passed with warnings in {count} files.",
    "check.run.fail": "🚫 Check failed. Found errors in {count} files."
}
~~~~~

#### Acts 2: 优化 `check` 命令的中文反馈文案

相应地，我们将更新中文文案，使其与英文版的逻辑和术语保持一致，并解决用户提出的“缺失”与“代办”的模糊性问题。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/main.json
~~~~~
~~~~~json
{
    "check.file.pass": "✅ {path}: 已同步。",
    "check.file.fail": "❌ {path}: 发现 {count} 个错误。",
    "check.file.warn": "⚠️  {path}: 发现 {count} 个警告。",
    "check.file.untracked": "⚠️  {path}: 未被追踪 (缺少 .stitcher.yaml 文件；请运行 `stitcher init` 或 `hydrate`)",
    "check.file.untracked_with_details": "⚠️  {path}: 未被追踪，且有 {count} 个公开 API 需要文档:",
    "check.issue.untracked_missing_key": "   - [文档缺失] {key} (请在代码中为其添加文档字符串)",
    "check.issue.missing": "   - [文档缺失] {key} (代码实体存在，但代码和 YAML 中均无文档)",
    "check.issue.pending": "   - [等待同步] {key} (代码中有新文档，请运行 `stitcher hydrate`)",
    "check.issue.redundant": "   - [文档冗余] {key} (代码和 YAML 中存在重复文档，请运行 `stitcher strip`)",
    "check.issue.extra": "   - [定义悬空] {key} (YAML 中存在，但代码中对应的实体已删除)",
    "check.issue.conflict": "   - [内容冲突] {key} (代码和 YAML 中的文档内容不一致)",
    "check.run.success": "✨ 所有检查通过，文档保持同步。",
    "check.run.success_with_warnings": "⚠️  检查通过，但在 {count} 个文件中发现警告。",
    "check.run.fail": "🚫 检查失败，在 {count} 个文件中发现错误。"
}
~~~~~

#### Acts 3: 优化签名检查的英文反馈文案

使签名检查的输出与核心检查保持风格一致。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/signatures.json
~~~~~
~~~~~json
{
    "check.issue.mismatch": "   - [CHANGED]   {key} (signature has changed, docs may be outdated)"
}
~~~~~

#### Acts 4: 优化签名检查的中文反馈文案

对应更新中文版的签名检查输出。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/signatures.json
~~~~~
~~~~~json
{
    "check.issue.mismatch": "   - [签名变更] {key} (函数签名已更改，文档可能已过时)"
}
~~~~~

#### Acts 5: 优化 `hydrate` 命令的英文冲突提示

使 `hydrate` 的冲突提示信息更清晰，并同时告知用户 `--force` 和 `--reconcile` 两种解决策略。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/hydrate/main.json
~~~~~
~~~~~json
{
    "hydrate.run.start": "💧 Starting hydration process...",
    "hydrate.file.success": "💧 Hydrated {count} new docstrings from: {path}",
    "hydrate.run.complete": "✨ Hydration complete. {count} files updated.",
    "hydrate.run.no_changes": "🤔 No new docstrings found in source code to hydrate.",
    "hydrate.error.conflict": "❌ Conflict in {path} for '{key}': Docstrings differ. Use --force (code-first) or --reconcile (YAML-first) to resolve.",
    "hydrate.run.conflict": "🚫 Hydration aborted due to conflicts in {count} files.",
    "hydrate.info.reconciled": "ℹ️  Ignored {count} conflicts in {path} due to --reconcile mode."
}
~~~~~

#### Acts 6: 优化 `hydrate` 命令的中文冲突提示

同步更新 `hydrate` 的中文冲突提示。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/hydrate/main.json
~~~~~
~~~~~json
{
    "hydrate.run.start": "💧 开始补水过程...",
    "hydrate.file.success": "💧 从 {path} 补水了 {count} 个新的文档字符串",
    "hydrate.run.complete": "✨ 补水完成。{count} 个文件已更新。",
    "hydrate.run.no_changes": "🤔 在源代码中未找到可供补水的新文档字符串。",
    "hydrate.error.conflict": "❌ {path} 中 '{key}' 存在内容冲突。请使用 --force (代码优先) 或 --reconcile (YAML优先) 来解决。",
    "hydrate.run.conflict": "🚫 因在 {count} 个文件中存在冲突，补水操作已中止。",
    "hydrate.info.reconciled": "ℹ️  因处于 --reconcile 模式，已忽略 {path} 中的 {count} 个冲突。"
}
~~~~~
