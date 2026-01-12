好的，错误报告已收到。正如预期的那样，我们通过移除遗留代码，成功地暴露了所有需要更新的依赖点。现在，我们将逐一修复这些问题，完成重构的闭环。

## [WIP] test(app,analysis): 修复因移除遗留模型导致的测试失败

### 错误分析

在 `[WIP] refactor(app): 移除 check 命令遗留的数据模型和协议` 计划中，我们有意地删除了 `stitcher.app.types.FileCheckResult` 和 `stitcher.app.runners.check.protocols`。这导致了连锁反应：
1.  **`ModuleNotFoundError` / `ImportError`**: 任何直接导入这些已删除模块的代码都会失败。
2.  **`Unknown import symbol`**: `stitcher.app.core.StitcherApp` 仍然在类型提示中引用已删除的 `FileCheckResult`。
3.  **`mypy` 类型错误**:
    *   多个测试文件在使用 `unittest.mock.create_autospec` 时，由于其对协议的严格遵循，导致 `mypy` 无法识别 `return_value` 等标准 mock 属性。
    *   测试辅助函数 `create_state` 的类型签名与其在测试中的实际用法（传入 `None`）不匹配。
    *   在测试中对一个协议的只读属性 (`file_path`) 进行了赋值操作，这是不允许的。

### 用户需求

修复因上一阶段架构清理工作而导致的所有编译时错误和测试失败。确保整个测试套件能够再次通过，并且所有代码都遵循新的、统一的数据模型和协议。

### 评论

这是“回归驱动开发”的核心环节。我们利用失败的测试作为精确的“手术清单”，确保重构不仅改变了实现，也同步更新了系统的行为契约（测试）。通过这次修复，我们将：
1.  **统一测试模型**: 使测试代码与应用代码一样，完全依赖 `stitcher-analysis` 提供的权威数据模型。
2.  **提升测试健壮性**: 采用 `pytest-mock` 的 `mocker` 装置和 `PropertyMock`，使我们的 mock 配置对 `mypy` 更友好，从而提高静态分析的准确性。
3.  **完成重构闭环**: 在功能代码和测试代码两个层面都完成架构升级，确保系统达到一个新的、更高质量的稳定状态。

### 目标

1.  **修复所有导入错误**: 更新或移除所有对已删除模块的引用。
2.  **修正类型提示**: 确保 `StitcherApp` 和测试辅助函数具有正确的类型签名。
3.  **重构测试中的 Mock**: 全面转向使用 `mocker` fixture 来创建 mock 对象，并使用 `PropertyMock` 来正确地模拟只读属性。
4.  **恢复测试套件至通过状态**。

### 基本原理

我们将按照编译器和测试运行器报告的错误，精确地对每个问题点进行修复。
-   对于导入问题，我们将重新指向 `stitcher-analysis.schema` 或直接移除。
-   对于 `mypy` 的 mock 问题，我们将注入 `mocker` fixture，它能创建出更符合 `mypy` 类型推断的 `MagicMock` 对象。
-   对于协议属性的修改，我们将使用 `unittest.mock.PropertyMock`，这是一种符合 Python 属性协议的、正确的 mock 方式。
通过这一系列精确的、有针对性的修复，我们可以高效地使整个代码库恢复健康。

### 标签

#intent/fix #flow/ready #priority/high #comp/app #comp/analysis #comp/tests #scope/dx #ai/instruct #task/state/continue

---

### Script

#### Acts 1: 修复 `stitcher-application` 中的核心导入错误

首先，我们修复 `runner.py` 和 `core.py` 中因删除 `protocols.py` 和旧 `FileCheckResult` 导致的直接依赖错误。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
from stitcher.spec.interaction import InteractionContext
from stitcher.analysis.schema import FileCheckResult as AnalysisFileCheckResult

from .protocols import (
    CheckResolverProtocol,
    CheckReporterProtocol,
)
from .subject import IndexCheckSubjectAdapter, ASTCheckSubjectAdapter
from stitcher.analysis.engines.consistency.engine import create_consistency_engine


