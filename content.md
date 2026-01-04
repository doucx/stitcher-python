你说得非常对，这是一个更周全、更健壮的方案。

我的提议（简单删除源目录）过于草率，因为它忽略了源目录中可能存在的、非 `.py` 但对项目同样重要的文件（如文档、资源文件、配置文件等）。直接删除会导致数据丢失。

你的方案——**先智能移动 Python 相关文件并重构，再批量移动所有剩余文件，最后安全删除空目录**——是更优越的策略。它确保了 `MoveDirectoryOperation` 的行为与用户对文件管理器中“移动文件夹”操作的直觉期望完全一致，同时又保留了 Stitcher 的代码感知重构能力。

我将立即生成一个计划来实现这个新方案。

## [WIP] feat(refactor): 增强 MoveDirectoryOperation 以支持全量文件迁移

### 用户需求
增强 `MoveDirectoryOperation`，使其不仅能移动 `.py` 及其 sidecar 文件并更新代码引用，还能将源目录中所有其他类型的文件（如 `README.md`, `config.json` 等）一并迁移到目标目录，并在迁移完成后删除源目录。

### 评论
这是一个关键的用户体验 (UX) 和功能完整性改进。通过实现全量迁移，`MoveDirectoryOperation` 从一个纯粹的“Python 代码重构工具”演变为一个完整的、对开发者友好的“智能文件系统操作工具”。这使得大规模重构操作变得更加安全和可预测。

### 目标
1.  为 `TransactionManager` 添加一个新的操作类型 `DeleteDirectoryOp`，用于安全地递归删除目录。
2.  重写 `MoveDirectoryOperation` 的 `analyze` 方法，以实现新的三阶段迁移逻辑。
3.  更新集成测试，以验证新行为：
    *   非 Python 文件被正确移动。
    *   源目录在操作后被成功删除。

### 基本原理
我们将采用你建议的三阶段工作流来实现 `MoveDirectoryOperation`：

1.  **阶段一：语义移动 (Semantic Move)**:
    *   与当前实现相同，首先使用 `rglob("*.py")` 找到所有 Python 文件。
    *   为每个 `.py` 文件调用 `MoveFileOperation`。这将生成对 `.py` 文件、其 Sidecar 文件 (`.yaml`, `.json`) 的移动操作，以及对代码库中所有引用的更新操作。
    *   我们会记录下所有在此阶段被处理过的文件的路径。

2.  **阶段二：逐字移动 (Verbatim Move)**:
    *   接下来，我们将遍历源目录下的**所有**文件 (`*.*`)。
    *   对于每个文件，检查它是否已在阶段一中被处理过。
    *   如果**没有**，则为它创建一个简单的 `MoveFileOp`，将其按原样移动到目标目录的相应位置。这确保了所有非代码文件的迁移。

3.  **阶段三：清理 (Cleanup)**:
    *   在所有文件移动操作都规划完毕后，向事务中添加一个最终的 `DeleteDirectoryOp` 操作，以删除现已为空的源目录。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/executor #scope/core #scope/ux #ai/brainstorm #task/domain/refactoring #task/object/directory-move #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 为事务管理器添加目录删除能力

首先，我们需要让 `TransactionManager` 能够处理目录删除操作。我将通过 `patch_file` 为 `transaction.py` 添加 `DeleteDirectoryOp` 类和相应的 `add_delete_directory` 方法。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/transaction.py
~~~~~
~~~~~python.old
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union, Protocol, Optional
~~~~~
~~~~~python.new
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union, Protocol, Optional
import rmtree
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/transaction.py
~~~~~
~~~~~python.old
    def describe(self) -> str:
        return f"[MOVE] {self.path} -> {self.dest}"


class TransactionManager:
    def __init__(self, root_path: Path, fs: Optional[FileSystemAdapter] = None):
        self.root_path = root_path
        self.fs = fs or RealFileSystem()
        self._ops: List[FileOp] = []

    def add_write(self, path: Union[str, Path], content: str) -> None:
~~~~~
~~~~~python.new
    def describe(self) -> str:
        return f"[MOVE] {self.path} -> {self.dest}"


@dataclass
class DeleteDirectoryOp(FileOp):
    def execute(self, fs: FileSystemAdapter, root: Path) -> None:
        # We use a simple wrapper around shutil for now
        dir_to_delete = root / self.path
        if dir_to_delete.is_dir():
            shutil.rmtree(dir_to_delete)

    def describe(self) -> str:
        return f"[DELETE_DIR] {self.path}"


class TransactionManager:
    def __init__(self, root_path: Path, fs: Optional[FileSystemAdapter] = None):
        self.root_path = root_path
        self.fs = fs or RealFileSystem()
        self._ops: List[FileOp] = []

    def add_write(self, path: Union[str, Path], content: str) -> None:
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/transaction.py
~~~~~
~~~~~python.old
    def add_move(self, src: Union[str, Path], dest: Union[str, Path]) -> None:
        self._ops.append(MoveFileOp(Path(src), Path(dest)))

    def preview(self) -> List[str]:
        return [op.describe() for op in self._ops]
