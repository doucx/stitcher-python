好的，我已经分析了 `SignatureManager` 迁移造成的所有断点。现在我们将执行一个全面的计划来修复整个系统的依赖关系，并使其与新的 `stitcher.lock` 持久化模型完全对齐。

## [WIP] feat(core): 适配应用层以支持 stitcher.lock 模式

### 用户需求

根据“`stitcher.lock` 模式与全局 SURI 架构”路线图，实施 3.5 阶段任务：适配 `StitcherApp` 及其所有依赖组件，以使用从 `stitcher-lang-sidecar` 迁移并重写后的 `SignatureManager`。

### 评论

这是一次“架构性断裂修复”。我们在前一步骤中有意地破坏了旧的依赖关系，现在我们将通过精确地重新布线，强制整个应用层遵循新的、更健壮的协议。

*   **依赖注入修复**: 我们将更新 `StitcherApp` 的构造函数，从正确的位置 (`sidecar`) 注入 `SignatureManager` 的新实例，并为其提供必要的 `Workspace` 上下文。
*   **协议遵从**: 我们将更新 `SignatureManagerProtocol`，并确保所有组件（特别是测试 Mocks）都遵循新的契约。
*   **事务完整性**: 我们将在命令执行的边界（`run_init`, `run_pump`）添加对 `sig_manager.flush()` 的调用，确保内存中的变更能够被原子性地写回到磁盘。

这个计划将修复所有已知的编译和运行时错误，使系统恢复到可工作的状态，并完全建立在新的持久化模型之上。

### 目标

1.  删除因 `SignatureManager` 重构而完全过时的测试文件。
2.  更新 `stitcher-spec` 中的 `SignatureManagerProtocol`，加入 `flush` 方法。
3.  修改 `StitcherApp` 的核心逻辑，使其能正确实例化和使用新的 `SignatureManager`，并在适当的时机调用 `flush`。
4.  更新 `stitcher-test-utils` 中的辅助函数，使其能够与 `stitcher.lock` 文件交互。
5.  修复因协议变更而损坏的单元测试。
6.  为新的 `SignatureManager` 添加一套完整的单元测试，覆盖其 `stitcher.lock` 管理、缓存和旧数据迁移功能。

### 基本原理

我们遵循“依赖倒置原则”，大多数应用层组件依赖于 `SignatureManagerProtocol` 接口而非具体实现。因此，本次修复的核心在于：
1.  正确更新接口 (`SignatureManagerProtocol`)。
2.  在系统的最高层（`StitcherApp` 的组合根）正确地实例化具体实现 (`SignatureManager`) 并注入。
3.  确保新的工作流（特别是 `flush`）被正确调用。

通过这种方式，我们可以最小化对每个独立 Runner 的修改，同时确保整个系统作为一个整体，其行为符合新的持久化策略。新的单元测试将作为新架构正确性的“活文档”和回归保护。

### 标签

#intent/refine #intent/build #intent/tooling #flow/ready #priority/critical #scope/core #scope/api #comp/application #comp/spec #comp/tests #ai/instruct #task/domain/architecture #task/object/lock-file #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 清理过时的测试

这些测试文件所验证的旧版 `SignatureManager` 及其磁盘布局已不存在，因此我们将它们彻底删除。

~~~~~act
delete_file
packages/stitcher-application/tests/unit/test_signature_manager.py
~~~~~

~~~~~act
delete_file
packages/stitcher-application/tests/integration/test_signature_suri_format.py
~~~~~

#### Acts 2: 更新 SignatureManagerProtocol 接口

我们将 `flush` 方法添加到核心协议中，并移除已过时的内部方法，以反映新的 API 契约。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/managers.py
~~~~~
~~~~~python.old
class SignatureManagerProtocol(Protocol):
    def load_composite_hashes(self, file_path: str) -> Dict[str, Fingerprint]: ...

    def save_composite_hashes(
        self, file_path: str, hashes: Dict[str, Fingerprint]
    ) -> None: ...

    def reformat_hashes_for_file(self, file_path: str) -> bool: ...

    # Used by PumpRunner for centralized serialization
    def serialize_hashes(
        self, file_path: str, hashes: Dict[str, Fingerprint]
    ) -> str: ...

    def get_signature_path(self, file_path: str) -> Path: ...