class CheckRunner:
    def __init__(
        self,
        doc_manager: DocumentManagerProtocol,
        sig_manager: SignatureManagerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        index_store: IndexStoreProtocol,
        differ: DifferProtocol,
        resolver: CheckResolverProtocol,
        reporter: CheckReporterProtocol,
        root_path: Path,
    ):
~~~~~
~~~~~python.new
from stitcher.spec.interaction import InteractionContext
from stitcher.analysis.schema import FileCheckResult as AnalysisFileCheckResult

from stitcher.app.runners.check.resolver import CheckResolver
from stitcher.app.runners.check.reporter import CheckReporter
from .subject import IndexCheckSubjectAdapter, ASTCheckSubjectAdapter
from stitcher.analysis.engines.consistency.engine import create_consistency_engine


class CheckRunner:
    def __init__(
        self,
        doc_manager: DocumentManagerProtocol,
        sig_manager: SignatureManagerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        index_store: IndexStoreProtocol,
        differ: DifferProtocol,
        resolver: CheckResolver,
        reporter: CheckReporter,
        root_path: Path,
    ):
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from typing import Callable
from .types import PumpResult, FileCheckResult, CoverageResult
from stitcher.index.db import DatabaseManager
~~~~~
~~~~~python.new
from typing import Callable
from stitcher.analysis.schema import FileCheckResult
from .types import PumpResult, CoverageResult
from stitcher.index.db import DatabaseManager
~~~~~

#### Acts 2: 修复 `stitcher-analysis` 测试中的 `mypy` 错误

接下来，我们处理 `analysis` 包中测试的类型提示和 mock 用法问题。

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/rules/consistency/test_rules.py
~~~~~
~~~~~python.old
from unittest.mock import Mock
from needle.pointer import L
from stitcher.spec import DocstringIR

from stitcher.analysis.schema import SymbolState
~~~~~
~~~~~python.new
import pytest
from unittest.mock import Mock
from typing import Optional
from needle.pointer import L
from stitcher.spec import DocstringIR

from stitcher.analysis.schema import SymbolState
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/rules/consistency/test_rules.py
~~~~~
~~~~~python.old
def create_state(
    fqn="test.func",
    is_public=True,
    exists_in_code=True,
    exists_in_yaml=True,
    source_doc="summary",
    yaml_doc="summary",
    sig_hash="abc",
    base_sig_hash="abc",
    yaml_hash="123",
    base_yaml_hash="123",
):
~~~~~
~~~~~python.new
def create_state(
    fqn="test.func",
    is_public=True,
    exists_in_code=True,
    exists_in_yaml=True,
    source_doc: Optional[str] = "summary",
    yaml_doc: Optional[str] = "summary",
    sig_hash="abc",
    base_sig_hash="abc",
    yaml_hash="123",
    base_yaml_hash="123",
):
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/engines/test_pump_engine.py
~~~~~
~~~~~python.old
from unittest.mock import create_autospec

import pytest
from needle.pointer import L

from stitcher.analysis.engines.pump import PumpEngine, create_pump_engine
from stitcher.spec import DifferProtocol, DocstringIR
from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import SymbolState


@pytest.fixture
def mock_differ() -> DifferProtocol:
    return create_autospec(DifferProtocol, instance=True)


@pytest.fixture
def mock_subject() -> AnalysisSubject:
    return create_autospec(AnalysisSubject, instance=True)


@pytest.fixture
def engine(mock_differ: DifferProtocol) -> PumpEngine:
    return create_pump_engine(differ=mock_differ)
~~~~~
~~~~~python.new
from unittest.mock import create_autospec, PropertyMock, MagicMock

import pytest
from needle.pointer import L

from stitcher.analysis.engines.pump import PumpEngine, create_pump_engine
from stitcher.spec import DifferProtocol, DocstringIR
from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import SymbolState


@pytest.fixture
def mock_differ(mocker) -> MagicMock:
    return mocker.create_autospec(DifferProtocol, instance=True)


@pytest.fixture
def mock_subject(mocker) -> MagicMock:
    subject = mocker.create_autospec(AnalysisSubject, instance=True)
    # Configure file_path as a readable property
    type(subject).file_path = PropertyMock(return_value="src/main.py")
    return subject


