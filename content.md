你的观察非常及时。重构后的测试套件确实存在过时引用和命名冲突：

1.  **`test_scanner_aliases.py`**: 仍然在使用已经不存在的 `WorkspaceScanner` 及其 `scan()` 方法。
2.  **`test_workspace.py` 冲突与错位**: 
    - `packages/stitcher-refactor` 中还残留着 `Workspace` 的单元测试。
    - 既然 `Workspace` 已经独立成包，这些关于布局发现（Standard, Flat, Namespace）的测试理应迁移到 `stitcher-workspace` 中，与 `discover_files` 的测试合并。

我将立即清理这些残留，完成测试套件的现代化。

## [WIP] refactor(tests): 清理过时测试并统一 Workspace 测试

### 错误分析

1.  **逻辑过时**: `packages/stitcher-index/tests/integration/test_scanner_aliases.py` 依赖于已重构的 `WorkspaceScanner` API，无法运行。
2.  **职责错位**: `packages/stitcher-refactor/tests/unit/refactor/test_workspace.py` 中的测试逻辑（验证项目布局解析）现在属于 `stitcher-workspace` 的核心职责，留在 `refactor` 包中会导致维护混乱。
3.  **命名冲突**: 两个包中存在同名的 `test_workspace.py`，不利于测试结果的清晰展示。

### 用户需求

1.  更新 `stitcher-index` 的集成测试，将其适配为 `FileIndexer`。
2.  将 `stitcher-refactor` 中关于 `Workspace` 的测试迁移并合并到 `stitcher-workspace` 包中。
3.  删除 `stitcher-refactor` 中不再需要的测试文件。

### 目标

1.  将 `test_scanner_aliases.py` 重命名为 `test_indexer_aliases.py`。
2.  重构 `test_indexer_aliases.py`，使用 `Workspace` 发现文件，并调用 `FileIndexer.index_files()`。
3.  将 `stitcher-refactor` 中的工作区布局测试合并到 `packages/stitcher-workspace/tests/unit/test_workspace.py`。
4.  删除 `packages/stitcher-refactor/tests/unit/refactor/test_workspace.py`。

### 标签

#intent/refine #intent/tooling #flow/ready #priority/medium #comp/tests #scope/core #ai/instruct #task/domain/architecture #task/object/test-suite #task/action/cleanup #task/state/continue

---

### Script

#### Acts 1: 重构索引器别名集成测试

重命名并更新 `test_scanner_aliases.py`，使其反映“发现 -> 索引”的新流。

~~~~~act
move_file
packages/stitcher-index/tests/integration/test_scanner_aliases.py
packages/stitcher-index/tests/integration/test_indexer_aliases.py
~~~~~

~~~~~act
write_file
packages/stitcher-index/tests/integration/test_indexer_aliases.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.index.indexer import FileIndexer
from stitcher.adapter.python.index_adapter import PythonAdapter
from stitcher.test_utils.workspace import WorkspaceFactory
from stitcher.workspace import Workspace

import pytest


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
    wf.with_source(
        "pkg/defs.py",
        dedent(
            """
            class MyClass:
                pass

            def my_func():
                pass
            """
        ),
    )
    wf.with_source(
        "pkg/main.py",
        dedent(
            """
            import pkg.defs
            from pkg.defs import MyClass
            from pkg.defs import my_func as func_alias

            # Usages
            instance = MyClass()
            pkg.defs.my_func()
            func_alias()
            """
        ),
    )
    project_root = wf.build()

    # 2. Execution: Run the full indexer pipeline
    workspace = Workspace(project_root)
    files_to_index = workspace.discover_files()

    indexer = FileIndexer(project_root, store)
    # Manual search_paths to avoid dependency on Workspace service in pure index tests
    adapter = PythonAdapter(project_root, [project_root])
    indexer.register_adapter(".py", adapter)
    indexer.index_files(files_to_index)

    # 3. Verification
    main_py_record = store.get_file_by_path("pkg/main.py")
    assert main_py_record is not None

    # 3a. Verify Alias Symbols in main.py
    symbols = store.get_symbols_by_file(main_py_record.id)
    symbols_by_name = {s.name: s for s in symbols}

    # from pkg.defs import MyClass
    alias_myclass = symbols_by_name.get("MyClass")
    assert alias_myclass is not None
    assert alias_myclass.kind == "alias"
    assert alias_myclass.alias_target_id == "py://pkg/defs.py#MyClass"

    # from pkg.defs import my_func as func_alias
    alias_funcalias = symbols_by_name.get("func_alias")
    assert alias_funcalias is not None
    assert alias_funcalias.kind == "alias"
    assert alias_funcalias.alias_target_id == "py://pkg/defs.py#my_func"

    # import pkg.defs
    alias_pkg_defs = symbols_by_name.get("pkg")
    assert alias_pkg_defs is not None
    assert alias_pkg_defs.kind == "alias"
    assert alias_pkg_defs.alias_target_id == "py://pkg/__init__.py"

    # 3b. Verify References in main.py
    references = store.get_references_by_file(main_py_record.id)
    ref_targets = {ref.target_id for ref in references}

    assert "py://pkg/defs.py#MyClass" in ref_targets
    assert "py://pkg/defs.py#my_func" in ref_targets
