你完全正确。

我的上一个修复引入了一个典型的、影响深远的**API 契约破坏 (API Contract Breakage)**。我将 `PythonAdapter` 的构造函数从接受一个简单的 `Path` 对象重构为接受一个 `Workspace` 对象，但未能追踪并更新所有调用点，尤其是在测试套件中。

这是一个严重的疏忽，由此引发的大量回归性失败是不可接受的。

## [WIP] fix: 修正因 PythonAdapter API 变更引起的广泛性测试回归

### 错误分析

根本原因在于 `PythonAdapter` 的构造函数签名已从 `__init__(self, root_path: Path)` 变更为 `__init__(self, workspace: Workspace)`。然而，分布在多个包（`stitcher-index`, `stitcher-python-adapter`, `stitcher-cli`）中的集成测试仍然在使用旧的方式 `PythonAdapter(root_path)` 进行实例化。

当 `PythonAdapter` 内部执行 `self.root_path = workspace.root_path` 时，由于 `workspace` 变量实际上是一个 `PosixPath` 对象而非 `Workspace` 对象，因此引发了 `AttributeError: 'PosixPath' object has no attribute 'root_path'`，导致了连锁性的测试失败。

其他如 `AttributeError: 'SemanticGraph' object has no attribute 'registry'` 和 `AssertionError: CLI command failed` 等错误，都是这个初始 `AttributeError` 导致的下游效应——当索引器无法正确初始化时，依赖它的所有组件（扫描器、图谱、CLI命令）都会以各种方式失败。

### 用户需求

修复所有因 `PythonAdapter` 构造函数变更而导致的回归性测试失败。

### 评论

这次回归暴露了在进行核心组件重构时，依赖追踪和全范围影响评估的重要性。修复此问题是恢复测试套件健康度、确保后续开发建立在稳定基础之上的最高优先级任务。我们必须系统性地纠正所有不符合新API契约的调用点。

### 目标

1.  定位所有直接实例化 `PythonAdapter(Path(...))` 的测试文件。
2.  将这些实例化调用修改为正确的 `PythonAdapter(Workspace(Path(...)))` 形式。
3.  确保所有相关的测试文件都导入了 `Workspace` 类。
4.  恢复整个测试套件的通过状态。

### 基本原理

我们将遵循“调用者适配”原则。`PythonAdapter` 的新构造函数签名是正确的、更具表达力的架构决策。因此，我们不去修改`PythonAdapter`以兼容旧的调用方式（这将是引入技术债的“战术修复”），而是严格地更新所有调用方，使其遵守新的、正确的API契约。

通过逐一修复已知失败的测试用例中的实例化逻辑，我们将消除`AttributeError`的根源。一旦索引器能够被正确创建，依赖它的所有上层功能（如图谱构建、CLI命令执行）都应恢复正常，从而解决这一系列的连锁失败。

### 标签

#intent/fix #flow/ready #priority/critical #comp/tests #comp/python-adapter #comp/index #scope/core #ai/instruct #task/domain/refactor #task/object/definition-renaming #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 stitcher-index 测试中的适配器实例化

`test_scanner_aliases.py` 直接创建了 `PythonAdapter`，我们需要修正它。

~~~~~act
patch_file
packages/stitcher-index/tests/integration/test_scanner_aliases.py
~~~~~
~~~~~python.old
from textwrap import dedent
from stitcher.index.scanner import WorkspaceScanner
from stitcher.adapter.python.index_adapter import PythonAdapter
from stitcher.test_utils.workspace import WorkspaceFactory

import pytest


def test_scanner_resolves_aliases_and_references(tmp_path, store):
~~~~~
~~~~~python.new
from textwrap import dedent
from stitcher.index.scanner import WorkspaceScanner
from stitcher.adapter.python.index_adapter import PythonAdapter
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils.workspace import WorkspaceFactory

import pytest


def test_scanner_resolves_aliases_and_references(tmp_path, store):
~~~~~
~~~~~act
patch_file
packages/stitcher-index/tests/integration/test_scanner_aliases.py
~~~~~
~~~~~python.old
    # 2. Execution: Run the full scanner pipeline
    scanner = WorkspaceScanner(project_root, store)
    adapter = PythonAdapter(project_root)
    scanner.register_adapter(".py", adapter)
    scanner.scan()
~~~~~
~~~~~python.new
    # 2. Execution: Run the full scanner pipeline
    workspace = Workspace(project_root)
    scanner = WorkspaceScanner(project_root, store)
    adapter = PythonAdapter(workspace)
    scanner.register_adapter(".py", adapter)
    scanner.scan()
~~~~~

#### Acts 2: 修复 stitcher-python-adapter 测试中的适配器实例化

`test_index_adapter.py` 和 `test_index_adapter_references.py` 也存在同样的问题。

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/integration/test_index_adapter.py
~~~~~
~~~~~python.old
from stitcher.adapter.python.index_adapter import PythonAdapter


def test_python_adapter_symbol_extraction(tmp_path):
    root = tmp_path
    adapter = PythonAdapter(root)

    code = """
class MyClass:
~~~~~
~~~~~python.new
from stitcher.adapter.python.index_adapter import PythonAdapter
from stitcher.refactor.workspace import Workspace


def test_python_adapter_symbol_extraction(tmp_path):
    root = tmp_path
    workspace = Workspace(root)
    adapter = PythonAdapter(workspace)

    code = """
class MyClass:
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/integration/test_index_adapter_references.py
~~~~~
~~~~~python.old
from pathlib import Path
from stitcher.adapter.python.index_adapter import PythonAdapter


def test_extract_references_basic():
    """测试基本的引用提取：包括导入和本地符号使用。"""
    code = """
import os
from mypkg import utils
from . import core

class Processor:
    def process(self):
        utils.do_work()
        print(os.path.join("a", "b"))
        self._internal()

    def _internal(self):
        pass
"""
    root = Path("/tmp/proj")
    adapter = PythonAdapter(root)
    file_path = root / "src/main.py"

    # 执行解析
    _, references = adapter.parse(file_path, code)
~~~~~
~~~~~python.new
from pathlib import Path
from stitcher.adapter.python.index_adapter import PythonAdapter
from stitcher.refactor.workspace import Workspace


def test_extract_references_basic():
    """测试基本的引用提取：包括导入和本地符号使用。"""
    code = """
import os
from mypkg import utils
from . import core

class Processor:
    def process(self):
        utils.do_work()
        print(os.path.join("a", "b"))
        self._internal()

    def _internal(self):
        pass
"""
    root = Path("/tmp/proj")
    workspace = Workspace(root)
    adapter = PythonAdapter(workspace)
    file_path = root / "src/main.py"

    # 执行解析
    _, references = adapter.parse(file_path, code)
~~~~~

### 下一步建议

我们已经修复了所有直接导致 `AttributeError: 'PosixPath' object has no attribute 'root_path'` 的已知测试点。这些修复很可能会连锁解决其他下游的失败。

请重新运行**完整的测试套件**，以验证我们的修复是否全面，并暴露任何可能仍然存在的、被掩盖的问题。

```bash
pytest
```
