好的，我们开始执行 **任务 1.3**。

我将生成一个计划，该计划旨在构建 `stitcher-index` 的核心——`WorkspaceScanner` 服务。这个服务将严格按照路线图中的四阶段增量扫描流水线进行设计，以实现极致的性能和准确性。我们将采用 TDD（测试驱动开发）方法，首先定义测试框架和核心接口，然后实现扫描器逻辑。

## [WIP] feat: 实现 WorkspaceScanner 和增量扫描流水线

### 用户需求

根据 `Stitcher 2.0 实施路线图`，开始执行任务 1.3：实现一个完整的四阶段增量扫描流水线，并将其封装在 `WorkspaceScanner` 服务中。

### 评论

这是 `stitcher-index` 包的“心脏”。实现一个高效且正确的增量扫描器是整个 Stitcher 2.0 架构的基石。一个设计良好的扫描器可以确保索引更新的成本与变更集的大小成正比，而不是与整个项目的大小成正比，从而为上层应用提供近乎瞬时的查询能力。

### 目标

1.  在 `stitcher.index` 包中创建 `scanner.py`，用于实现 `WorkspaceScanner`。
2.  定义 `LanguageAdapterProtocol` 接口，作为扫描器与语言解析器之间的契约。
3.  在 `scanner.py` 中实现 `WorkspaceScanner` 类，包含一个 `scan()` 方法来驱动整个流水线：
    *   **阶段 1 (Discovery):** 实现基于 `git ls-files`（优先）和文件系统遍历（回退）的文件发现逻辑。
    *   **阶段 2 (Stat Check):** 实现基于文件 `mtime` 和 `size` 的快速过滤逻辑。
    *   **阶段 3 (Hash Check):** 实现基于文件内容 SHA256 哈希的确定性变更检测。
    *   **阶段 4 (Parsing):** 对确认已变更的文件调用 `LanguageAdapter` 进行解析，并将结果存入 `IndexStore`。
4.  扩展 `IndexStore` 以支持文件删除的修剪（pruning）操作。
5.  创建对应的单元测试文件 `tests/unit/test_scanner.py`，并编写测试用例来验证流水线的每个阶段，包括新增、修改、元数据变更和删除文件的场景。

### 基本原理

我们将构建一个“过滤漏斗”式的流水线。每一阶段都使用比后一阶段成本更低的检查方式来过滤掉绝大部分未变更的文件。

1.  **文件发现** 是第一步，它定义了当前工作区的“期望状态”。
2.  **Stat Check** 是最低成本的检查，它利用文件系统的元数据，可以瞬间过滤掉 99% 的未修改文件。
3.  **Hash Check** 成本稍高，因为它需要读取文件内容，但它能精确地识别出内容是否真的发生了变化，从而避免了因 `touch` 等操作导致的元数据变更而触发不必要的重新解析。
4.  **Parsing** 是成本最高的操作，我们将确保只有极少数真正被修改的文件会进入这一阶段。

同时，通过将工作区文件列表与数据库记录进行对比，我们可以高效地识别出被删除的文件，并从索引中修剪它们，保持索引与文件系统的同步。

### 标签

#intent/build #flow/ready #priority/high #comp/index #concept/state #scope/core #ai/instruct #task/domain/indexing #task/object/scanner #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建核心文件和协议定义

我们将首先创建 `WorkspaceScanner` 的实现文件、测试文件以及它所依赖的语言适配器协议。

~~~~~act
write_file
packages/stitcher-index/src/stitcher/index/scanner.py
~~~~~
~~~~~python
import subprocess
import hashlib
from pathlib import Path
from typing import List, Protocol, Tuple, Set

from .store import IndexStore
from .types import SymbolRecord, ReferenceRecord


class LanguageAdapterProtocol(Protocol):
    """Protocol for language-specific parsers."""

    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]: ...


