好的，收到了 `pyright` 的错误报告。这是一个预料之中的情况，因为我们在上一阶段进行了大规模的“切除”手术，但尚未修复所有引用了被切除器官（`SignatureManagerProtocol`）的测试和代码。现在是时候进行全面的“缝合”和“康复”了。

## [WIP] fix: 修复因切换至 LockManager 引发的类型错误和测试失败

### 错误分析
`pyright` 的错误报告主要分为三类：
1.  **协议不匹配**: 我在 `PumpExecutor` 中调用了 `lock_manager.serialize()` 和 `lock_manager.LOCK_FILE_NAME`，但这些并未在 `LockManagerProtocol` 中定义，导致类型错误。
2.  **导入失败**: 我删除了 `SignatureManager` 并计划删除其协议，但大量测试文件和 `stitcher-spec` 的 `__init__.py` 仍然在导入 `SignatureManagerProtocol`，导致 `ImportError`。
3.  **构造函数签名变更**: 我更新了 `CheckRunner`, `PumpRunner`, `PumpExecutor` 等核心类的 `__init__` 方法，加入了 `lock_manager`, `uri_generator`, `workspace` 等新依赖，但所有相关的测试用例仍在以旧的方式实例化它们，导致 `TypeError` (参数不匹配)。

此外，有两个测试文件 (`test_signature_suri_format.py`, `test_signature_manager.py`) 是专门为已删除的 `SignatureManager` 编写的，它们现在已经完全过时，应该被删除。

### 用户需求
根据 `pyright` 的错误报告，系统性地修复所有类型错误、导入错误和测试用例，使项目恢复到类型安全且测试可通过的状态。

### 评论
这是一个“重构后清理”的关键步骤。我们将遵循以下策略：
1.  **完善协议**: 将必要的 `serialize` 方法添加到 `LockManagerProtocol`。
2.  **删除过时资产**: 彻底删除 `SignatureManagerProtocol` 及其相关的测试文件。
3.  **全面适配测试**: 逐一修复所有受影响的测试用例，将旧的 `SignatureManagerProtocol` mock 替换为新的 `LockManagerProtocol`, `URIGeneratorProtocol`, 和 `Workspace` mock，并更新构造函数调用。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #comp/interfaces #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/suri-lockfile #task/action/test-suite-migration #task/state/continue

---

### Script

#### Acts 1: 完善协议并清理过时定义 (`stitcher-spec`)

首先，我们修复 `LockManagerProtocol` 并彻底移除 `SignatureManagerProtocol`。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python.old
class LockManagerProtocol(Protocol):
    """
    Protocol for managing the stitcher.lock file, which serves as the distributed
    persistence layer for fingerprints.
    """

    def load(self, package_root: Path) -> Dict[str, Fingerprint]: ...

    def save(self, package_root: Path, data: Dict[str, Fingerprint]) -> None: ...
~~~~~
~~~~~python.new
class LockManagerProtocol(Protocol):
    """
    Protocol for managing the stitcher.lock file, which serves as the distributed
    persistence layer for fingerprints.
    """

    def load(self, package_root: Path) -> Dict[str, Fingerprint]: ...

    def save(self, package_root: Path, data: Dict[str, Fingerprint]) -> None: ...

    def serialize(self, data: Dict[str, Fingerprint]) -> str: ...
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/managers.py
~~~~~
~~~~~python.old
from typing import Protocol, Dict, Union, Optional, Any
from pathlib import Path

from .docstring import DocstringIR
from .fingerprint import Fingerprint
from .models import ModuleDef


