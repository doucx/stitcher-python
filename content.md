好的，我将立即开始实现 `MoveDirectoryOperation`。这是执行计划。

## [WIP] feat(refactor): 实现 MoveDirectoryOperation 以支持目录级重构

### 用户需求
根据我们的讨论，需要实现 `MoveDirectoryOperation` 来支持对整个文件夹（及其包含的所有 Python 文件和 Sidecar 文件）的移动和重构操作。

### 评论
这是完成 `阶段三` 目标的关键一步，它将 `stitcher-refactor` 引擎从处理单个文件的能力提升到了处理整个包结构调整的能力。该功能构建在 `MoveFileOperation` 的坚实基础之上，是实现大规模、自动化架构演进的核心。

### 目标
1.  创建新的操作类 `MoveDirectoryOperation`，使其能够编排对目录内所有文件的 `MoveFileOperation`。
2.  为 `MoveDirectoryOperation` 编写一个全面的端到端集成测试，确保代码引用更新、Sidecar 文件移动和 Sidecar 内容更新三个方面都能正确工作。

### 基本原理
我们将遵循之前讨论的设计方案，创建一个专门的 `MoveDirectoryOperation` 类作为编排器。它将递归地扫描源目录中的所有 `.py` 文件，并为每个文件实例化和调用一个 `MoveFileOperation`。这种方法将目录遍历的逻辑与文件移动的复杂逻辑（FQN计算、代码转换、Sidecar更新）分离开来，最大限度地重用了现有代码，并遵循了单一职责原则。

### 标签
#intent/build #flow/ready #priority/high #concept/executor #scope/core #ai/brainstorm #task/domain/refactoring #task/object/directory-move #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建 `MoveDirectoryOperation` 实现文件

我将创建 `move_directory.py` 文件，并添加 `MoveDirectoryOperation` 类。这个类将作为编排器，将目录移动任务分解为一系列针对单个文件的移动任务。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.move_file import MoveFileOperation


class MoveDirectoryOperation(AbstractOperation):
    """Orchestrates the move of an entire directory."""

    def __init__(self, src_dir: Path, dest_dir: Path):
        if not src_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {src_dir}")
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        """
        Analyzes the directory move by creating a MoveFileOperation for each file.
        """
        all_ops: List[FileOp] = []

        # Find all Python files within the source directory
        for src_file in self.src_dir.rglob("*.py"):
            # Calculate the corresponding destination path for the file
            relative_path = src_file.relative_to(self.src_dir)
            dest_file = self.dest_dir / relative_path

            # Delegate the complex analysis to the existing MoveFileOperation
            file_mover = MoveFileOperation(src_file, dest_file)

            # Analyze the individual file move and collect the resulting operations
            file_specific_ops = file_mover.analyze(ctx)
            all_ops.extend(file_specific_ops)

        return all_ops
~~~~~

#### Acts 2: 添加端到端集成测试

现在，我将创建一个新的测试文件来验证 `MoveDirectoryOperation` 的行为。这个测试将模拟一个真实的场景：移动一个包含 Python 模块的子目录，并验证外部对该模块的引用是否被正确更新，以及所有相关的 Sidecar 文件是否同步迁移和更新。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python
from pathlib import Path
import yaml
import json

from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation


def test_move_directory_updates_all_contents_and_references(tmp_path):
    # 1. SETUP
    # /
    # ├── mypkg/
    # │   ├── __init__.py
    # │   └── core/
    # │       ├── __init__.py
    # │       └── utils.py  (defines Helper)
    # └── app.py            (imports from mypkg.core.utils)

    pkg_dir = tmp_path / "mypkg"
    core_dir = pkg_dir / "core"
    core_dir.mkdir(parents=True)

    (pkg_dir / "__init__.py").touch()
    (core_dir / "__init__.py").touch()
    utils_py = core_dir / "utils.py"
    utils_py.write_text("class Helper: pass", encoding="utf-8")

    app_py = tmp_path / "app.py"
    app_py.write_text(
        "from mypkg.core.utils import Helper\n\n" "h = Helper()", encoding="utf-8"
    )

    # Sidecars for utils.py
    utils_yaml = utils_py.with_suffix(".stitcher.yaml")
    utils_yaml.write_text(
        yaml.dump({"mypkg.core.utils.Helper": "Doc for Helper"})
    )

    sig_root = tmp_path / ".stitcher/signatures"
    utils_sig_path = sig_root / "mypkg/core/utils.json"
    utils_sig_path.parent.mkdir(parents=True)
    utils_sig_path.write_text(
        json.dumps({"mypkg.core.utils.Helper": {"hash": "123"}})
    )

    # 2. ANALYSIS
    # We want to move `mypkg/core` -> `mypkg/services`
    services_dir = pkg_dir / "services"

    graph = SemanticGraph(root_path=tmp_path)
    graph.load("mypkg")
    graph.load("app")
    ctx = RefactorContext(graph=graph)

    op = MoveDirectoryOperation(core_dir, services_dir)
    file_ops = op.analyze(ctx)

    # 3. EXECUTION
    tm = TransactionManager(tmp_path)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. VERIFICATION
    # Directories and files moved?
    assert not core_dir.exists()
    assert services_dir.exists()
    assert (services_dir / "utils.py").exists()

    # Sidecars moved?
    assert not utils_yaml.exists()
    assert (services_dir / "utils.stitcher.yaml").exists()
    assert not utils_sig_path.exists()
    new_sig_path = sig_root / "mypkg/services/utils.json"
    assert new_sig_path.exists()

    # Code references updated in app.py?
    updated_app_code = app_py.read_text(encoding="utf-8")
    assert "from mypkg.services.utils import Helper" in updated_app_code

    # Sidecar content updated?
    new_yaml_data = yaml.safe_load(
        (services_dir / "utils.stitcher.yaml").read_text()
    )
    assert "mypkg.services.utils.Helper" in new_yaml_data

    new_sig_data = json.loads(new_sig_path.read_text())
    assert "mypkg.services.utils.Helper" in new_sig_data
~~~~~

### 下一步建议
在执行此计划后，`stitcher-refactor` 引擎将具备处理大规模包结构调整的能力。下一步的关键是进入路线图的**第四阶段：迁移包系统与 CLI**。这将为我们刚刚实现的功能提供一个面向用户的、可编写脚本的接口（例如 `stitcher refactor apply <migration_script.py>`），从而使整个重构引擎变得真正可用。