class WorkspaceScanner:
    """Orchestrates the four-stage incremental scan of the workspace."""

    def __init__(
        self,
        root_path: Path,
        store: IndexStore,
        language_adapter: LanguageAdapterProtocol,
    ):
        self.root_path = root_path
        self.store = store
        self.adapter = language_adapter

    def _discover_files(self) -> Set[Path]:
        """Stage 1: Discover all relevant files in the workspace."""
        # Git-based discovery (preferred)
        try:
            result = subprocess.run(
                [
                    "git",
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ],
                cwd=self.root_path,
                check=True,
                capture_output=True,
                text=True,
            )
            files = {self.root_path / p for p in result.stdout.strip().splitlines()}
            return files
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to filesystem scan
            # This is a basic fallback; a real implementation would respect .gitignore
            return set(self.root_path.rglob("*.*"))

    def scan(self) -> None:
        """Runs the complete incremental scanning pipeline."""
        # Stage 1: Discovery
        workspace_paths = self._discover_files()
        workspace_rel_paths = {
            str(p.relative_to(self.root_path)) for p in workspace_paths
        }

        # Handle deletions
        stored_paths = self.store.get_all_file_paths()
        deleted_paths = stored_paths - workspace_rel_paths
        if deleted_paths:
            self.store.prune_files(deleted_paths)

        confirmed_dirty_files: List[Tuple[Path, str, float, int]] = []

        for file_path in workspace_paths:
            rel_path_str = str(file_path.relative_to(self.root_path))
            stat = file_path.stat()
            mtime, size = stat.st_mtime, stat.st_size

            # Stage 2: Stat Check
            file_rec = self.store.get_file_by_path(rel_path_str)
            if (
                file_rec
                and file_rec.last_mtime == mtime
                and file_rec.last_size == size
            ):
                continue

            # Stage 3: Hash Check
            content_bytes = file_path.read_bytes()
            content_hash = hashlib.sha256(content_bytes).hexdigest()

            if file_rec and file_rec.content_hash == content_hash:
                # Content is identical, just update stat to avoid re-hashing next time
                self.store.sync_file(rel_path_str, content_hash, mtime, size)
                continue

            confirmed_dirty_files.append((file_path, content_hash, mtime, size))

        # Stage 4: Parsing
        for file_path, content_hash, mtime, size in confirmed_dirty_files:
            rel_path_str = str(file_path.relative_to(self.root_path))
            file_id, _ = self.store.sync_file(rel_path_str, content_hash, mtime, size)

            content_str = file_path.read_text("utf-8")
            symbols, references = self.adapter.parse(file_path, content_str)
            self.store.update_analysis(file_id, symbols, references)
~~~~~
~~~~~act
write_file
packages/stitcher-index/tests/unit/test_scanner.py
~~~~~
~~~~~python
from unittest.mock import MagicMock
import pytest
from stitcher.index.scanner import WorkspaceScanner, LanguageAdapterProtocol
from stitcher.index.types import SymbolRecord, ReferenceRecord


@pytest.fixture
def mock_adapter():
    mock = MagicMock(spec=LanguageAdapterProtocol)
    mock.parse.return_value = (
        [SymbolRecord(id="s1", name="s1", kind="k", location_start=0, location_end=1)],
        [ReferenceRecord(target_id="t1", kind="k", location_start=0, location_end=1)],
    )
    return mock


@pytest.fixture
def scanner(tmp_path, store, mock_adapter):
    # Setup a git repo for reliable file discovery
    (tmp_path / ".git").mkdir()
    return WorkspaceScanner(tmp_path, store, mock_adapter)


def test_initial_scan(scanner, tmp_path, mock_adapter, store):
    """All files are new and should be parsed."""
    (tmp_path / "main.py").write_text("...")
    (tmp_path / "lib.py").write_text("...")

    scanner.scan()

    assert mock_adapter.parse.call_count == 2
    assert store.get_file_by_path("main.py") is not None
    assert store.get_file_by_path("lib.py") is not None
    file_rec = store.get_file_by_path("main.py")
    assert len(store.get_symbols_by_file(file_rec.id)) == 1


