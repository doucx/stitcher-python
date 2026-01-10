## [WIP] test: 修复解析器鲁棒性测试的脆弱性

### 错误分析
测试 `test_check_fails_gracefully_on_local_import` 旨在验证当解析器崩溃时应用是否能优雅失败。然而，它依赖于一段特定的“错误”代码（包含局部导入）在 Griffe 解析器中触发崩溃。由于 Griffe 的行为可能随版本变化或在特定环境下表现不同（不再崩溃），导致测试无法触发预期的异常，从而使 `ScannerService` 未能捕获错误，`had_errors` 标志未被设置，最终 `run_check` 返回了 `True`（成功），导致断言失败。

我们不应依赖第三方库的具体 Bug 来进行鲁棒性测试。

### 用户需求
使集成测试 `test_check_fails_gracefully_on_local_import` 具有确定性，无论底层解析器是否修复了该 Bug，测试都应能验证 `StitcherApp` 正确处理了解析异常。

### 评论
通过 Mock `parser.parse` 方法来强制抛出异常，我们可以将测试的关注点从“Griffe 是否有 Bug”转移到“Stitcher 是否能处理异常”这一核心意图上。这符合 D3-P1 测试原则。

### 目标
1.  修改 `packages/stitcher-application/tests/integration/test_parser_robustness.py`。
2.  使用 `monkeypatch` 拦截 `app.scanner.parser.parse`，对特定文件强制抛出 `ValueError`。
3.  验证 `run_check` 返回 `False` 且错误被记录到 `SpyBus`。

### 基本原理
确定性测试优于依赖外部行为的测试。Mock 是模拟故障场景的标准手段。

### 标签
#intent/fix #flow/ready #priority/medium #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/test-robustness #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重构测试用例以使用 Mock 注入故障

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_parser_robustness.py
~~~~~
~~~~~python
from stitcher.test_utils import WorkspaceFactory, create_test_app, SpyBus
from needle.pointer import L


def test_check_fails_gracefully_on_local_import(tmp_path, monkeypatch):
    """
    Verifies that when the parser raises an exception during scanning,
    the application handles it gracefully:
    1. Catches the exception.
    2. Logs a generic error.
    3. Ensures the overall command fails (returns False).
    """
    # GIVEN a project with a source file
    ws = WorkspaceFactory(tmp_path)
    ws.with_config({"scan_paths": ["src/pkg"]})
    ws.with_source("src/pkg/__init__.py", "")
    ws.with_source(
        "src/pkg/core.py",
        """
        def foo():
            pass
        """,
    )
    ws.build()

    # Create the app
    app = create_test_app(tmp_path)
    
    # SETUP: Mock the parser to simulate a crash on specific file
    # We access the parser instance directly attached to the scanner
    real_parse = app.scanner.parser.parse
    
    def failing_parse(source_code, file_path=""):
        if "core.py" in str(file_path):
            raise ValueError("Simulated parser crash for testing")
        return real_parse(source_code, file_path)
        
    monkeypatch.setattr(app.scanner.parser, "parse", failing_parse)

    # WHEN we run the check command
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch):
        success = app.run_check()

    # THEN the command should fail
    assert not success, "Command should return False when parser fails"
    
    # AND report a generic error
    spy_bus.assert_id_called(L.error.generic, level="error")

    messages = spy_bus.get_messages()
    error_msg = next(
        (m for m in messages if m["id"] == str(L.error.generic)),
        None,
    )
    assert error_msg is not None
    assert "Simulated parser crash" in str(error_msg["params"].get("error", ""))
~~~~~

### 下一步建议
运行测试。
