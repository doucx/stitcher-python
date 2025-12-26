好的，现在我们将为 `stitcher-common` 包中定义的所有运行时消息（如错误、成功、警告信息）提供中文支持，从而完成整个工具链的核心汉化。

## [WIP] feat(common): 为运行时消息提供完整的中文本地化支持

### 用户需求
用户要求补全 `stitcher-common` 包的中文翻译，以便在 `LANG=zh_CN.UTF-8` 环境下，所有 CLI 输出（包括进度、成功、错误信息）都能以中文显示。

### 评论
这是实现完全沉浸式本地化体验的关键一步。通过为 `stitcher-common` 添加语言包，我们确保了 `stitcher-cli` 的 UI (在 `cli` 包中) 和其业务逻辑反馈 (在 `common` 包中) 都能统一响应语言设置，提供了无缝的用户体验。

### 目标
1.  在 `packages/stitcher-common/src/stitcher/common/assets/needle/` 下创建 `zh` 目录。
2.  复制 `en` 目录的完整结构到 `zh` 目录下。
3.  翻译所有 `.json` 文件中的值为中文。

### 基本原理
`stitcher-needle` 的多根加载和语言回退机制使这个过程非常简单。我们只需在 `stitcher-common` 包内提供与 `en` 目录结构平行的 `zh` 目录。当 `LANG` 设置为中文时，运行时会优先在 `zh` 目录中查找资源。如果 `zh` 目录中某个键缺失（例如，未来新增了功能但未及时翻译），系统会自动回退到 `en` 目录中查找，保证了程序的健壮性。

### 标签
#intent/build #flow/ready #priority/medium #comp/common #concept/i18n #scope/ux #ai/instruct #task/domain/i18n #task/object/runtime-messages #task/action/localize #task/state/continue

---

### Script

#### Acts 1: 创建中文资源文件

我们将为 `stitcher-common` 的每个消息类别创建对应的中文 `.json` 文件。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/main.json
~~~~~
~~~~~json
{
    "check.file.pass": "✅ {path}: 已同步。",
    "check.file.fail": "❌ {path}: 发现 {count} 个错误。",
    "check.file.warn": "⚠️  {path}: 发现 {count} 个警告。",
    "check.issue.missing": "   - [缺失] {key} (存在于代码中，但在 YAML 中缺失)",
    "check.issue.extra": "   - [多余]   {key} (存在于 YAML 中，但在代码中缺失)",
    "check.issue.conflict": "   - [冲突] {key} (代码与 YAML 中的内容不一致)",
    "check.run.success": "✨ 所有检查通过。文档已同步。",
    "check.run.success_with_warnings": "⚠️  检查通过，在 {count} 个文件中发现警告。",
    "check.run.fail": "🚫 检查失败。在 {count} 个文件中发现错误。"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/signatures.json
~~~~~
~~~~~json
{
    "check.issue.mismatch": "   - [变更] {key} (函数签名已更改，文档可能已过时)"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/command.json
~~~~~
~~~~~json
{
    "cli.command.not_implemented": "ℹ️  命令 '{command}' 尚未实现。"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/eject/main.json
~~~~~
~~~~~json
{
    "eject.run.confirm": "⚠️  此操作将使用 .stitcher.yaml 文件的内容覆盖源文件。您代码中当前的任何文档字符串都将被替换。确定要继续吗？",
    "eject.run.aborted": "弹出操作已中止。",
    "eject.file.success": "📝 已将文档字符串注入: {path}",
    "eject.run.complete": "🎉 弹出完成。{count} 个文件已修改。",
    "eject.no_docs_found": "🤔 在任何 .stitcher.yaml 文件中均未找到文档字符串。无可弹出内容。"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/error/main.json
~~~~~
~~~~~json
{
    "error.config.not_found": "⚠️  在 pyproject.toml 中未找到 [tool.stitcher] 配置。无可执行操作。",
    "error.generic": "❌ 发生意外错误: {error}",
    "error.plugin.inspection": "❌ 检查插件时出错: {error}"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/generate/main.json
~~~~~
~~~~~json
{
    "generate.file.success": "✅ 已生成存根: {path}",
    "generate.run.complete": "✨ 生成完成。{count} 个文件已创建。"
}
~~~~~

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
    "hydrate.error.conflict": "❌ {path} 中存在冲突：'{key}' 的文档字符串在代码和 YAML 中都存在但内容不同。请使用 --force 覆盖 YAML。",
    "hydrate.run.conflict": "🚫 因在 {count} 个文件中存在冲突，补水操作已中止。",
    "hydrate.info.reconciled": "ℹ️  因处于 --reconcile 模式，已忽略 {path} 中的 {count} 个冲突。"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/init/main.json
~~~~~
~~~~~json
{
    "init.file.created": "📝 已创建文档文件: {path}",
    "init.run.complete": "🎉 初始化完成。{count} 个文档文件已创建。",
    "init.no_docs_found": "🤔 在源文件中未找到文档字符串。未创建 .stitcher.yaml 文件。"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/strip/main.json
~~~~~
~~~~~json
{
    "strip.run.confirm": "⚠️  此操作将永久从源文件中删除文档字符串。除非您使用版本控制，否则此操作不可逆。确定要继续吗？",
    "strip.run.aborted": "剥离操作已中止。",
    "strip.file.success": "✅ 已从 {path} 剥离文档字符串",
    "strip.run.complete": "✨ 剥离完成。{count} 个文件已修改。"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/warning/main.json
~~~~~
~~~~~json
{
    "warning.no_files_or_plugins_found": "🤔 未找到可供处理的源文件或插件。"
}
~~~~~

### 下一步建议
现在，项目核心的国际化工作已经完成。
- **测试**: 可以通过手动触发一些错误（例如，在 `check` 命令中制造一个冲突）并在 `LANG=zh_CN.UTF-8` 环境下运行，来验证错误信息是否已正确汉化。
- **文档**: 更新项目的 `README.md` 或贡献指南，说明如何添加新的语言支持，鼓励社区贡献其他语言的翻译。
- **提交**: 这个宏观任务（本地化）已经完成，我将生成一个 `[COMMIT]` 计划来提交这些变更。
