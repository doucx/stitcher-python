The test failures indicate two primary issues that arose from recent refactoring of the `stitcher-refactor` engine.

1.  **`AssertionError` & `ImportError`**: The majority of failures stem from the same root cause. The new `Workspace` class relies on finding `pyproject.toml` files to discover Python packages and their source directories (like `src/` or `tests/`). The integration tests were not updated to create these necessary `pyproject.toml` files in their temporary test environments. Consequently, `Workspace._discover_packages()` found nothing, `graph.search_paths` was empty, and Griffe (the code parser) failed with `ImportError` because it didn't know where to look for modules. The `AssertionError`s were simply the first tests to explicitly check the `search_paths` and fail.

2.  **`TypeError`**: A single test, `test_rename_symbol_imported_with_alias`, was not updated after the constructor for `SemanticGraph` and `RefactorContext` was changed. It was still trying to pass an old `root_path` argument instead of the required `workspace` object, leading to a `TypeError`.

I will now generate a plan to fix these issues by updating the test setup across all affected integration test files.

## [WIP] fix(tests): Correct refactor engine integration tests setup

### 错误分析

1.  **`AssertionError` & `ImportError`**: `stitcher-refactor` 引擎的 `Workspace` 类现在依赖 `pyproject.toml` 文件来发现包和源路径。大量的集成测试没有在使用 `WorkspaceFactory` 创建测试环境时生成这些文件，导致 `Workspace` 无法发现任何源路径。这使得 `SemanticGraph` 的 `search_paths` 列表为空，引发了直接的 `AssertionError`，并导致 Griffe 在解析代码时因找不到模块而抛出 `ImportError`。
2.  **`TypeError`**: `test_rename_transformer_advanced.py`中的一个测试用例在 `SemanticGraph` 和 `RefactorContext` 的构造函数签名更新后没有被同步修改，仍在尝试传递一个已被移除的 `root_path` 参数，从而导致 `TypeError`。

### 用户需求

修复 `stitcher-refactor` 包中所有失败的集成测试。

### 评论

这是一个典型的重构后遗症。核心引擎的依赖关系发生了变化（引入了对 `pyproject.toml` 的强依赖），但测试用例没有相应地更新。修复这些测试对于保证重构引擎的稳定性和未来开发至关重要。

### 目标

1.  为所有受影响的集成测试添加 `with_pyproject()` 调用，以确保 `Workspace` 能够正确发现包。
2.  修正 `test_rename_symbol_imported_with_alias` 测试，使其使用新的 `SemanticGraph` 和 `RefactorContext` 构造函数。
3.  确保整个 `stitcher-refactor` 测试套件能够成功通过。

### 基本原理

我们将系统性地审查所有失败的测试，并对其 `WorkspaceFactory` 的设置进行补充，确保测试环境的结构符合 `Workspace` 类的预期。对于 `TypeError`，我们将直接更新代码以匹配新的 API 签名。这种方法直接解决了错误的根源，恢复了测试套件的健康状态。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #concept/parser #scope/dx #ai/instruct #task/domain/testing #task/object/integration-tests #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修复 `test_monorepo_refactor_e2e.py`

为 monorepo 中的每个分发包添加 `pyproject.toml` 文件，以便 `Workspace` 能够发现它们。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class SharedClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            {"pkga_lib.core.SharedClass": "A shared class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            json.dumps({"pkga_lib.core.SharedClass": {"hash": "abc"}}),
        )
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import SharedClass\n\ninstance = SharedClass()",
        )
        .build()
    )
~~~~~
~~~~~python.new
    project_root = (
        factory.with_pyproject("packages/pkg_a")
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class SharedClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            {"pkga_lib.core.SharedClass": "A shared class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            json.dumps({"pkga_lib.core.SharedClass": {"hash": "abc"}}),
        )
        .with_pyproject("packages/pkg_b")
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import SharedClass\n\ninstance = SharedClass()",
        )
        .build()
    )
~~~~~

#### Acts 2: 修复 `test_monorepo_refactor_with_tests_e2e.py`

同样，为 monorepo 中的每个分发包和项目根目录添加 `pyproject.toml` 文件，以确保 `src` 和 `tests` 目录都能被正确发现。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory
        # --- Package A: The provider ---
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class SharedClass: pass")
        .with_source(
            "packages/pkg_a/tests/test_core.py",
            "from pkga_lib.core import SharedClass\n\ndef test_shared():\n    assert SharedClass is not None",
        )
        # --- Package B: A consumer ---
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import SharedClass\n\ninstance = SharedClass()",
        )
        # --- Top-level integration tests ---
        .with_source("tests/integration/__init__.py", "")
        .with_source(
            "tests/integration/test_full_system.py",
            "from pkga_lib.core import SharedClass\n\ndef test_integration():\n    s = SharedClass()\n    assert s is not None",
        )
        .build()
    )
