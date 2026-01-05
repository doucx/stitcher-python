Excellent. The tool has been enhanced, and we've proven its value on a key test case. Now, let's apply this improved pattern to the rest of the integration tests in the `stitcher-refactor` package.

I will proceed to refactor `test_move_file_e2e.py`, `test_move_directory_e2e.py`, and `test_rename_transformer_advanced.py`. This will complete the task of standardizing our integration test setup logic using our own powerful `WorkspaceFactory`.

Here is the plan to complete the refactoring.

## [WIP] refactor: 全面应用 WorkspaceFactory 重构剩余集成测试

### 用户需求

使用 `WorkspaceFactory` 重构 `stitcher-refactor` 包中剩余的集成测试。

### 评论

这是一个完美的收尾工作。通过将所有集成测试都迁移到 `WorkspaceFactory`，我们不仅统一了代码风格，还建立了一个“良性循环”：我们开发了高质量的测试工具，然后用它来保证我们核心业务逻辑的质量。这极大地提升了整个测试套件的可维护性和可读性。

### 目标

1.  重构 `packages/stitcher-refactor/tests/integration/test_move_file_e2e.py`。
2.  重构 `packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py`。
3.  重构 `packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py`。
4.  确保所有重构后的测试用例都使用声明式的 `WorkspaceFactory` API 来构建其测试环境。

### 基本原理

我们将遵循与上一步完全相同的模式。对于每个测试文件，我们会分析其手动的、命令式的环境设置代码块（`mkdir`, `write_text`, `json.dumps`, `yaml.dump`），并将其完整地替换为一次性的、链式的 `WorkspaceFactory` 调用。

这种方法将分散在多行中的设置逻辑收敛到一个单一、清晰的声明中，使得每个测试的“Arrange”阶段都变得极其简洁和易于理解。

### 标签

#intent/refine #flow/ready #priority/medium #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/workspace-factory #task/action/integration #task/state/continue

---

### Script

#### Acts 1: 重构文件移动测试 (`test_move_file_e2e.py`)

这个测试验证了移动单个文件时，相关的导入和 sidecar 文件是否能被正确更新。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python
import yaml
import json
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.test_utils import WorkspaceFactory


def test_move_file_flat_layout(tmp_path):
    # 1. Arrange: Declaratively build the project structure
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_source("mypkg/__init__.py", "")
        .with_source("mypkg/old.py", "class A:\n    pass")
        .with_source(
            "mypkg/app.py",
            """
            import mypkg.old
            from mypkg.old import A
            from . import old
            from .old import A as AliasA

            x = mypkg.old.A()
            y = A()
            z = old.A()
            w = AliasA()
            """,
        )
        .with_docs("mypkg/old.stitcher.yaml", {"mypkg.old.A": "Doc"})
        .with_raw_file(
            ".stitcher/signatures/mypkg/old.json",
            json.dumps({"mypkg.old.A": {"h": "1"}}),
        )
        .build()
    )

    pkg_dir = project_root / "mypkg"
    old_py = pkg_dir / "old.py"
    app_py = pkg_dir / "app.py"
    old_yaml = old_py.with_suffix(".stitcher.yaml")
    sig_dir = project_root / ".stitcher/signatures/mypkg"
    old_json = sig_dir / "old.json"
    new_py = pkg_dir / "new.py"

    # 2. Analyze
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    ctx = RefactorContext(graph=graph)
    op = MoveFileOperation(old_py, new_py)
    file_ops = op.analyze(ctx)

    # 3. Commit
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. Verify
    # Files moved?
    assert not old_py.exists()
    assert new_py.exists()
    assert not old_yaml.exists()
    assert new_py.with_suffix(".stitcher.yaml").exists()
    assert not old_json.exists()
    assert (sig_dir / "new.json").exists()

    # Content updated?
    new_app = app_py.read_text("utf-8")
    assert "import mypkg.new" in new_app
    assert "from mypkg.new import A" in new_app
    assert "from . import new" in new_app
    assert "from .new import A as AliasA" in new_app

    # Sidecar Keys
    new_yaml_content = new_py.with_suffix(".stitcher.yaml").read_text("utf-8")
    assert "mypkg.new.A" in new_yaml_content
    assert "mypkg.old.A" not in new_yaml_content
~~~~~

#### Acts 2: 重构目录移动测试 (`test_move_directory_e2e.py`)

此测试验证了移动整个目录时，所有内部文件、sidecars 以及外部代码引用都能正确更新。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python
import yaml
import json

from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation
from stitcher.test_utils import WorkspaceFactory


def test_move_directory_updates_all_contents_and_references(tmp_path):
    # 1. SETUP: Declaratively build the project
    factory = WorkspaceFactory(tmp_path)
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

    core_dir = project_root / "mypkg/core"
    services_dir = project_root / "mypkg/services"
    app_py = project_root / "app.py"
    sig_root = project_root / ".stitcher/signatures"

    # 2. ANALYSIS
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    graph.load("app")
    ctx = RefactorContext(graph=graph)

    op = MoveDirectoryOperation(core_dir, services_dir)
    file_ops = op.analyze(ctx)

    # 3. EXECUTION
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. VERIFICATION
    assert not core_dir.exists()
    assert services_dir.exists()
    assert (services_dir / "utils.py").exists()
    assert (services_dir / "config.txt").read_text() == "setting=value"

    assert (services_dir / "utils.stitcher.yaml").exists()
    new_sig_path = sig_root / "mypkg/services/utils.json"
    assert new_sig_path.exists()

    new_yaml_data = yaml.safe_load((services_dir / "utils.stitcher.yaml").read_text())
    assert "mypkg.services.utils.Helper" in new_yaml_data
    new_sig_data = json.loads(new_sig_path.read_text())
    assert "mypkg.services.utils.Helper" in new_sig_data

    updated_app_code = app_py.read_text(encoding="utf-8")
    assert "from mypkg.services.utils import Helper" in updated_app_code
~~~~~

#### Acts 3: 重构高级重命名测试 (`test_rename_transformer_advanced.py`)

这两个测试用例验证了更复杂的导入场景，例如通过属性访问和别名导入。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
~~~~~
~~~~~python
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.test_utils import WorkspaceFactory


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
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    graph.load("main")
    ctx = RefactorContext(graph=graph)

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

### 下一步建议

我们已经成功地完成了对 `stitcher-refactor` 集成测试的全面重构。现在，所有的测试都采用了统一、声明式的 `WorkspaceFactory` 来构建环境，代码库的一致性和可读性得到了显著提升。

这个宏观任务（`#task/action/enhancement`）已经逻辑上完成。下一步，我建议创建一个 `[COMMIT]` 计划，将过去几个 `[WIP]` 计划中的所有修改（包括 `SpyBus` 的应用、`WorkspaceFactory` 的增强以及所有测试文件的重构）作为一个完整的、有价值的工作单元提交到版本控制中。
