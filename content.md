**简要回答**

你发现了一个非常好的问题，这暴露了我的测试实现中的一个缺陷，同时也揭示了应用层代码中的一个不一致之处。你的分析完全正确。

`SpyBus` 的设计原则是捕获**语义意图**（即 `L` 指针和参数），而不是最终渲染的**UI字符串** (`message`)。我的测试错误地试图断言一个不存在于捕-获数据中的 `"message"` 键。

为了解决这个问题并提升代码质量，我将执行一个两步修复：
1.  **修复应用代码**: 我会将 `core.py` 中硬编码的 `"Hydration aborted by user."` 错误消息替换为一个标准的、可测试的语义指针 `L.hydrate.run.aborted`。
2.  **修复测试代码**: 我会更新测试用例，使用 `spy_bus.assert_id_called()` 来断言正确的**语义ID**，而不是脆弱的UI字符串。

这将使代码和测试都更加健壮和一致。

## [WIP] fix(testing): 修正 hydrate 交互测试并统一 abort 消息

### 错误分析
测试 `test_hydrate_interactive_abort_stops_process` 失败，因为 `SpyBus` 捕获的消息字典结构为 `{"level": ..., "id": ..., "params": ...}`，它并不包含最终渲染的 `"message"` 字符串键。测试代码错误地假设了 `SpyBus` 的内部数据结构，并违反了“验证意图而非呈现”的测试原则。

此外，`StitcherApp.run_hydrate` 在处理中止逻辑时使用了硬编码的英文字符串 `bus.error("Hydration aborted by user.")`，这使得它无法被 `SpyBus` 进行语义捕获，也无法进行国际化。

### 用户需求
修正集成测试 `test_hydrate_interactive_abort_stops_process` 使其能够正确验证当用户选择 `[A]bort` 时，系统发出了一个表示“中止”的语义消息。

### 评论
这是一个重要的修复，它不仅纠正了测试中的一个直接错误，还通过移除硬编码字符串和引入语义指针，提升了核心应用代码的可维护性和可测试性。这是一个典范的“由测试驱动改进”的例子。

### 目标
1.  在 `en` 和 `zh` 的 `needle` 资源文件中为 `hydrate` 命令添加 `aborted` 消息。
2.  修改 `StitcherApp.run_hydrate`，在用户中止时调用 `bus.error(L.hydrate.run.aborted)`。
3.  修改 `test_hydrate_interactive_flow.py`，使用 `spy_bus.assert_id_called(L.hydrate.run.aborted)` 进行断言。
4.  将此修复作为一个完整的提交。

### 基本原理
我们将首先扩充我们的国际化（i18n）资源，为“补水中止”这一事件定义一个标准的语义指针。然后，我们将重构应用代码以使用此指针，确保所有用户反馈都通过统一的消息总线进行。最后，我们将修正测试代码，使其遵循最佳实践，通过断言语义指针（意图）而非具体文本（呈现）来验证行为的正确性。

### 标签
#intent/fix #intent/tooling #flow/ready #priority/high #comp/tests #comp/runtime #concept/ui #scope/dx #task/domain/cli #task/object/interactive-mode #task/action/integration #task/state/continue

---

### Script

#### Acts 1: 添加新的本地化消息键

我们首先在 `en` 和 `zh` 的资源文件中添加新的 `hydrate.run.aborted` 消息。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/hydrate/main.json
~~~~~
~~~~~json.old
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
~~~~~json.new
{
    "hydrate.run.start": "💧 Starting hydration process...",
    "hydrate.file.success": "💧 Hydrated {count} new docstrings from: {path}",
    "hydrate.run.complete": "✨ Hydration complete. {count} files updated.",
    "hydrate.run.no_changes": "🤔 No new docstrings found in source code to hydrate.",
    "hydrate.error.conflict": "❌ Conflict in {path} for '{key}': Docstrings differ. Use --force (code-first) or --reconcile (YAML-first) to resolve.",
    "hydrate.run.conflict": "🚫 Hydration aborted due to conflicts in {count} files.",
    "hydrate.info.reconciled": "ℹ️  Ignored {count} conflicts in {path} due to --reconcile mode.",
    "hydrate.run.aborted": "Hydration aborted by user."
}
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/hydrate/main.json
~~~~~
~~~~~json.old
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
~~~~~json.new
{
    "hydrate.run.start": "💧 开始补水过程...",
    "hydrate.file.success": "💧 从 {path} 补水了 {count} 个新的文档字符串",
    "hydrate.run.complete": "✨ 补水完成。{count} 个文件已更新。",
    "hydrate.run.no_changes": "🤔 在源代码中未找到可供补水的新文档字符串。",
    "hydrate.error.conflict": "❌ {path} 中 '{key}' 存在内容冲突。请使用 --force (代码优先) 或 --reconcile (YAML优先) 来解决。",
    "hydrate.run.conflict": "🚫 因在 {count} 个文件中存在冲突，补水操作已中止。",
    "hydrate.info.reconciled": "ℹ️  因处于 --reconcile 模式，已忽略 {path} 中的 {count} 个冲突。",
    "hydrate.run.aborted": "用户中止了补水操作。"
}
~~~~~

#### Acts 2: 修正应用与测试代码

现在，我们更新 `core.py` 以使用新的语义指针，并修正测试用例以正确断言该指针。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
                action = chosen_actions[i]
                if action == ResolutionAction.ABORT:
                    bus.warning(L.hydrate.run.conflict, count=len(all_conflicts)) # Reuse conflict msg as abort indicator?
                    bus.error("Hydration aborted by user.")
                    return False
                resolutions_by_file[context.file_path][context.fqn] = action
~~~~~
~~~~~python.new
                action = chosen_actions[i]
                if action == ResolutionAction.ABORT:
                    bus.error(L.hydrate.run.aborted)
                    return False
                resolutions_by_file[context.file_path][context.fqn] = action
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_hydrate_interactive_flow.py
~~~~~
~~~~~python.old
    # 3. Assert
    assert success is False
    # A specific "aborted" message would be better, but for now we check for conflict error
    assert "aborted" in spy_bus.get_messages()[-1]["message"].lower()

    # Verify file content was NOT changed
~~~~~
~~~~~python.new
    # 3. Assert
    assert success is False
    # Assert that the correct semantic 'aborted' message was sent.
    spy_bus.assert_id_called(L.hydrate.run.aborted, level="error")

    # Verify file content was NOT changed
~~~~~