class DocumentManagerProtocol(Protocol):
    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def load_docs_for_path(self, file_path: str) -> Dict[str, DocstringIR]: ...

    def save_docs_for_module(self, module: ModuleDef) -> Path: ...

    def flatten_module_docs(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]: ...

    def compute_yaml_content_hash(self, content: Union[str, Dict[str, Any]]) -> str: ...

    def hydrate_module(
        self,
        module: ModuleDef,
        force: bool = False,
        reconcile: bool = False,
        resolution_map: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        source_docs_override: Optional[Dict[str, DocstringIR]] = None,
    ) -> Dict[str, Any]: ...

    def reformat_docs_for_module(self, module: ModuleDef) -> bool: ...

    def serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...

    def compute_ir_hash(self, ir: DocstringIR) -> str: ...

    def dump_data(self, data: Dict[str, Any]) -> str: ...

    def load_raw_data(self, file_path: str) -> Dict[str, Any]: ...

    def dump_raw_data_to_string(self, data: Dict[str, Any]) -> str: ...
~~~~~
~~~~~python.new
from typing import Protocol, Dict, Union, Optional, Any
from pathlib import Path

from .docstring import DocstringIR
from .fingerprint import Fingerprint
from .models import ModuleDef


class DocumentManagerProtocol(Protocol):
    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def load_docs_for_path(self, file_path: str) -> Dict[str, DocstringIR]: ...

    def save_docs_for_module(self, module: ModuleDef) -> Path: ...

    def flatten_module_docs(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]: ...

    def compute_yaml_content_hash(self, content: Union[str, Dict[str, Any]]) -> str: ...

    def hydrate_module(
        self,
        module: ModuleDef,
        force: bool = False,
        reconcile: bool = False,
        resolution_map: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        source_docs_override: Optional[Dict[str, DocstringIR]] = None,
    ) -> Dict[str, Any]: ...

    def reformat_docs_for_module(self, module: ModuleDef) -> bool: ...

    def serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...

    def compute_ir_hash(self, ir: DocstringIR) -> str: ...

    def dump_data(self, data: Dict[str, Any]) -> str: ...

    def load_raw_data(self, file_path: str) -> Dict[str, Any]: ...

    def dump_raw_data_to_string(self, data: Dict[str, Any]) -> str: ...
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
    "URIGeneratorProtocol",
    "LockManagerProtocol",
    "DocumentManagerProtocol",
    "SignatureManagerProtocol",
    "DifferProtocol",
    "DocstringMergerProtocol",
~~~~~
~~~~~python.new
    "URIGeneratorProtocol",
    "LockManagerProtocol",
    "DocumentManagerProtocol",
    "DifferProtocol",
    "DocstringMergerProtocol",
~~~~~

#### Acts 2: 修复 `PumpExecutor` 的协议访问问题

将硬编码的 `LOCK_FILE_NAME` 移入 `PumpExecutor`，因为它是一个实现细节。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
~~~~~
~~~~~python.old
                lock_content = self.lock_manager.serialize(new_lock_data)
                lock_path = pkg_root / self.lock_manager.LOCK_FILE_NAME
                tm.add_write(str(lock_path.relative_to(self.root_path)), lock_content)
~~~~~
~~~~~python.new
                lock_content = self.lock_manager.serialize(new_lock_data)
                lock_path = pkg_root / "stitcher.lock"
                tm.add_write(str(lock_path.relative_to(self.root_path)), lock_content)
~~~~~

#### Acts 3: 删除过时的测试文件

这两个文件已无用，直接删除。

~~~~~act
delete_file
packages/stitcher-application/tests/integration/test_signature_suri_format.py
~~~~~

~~~~~act
delete_file
packages/stitcher-application/tests/unit/test_signature_manager.py
~~~~~