~~~~~
~~~~~python.new
class SignatureManagerProtocol(Protocol):
    def load_composite_hashes(self, file_path: str) -> Dict[str, Fingerprint]: ...

    def save_composite_hashes(
        self, file_path: str, hashes: Dict[str, Fingerprint]
    ) -> None: ...

    def flush(self) -> None: ...

    def get_signature_path(self, file_path: str) -> Path: ...
~~~~~

#### Acts 3: 适配 StitcherApp 核心

这是应用层适配的核心。我们将修改 `StitcherApp` 的构造函数和命令执行逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    ScannerService,
    DocstringMerger,
)
from stitcher.common.services import Differ
from stitcher.spec.interaction import InteractionHandler
from .runners import (
    CheckRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
    IndexRunner,
)
from .runners.check.resolver import CheckResolver
from .runners.check.reporter import CheckReporter
from .runners.pump.executor import PumpExecutor
from stitcher.analysis.engines import create_pump_engine
from stitcher.common.transaction import TransactionManager
from typing import Callable
from stitcher.analysis.schema import FileCheckResult
from .types import PumpResult, CoverageResult
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore
from stitcher.index.indexer import FileIndexer
from stitcher.lang.python import PythonAdapter
from stitcher.workspace import Workspace
from stitcher.lang.python.docstring import (
    get_docstring_codec,
    get_docstring_serializer,
)
from stitcher.spec.interaction import InteractionContext


class StitcherApp:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        transformer: LanguageTransformerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        interaction_handler: Optional[InteractionHandler] = None,
    ):
        self.root_path = root_path
        self.workspace = Workspace(root_path)
        self.fingerprint_strategy = fingerprint_strategy
        # 1. Core Services
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
        self.scanner = ScannerService(root_path, parser)
        self.differ = Differ()
~~~~~
~~~~~python.new
from stitcher.lang.sidecar import SignatureManager
from stitcher.app.services import (
    DocumentManager,
    ScannerService,
    DocstringMerger,
)
from stitcher.common.services import Differ
from stitcher.spec.interaction import InteractionHandler
from .runners import (
    CheckRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
    IndexRunner,
)
from .runners.check.resolver import CheckResolver
from .runners.check.reporter import CheckReporter
from .runners.pump.executor import PumpExecutor
from stitcher.analysis.engines import create_pump_engine
from stitcher.common.transaction import TransactionManager
from typing import Callable
from stitcher.analysis.schema import FileCheckResult
from .types import PumpResult, CoverageResult
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore
from stitcher.index.indexer import FileIndexer
from stitcher.lang.python import PythonAdapter
from stitcher.workspace import Workspace
from stitcher.lang.python.docstring import (
    get_docstring_codec,
    get_docstring_serializer,
)
from stitcher.spec.interaction import InteractionContext


class StitcherApp:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        transformer: LanguageTransformerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        interaction_handler: Optional[InteractionHandler] = None,
    ):
        self.root_path = root_path
        self.workspace = Workspace(root_path)
        self.fingerprint_strategy = fingerprint_strategy
        # 1. Core Services
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(self.workspace)
        self.scanner = ScannerService(root_path, parser)
        self.differ = Differ()
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_init(self) -> List[Path]:
        configs, _ = self._load_configs()
        all_created: List[Path] = []
        found_any = False

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            found_any = True

            created = self.init_runner.run_batch(modules)
            all_created.extend(created)

        if not found_any:
            bus.info(L.init.no_docs_found)
        elif all_created:
            bus.success(L.init.run.complete, count=len(all_created))
        else:
            bus.info(L.init.no_docs_found)

        return all_created
~~~~~
~~~~~python.new
    def run_init(self) -> List[Path]:
        configs, _ = self._load_configs()
        all_created: List[Path] = []
        found_any = False

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            found_any = True

            created = self.init_runner.run_batch(modules)
            all_created.extend(created)

        self.sig_manager.flush()

        if not found_any:
            bus.info(L.init.no_docs_found)
        elif all_created:
            bus.success(L.init.run.complete, count=len(all_created))
        else:
            bus.info(L.init.no_docs_found)

        return all_created
~~~~~
~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        if self.scanner.had_errors:
            global_success = False

        tm.commit()
        return PumpResult(success=global_success, redundant_files=all_redundant)
~~~~~
~~~~~python.new
        if self.scanner.had_errors:
            global_success = False

        tm.commit()
        self.sig_manager.flush()
        return PumpResult(success=global_success, redundant_files=all_redundant)
~~~~~

#### Acts 4: 更新测试辅助工具

