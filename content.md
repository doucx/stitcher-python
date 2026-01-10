好的，我理解了。将 `import` 语句放在方法内部是合法的 Python 语法，但我们的解析器 `griffe` 在解析类型别名时，显然没能处理这种情况，导致了崩溃。

这是一个典型的系统鲁棒性问题。我们的上层应用应该能够优雅地处理底层解析器的失败，而不是直接崩溃。

我将创建一个新的集成测试来复现这个问题。这个测试会构造一个包含方法内导入语句的源文件，然后运行 `stitcher check` 命令，并断言该命令会失败（而不是崩溃），同时在总线上报告一个解析错误。这确保了我们为未来的修复工作建立了一个可靠的安全网。

## [WIP] test: 为本地导入导致的解析失败添加回归测试

### 错误分析

错误 `Could not resolve alias ... Optional pointing at typing.Optional` 的根本原因是 `griffe` 解析器在尝试解析函数返回类型注解 `Optional[str]` 时，无法找到 `Optional` 的定义。这是因为它没有扫描到在方法体内部的 `from typing import Optional` 语句。

这暴露了 `stitcher` 系统的一个缺陷：

1.  **解析器脆弱性**: 我们依赖的 `griffe` 解析器无法处理在非模块顶层作用域的导入语句，而这在技术上是有效的 Python 代码。
2.  **错误处理**: 更重要的是，当解析器遇到它无法处理的情况并抛出异常时，我们的 `ScannerService` 只是捕获了一个非常通用的 `Exception`，这虽然阻止了整个应用的崩溃，但没能给用户提供足够清晰的错误上下文。

因此，我们需要一个测试来保证，无论底层解析器行为如何，`stitcher` 应用本身都不会因此崩溃，而是能将其识别为一个文件级的错误并继续或优雅地失败。

### 用户需求

创建一个新的集成测试文件，该文件：
1.  在一个隔离的测试工作区中，创建一个包含非顶层 `import` 语句的 Python 源文件。
2.  运行 `stitcher check` 命令。
3.  断言该命令执行失败 (返回 `False`)。
4.  断言消息总线（bus）上捕获到了相应的错误信息。
5.  此测试在当前代码库下必须失败或验证预期的失败行为。

### 评论

这是一个至关重要的鲁棒性测试。它将强制我们的系统对解析层面的异常有更强的防御能力。一个健壮的工具不应该因为用户代码中不常见的、但合法的语法模式而崩溃。这个测试将成为未来改进解析器或其错误处理逻辑的基准。

### 目标

1.  创建新文件 `packages/stitcher-application/tests/integration/test_parser_robustness.py`。
2.  在该文件中，实现一个名为 `test_check_fails_gracefully_on_local_import` 的测试用例。
3.  该测试将使用 `WorkspaceFactory` 创建一个包含问题代码（`import` 在方法内）的包。
4.  运行 `StitcherApp.run_check()` 并断言其返回值为 `False`，同时验证 `SpyBus` 捕获到了 `L.error.generic` 错误。

### 基本原理

我们将遵循项目的测试架构，在 `stitcher-application` 包中添加一个新的集成测试。通过 `WorkspaceFactory` 和 `SpyBus` 这两个测试工具，我们可以精确地模拟出导致失败的场景，并验证系统的高层行为（即 `run_check` 命令）是否如预期般优雅地失败，而不是抛出未处理的异常。这确保了测试的重点是我们的应用逻辑，而非底层 `griffe` 库的具体实现。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/application #concept/parser #scope/dx #ai/instruct #task/domain/testing #task/object/parser-robustness #task/action/bug-repro #task/state/begin

---

### Script

#### Acts 1: 创建回归测试文件

我们将创建新的测试文件，用于捕获因本地导入导致的解析失败。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_parser_robustness.py
~~~~~
~~~~~python
import pytest
from stitcher.test_utils import WorkspaceFactory, create_test_app, SpyBus
from needle.pointer import L


def test_check_fails_gracefully_on_local_import(tmp_path, monkeypatch):
    """
    Verifies that the parser failing on a local (non-module-level) import
    is handled gracefully by the application, causing `check` to fail
    without crashing.
    """
    # GIVEN a project with a source file containing a local import
    # that is known to cause issues with type alias resolution in griffe.
    ws = WorkspaceFactory(tmp_path)
    ws.with_config({"scan_paths": ["src/buggy_pkg"]})
    ws.with_source("src/buggy_pkg/__init__.py", "")
    ws.with_source(
        "src/buggy_pkg/core.py",
        """
        class MyClass:
            def __init__(self):
                pass

            def a_method(self) -> "Optional[str]":
                from typing import Optional  # <-- This import causes the parser to fail
                return "hello"
        """,
    )
    ws.build()

    # WHEN we run the check command
    app = create_test_app(tmp_path)
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch):
        success = app.run_check()

    # THEN the command should fail, not crash, and report a generic error
    assert not success
    spy_bus.assert_id_called(L.error.generic, level="error")

    messages = spy_bus.get_messages()
    error_msg = next(
        (m for m in messages if m["id"] == str(L.error.generic)),
        None,
    )
    assert error_msg is not None
    # Check that the error reported contains information about the root cause
    assert "Could not resolve alias" in str(error_msg["params"].get("error", ""))
~~~~~

### 下一步建议

现在我们已经有了一个能够稳定复现此 Bug 的测试用例。下一步的核心任务就是修复 `stitcher-python-adapter` 中的 `GriffePythonParser`，使其能够正确处理这种情况，或者至少在失败时能抛出更具上下文的、可被上层捕获和处理的特定异常，从而让这个测试用例转为通过状态。