~~~~~

#### Acts 2: 迁移并合并 Workspace 单元测试

我们将 `stitcher-refactor` 中的布局测试合并到 `stitcher-workspace` 的单元测试文件中，并删除旧文件。

~~~~~act
write_file
packages/stitcher-workspace/tests/unit/test_workspace.py
~~~~~
~~~~~python
from stitcher.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_discover_files_git(tmp_path):
    # Arrange
    factory = WorkspaceFactory(tmp_path).init_git()
    factory.with_source("src/pkg_a/mod1.py", "pass")
    factory.with_source("src/pkg_a/data.txt", "data")
    factory.with_source("untracked.py", "pass")
    factory.with_raw_file(".gitignore", "*.txt\n.stitcher/")
    factory.with_source(".stitcher/signatures/src/pkg_a/mod1.json", "{}")
    project_root = factory.build()

    # Act
    workspace = Workspace(project_root)
    files = workspace.discover_files()

    # Assert
    assert "src/pkg_a/mod1.py" in files
    assert "untracked.py" in files
    assert ".gitignore" in files
    assert "src/pkg_a/data.txt" not in files, "Should be gitignored"
    assert (
        ".stitcher/signatures/src/pkg_a/mod1.json" not in files
    ), "Should ignore .stitcher dir"


def test_discover_files_os_walk(tmp_path):
    # Arrange
    factory = WorkspaceFactory(tmp_path)  # No git
    factory.with_source("src/pkg_a/mod1.py", "pass")
    factory.with_source("src/pkg_a/data.txt", "data")
    factory.with_source(".hidden/file.py", "pass")
    factory.with_source(".stitcher/config.json", "{}")
    project_root = factory.build()

    # Act
    workspace = Workspace(project_root)
    files = workspace.discover_files()

    # Assert
    assert "src/pkg_a/mod1.py" in files
    assert "src/pkg_a/data.txt" in files
    assert ".hidden/file.py" not in files, "Should ignore hidden directories"
    assert ".stitcher/config.json" not in files, "Should ignore .stitcher directory"


def test_workspace_standard_src_layout(tmp_path):
    # ARRANGE
    factory = (
        WorkspaceFactory(tmp_path)
        .with_pyproject("pkg_a")
        .with_source("pkg_a/src/pkga_lib/__init__.py", "")
    )
    project_root = factory.build()
    pkg_a_src = project_root / "pkg_a" / "src"

    # ACT
    workspace = Workspace(project_root)

    # ASSERT
    assert workspace.import_to_source_dirs["pkga_lib"] == {pkg_a_src}
    assert sorted(workspace.get_search_paths()) == sorted([project_root, pkg_a_src])


def test_workspace_flat_layout(tmp_path):
    # ARRANGE
    factory = (
        WorkspaceFactory(tmp_path)
        .with_pyproject("pkg_b")
        .with_source("pkg_b/pkgb_lib/__init__.py", "")
    )
    project_root = factory.build()
    pkg_b_root = project_root / "pkg_b"

    # ACT
    workspace = Workspace(project_root)

    # ASSERT
    assert workspace.import_to_source_dirs["pkgb_lib"] == {pkg_b_root}
    assert sorted(workspace.get_search_paths()) == sorted([project_root, pkg_b_root])


def test_workspace_namespace_package(tmp_path):
    # ARRANGE
    factory = (
        WorkspaceFactory(tmp_path)
        .with_pyproject("cascade-engine")
        .with_source("cascade-engine/src/cascade/__init__.py", "")
        .with_pyproject("cascade-app")
        .with_source("cascade-app/src/cascade/__init__.py", "")
    )
    project_root = factory.build()
    engine_src = project_root / "cascade-engine" / "src"
    app_src = project_root / "cascade-app" / "src"

    # ACT
    workspace = Workspace(project_root)

    # ASSERT
    assert workspace.import_to_source_dirs["cascade"] == {engine_src, app_src}
    assert sorted(workspace.get_search_paths()) == sorted(
        [project_root, engine_src, app_src]
    )
~~~~~

~~~~~act
delete_file
packages/stitcher-refactor/tests/unit/refactor/test_workspace.py
~~~~~

### 下一步建议

测试套件现在的结构已经与新架构完全同步。

我建议现在运行 `pytest` 来验证所有变更。如果所有测试通过，我们将准备最后的 `[COMMIT]` 计划。