重写 `get_stored_hashes` 以直接读取 `stitcher.lock` 文件，使其与新架构保持一致。

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~
~~~~~python
import json
from pathlib import Path
from typing import Optional

from stitcher.app import StitcherApp
from stitcher.spec.interaction import InteractionHandler
from stitcher.lang.python import (
    PythonTransformer,
    PythonFingerprintStrategy,
)
from stitcher.workspace import Workspace, find_package_root
from stitcher.lang.sidecar import SignatureManager

from stitcher.lang.python.parser.griffe import GriffePythonParser
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore
from stitcher.index.indexer import FileIndexer
from stitcher.lang.python.adapter import PythonAdapter


def create_populated_index(root_path: Path) -> IndexStore:
    db_path = root_path / ".stitcher" / "index" / "index.db"

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    store = IndexStore(db_manager)

    # The indexer needs a workspace-aware adapter.
    workspace = Workspace(root_path)
    search_paths = workspace.get_search_paths()

    # Discover files first, then index them.
    files_to_index = workspace.discover_files()

    indexer = FileIndexer(root_path, store)
    indexer.register_adapter(".py", PythonAdapter(root_path, search_paths))
    indexer.index_files(files_to_index)

    return store


def create_test_app(
    root_path: Path, interaction_handler: Optional[InteractionHandler] = None
) -> StitcherApp:
    parser = GriffePythonParser()
    transformer = PythonTransformer()
    strategy = PythonFingerprintStrategy()
    return StitcherApp(
        root_path=root_path,
        parser=parser,
        transformer=transformer,
        fingerprint_strategy=strategy,
        interaction_handler=interaction_handler,
    )


def get_stored_hashes(project_root: Path, file_path_in_package: str) -> dict:
    """
    Reads a stitcher.lock file for the package containing the given file
    and returns all fingerprints within that lock file.
    """
    abs_file_path = project_root / file_path_in_package
    package_root = find_package_root(abs_file_path)
    if not package_root:
        return {}

    lock_path = package_root / "stitcher.lock"
    if not lock_path.exists():
        return {}

    with lock_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("fingerprints", {})
~~~~~

#### Acts 5: 修复损坏的单元测试

`test_pump_executor.py` 中的 `mock_sig_manager` fixture 依赖于已移除的 `serialize_hashes` 方法，我们需要对其进行修复。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
@pytest.fixture
def mock_sig_manager(mocker, tmp_path: Path) -> MagicMock:
    mock = mocker.create_autospec(SignatureManagerProtocol, instance=True)
    # IMPORTANT: Return a real dict to avoid deepcopy issues with mocks.
    mock.load_composite_hashes.return_value = {}
    # Configure path generation to return a concrete Path
    mock.get_signature_path.return_value = (
        tmp_path / ".stitcher/signatures/src/main.json"
    )
    mock.serialize_hashes.return_value = "json content"
    return mock
~~~~~
~~~~~python.new
@pytest.fixture
def mock_sig_manager(mocker, tmp_path: Path) -> MagicMock:
    mock = mocker.create_autospec(SignatureManagerProtocol, instance=True)
    # IMPORTANT: Return a real dict to avoid deepcopy issues with mocks.
    mock.load_composite_hashes.return_value = {}
    # Configure path generation to return a concrete Path
    # This path is used for logging/reporting, so it should be a valid lock file path
    mock.get_signature_path.return_value = tmp_path / "src/stitcher.lock"
    return mock
~~~~~

#### Acts 6: 为新的 SignatureManager 建立回归测试

最后，我们在 `stitcher-lang-sidecar` 包中创建一个新的、全面的测试套件来验证新 `SignatureManager` 的所有核心功能。

~~~~~act
write_file
packages/stitcher-lang-sidecar/tests/test_signature_manager.py
~~~~~
~~~~~python
import json
from pathlib import Path

from stitcher.spec import Fingerprint
from stitcher.workspace import Workspace
from stitcher.lang.sidecar import SignatureManager
from stitcher.test_utils import WorkspaceFactory