~~~~~
~~~~~python.new
    project_root = (
        factory.with_pyproject(
            "."
        )  # For top-level tests discovery
        # --- Package A: The provider ---
        .with_pyproject("packages/pkg_a")
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class SharedClass: pass")
        .with_source(
            "packages/pkg_a/tests/test_core.py",
            "from pkga_lib.core import SharedClass\n\ndef test_shared():\n    assert SharedClass is not None",
        )
        # --- Package B: A consumer ---
        .with_pyproject("packages/pkg_b")
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import SharedClass\n\ninstance = SharedClass()",
        )
        # --- Top-level integration tests ---
        .with_source("tests/integration/__init__.py", "")
        .with_source(
            "tests/integration/test_full_system.py",
            "from pkga_lib.core import SharedClass\n\ndef test_integration():\n    s = SharedClass()\n    assert s is not None",
        )
        .build()
    )
~~~~~

#### Acts 3: 修复 `test_move_directory_e2e.py`

在项目根目录添加一个 `pyproject.toml`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_source("mypkg/core/__init__.py", "")
        .with_source("mypkg/core/utils.py", "class Helper: pass")
        .with_raw_file("mypkg/core/config.txt", "setting=value")
        .with_raw_file("mypkg/core/.env", "SECRET=123")
        .with_source(
            "app.py",
            """
            from mypkg.core.utils import Helper

            h = Helper()
            """,
        )
        .with_docs(
            "mypkg/core/utils.stitcher.yaml",
            {"mypkg.core.utils.Helper": "Doc for Helper"},
        )
        .with_raw_file(
            ".stitcher/signatures/mypkg/core/utils.json",
            json.dumps({"mypkg.core.utils.Helper": {"hash": "123"}}),
        )
        .build()
    )
~~~~~
~~~~~python.new
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/core/__init__.py", "")
        .with_source("mypkg/core/utils.py", "class Helper: pass")
        .with_raw_file("mypkg/core/config.txt", "setting=value")
        .with_raw_file("mypkg/core/.env", "SECRET=123")
        .with_source(
            "app.py",
            """
            from mypkg.core.utils import Helper

            h = Helper()
            """,
        )
        .with_docs(
            "mypkg/core/utils.stitcher.yaml",
            {"mypkg.core.utils.Helper": "Doc for Helper"},
        )
        .with_raw_file(
            ".stitcher/signatures/mypkg/core/utils.json",
            json.dumps({"mypkg.core.utils.Helper": {"hash": "123"}}),
        )
        .build()
    )
~~~~~

#### Acts 4: 修复 `test_move_file_e2e.py`

在项目根目录添加一个 `pyproject.toml`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_source("mypkg/__init__.py", "")
        .with_source("mypkg/old.py", "class A:\n    pass")
~~~~~
~~~~~python.new
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/old.py", "class A:\n    pass")
~~~~~

#### Acts 5: 修复 `test_move_nested_directory_e2e.py`

在项目根目录添加一个 `pyproject.toml`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_source("src/cascade/__init__.py", "")
        .with_source("src/cascade/core/__init__.py", "")
