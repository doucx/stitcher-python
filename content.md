好的，我已经在 `stitcher-index` 包中识别出了另外两个需要重构的测试文件。

以下是扩展后的重构计划，旨在将 `test_indexer_aliases.py` 和 `test_indexer.py` 中的手动实例化逻辑替换为标准的 `workspace_factory` 插件。

## [WIP] refactor: 在 stitcher-index 集成与单元测试中统一使用 workspace_factory 插件

### 用户需求
将 `packages/stitcher-index` 目录下手动实例化 `WorkspaceFactory(tmp_path)` 的测试代码重构为使用 Pytest 的 `workspace_factory` 插件。

### 评论
在 `stitcher-index` 这种涉及复杂文件状态（Git 状态、mtime、文件删除）的模块中，统一使用 `workspace_factory` 插件尤为重要。这不仅能减少样板代码，还能确保所有测试都在一个受控的、由插件管理的物理路径中运行，避免手动路径拼接可能引入的错误。

### 目标
1. 修改 `test_indexer_aliases.py` 和 `test_indexer.py`。
2. 将函数签名中的 `tmp_path` 替换为（或补充）`workspace_factory`。
3. 移除 `wf = WorkspaceFactory(tmp_path)`。
4. 确保在调用 `Workspace(...)` 或 `FileIndexer(...)` 时，使用的路径与工厂管理的路径一致。

### 基本原理
由于 `workspace_factory` 插件本身就是基于 `tmp_path` 构建的，直接使用它作为依赖注入项不仅符合 Pytest 的惯用法，还利用了 `stitcher-test-utils` 提供的领域特定语言（DSL）来快速构建测试场景，使测试代码的焦点集中在索引逻辑而非环境准备上。

### 标签
#intent/refine #flow/ready #priority/medium #comp/tests #comp/engine #concept/state #ai/instruct #task/domain/testing #task/object/workspace-factory-fixture #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重构 `test_indexer_aliases.py`

我们将修改别名解析测试，移除手动导入并改用插件。

~~~~~act
patch_file
packages/stitcher-index/tests/integration/test_indexer_aliases.py
~~~~~
~~~~~python.old
from textwrap import dedent
from stitcher.index.indexer import FileIndexer
from stitcher.lang.python.adapter import PythonAdapter
from stitcher.test_utils.workspace import WorkspaceFactory
from stitcher.workspace import Workspace


def test_indexer_resolves_aliases_and_references(tmp_path, store):
    """
    End-to-end test for alias resolution and reference scanning.
    Verifies that:
    1. Aliases (imports) are stored as symbols with kind='alias'.
    2. `alias_target_id` correctly points to the original symbol's SURI.
    3. Usages of aliases create correct ReferenceRecords.
    """
    # 1. Setup: A multi-file python package
    wf = WorkspaceFactory(tmp_path)
    wf.with_source("pkg/__init__.py", "")
~~~~~
~~~~~python.new
from textwrap import dedent
from stitcher.index.indexer import FileIndexer
from stitcher.lang.python.adapter import PythonAdapter
from stitcher.test_utils.workspace import WorkspaceFactory
from stitcher.workspace import Workspace


def test_indexer_resolves_aliases_and_references(workspace_factory: WorkspaceFactory, store):
    """
    End-to-end test for alias resolution and reference scanning.
    Verifies that:
    1. Aliases (imports) are stored as symbols with kind='alias'.
    2. `alias_target_id` correctly points to the original symbol's SURI.
    3. Usages of aliases create correct ReferenceRecords.
    """
    # 1. Setup: A multi-file python package
    wf = workspace_factory
    wf.with_source("pkg/__init__.py", "")
~~~~~

#### Acts 2: 重构 `test_indexer.py`

这个文件包含多个测试函数，我们将逐一替换它们的实例化逻辑。