~~~~~
~~~~~python.new
    def add_move(self, src: Union[str, Path], dest: Union[str, Path]) -> None:
        self._ops.append(MoveFileOp(Path(src), Path(dest)))

    def add_delete_directory(self, path: Union[str, Path]) -> None:
        self._ops.append(DeleteDirectoryOp(Path(path)))

    def preview(self) -> List[str]:
        return [op.describe() for op in self._ops]
~~~~~

#### Acts 2: 采用三阶段逻辑重写 `MoveDirectoryOperation`

现在我将用新的三阶段逻辑重写 `MoveDirectoryOperation` 的 `analyze` 方法。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Set

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, DeleteDirectoryOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.move_file import MoveFileOperation


class MoveDirectoryOperation(AbstractOperation):
    """
    Orchestrates the move of an entire directory, including Python files,
    sidecars, other assets, and finally cleaning up the source directory.
    """

    def __init__(self, src_dir: Path, dest_dir: Path):
        if not src_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {src_dir}")
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        """
        Analyzes the directory move using a three-phase process:
        1. Semantic Move: Handles Python files and their sidecars, updating references.
        2. Verbatim Move: Moves all remaining files.
        3. Cleanup: Deletes the now-empty source directory.
        """
        all_ops: List[FileOp] = []
        handled_paths: Set[Path] = set()

        # --- Phase 1: Semantic Move ---
        for src_file in self.src_dir.rglob("*.py"):
            relative_path = src_file.relative_to(self.src_dir)
            dest_file = self.dest_dir / relative_path

            file_mover = MoveFileOperation(src_file, dest_file)
            file_specific_ops = file_mover.analyze(ctx)
            all_ops.extend(file_specific_ops)

            # Track which source files were handled by the semantic mover
            # Note: MoveFileOperation handles the .py, .yaml, and .json sidecars.
            handled_paths.add(src_file)
            if src_file.with_suffix(".stitcher.yaml").exists():
                handled_paths.add(src_file.with_suffix(".stitcher.yaml"))

            rel_sig_path = (
                ctx.graph.root_path
                / ".stitcher/signatures"
                / src_file.relative_to(ctx.graph.root_path).with_suffix(".json")
            )
            if rel_sig_path.exists():
                handled_paths.add(rel_sig_path)

        # --- Phase 2: Verbatim Move ---
        for src_item in self.src_dir.rglob("*"):
            if not src_item.is_file():
                continue
            if src_item in handled_paths:
                continue

            relative_path = src_item.relative_to(self.src_dir)
            dest_item = self.dest_dir / relative_path

            all_ops.append(
                MoveFileOp(
                    src_item.relative_to(ctx.graph.root_path),
                    dest_item.relative_to(ctx.graph.root_path),
                )
            )
            handled_paths.add(src_item)

        # --- Phase 3: Cleanup ---
        all_ops.append(
            DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path))
        )

        return all_ops
~~~~~

#### Acts 3: 升级集成测试以验证全量迁移和目录删除

最后，我将更新集成测试。它现在会包含一个非 Python 文件，并断言该文件被移动且源目录最终被删除。

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
    # │       ├── utils.py      (defines Helper)
    # │       └── config.txt    (non-python file)
    # └── app.py                (imports from mypkg.core.utils)

    pkg_dir = tmp_path / "mypkg"
    core_dir = pkg_dir / "core"
    core_dir.mkdir(parents=True)

    (pkg_dir / "__init__.py").touch()
    (core_dir / "__init__.py").touch()
    utils_py = core_dir / "utils.py"
    utils_py.write_text("class Helper: pass", encoding="utf-8")
    (core_dir / "config.txt").write_text("some-config", encoding="utf-8")

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
        elif hasattr(fop, 'content'): # WriteFileOp
             tm.add_write(fop.path, fop.content)
        else: # DeleteDirectoryOp
            tm.add_delete_directory(fop.path)
    tm.commit()

    # 4. VERIFICATION
    # Source directory is gone
    assert not core_dir.exists()
    assert pkg_dir.exists() # Make sure we didn't delete too much

    # Destination directory and its contents are there
    assert services_dir.exists()
    assert (services_dir / "utils.py").exists()
    assert (services_dir / "config.txt").exists()
    assert (services_dir / "config.txt").read_text() == "some-config"

    # Sidecars moved?
    assert (services_dir / "utils.stitcher.yaml").exists()
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
我们已经完成了对 `MoveDirectoryOperation` 的功能增强和测试覆盖。现在，`stitcher-refactor` 已经具备了处理大规模包结构重构的核心能力。我建议我们继续推进路线图，进入 **第四阶段：迁移包系统与 CLI**，为这个强大的引擎创建一个用户友好的入口。