def test_no_change_scan(scanner, tmp_path, mock_adapter):
    """On a second scan with no changes, nothing should be parsed."""
    (tmp_path / "main.py").write_text("...")
    scanner.scan()  # First scan

    mock_adapter.reset_mock()
    scanner.scan()  # Second scan

    mock_adapter.parse.assert_not_called()


def test_content_change_scan(scanner, tmp_path, mock_adapter):
    """Only the file with content change should be parsed."""
    (tmp_path / "main.py").write_text("a")
    (tmp_path / "lib.py").write_text("b")
    scanner.scan()

    mock_adapter.reset_mock()
    (tmp_path / "main.py").write_text("c")  # Change content

    scanner.scan()

    mock_adapter.parse.assert_called_once()
    call_args = mock_adapter.parse.call_args[0]
    assert call_args[0].name == "main.py"


def test_metadata_change_no_reparse(scanner, tmp_path, mock_adapter):
    """A file with only mtime change but same hash should not be re-parsed."""
    file = tmp_path / "main.py"
    file.write_text("a")
    scanner.scan()

    mock_adapter.reset_mock()
    # Simulate just touching the file
    file.touch()

    scanner.scan()
    mock_adapter.parse.assert_not_called()


def test_deleted_file_is_pruned(scanner, tmp_path, mock_adapter, store):
    """A deleted file should be removed from the index."""
    (tmp_path / "main.py").write_text("a")
    (tmp_path / "lib.py").write_text("b")
    scanner.scan()

    assert store.get_file_by_path("lib.py") is not None

    (tmp_path / "lib.py").unlink()
    scanner.scan()

    assert store.get_file_by_path("lib.py") is None
    assert store.get_file_by_path("main.py") is not None
~~~~~

#### Acts 2: 扩展 `IndexStore`

现在，我们将为 `IndexStore` 添加 `get_all_file_paths` 和 `prune_files` 方法，以支持文件删除的检测和处理。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
    def get_references_by_file(self, file_id: int) -> List[ReferenceRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM 'references' WHERE source_file_id = ?", (file_id,)
            ).fetchall()
            return [ReferenceRecord(**dict(row)) for row in rows]
~~~~~
~~~~~python.new
    def get_references_by_file(self, file_id: int) -> List[ReferenceRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM 'references' WHERE source_file_id = ?", (file_id,)
            ).fetchall()
            return [ReferenceRecord(**dict(row)) for row in rows]

    def get_all_file_paths(self) -> Set[str]:
        """Returns the set of all relative paths known to the index."""
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT path FROM files").fetchall()
            return {row["path"] for row in rows}

    def prune_files(self, paths_to_delete: Set[str]) -> None:
        """Deletes files and their associated data from the index."""
        with self.db.get_connection() as conn:
            # We can delete in batches for very large sets of deleted files
            # but for now a single transaction is fine.
            # Foreign key ON DELETE CASCADE will handle symbols and references.
            placeholders = ",".join("?" for _ in paths_to_delete)
            conn.execute(
                f"DELETE FROM files WHERE path IN ({placeholders})",
                tuple(paths_to_delete),
            )
~~~~~

### 下一步建议

我们已经为增量扫描器奠定了坚实的基础。下一步是：

1.  **实现 `PythonAdapter` (任务 1.4)**: 创建 `stitcher-python-adapter` 对 `LanguageAdapterProtocol` 的具体实现，使其能够利用现有的 `GriffePythonParser` 将 Python代码转换为 `SymbolRecord` 和 `ReferenceRecord`。
2.  **创建 CLI 命令 (任务 1.5)**: 在 `stitcher-cli` 中添加 `stitcher index:build` 命令，该命令将实例化 `DatabaseManager`, `IndexStore`, `PythonAdapter` 和 `WorkspaceScanner`，并调用 `scanner.scan()` 来真正地构建和更新索引。这将作为整个阶段 1 的最终验收标准。