~~~~~act
patch_file
packages/stitcher-index/tests/unit/test_indexer.py
~~~~~
~~~~~python.old
def test_index_files_git_discovery(tmp_path, store):
    """Test that indexer processes files found by Workspace via git."""
    wf = WorkspaceFactory(tmp_path)
    wf.init_git()
~~~~~
~~~~~python.new
def test_index_files_git_discovery(workspace_factory: WorkspaceFactory, store):
    """Test that indexer processes files found by Workspace via git."""
    wf = workspace_factory
    wf.init_git()
~~~~~
~~~~~act
patch_file
packages/stitcher-index/tests/unit/test_indexer.py
~~~~~
~~~~~python.old
def test_index_files_stat_optimization(tmp_path, store):
    """Test Phase 2 optimization: skip if mtime/size matches."""
    wf = WorkspaceFactory(tmp_path).init_git()
    wf.with_source("main.py", "content")
~~~~~
~~~~~python.new
def test_index_files_stat_optimization(workspace_factory: WorkspaceFactory, store):
    """Test Phase 2 optimization: skip if mtime/size matches."""
    wf = workspace_factory.init_git()
    wf.with_source("main.py", "content")
~~~~~
~~~~~act
patch_file
packages/stitcher-index/tests/unit/test_indexer.py
~~~~~
~~~~~python.old
def test_index_files_content_update(tmp_path, store):
    """Test Phase 3: Update if content changes."""
    wf = WorkspaceFactory(tmp_path).init_git()
    wf.with_source("main.py", "v1")
~~~~~
~~~~~python.new
def test_index_files_content_update(workspace_factory: WorkspaceFactory, store):
    """Test Phase 3: Update if content changes."""
    wf = workspace_factory.init_git()
    wf.with_source("main.py", "v1")
~~~~~
~~~~~act
patch_file
packages/stitcher-index/tests/unit/test_indexer.py
~~~~~
~~~~~python.old
def test_index_files_binary_file(tmp_path, store):
    """Test Phase 4: Binary files are tracked but not parsed."""
    wf = WorkspaceFactory(tmp_path).init_git()
    wf.build()
~~~~~
~~~~~python.new
def test_index_files_binary_file(workspace_factory: WorkspaceFactory, store):
    """Test Phase 4: Binary files are tracked but not parsed."""
    wf = workspace_factory.init_git()
    wf.build()
~~~~~
~~~~~act
patch_file
packages/stitcher-index/tests/unit/test_indexer.py
~~~~~
~~~~~python.old
def test_index_files_adapter_integration(tmp_path, store):
    """Test Phase 4: Adapter is called for text files."""
    wf = WorkspaceFactory(tmp_path).init_git()
    wf.with_source("app.py", "class Main: pass")
~~~~~
~~~~~python.new
def test_index_files_adapter_integration(workspace_factory: WorkspaceFactory, store):
    """Test Phase 4: Adapter is called for text files."""
    wf = workspace_factory.init_git()
    wf.with_source("app.py", "class Main: pass")
~~~~~
~~~~~act
patch_file
packages/stitcher-index/tests/unit/test_indexer.py
~~~~~
~~~~~python.old
def test_index_files_deletion(tmp_path, store):
    """Test deletion sync."""
    wf = WorkspaceFactory(tmp_path).init_git()
    wf.with_source("todelete.py", "pass")
~~~~~
~~~~~python.new
def test_index_files_deletion(workspace_factory: WorkspaceFactory, store):
    """Test deletion sync."""
    wf = workspace_factory.init_git()
    wf.with_source("todelete.py", "pass")
~~~~~

### 下一步建议
- **运行索引测试**: 特别是 `pytest packages/stitcher-index/tests`。
- **验证 Git 逻辑**: 确保 `init_git()` 依然能在 `workspace_factory` 管理的路径中正确初始化仓库。
- **全量回归**: 由于索引是核心组件，建议在重构后运行所有集成测试以确保万无一失。
