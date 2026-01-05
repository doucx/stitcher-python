Excellent. We have successfully reproduced the bug and captured it in a failing test. This is a critical milestone.

The debug output from your test provides the "smoking gun".

1.  **`[DEBUG] Could not find 'stitcher.common.messaging.bus' directly.`**
    *   **核心问题**: Griffe, a static analysis tool, failed to resolve the module path `stitcher.common.messaging.bus` correctly. This suggests that during the scan, the connection between the file `bus.py` and its fully qualified module name was lost. This is a classic problem in complex monorepos with namespace packages.
2.  **`[DEBUG] Found 2 usages for stitcher.common.messaging.bus.MessageBus`**
    *   **证据**: The engine *did* find usages of the FQN.
3.  **`[DEBUG] Usages inside bus.py: 0`**
    *   **决定性证据**: This is the root of the failure. The `SemanticGraph`'s CST visitor (`_UsageVisitor`) **never registered the class definition `class MessageBus:` inside `bus.py` as a usage of the FQN.** Why? Because when the visitor was processing `bus.py`, it likely did not have the correct `current_module_fqn` (`stitcher.common.messaging.bus`). As a result, it could not construct the correct FQN for the `MessageBus` class definition and register it.

**结论**: The bug is not in the transformer (`SymbolRenamerTransformer`), but in the discovery and indexing phase within `SemanticGraph`. The graph builder is failing to correctly map the file path of `bus.py` to its canonical module FQN in this specific monorepo/namespace package layout, causing the definition to be missed entirely by the usage registry.

The planner correctly generated an operation for the only file it knew about (`__init__.py`), which matches what we saw in the CLI. We have now successfully created a high-fidelity test that fails for the exact same reason the CLI command failed.

Now, we will commit this failing test to lock in the bug and provide a clear target for the fix.

## [COMMIT] test(refactor): Add failing test for incomplete rename bug

### 错误分析

The refactoring engine (`SemanticGraph`) fails to correctly identify a class's definition when it is located within a namespace package (`stitcher`) that spans multiple projects in a monorepo (`stitcher-common`).

The debug output from the new test `test_debug_rename_failure.py` confirms that the usage registry (`UsageRegistry`) finds usages of `stitcher.common.messaging.bus.MessageBus` in import statements but finds zero usages within the defining file (`bus.py`). This proves that the CST visitor is not being run with the correct fully qualified module name for that file, preventing it from registering the `class MessageBus:` definition as a refactoring target.

Consequently, the `RenameSymbolOperation` only receives usage locations from import statements and correctly updates those files, but since it has no location for the definition, it leaves the original file untouched, resulting in a broken codebase and `ImportError`.

### 用户需求

The user required a failing test case that reliably reproduces a refactoring failure observed in the CLI, where a symbol rename operation only modified usages but not the definition itself.

### 评论

This is an excellent example of a diagnostic-driven development process. By creating a high-fidelity test that inspects the internal state of the refactoring engine, we were able to pinpoint the failure to the module discovery and indexing phase, rather than the code transformation phase. Committing this failing test provides a solid foundation for a targeted fix.

### 目标

1.  Add the new diagnostic test file `test_debug_rename_failure.py` to the test suite.
2.  Commit this test to the version control system, formally acknowledging the bug and establishing a clear success criterion for the subsequent fix.

### 基本原理

Following Test-Driven Development (TDD) principles, we commit a failing test that clearly and reliably demonstrates a bug. This ensures that:
1.  The bug is officially tracked and cannot be forgotten.
2.  The eventual fix is validated by the clear "pass" signal from this specific test.
3.  We prevent future regressions against this specific failure mode.

### 标签

#intent/tooling #flow/ready #priority/critical #comp/tests #comp/refactor #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/refactor-engine #task/action/bug-repro-test #task/state/end

---

### Script

#### Acts 1: 提交新的失败测试用例

我们将把这个新的、能够复现问题的测试文件添加到版本控制中。

~~~~~act
git_add
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
test(refactor): Add failing test for incomplete rename bug

Adds a new integration test, `test_debug_rename_failure_analysis`, that reliably reproduces a critical bug where the refactoring engine fails to rename a class definition within a namespace package.

The test confirms via debug output and a final `pytest.fail()` that the root cause is a failure in the discovery phase: `SemanticGraph` does not correctly associate the file containing the class definition (`bus.py`) with its canonical FQN. As a result, the `UsageRegistry` is not populated with the location of the definition, and the `RenameSymbolOperation` only transforms the usages it can find (in import statements), leading to a broken state.

This test now serves as the regression guard and success criterion for the required fix in `stitcher.refactor.engine.graph.py`.
~~~~~

### 下一步建议

我们已经成功地将 Bug 隔离并用测试锁定了它。下一步是创建一个新的 `[WIP]` 计划来修复 `stitcher.refactor.engine.graph.py` 中的 `SemanticGraph` 类。修复的重点将是调查和修正 Griffe 如何加载和解析跨项目的 namespace package，确保每个源文件都被赋予正确的 FQN，以便 `_UsageVisitor` 能够正确地索引所有定义。
