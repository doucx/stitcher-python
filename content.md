简要回答
测试失败是因为在使用 `unittest.mock.patch.object` 替换 `Path.read_text` 时，默认生成的 Mock 对象不会自动绑定到实例（也就是 `self` 不会被自动传入）。导致 `mock_read_text` 函数在被调用时，缺失了第一个参数 `path`（即调用该方法的 Path 实例）。

解决方案是在 `patch.object` 中添加 `autospec=True` 参数。这会指示 Mock 库通过内省来模仿原始方法的行为，包括正确地将实例作为第一个参数（`self`）传递给 side_effect 函数。

## [WIP] fix: 修复 Path.read_text Mock 缺失 self 参数的测试错误

### 错误分析
-   **现象**: `TypeError: ... mock_read_text() missing 1 required positional argument: 'path'`
-   **原因**: `patch.object(Path, "read_text", ...)` 替换了类方法，但在通过实例调用时（`instance.read_text()`），Mock 对象没有自动绑定 `instance` 给第一个参数。
-   **解决**: 使用 `autospec=True` 启用自动签名模拟和实例绑定。

### 用户需求
修复 `test_rename_symbol_analyze_orchestration` 单元测试。

### 目标
修改 `packages/stitcher-refactor/tests/unit/test_rename_operation.py`，为 `patch.object` 添加 `autospec=True`。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #task/domain/refactor #task/object/rename-operation #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复测试中的 Mock 配置

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
    # Use monkeypatch to control Path.read_text
    # This is slightly more integration-y but tests the real interaction with LibCST better.
    from unittest.mock import patch
    with patch.object(Path, "read_text", side_effect=mock_read_text):
        # 3. Execute
        op = RenameSymbolOperation(old_fqn, new_fqn)
~~~~~
~~~~~python.new
    # Use monkeypatch to control Path.read_text
    # This is slightly more integration-y but tests the real interaction with LibCST better.
    from unittest.mock import patch
    with patch.object(Path, "read_text", side_effect=mock_read_text, autospec=True):
        # 3. Execute
        op = RenameSymbolOperation(old_fqn, new_fqn)
~~~~~

### 下一步建议
测试通过后，即可开始编写端到端的集成测试，使用真实的 `SemanticGraph` 和 `TransactionManager` 来验证重命名操作。
