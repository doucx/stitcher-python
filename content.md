你提出了一个非常深刻且关键的观点，完全正确。

我的前一个方案过于简单，只考虑了 `.py` 文件，**这可能导致数据丢失**——任何非 Python 文件（如配置文件、文档、资源文件）都会被留在旧目录中，然后旧目录被删除。你的方案——**移动所有内容，但对 Python 文件进行特殊处理**——是唯一正确且健壮的方法。

我将立即采纳你的建议，并生成一个实现此增强逻辑的计划。

## [WIP] refactor(refactor): 增强 MoveDirectoryOperation 以处理非代码文件并清理源目录

### 用户需求
`MoveDirectoryOperation` 必须能够：
1.  移动源目录下的**所有**内容（包括子目录、非 Python 文件和隐藏文件）。
2.  对 `.py` 文件应用智能重构逻辑（更新代码引用和 Sidecar）。
3.  对所有其他文件执行简单的物理移动。
4.  在所有内容成功移动后，安全地删除空的源目录。

### 评论
这是一个关键的健壮性改进，它将 `MoveDirectoryOperation` 从一个特定于 Python 的工具，转变为一个通用的、同时具备语义感知能力的文件系统重构工具。通过处理所有文件类型，我们确保了操作的完整性，避免了任何潜在的数据丢失风险，这完全符合用户对一个可靠的自动化工具的期望。

### 目标
1.  为 `TransactionManager` 增加 `DeleteDirectoryOp` 和 `DeleteFileOp`，使其具备删除文件和目录的能力。
2.  重写 `MoveDirectoryOperation.analyze` 的逻辑，使其能够遍历源目录下的所有文件和目录，并根据文件类型应用不同的移动策略。
3.  扩展集成测试，使其包含非 Python 文件和隐藏文件，并验证它们是否被正确移动，以及源目录最终是否被删除。

### 基本原理
新的 `MoveDirectoryOperation` 将遵循以下策略：
1.  **全面扫描**: 使用 `rglob("*")` 遍历源目录下的所有路径。
2.  **分类处理**:
    -   如果路径是 `.py` 文件，则委托给 `MoveFileOperation` 进行“智能移动”，这会处理代码和 Sidecar 的重构。
    -   如果路径是任何其他文件（非 `.py`），则为其生成一个简单的 `MoveFileOp`，只进行物理移动。
3.  **最终清理**: 在规划完所有文件的移动后，为源目录本身和其所有子目录添加 `DeleteDirectoryOp`。`TransactionManager` 将在最后执行这些删除操作，此时这些目录应该已经为空。

---

### Script

#### Acts 1: 扩展 `TransactionManager` 以支持删除操作

首先，我们需要赋予事务管理器删除文件和目录的能力。

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


class FileSystemAdapter(Protocol):
    def write_text(self, path: Path, content: str) -> None: ...
    def move(self, src: Path, dest: Path) -> None: ...
    def exists(self, path: Path) -> bool: ...
    def read_text(self, path: Path) -> str: ...


