现在，我将按照您的指示，着手重构测试基础设施，以消除那些恼人的覆盖率警告。

## [WIP] refactor(tests): Revert fixture plugin to fix coverage warnings

### 用户需求

撤销将 `stitcher-test-utils` 作为 pytest 插件的实现，改回在测试用例中直接实例化 `WorkspaceFactory` 和 `SpyBus`，以消除 `CoverageWarning`。

### 评论

您的诊断完全正确。pytest 插件机制导致的“过早导入”问题干扰了覆盖率工具的正常工作。虽然插件化在架构上很优雅，但一个干净、无警告的测试输出在实践中更为重要。回归到更简单的直接实例化模式，是一个明智且务实的工程决策。

### 目标

1.  从 `stitcher-test-utils/pyproject.toml` 中移除 `pytest11` 入口点。
2.  删除 `stitcher-test-utils/src/stitcher/test_utils/fixtures.py` 文件，因为它不再被插件机制使用。
3.  修改 `test_check_ignores_imports.py`，在测试函数内部显式导入并创建 `WorkspaceFactory` 和 `SpyBus` 的实例。

### 基本原理

通过移除 `pytest11` 入口点，我们阻止了 pytest 在启动时自动加载 `test-utils`。相应地，对 `stitcher` 核心代码的导入将延迟到测试函数执行时才发生。此时，`pytest-cov` 已经完成了它的设置并开始监控，从而可以正确地测量所有模块的覆盖率，消除了警告。

### 标签

#intent/refine #intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #task/domain/testing #task/object/test-infrastructure #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 移除 Pytest 插件配置

我将首先修改 `pyproject.toml` 并删除不再需要的 `fixtures.py` 文件。

~~~~~act
patch_file
packages/stitcher-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
[project.entry-points."pytest11"]
stitcher = "stitcher.test_utils.fixtures"

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~
~~~~~toml.new
[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~

~~~~~act
delete_file
packages/stitcher-test-utils/src/stitcher/test_utils/fixtures.py
~~~~~

#### Acts 2: 修改测试用例以直接实例化依赖

现在，我将更新测试文件，使其自给自足，不再依赖注入的 fixture。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_ignores_imports.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
import pytest
from needle.pointer import L
from pathlib import Path

from stitcher.test_utils import WorkspaceFactory, SpyBus, create_test_app


def test_check_does_not_report_imports_as_missing_docs(
    tmp_path: Path, monkeypatch
):
    """
    Verifies that 'stitcher check' does not incorrectly flag imported symbols
    as missing documentation. It should only flag symbols defined within the
    scanned module.
    """
    # 1. Setup: Create a project with a file that has imports and defined symbols
    workspace_factory = WorkspaceFactory(tmp_path)
    spy_bus = SpyBus()
    ws = (
        workspace_factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/my_pkg/core.py",
~~~~~

### 下一步建议

我们已经成功地将核心逻辑修复提交，并按照您的指示重构了测试基础设施以解决覆盖率警告。现在，测试套件应该能干净利落地运行。您可以继续进行其他开发任务，或者我们可以寻找项目中其他可以改进的地方。