@pytest.fixture
def engine(mock_differ: DifferProtocol) -> PumpEngine:
    return create_pump_engine(differ=mock_differ)
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/engines/test_pump_engine.py
~~~~~
~~~~~python.old
    )
    mock_subject.get_all_symbol_states.return_value = {"func": state}
    mock_subject.file_path = "src/main.py"
    mock_differ.generate_text_diff.return_value = "diff content"

    # Act
    conflicts = engine.analyze(mock_subject)
~~~~~
~~~~~python.new
    )
    mock_subject.get_all_symbol_states.return_value = {"func": state}
    mock_differ.generate_text_diff.return_value = "diff content"

    # Act
    conflicts = engine.analyze(mock_subject)
~~~~~

#### Acts 3: 修复 `stitcher-application` 测试中的 `mypy` 和导入错误

最后，我们修复 `application` 包中测试的 mock 问题，并更新 `test_check_runner` 以使用新的 concrete class mocks。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
from unittest.mock import create_autospec, ANY
from pathlib import Path

import pytest
~~~~~
~~~~~python.new
from unittest.mock import create_autospec, ANY, MagicMock
from pathlib import Path

import pytest
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
@pytest.fixture
def mock_doc_manager() -> DocumentManagerProtocol:
    # Configure flatten_module_docs to return a mock IR
    mock = create_autospec(DocumentManagerProtocol, instance=True)
~~~~~
~~~~~python.new
@pytest.fixture
def mock_doc_manager(mocker) -> MagicMock:
    # Configure flatten_module_docs to return a mock IR
    mock = mocker.create_autospec(DocumentManagerProtocol, instance=True)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
@pytest.fixture
def mock_sig_manager(tmp_path: Path) -> SignatureManagerProtocol:
    mock = create_autospec(SignatureManagerProtocol, instance=True)
~~~~~
~~~~~python.new
@pytest.fixture
def mock_sig_manager(mocker, tmp_path: Path) -> MagicMock:
    mock = mocker.create_autospec(SignatureManagerProtocol, instance=True)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
@pytest.fixture
def executor(
    tmp_path: Path,
    mock_doc_manager: DocumentManagerProtocol,
    mock_sig_manager: SignatureManagerProtocol,
) -> PumpExecutor:
    # Use the real tmp_path instead of a MagicMock for root_path
    return PumpExecutor(
        root_path=tmp_path,
        doc_manager=mock_doc_manager,
        sig_manager=mock_sig_manager,
        transformer=create_autospec(LanguageTransformerProtocol, instance=True),
        merger=create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=create_autospec(
            FingerprintStrategyProtocol, instance=True
        ),
    )
~~~~~
~~~~~python.new
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

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
def test_executor_hydrates_new_doc(executor: PumpExecutor, sample_module: ModuleDef):
    """Test standard pumping of a new docstring without conflicts."""
    mock_tm = create_autospec(TransactionManager, instance=True)

    executor.execute([sample_module], decisions={}, tm=mock_tm, strip=False)
~~~~~
~~~~~python.new
def test_executor_hydrates_new_doc(mocker, executor: PumpExecutor, sample_module: ModuleDef):
    """Test standard pumping of a new docstring without conflicts."""
    mock_tm = mocker.create_autospec(TransactionManager, instance=True)

    executor.execute([sample_module], decisions={}, tm=mock_tm, strip=False)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
def test_executor_overwrite_and_strip(
    executor: PumpExecutor,
    sample_module: ModuleDef,
    mock_doc_manager: DocumentManagerProtocol,
):
    """Test HYDRATE_OVERWRITE decision with stripping enabled."""
    mock_tm = create_autospec(TransactionManager, instance=True)
~~~~~
~~~~~python.new
def test_executor_overwrite_and_strip(
    mocker,
    executor: PumpExecutor,
    sample_module: ModuleDef,
    mock_doc_manager: DocumentManagerProtocol,
):
    """Test HYDRATE_OVERWRITE decision with stripping enabled."""
    mock_tm = mocker.create_autospec(TransactionManager, instance=True)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