class RealFileSystem:
    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def move(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

    def exists(self, path: Path) -> bool:
        return path.exists()
~~~~~
~~~~~python.new
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union, Protocol, Optional


class FileSystemAdapter(Protocol):
    def write_text(self, path: Path, content: str) -> None: ...
    def move(self, src: Path, dest: Path) -> None: ...
    def exists(self, path: Path) -> bool: ...
    def read_text(self, path: Path) -> str: ...
    def rmtree(self, path: Path) -> None: ...
    def remove(self, path: Path) -> None: ...


class RealFileSystem:
    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def move(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

    def exists(self, path: Path) -> bool:
        return path.exists()

    def rmtree(self, path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)

    def remove(self, path: Path) -> None:
        if path.exists():
            path.unlink()
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/transaction.py
~~~~~
~~~~~python.old
@dataclass
class MoveFileOp(FileOp):
    dest: Path

    def execute(self, fs: FileSystemAdapter, root: Path) -> None:
        fs.move(root / self.path, root / self.dest)

    def describe(self) -> str:
        return f"[MOVE] {self.path} -> {self.dest}"


class TransactionManager:
    def __init__(self, root_path: Path, fs: Optional[FileSystemAdapter] = None):
        self.root_path = root_path
        self.fs = fs or RealFileSystem()
        self._ops: List[FileOp] = []

    def add_write(self, path: Union[str, Path], content: str) -> None:
        self._ops.append(WriteFileOp(Path(path), content))

    def add_move(self, src: Union[str, Path], dest: Union[str, Path]) -> None:
        self._ops.append(MoveFileOp(Path(src), Path(dest)))

    def preview(self) -> List[str]:
        return [op.describe() for op in self._ops]
~~~~~
~~~~~python.new
@dataclass
class MoveFileOp(FileOp):
    dest: Path

    def execute(self, fs: FileSystemAdapter, root: Path) -> None:
        fs.move(root / self.path, root / self.dest)

    def describe(self) -> str:
        return f"[MOVE] {self.path} -> {self.dest}"


@dataclass
class DeleteFileOp(FileOp):
    def execute(self, fs: FileSystemAdapter, root: Path) -> None:
        fs.remove(root / self.path)

    def describe(self) -> str:
        return f"[DELETE] {self.path}"


@dataclass
class DeleteDirectoryOp(FileOp):
    def execute(self, fs: FileSystemAdapter, root: Path) -> None:
        fs.rmtree(root / self.path)

    def describe(self) -> str:
        return f"[DELETE_DIR] {self.path}"


class TransactionManager:
    def __init__(self, root_path: Path, fs: Optional[FileSystemAdapter] = None):
        self.root_path = root_path
        self.fs = fs or RealFileSystem()
        self._ops: List[FileOp] = []

    def add_write(self, path: Union[str, Path], content: str) -> None:
        self._ops.append(WriteFileOp(Path(path), content))

    def add_move(self, src: Union[str, Path], dest: Union[str, Path]) -> None:
        self._ops.append(MoveFileOp(Path(src), Path(dest)))

    def add_delete_file(self, path: Union[str, Path]) -> None:
        self._ops.append(DeleteFileOp(Path(path)))

    def add_delete_dir(self, path: Union[str, Path]) -> None:
        self._ops.append(DeleteDirectoryOp(Path(path)))

    def preview(self) -> List[str]:
        return [op.describe() for op in self._ops]
~~~~~

#### Acts 2: 重写 `MoveDirectoryOperation` 以处理所有文件

现在，我将更新 `move_directory.py` 以实现新的、更健壮的逻辑。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, DeleteDirectoryOp
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
        Analyzes the directory move by planning moves for all contents
        and scheduling the source directory for deletion.
        """
        all_ops: List[FileOp] = []

        # Iterate over all items (files and directories)
        for src_item in self.src_dir.rglob("*"):
            relative_path = src_item.relative_to(self.src_dir)
            dest_item = self.dest_dir / relative_path
            rel_src_item = src_item.relative_to(ctx.graph.root_path)

            if src_item.is_file():
                if src_item.suffix == ".py":
                    # Smart move for Python files
                    file_mover = MoveFileOperation(src_item, dest_item)
                    file_specific_ops = file_mover.analyze(ctx)
                    all_ops.extend(file_specific_ops)
                else:
                    # Simple move for all other files
                    rel_dest_item = dest_item.relative_to(ctx.graph.root_path)
                    all_ops.append(MoveFileOp(rel_src_item, rel_dest_item))

        # After planning all moves, schedule the source directory for deletion
        all_ops.append(
            DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path))
        )

        return all_ops
~~~~~

#### Acts 3: 扩展集成测试以确保完整性

最后，我将重写测试用例，使其包含非 Python 文件和隐藏文件，并验证所有内容是否都按预期迁移，以及源目录是否最终被删除。

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
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation


def test_move_directory_updates_all_contents_and_references(tmp_path):
    # 1. SETUP
    # /
    # ├── mypkg/
    # │   └── core/
    # │       ├── __init__.py
    # │       ├── utils.py      (Python file)
    # │       ├── config.txt    (Non-Python file)
    # │       └── .env          (Hidden file)
    # └── app.py                (Imports from mypkg.core.utils)

    pkg_dir = tmp_path / "mypkg"
    core_dir = pkg_dir / "core"
    core_dir.mkdir(parents=True)

    (core_dir / "__init__.py").touch()
    utils_py = core_dir / "utils.py"
    utils_py.write_text("class Helper: pass", encoding="utf-8")
    (core_dir / "config.txt").write_text("setting=value", encoding="utf-8")
    (core_dir / ".env").write_text("SECRET=123", encoding="utf-8")

    app_py = tmp_path / "app.py"
    app_py.write_text(
        "from mypkg.core.utils import Helper\n\nh = Helper()", encoding="utf-8"
    )

    # Sidecars for utils.py
    utils_yaml = utils_py.with_suffix(".stitcher.yaml")
    utils_yaml.write_text(yaml.dump({"mypkg.core.utils.Helper": "Doc for Helper"}))

    sig_root = tmp_path / ".stitcher/signatures"
    utils_sig_path = sig_root / "mypkg/core/utils.json"
    utils_sig_path.parent.mkdir(parents=True)
    utils_sig_path.write_text(
        json.dumps({"mypkg.core.utils.Helper": {"hash": "123"}})
    )

    # 2. ANALYSIS
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
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. VERIFICATION
    # A. Source directory is gone
    assert not core_dir.exists()

    # B. Destination directory and its contents are correct
    assert services_dir.exists()
    assert (services_dir / "utils.py").exists()
    assert (services_dir / "config.txt").exists()
    assert (services_dir / ".env").exists()
    assert (services_dir / "config.txt").read_text() == "setting=value"
    assert (services_dir / ".env").read_text() == "SECRET=123"

    # C. Sidecars are moved and updated
    assert (services_dir / "utils.stitcher.yaml").exists()
    new_sig_path = sig_root / "mypkg/services/utils.json"
    assert new_sig_path.exists()
    new_yaml_data = yaml.safe_load(
        (services_dir / "utils.stitcher.yaml").read_text()
    )
    assert "mypkg.services.utils.Helper" in new_yaml_data
    new_sig_data = json.loads(new_sig_path.read_text())
    assert "mypkg.services.utils.Helper" in new_sig_data

    # D. Code references are updated
    updated_app_code = app_py.read_text(encoding="utf-8")
    assert "from mypkg.services.utils import Helper" in updated_app_code
~~~~~

### 下一步建议
我们已经根据你的反馈，实现了一个更加健壮和安全的目录移动功能。在执行并验证此计划后，`stitcher-refactor` 的核心移动/重命名功能将非常完善。下一步，我们应该继续推进**阶段四：迁移包系统与 CLI**，为这个强大的引擎提供一个用户友好的接口。