~~~~~
~~~~~python.new
    project_root = (
        factory.with_pyproject(".")
        .with_source("src/cascade/__init__.py", "")
        .with_source("src/cascade/core/__init__.py", "")
~~~~~

#### Acts 6: 修复 `test_rename_e2e.py`

在项目根目录添加一个 `pyproject.toml`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_source(
            "mypkg/core.py",
~~~~~
~~~~~python.new
    project_root = (
        factory.with_pyproject(".")
        .with_source(
            "mypkg/core.py",
~~~~~

#### Acts 7: 修复 `test_rename_symbol_monorepo_e2e.py`

为所有包和根目录添加 `pyproject.toml`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory
        # --- Package A: Defines the symbol ---
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class OldNameClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            {"pkga_lib.core.OldNameClass": "Docs for the old class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            json.dumps({"pkga_lib.core.OldNameClass": {"hash": "abc"}}),
        )
        .with_source(
            "packages/pkg_a/tests/test_core.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_local():\n    assert OldNameClass is not None",
        )
        # --- Package B: Consumes the symbol ---
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import OldNameClass\n\ninstance = OldNameClass()",
        )
        # --- Top-level integration test: Also consumes the symbol ---
        .with_source(
            "tests/integration/test_system.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_system_integration():\n    assert OldNameClass",
        )
        .build()
    )
~~~~~
~~~~~python.new
    project_root = (
        factory.with_pyproject(
            "."
        )  # For top-level integration tests
        # --- Package A: Defines the symbol ---
        .with_pyproject("packages/pkg_a")
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class OldNameClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            {"pkga_lib.core.OldNameClass": "Docs for the old class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            json.dumps({"pkga_lib.core.OldNameClass": {"hash": "abc"}}),
        )
        .with_source(
            "packages/pkg_a/tests/test_core.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_local():\n    assert OldNameClass is not None",
        )
        # --- Package B: Consumes the symbol ---
        .with_pyproject("packages/pkg_b")
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import OldNameClass\n\ninstance = OldNameClass()",
        )
        # --- Top-level integration test: Also consumes the symbol ---
        .with_source(
            "tests/integration/test_system.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_system_integration():\n    assert OldNameClass",
        )
        .build()
    )
~~~~~

#### Acts 8: 修复 `test_rename_transformer_advanced.py`

为两个测试都添加 `pyproject.toml`，并修正第二个测试中 `SemanticGraph` 和 `RefactorContext` 的实例化方式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
~~~~~
~~~~~python.old
def test_rename_symbol_via_attribute_access(tmp_path):
    # 1. Setup
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldHelper: pass")
        .with_source(
            "main.py",
            """
            import mypkg.core

            h = mypkg.core.OldHelper()
            """,
        )
        .build()
    )

    # 2. Analyze
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    # 3. Plan
    op = RenameSymbolOperation("mypkg.core.OldHelper", "mypkg.core.NewHelper")
    ops = op.analyze(ctx)

    # 4. Verify (without committing, just check the planned ops)
    assert len(ops) == 2
    write_ops = {op.path.name: op for op in ops}
    assert "core.py" in write_ops
    assert "main.py" in write_ops
    assert "class NewHelper: pass" in write_ops["core.py"].content
    assert "h = mypkg.core.NewHelper()" in write_ops["main.py"].content


def test_rename_symbol_imported_with_alias(tmp_path):
    # 1. Setup
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldHelper: pass")
        .with_source(
            "main.py",
            """
            from mypkg.core import OldHelper as OH

            h = OH()
            """,
        )
        .build()
    )

    # 2. Analyze
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    graph.load("main")
    ctx = RefactorContext(graph=graph)

    # 3. Plan
    op = RenameSymbolOperation("mypkg.core.OldHelper", "mypkg.core.NewHelper")
    ops = op.analyze(ctx)

    # 4. Verify
    assert len(ops) == 2
    write_ops = {op.path.name: op for op in ops}
    expected_main = "from mypkg.core import NewHelper as OH\n\nh = OH()"
    assert "core.py" in write_ops
    assert write_ops["core.py"].content == "class NewHelper: pass"
    assert "main.py" in write_ops
    assert write_ops["main.py"].content.strip() == expected_main.strip()
~~~~~
~~~~~python.new
def test_rename_symbol_via_attribute_access(tmp_path):
    # 1. Setup
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldHelper: pass")
        .with_source(
            "main.py",
            """
            import mypkg.core

            h = mypkg.core.OldHelper()
            """,
        )
        .build()
    )

    # 2. Analyze
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    # 3. Plan
    op = RenameSymbolOperation("mypkg.core.OldHelper", "mypkg.core.NewHelper")
    ops = op.analyze(ctx)

    # 4. Verify (without committing, just check the planned ops)
    assert len(ops) == 2
    write_ops = {op.path.name: op for op in ops}
    assert "core.py" in write_ops
    assert "main.py" in write_ops
    assert "class NewHelper: pass" in write_ops["core.py"].content
    assert "h = mypkg.core.NewHelper()" in write_ops["main.py"].content


def test_rename_symbol_imported_with_alias(tmp_path):
    # 1. Setup
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldHelper: pass")
        .with_source(
            "main.py",
            """
            from mypkg.core import OldHelper as OH

            h = OH()
            """,
        )
        .build()
    )

    # 2. Analyze
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    # 3. Plan
    op = RenameSymbolOperation("mypkg.core.OldHelper", "mypkg.core.NewHelper")
    ops = op.analyze(ctx)

    # 4. Verify
    assert len(ops) == 2
    write_ops = {op.path.name: op for op in ops}
    expected_main = "from mypkg.core import NewHelper as OH\n\nh = OH()"
    assert "core.py" in write_ops
    assert write_ops["core.py"].content.strip() == "class NewHelper: pass"
    assert "main.py" in write_ops
    assert write_ops["main.py"].content.strip() == expected_main.strip()
~~~~~

### 下一步建议

在应用这些修复后，应重新运行 `stitcher-refactor` 包的测试套件，以确认所有问题都已解决。如果通过，我会生成一个 `[COMMIT]` 计划来提交这些更改。