#### Acts 4: 修复 `CheckRunner` 的测试

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
from stitcher.app.runners.check.runner import CheckRunner
from stitcher.app.runners.check.resolver import CheckResolver
from stitcher.app.runners.check.reporter import CheckReporter
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec import (
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    ModuleDef,
    DifferProtocol,
)
~~~~~
~~~~~python.new
from stitcher.app.runners.check.runner import CheckRunner
from stitcher.app.runners.check.resolver import CheckResolver
from stitcher.app.runners.check.reporter import CheckReporter
from stitcher.spec.managers import DocumentManagerProtocol
from stitcher.spec import (
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    ModuleDef,
    DifferProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
from stitcher.workspace import Workspace
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
def test_check_runner_orchestrates_analysis_and_resolution(mocker):
    """
    验证 CheckRunner 正确地按顺序调用其依赖项：
    1. Engine (通过 analyze_batch)
    2. Resolver (auto_reconcile, 然后 resolve_conflicts)
    3. Reporter
    """
    # 1. Arrange: 为所有依赖项创建 mock
    mock_doc_manager = mocker.create_autospec(DocumentManagerProtocol, instance=True)
    mock_sig_manager = mocker.create_autospec(SignatureManagerProtocol, instance=True)
    mock_fingerprint_strategy = mocker.create_autospec(
        FingerprintStrategyProtocol, instance=True
    )
    mock_index_store = mocker.create_autospec(IndexStoreProtocol, instance=True)
    mock_differ = mocker.create_autospec(DifferProtocol, instance=True)
    mock_resolver = mocker.create_autospec(CheckResolver, instance=True)
    mock_reporter = mocker.create_autospec(CheckReporter, instance=True)
~~~~~
~~~~~python.new
def test_check_runner_orchestrates_analysis_and_resolution(mocker):
    """
    验证 CheckRunner 正确地按顺序调用其依赖项：
    1. Engine (通过 analyze_batch)
    2. Resolver (auto_reconcile, 然后 resolve_conflicts)
    3. Reporter
    """
    # 1. Arrange: 为所有依赖项创建 mock
    mock_doc_manager = mocker.create_autospec(DocumentManagerProtocol, instance=True)
    mock_lock_manager = mocker.create_autospec(LockManagerProtocol, instance=True)
    mock_uri_generator = mocker.create_autospec(URIGeneratorProtocol, instance=True)
    mock_workspace = mocker.create_autospec(Workspace, instance=True)
    mock_fingerprint_strategy = mocker.create_autospec(
        FingerprintStrategyProtocol, instance=True
    )
    mock_index_store = mocker.create_autospec(IndexStoreProtocol, instance=True)
    mock_differ = mocker.create_autospec(DifferProtocol, instance=True)
    mock_resolver = mocker.create_autospec(CheckResolver, instance=True)
    mock_reporter = mocker.create_autospec(CheckReporter, instance=True)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
    # 2. Act: 实例化 runner 并注入 mock engine
    runner = CheckRunner(
        doc_manager=mock_doc_manager,
        sig_manager=mock_sig_manager,
        fingerprint_strategy=mock_fingerprint_strategy,
        index_store=mock_index_store,
        differ=mock_differ,
        resolver=mock_resolver,
        reporter=mock_reporter,
        root_path=Path("/tmp"),
    )
~~~~~
~~~~~python.new
    # 2. Act: 实例化 runner 并注入 mock engine
    runner = CheckRunner(
        doc_manager=mock_doc_manager,
        lock_manager=mock_lock_manager,
        uri_generator=mock_uri_generator,
        fingerprint_strategy=mock_fingerprint_strategy,
        index_store=mock_index_store,
        workspace=mock_workspace,
        differ=mock_differ,
        resolver=mock_resolver,
        reporter=mock_reporter,
        root_path=Path("/tmp"),
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
    # Arrange
    mock_resolver = mocker.create_autospec(CheckResolver, instance=True)
    runner = CheckRunner(
        doc_manager=mocker.create_autospec(DocumentManagerProtocol, instance=True),
        sig_manager=mocker.create_autospec(SignatureManagerProtocol, instance=True),
        fingerprint_strategy=mocker.create_autospec(
            FingerprintStrategyProtocol, instance=True
        ),
        index_store=mocker.create_autospec(IndexStoreProtocol, instance=True),
        differ=mocker.create_autospec(DifferProtocol, instance=True),
        resolver=mock_resolver,
        reporter=mocker.create_autospec(CheckReporter, instance=True),
        root_path=Path("/tmp"),
    )
~~~~~
~~~~~python.new
    # Arrange
    mock_resolver = mocker.create_autospec(CheckResolver, instance=True)
    runner = CheckRunner(
        doc_manager=mocker.create_autospec(DocumentManagerProtocol, instance=True),
        lock_manager=mocker.create_autospec(LockManagerProtocol, instance=True),
        uri_generator=mocker.create_autospec(URIGeneratorProtocol, instance=True),
        workspace=mocker.create_autospec(Workspace, instance=True),
        fingerprint_strategy=mocker.create_autospec(
            FingerprintStrategyProtocol, instance=True
        ),
        index_store=mocker.create_autospec(IndexStoreProtocol, instance=True),
        differ=mocker.create_autospec(DifferProtocol, instance=True),
        resolver=mock_resolver,
        reporter=mocker.create_autospec(CheckReporter, instance=True),
        root_path=Path("/tmp"),
    )
~~~~~

#### Acts 5: 修复 `Pump` 相关测试

修复 `PumpExecutor` 和 `PumpRunner` 的测试用例。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    DocstringMergerProtocol,
    FingerprintStrategyProtocol,
    LanguageTransformerProtocol,
    ModuleDef,
    FunctionDef,
    ResolutionAction,
    DocstringIR,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.common.transaction import TransactionManager
~~~~~
~~~~~python.new
from stitcher.spec import (
    DocstringMergerProtocol,
    FingerprintStrategyProtocol,
    LanguageTransformerProtocol,
    ModuleDef,
    FunctionDef,
    ResolutionAction,
    DocstringIR,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol
from stitcher.common.transaction import TransactionManager
from stitcher.workspace import Workspace
~~~~~

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


@pytest.fixture
def executor(
    tmp_path: Path,
    mocker,
    mock_doc_manager: DocumentManagerProtocol,
    mock_sig_manager: SignatureManagerProtocol,
) -> PumpExecutor:
    # Use the real tmp_path instead of a MagicMock for root_path
    return PumpExecutor(
        root_path=tmp_path,
        doc_manager=mock_doc_manager,
        sig_manager=mock_sig_manager,
        transformer=mocker.create_autospec(LanguageTransformerProtocol, instance=True),
        merger=mocker.create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=mocker.create_autospec(
            FingerprintStrategyProtocol, instance=True
        ),
    )
~~~~~
~~~~~python.new
@pytest.fixture
def mock_lock_manager(mocker) -> MagicMock:
    mock = mocker.create_autospec(LockManagerProtocol, instance=True)
    mock.load.return_value = {}
    mock.serialize.return_value = '{"version": "1.0", "fingerprints": {}}'
    return mock


@pytest.fixture
def executor(
    tmp_path: Path,
    mocker,
    mock_doc_manager: DocumentManagerProtocol,
    mock_lock_manager: LockManagerProtocol,
) -> PumpExecutor:
    mock_workspace = mocker.create_autospec(Workspace, instance=True)
    mock_workspace.find_owning_package.return_value = tmp_path
    # Use the real tmp_path instead of a MagicMock for root_path
    return PumpExecutor(
        root_path=tmp_path,
        workspace=mock_workspace,
        doc_manager=mock_doc_manager,
        lock_manager=mock_lock_manager,
        uri_generator=mocker.create_autospec(URIGeneratorProtocol, instance=True),
        transformer=mocker.create_autospec(LanguageTransformerProtocol, instance=True),
        merger=mocker.create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=mocker.create_autospec(
            FingerprintStrategyProtocol, instance=True
        ),
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
    # Assert YAML file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert signature file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", ANY)
~~~~~
~~~~~python.new
    # Assert YAML file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert lock file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call("stitcher.lock", ANY)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert signature is written
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", ANY)
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()  # type: ignore[reportAttributeAccessIssue]
~~~~~
~~~~~python.new
    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert lock file is written
    mock_tm.add_write.assert_any_call("stitcher.lock", ANY)
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()  # type: ignore[reportAttributeAccessIssue]
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    ResolutionAction,
    FingerprintStrategyProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.config import StitcherConfig
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    ResolutionAction,
    FingerprintStrategyProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.config import StitcherConfig
from stitcher.workspace import Workspace
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py
~~~~~
~~~~~python.old
    mock_executor = create_autospec(PumpExecutorProtocol, instance=True)
    mock_handler = create_autospec(InteractionHandler, instance=True)
    mock_tm = create_autospec(TransactionManager, instance=True)
    mock_doc_manager = create_autospec(DocumentManagerProtocol, instance=True)
    mock_sig_manager = create_autospec(SignatureManagerProtocol, instance=True)
    mock_fingerprint_strategy = create_autospec(
        FingerprintStrategyProtocol, instance=True
    )
~~~~~
~~~~~python.new
    mock_executor = create_autospec(PumpExecutorProtocol, instance=True)
    mock_handler = create_autospec(InteractionHandler, instance=True)
    mock_tm = create_autospec(TransactionManager, instance=True)
    mock_doc_manager = create_autospec(DocumentManagerProtocol, instance=True)
    mock_lock_manager = create_autospec(LockManagerProtocol, instance=True)
    mock_uri_generator = create_autospec(URIGeneratorProtocol, instance=True)
    mock_workspace = create_autospec(Workspace, instance=True)
    mock_fingerprint_strategy = create_autospec(
        FingerprintStrategyProtocol, instance=True
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py
~~~~~
~~~~~python.old
    runner = PumpRunner(
        pump_engine=mock_pump_engine,
        executor=mock_executor,
        interaction_handler=mock_handler,
        doc_manager=mock_doc_manager,
        sig_manager=mock_sig_manager,
        fingerprint_strategy=mock_fingerprint_strategy,
    )
~~~~~
~~~~~python.new
    runner = PumpRunner(
        pump_engine=mock_pump_engine,
        executor=mock_executor,
        interaction_handler=mock_handler,
        doc_manager=mock_doc_manager,
        lock_manager=mock_lock_manager,
        uri_generator=mock_uri_generator,
        workspace=mock_workspace,
        fingerprint_strategy=mock_fingerprint_strategy,
    )
~~~~~

#### Acts 6: 修复 `test_execution_planner.py`

这个测试文件用于测试 `PumpExecutor` 的内部方法 `_generate_execution_plan`，它的签名没有改变，但 `PumpExecutor` 的构造函数改变了。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_execution_planner.py
~~~~~
~~~~~python.old
@pytest.fixture
def executor(tmp_path) -> PumpExecutor:
    """A PumpExecutor instance for testing its internal methods."""
    return PumpExecutor(
        root_path=tmp_path,
        doc_manager=DocumentManager(root_path=tmp_path),
        sig_manager=MagicMock(),
        transformer=MagicMock(),
        merger=DocstringMerger(),
        fingerprint_strategy=MagicMock(),
    )
~~~~~
~~~~~python.new
@pytest.fixture
def executor(tmp_path, mocker) -> PumpExecutor:
    """A PumpExecutor instance for testing its internal methods."""
    return PumpExecutor(
        root_path=tmp_path,
        workspace=mocker.create_autospec(Workspace, instance=True),
        doc_manager=DocumentManager(root_path=tmp_path),
        lock_manager=mocker.create_autospec(LockManagerProtocol, instance=True),
        uri_generator=mocker.create_autospec(URIGeneratorProtocol, instance=True),
        transformer=MagicMock(),
        merger=DocstringMerger(),
        fingerprint_strategy=MagicMock(),
    )
~~~~~

### 下一步建议
我们已经完成了应用层的核心重构和测试修复。现在，`pyright` 的主要错误应该已经解决。

最后一步是 **阶段 4: 重构引擎简化 (Refactor Engine Lobotomy)**。我们需要进入 `stitcher-refactor` 包，删除所有与旧签名文件物理移动相关的逻辑，并将其替换为对 Lock 文件中 SURI Key 的更新操作。
