Your analysis is spot on. The `check` command is indeed behaving incorrectly by treating imported symbols as locally defined, public APIs that require documentation. This leads to a flood of false positives, making the tool's output unreliable.

To correct this, we must first define the expected behavior in a way that can be automatically verified. I will create a new integration test that formalizes the principle: **`stitcher check` must only report on symbols *defined* within a module, not symbols it *imports*.**

This test will serve as the foundation for fixing the underlying logic and will prevent this kind of regression in the future.

## [WIP] test: Add integration test to ensure check ignores imported symbols

### 用户需求

`stitcher check` 命令错误地将导入的符号（如 `os`, `Path`, `logging`）识别为模块的公共 API，并报告它们“文档缺失”。这是一种错误行为，因为工具应该只关心在模块内部定义的符号。

### 评论

这是一个关键的正确性修复。无法区分模块的内部定义和外部依赖会导致工具产生大量噪音，降低其可用性和可信度。建立一个明确的测试用例是解决此问题的首要步骤。

### 目标

1.  创建一个新的集成测试文件 `test_check_ignores_imports.py`。
2.  在该测试中，构建一个包含本地定义的、无文档的公共符号以及多个从标准库导入的符号的 Python 项目。
3.  执行 `stitcher check` 命令。
4.  断言测试结果：
    *   **必须** 报告本地定义的符号缺少文档。
    *   **绝不能** 报告任何导入的符号缺少文档。

### 基本原理

通过创建一个专门的集成测试，我们可以使用完整的应用程序堆栈来复现该问题。测试将利用 `WorkspaceFactory` 来模拟一个真实的项目结构，并使用 `SpyBus` 来精确捕获和断言应用程序发出的语义消息。这种方法不仅能够清晰地定义正确行为，还能在未来的代码修改中充当安全网，确保此缺陷不会再次出现。

### 标签

#intent/tooling #intent/fix #flow/ready #comp/tests #concept/state #task/domain/testing #task/object/check-command #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 创建集成测试文件

我将创建 `test_check_ignores_imports.py` 文件。这个测试将建立一个包含导入符号和本地定义符号的简单项目，并验证 `check` 命令只对后者发出警告。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_ignores_imports.py
~~~~~
~~~~~python
import pytest
from needle.pointer import L

from stitcher.test_utils import WorkspaceFactory, SpyBus, create_test_app


def test_check_does_not_report_imports_as_missing_docs(
    workspace_factory: WorkspaceFactory, spy_bus: SpyBus, monkeypatch
):
    """
    Verifies that 'stitcher check' does not incorrectly flag imported symbols
    as missing documentation. It should only flag symbols defined within the
    scanned module.
    """
    # 1. Setup: Create a project with a file that has imports and defined symbols
    ws = (
        workspace_factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/my_pkg/core.py",
            """
import os
import logging
from pathlib import Path
from typing import Optional, List

# This function is defined locally and should be reported as missing docs.
def my_public_function():
    pass

# This class is defined locally and should also be reported.
class MyPublicClass:
    pass
            """,
        )
        .build()
    )

    # 2. Execution: Run the check command
    app = create_test_app(ws)
    with spy_bus.patch(monkeypatch):
        # We expect this to fail because docs are missing, which is what we're testing.
        success = app.run_check()
        assert not success

    # 3. Assertion: Verify the output from the bus
    messages = spy_bus.get_messages()

    # Filter for only the 'missing documentation' warnings
    missing_doc_warnings = [
        msg for msg in messages if msg["id"] == str(L.check.issue.missing)
    ]

    assert len(missing_doc_warnings) == 2, "Should only find 2 missing doc warnings"

    # Extract the 'key' (the FQN) from the warning parameters
    reported_keys = {msg["params"]["key"] for msg in missing_doc_warnings}

    # Assert that our defined symbols ARE reported
    assert "my_public_function" in reported_keys
    assert "MyPublicClass" in reported_keys

    # Assert that imported symbols are NOT reported
    imported_symbols = {"os", "logging", "Path", "Optional", "List"}
    for symbol in imported_symbols:
        assert (
            symbol not in reported_keys
        ), f"Imported symbol '{symbol}' was incorrectly reported as missing docs"
~~~~~

### 下一步建议

现在我们已经有了一个能够稳定复现问题的测试用例。下一步就是运行这个测试，看它是否按预期失败（它现在应该会失败，因为它会报告 `os` 等符号缺失文档）。一旦确认失败，我将着手修改 `stitcher-application` 或 `stitcher-python-adapter` 中的分析逻辑，以确保测试通过。