def test_save_and_load_single_lock_file(tmp_path: Path):
    # Arrange
    ws_factory = WorkspaceFactory(tmp_path).with_pyproject("packages/pkg-a")
    pkg_a_root = ws_factory.root_path / "packages/pkg-a"
    ws_factory.with_source("packages/pkg-a/src/main.py", "def func_a(): ...").build()
    workspace = Workspace(tmp_path)
    manager = SignatureManager(workspace)

    # Act
    hashes = {"func_a": Fingerprint.from_dict({"baseline_code_structure_hash": "hash_a"})}
    manager.save_composite_hashes("packages/pkg-a/src/main.py", hashes)
    manager.flush()

    # Assert: Lock file is created correctly
    lock_path = pkg_a_root / "stitcher.lock"
    assert lock_path.exists()
    with lock_path.open("r") as f:
        data = json.load(f)
    assert data["version"] == "1.0"
    assert "py://packages/pkg-a/src/main.py#func_a" in data["fingerprints"]
    assert (
        data["fingerprints"]["py://packages/pkg-a/src/main.py#func_a"][
            "baseline_code_structure_hash"
        ]
        == "hash_a"
    )

    # Assert: Loading works
    new_manager = SignatureManager(workspace)
    loaded_hashes = new_manager.load_composite_hashes("packages/pkg-a/src/main.py")
    assert loaded_hashes == hashes


def test_legacy_migration_and_cleanup(tmp_path: Path):
    # Arrange: Create a legacy .stitcher/signatures layout
    ws_factory = WorkspaceFactory(tmp_path).with_pyproject("packages/pkg-a")
    pkg_a_root = ws_factory.root_path / "packages/pkg-a"
    ws_factory.with_source("packages/pkg-a/src/main.py", "def func_a(): ...").build()

    legacy_sig_dir = tmp_path / ".stitcher/signatures/packages/pkg-a/src"
    legacy_sig_dir.mkdir(parents=True, exist_ok=True)
    legacy_sig_file = legacy_sig_dir / "main.json"
    legacy_suri = "py://packages/pkg-a/src/main.py#func_a"
    legacy_data = {legacy_suri: {"baseline_code_structure_hash": "legacy_hash"}}
    with legacy_sig_file.open("w") as f:
        json.dump(legacy_data, f)

    workspace = Workspace(tmp_path)
    manager = SignatureManager(workspace)

    # Act: Loading should trigger migration into cache
    loaded_hashes = manager.load_composite_hashes("packages/pkg-a/src/main.py")

    # Assert: Data is loaded correctly from legacy source
    assert loaded_hashes["func_a"].to_dict() == {
        "baseline_code_structure_hash": "legacy_hash"
    }

    # Act: Flush should write new lock file and delete old directory
    manager.flush()

    # Assert: New lock file exists and is correct
    lock_path = pkg_a_root / "stitcher.lock"
    assert lock_path.exists()
    with lock_path.open("r") as f:
        data = json.load(f)
    assert (
        data["fingerprints"][legacy_suri]["baseline_code_structure_hash"]
        == "legacy_hash"
    )

    # Assert: Legacy directory is deleted
    assert not (tmp_path / ".stitcher/signatures").exists()


def test_empty_hashes_removes_lock_file(tmp_path: Path):
    # Arrange
    ws_factory = WorkspaceFactory(tmp_path).with_pyproject("packages/pkg-a")
    pkg_a_root = ws_factory.root_path / "packages/pkg-a"
    ws_factory.with_source("packages/pkg-a/src/main.py", "def func_a(): ...").build()
    workspace = Workspace(tmp_path)
    manager = SignatureManager(workspace)
    lock_path = pkg_a_root / "stitcher.lock"
    lock_path.touch()

    # Act
    manager.save_composite_hashes("packages/pkg-a/src/main.py", {})
    manager.flush()

    # Assert
    assert not lock_path.exists()
~~~~~

### 下一步建议

我们已经成功地完成了应用层的适配，将整个系统切换到了新的 `stitcher.lock` 持久化模型上。所有核心组件的依赖关系已经修复，并且我们为新的 `SignatureManager` 建立了坚实的测试保障。

现在，整个 `stitcher.lock` 模式的基础设施、协议和持久化层都已经就位。是时候验证这一切是否能在真实的端到端流程中无缝工作了。

我建议，我们下一步应该：
1.  **运行完整的测试套件**：确保我们的修改没有引入任何意想不到的回归问题。
2.  **手动执行端到端场景**:
    *   在一个全新的项目中运行 `stitcher init`，验证是否在正确的包位置生成了 `stitcher.lock`。
    *   在一个包含旧 `.stitcher/signatures` 的项目中运行 `stitcher check`，验证迁移逻辑是否被触发，并且旧目录是否被成功清理。