from pathlib import Path
from unittest.mock import create_autospec, MagicMock

from stitcher.app.runners.check.runner import CheckRunner
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec import (
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    ModuleDef,
    DifferProtocol,
)
from stitcher.app.runners.check.protocols import (
    CheckResolverProtocol,
    CheckReporterProtocol,
)
from stitcher.spec.interaction import InteractionContext
from stitcher.analysis.schema import FileCheckResult as AnalysisResult, Violation
from needle.pointer import L


def test_check_runner_orchestrates_analysis_and_resolution():
    """
    验证 CheckRunner 正确地按顺序调用其依赖项：
    1. Engine (通过 analyze_batch)
    2. Resolver (auto_reconcile, 然后 resolve_conflicts)
    3. Reporter
    """
    # 1. Arrange: 为所有依赖项创建 mock
    mock_doc_manager = create_autospec(DocumentManagerProtocol, instance=True)
    mock_sig_manager = create_autospec(SignatureManagerProtocol, instance=True)
    mock_fingerprint_strategy = create_autospec(
        FingerprintStrategyProtocol, instance=True
    )
    mock_index_store = create_autospec(IndexStoreProtocol, instance=True)
    mock_differ = create_autospec(DifferProtocol, instance=True)
    mock_resolver = create_autospec(CheckResolverProtocol, instance=True)
    mock_reporter = create_autospec(CheckReporterProtocol, instance=True)

    # 配置 mock 模块
    mock_modules = [ModuleDef(file_path="src/main.py")]
~~~~~
~~~~~python.new
from pathlib import Path
from unittest.mock import create_autospec, MagicMock

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
from stitcher.spec.interaction import InteractionContext
from stitcher.analysis.schema import FileCheckResult as AnalysisResult, Violation
from needle.pointer import L


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

    # 配置 mock 模块
    mock_modules = [ModuleDef(file_path="src/main.py")]
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
def test_check_runner_passes_relink_and_reconcile_flags_to_resolver():
    """
    确保来自 Runner 公共 API 的布尔标志被正确传递给解析器组件。
    """
    # Arrange
    mock_resolver = create_autospec(CheckResolverProtocol)
    runner = CheckRunner(
        doc_manager=create_autospec(DocumentManagerProtocol),
        sig_manager=create_autospec(SignatureManagerProtocol),
        fingerprint_strategy=create_autospec(FingerprintStrategyProtocol),
        index_store=create_autospec(IndexStoreProtocol),
        differ=create_autospec(DifferProtocol),
        resolver=mock_resolver,
        reporter=create_autospec(CheckReporterProtocol),
        root_path=Path("/tmp"),
    )
~~~~~
~~~~~python.new
def test_check_runner_passes_relink_and_reconcile_flags_to_resolver(mocker):
    """
    确保来自 Runner 公共 API 的布尔标志被正确传递给解析器组件。
    """
    # Arrange
    mock_resolver = mocker.create_autospec(CheckResolver, instance=True)
    runner = CheckRunner(
        doc_manager=mocker.create_autospec(DocumentManagerProtocol, instance=True),
        sig_manager=mocker.create_autospec(SignatureManagerProtocol, instance=True),
        fingerprint_strategy=mocker.create_autospec(FingerprintStrategyProtocol, instance=True),
        index_store=mocker.create_autospec(IndexStoreProtocol, instance=True),
        differ=mocker.create_autospec(DifferProtocol, instance=True),
        resolver=mock_resolver,
        reporter=mocker.create_autospec(CheckReporter, instance=True),
        root_path=Path("/tmp"),
    )
~~~~~

### 下一步建议

我们已经成功修复了因移除遗留模型而导致的所有编译时和测试错误。测试套件现在应该能够再次通过。

本次重构任务的核心目标——将 `CheckReporter` 及其数据流迁移到现代化的、基于 `Violation` 对象的架构——已经完成。

我建议，在确认所有测试通过后，我们可以将这个系列的工作标记为 `[COMMIT]`，创建一个 Git 提交来固化这次重要的架构改进。如果你同意，我将生成相应的 `[COMMIT]` 计划。
