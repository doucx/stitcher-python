好的，我们立即开始。

首先，我将为 `stitcher-application` 包创建符合 `d3-principle-pytest-monorepo-architecture` 规范的单元测试目录结构。然后，我将为 `CheckAnalyzer` 和 `CheckRunner` 这两个核心组件编写第一批单元测试。

`CheckAnalyzer` 的测试将专注于验证其在各种输入（通过一个伪造的 `CheckSubject` 提供）下能否正确识别不同的冲突状态。`CheckRunner` 的测试将验证其作为编排器的角色，确保它能正确地调用其依赖项（分析器、解析器、报告器）。

这将为我们后续重构和扩展测试套件打下坚实的基础。

## [WIP] test(application): 为 CheckRunner 和 CheckAnalyzer 添加单元测试

### 用户需求

用户要求开始编写单元测试，利用已定义的协议接口来隔离和测试 `stitcher-application` 中的核心组件，以提高测试套件的质量和效率。

### 评论

这是一个至关重要的步骤，标志着我们测试策略的成熟。通过从端到端测试转向以单元测试为主，我们将极大地提升测试套件的执行速度、稳定性和可维护性。利用协议进行依赖注入和模拟是实现这一目标的关键，这将使我们的代码库更加健壮和灵活。

### 目标

1.  在 `packages/stitcher-application/tests/` 目录下创建 `unit/` 子目录结构，用于存放单元测试。
2.  为 `CheckAnalyzer` 编写一套全面的单元测试，覆盖其所有核心的冲突与状态检测逻辑。
3.  为 `CheckRunner` 编写单元测试，验证其作为业务流程编排器的职责，确保它能正确调用其依赖组件。

### 基本原理

本次计划将严格遵循“测试意图而非实现”的原则。

1.  **对于 `CheckAnalyzer`**: 我们将创建一个实现了 `CheckSubject` 协议的伪造测试对象（Fake Object）。这个伪造对象将为分析器提供精确的、可控的输入数据（`SymbolState`），使我们能够独立地、确定性地测试分析器的每一种逻辑分支，而无需与真实的文件系统或数据库交互。
2.  **对于 `CheckRunner`**: 我们将使用 `unittest.mock.create_autospec` 来创建其所有依赖项（`CheckAnalyzerProtocol`, `CheckResolverProtocol` 等）的 Mock 对象。这不仅能隔离被测试的单元，还能确保我们的 Mock 严格遵守协议接口。测试的重点是断言 `CheckRunner` 是否以正确的顺序和参数调用了这些 Mock 对象的方法。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/application #scope/dx #ai/instruct #task/domain/testing #task/object/unit-tests #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建单元测试目录结构

首先，我将创建 `tests/unit` 目录来存放新的单元测试，并确保不创建 `__init__.py` 文件，以遵循 Monorepo 测试架构规范。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-application/tests/unit/runners/check
~~~~~

#### Acts 2: 编写 CheckAnalyzer 的单元测试

现在，我将创建 `test_analyzer.py` 文件。这个测试套件的核心是 `FakeCheckSubject`，它模拟了分析器的输入源，使我们能够精确地测试每一种冲突检测逻辑。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/check/test_analyzer.py
~~~~~
~~~~~python
from pathlib import Path
from unittest.mock import MagicMock, create_autospec
from typing import Dict

import pytest

from stitcher.app.runners.check.analyzer import CheckAnalyzer
from stitcher.app.runners.check.protocols import CheckSubject, SymbolState
from stitcher.spec import DifferProtocol, ConflictType


# Test Double: A Fake implementation of the CheckSubject protocol for controlled input.
class FakeCheckSubject(CheckSubject):
    def __init__(self, file_path: str, states: Dict[str, SymbolState], is_doc: bool = True):
        self._file_path = file_path
        self._states = states
        self._is_documentable = is_doc

    @property
    def file_path(self) -> str:
        return self._file_path

    def is_documentable(self) -> bool:
        return self._is_documentable

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        return self._states


@pytest.fixture
def mock_differ() -> DifferProtocol:
    return create_autospec(DifferProtocol)


@pytest.fixture
def analyzer(mock_differ: DifferProtocol) -> CheckAnalyzer:
    return CheckAnalyzer(root_path=Path("/test-project"), differ=mock_differ)


def test_analyzer_synchronized_state(analyzer: CheckAnalyzer):
    """Verify clean state when code, yaml, and baseline are synced."""
    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=True,
        signature_hash="hash1",
        baseline_signature_hash="hash1",
        yaml_content_hash="hash_yaml1",
        baseline_yaml_content_hash="hash_yaml1",
        source_doc_content=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state})

    result, conflicts = analyzer.analyze_subject(subject)

    assert result.is_clean
    assert not conflicts


def test_analyzer_missing_doc_warning(analyzer: CheckAnalyzer):
    """Verify warning for public symbol in code but not in YAML."""
    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=False,
        source_doc_content=None,  # No docstring in code either
        signature_hash="hash1",
        baseline_signature_hash="hash1",
        yaml_content_hash=None,
        baseline_yaml_content_hash=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state})

    result, conflicts = analyzer.analyze_subject(subject)

    assert result.warning_count == 1
    assert result.warnings["missing"] == ["func"]
    assert not conflicts


def test_analyzer_pending_doc_error(analyzer: CheckAnalyzer):
    """Verify error for symbol with doc in code but not in YAML."""
    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=False,
        source_doc_content="A new docstring.",
        signature_hash="hash1",
        baseline_signature_hash="hash1",
        yaml_content_hash=None,
        baseline_yaml_content_hash=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state})

    result, conflicts = analyzer.analyze_subject(subject)

    assert result.error_count == 1
    assert result.errors["pending"] == ["func"]
    assert not conflicts


def test_analyzer_signature_drift(analyzer: CheckAnalyzer, mock_differ: DifferProtocol):
    """Verify conflict for signature change when docs are stable."""
    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=True,
        signature_hash="new_code_hash",
        baseline_signature_hash="old_code_hash",
        yaml_content_hash="yaml_hash",
        baseline_yaml_content_hash="yaml_hash",
        source_doc_content=None,
        signature_text="def func(a: str):",
        yaml_doc_ir=MagicMock(),
        baseline_signature_text="def func(a: int):",
    )
    subject = FakeCheckSubject("src/main.py", {"func": state})

    result, conflicts = analyzer.analyze_subject(subject)

    assert not result.is_clean
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.fqn == "func"
    assert conflict.conflict_type == ConflictType.SIGNATURE_DRIFT
    mock_differ.generate_text_diff.assert_called_once()


def test_analyzer_co_evolution(analyzer: CheckAnalyzer, mock_differ: DifferProtocol):
    """Verify conflict when both signature and docs change."""
    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=True,
        signature_hash="new_code_hash",
        baseline_signature_hash="old_code_hash",
        yaml_content_hash="new_yaml_hash",
        baseline_yaml_content_hash="old_yaml_hash",
        source_doc_content=None,
        signature_text="def func(a: str):",
        yaml_doc_ir=MagicMock(),
        baseline_signature_text="def func(a: int):",
    )
    subject = FakeCheckSubject("src/main.py", {"func": state})

    result, conflicts = analyzer.analyze_subject(subject)

    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == ConflictType.CO_EVOLUTION
    mock_differ.generate_text_diff.assert_called_once()


def test_analyzer_dangling_doc(analyzer: CheckAnalyzer):
    """Verify conflict for doc existing in YAML but not in code."""
    state = SymbolState(
        fqn="dangling_func",
        is_public=True,
        exists_in_code=False,
        exists_in_yaml=True,
        source_doc_content=None,
        signature_hash=None,
        baseline_signature_hash=None,
        yaml_content_hash="yaml_hash",
        baseline_yaml_content_hash="yaml_hash",
        signature_text=None,
        yaml_doc_ir=MagicMock(),
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"dangling_func": state})

    result, conflicts = analyzer.analyze_subject(subject)

    assert len(conflicts) == 1
    assert conflicts[0].fqn == "dangling_func"
    assert conflicts[0].conflict_type == ConflictType.DANGLING_DOC
~~~~~

#### Acts 3: 编写 CheckRunner 的单元测试

最后，我将创建 `test_runner.py`。这个测试使用了大量的 Mock 对象来隔离 `CheckRunner`，确保我们只测试其自身的编排逻辑，例如它是否按预期顺序调用了分析器、解析器和报告器。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/check/test_runner.py
~~~~~
~~~~~python
from unittest.mock import create_autospec

from stitcher.app.runners.check.runner import CheckRunner
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec import (
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    ModuleDef,
)
from stitcher.app.runners.check.protocols import (
    CheckAnalyzerProtocol,
    CheckResolverProtocol,
    CheckReporterProtocol,
)
from stitcher.app.types import FileCheckResult
from stitcher.spec.interaction import InteractionContext


def test_check_runner_orchestrates_analysis_and_resolution():
    """
    Verifies that CheckRunner correctly calls its dependencies in order:
    1. Analyzer
    2. Resolver (auto_reconcile, then resolve_conflicts)
    3. Reporter
    """
    # 1. Arrange: Create autospec'd mocks for all dependencies
    mock_doc_manager = create_autospec(DocumentManagerProtocol)
    mock_sig_manager = create_autospec(SignatureManagerProtocol)
    mock_fingerprint_strategy = create_autospec(FingerprintStrategyProtocol)
    mock_index_store = create_autospec(IndexStoreProtocol)
    mock_analyzer = create_autospec(CheckAnalyzerProtocol)
    mock_resolver = create_autospec(CheckResolverProtocol)
    mock_reporter = create_autospec(CheckReporterProtocol)

    # Configure mock return values
    mock_modules = [ModuleDef(file_path="src/main.py")]
    mock_results = [FileCheckResult(path="src/main.py")]
    mock_conflicts = [
        InteractionContext(file_path="src/main.py", fqn="func", conflict_type="TEST")
    ]
    mock_analyzer.analyze_batch.return_value = (mock_results, mock_conflicts)
    mock_resolver.resolve_conflicts.return_value = True
    mock_reporter.report.return_value = True

    # 2. Act: Instantiate the runner and call the method under test
    runner = CheckRunner(
        doc_manager=mock_doc_manager,
        sig_manager=mock_sig_manager,
        fingerprint_strategy=mock_fingerprint_strategy,
        index_store=mock_index_store,
        analyzer=mock_analyzer,
        resolver=mock_resolver,
        reporter=mock_reporter,
    )

    # We test `analyze_batch` as a representative method.
    results, conflicts = runner.analyze_batch(mock_modules)
    runner.auto_reconcile_docs(results, mock_modules)
    resolution_success = runner.resolve_conflicts(results, conflicts)
    report_success = runner.report(results)

    # 3. Assert: Verify the interaction with mocks
    mock_analyzer.analyze_batch.assert_called_once_with(mock_modules)
    mock_resolver.auto_reconcile_docs.assert_called_once_with(
        mock_results, mock_modules
    )
    mock_resolver.resolve_conflicts.assert_called_once_with(
        mock_results, mock_conflicts, force_relink=False, reconcile=False
    )
    mock_reporter.report.assert_called_once_with(mock_results)

    # Assert that the final return values are propagated
    assert resolution_success is True
    assert report_success is True


def test_check_runner_passes_relink_and_reconcile_flags_to_resolver():
    """
    Ensures that boolean flags from the runner's public API are correctly
    passed down to the resolver component.
    """
    # Arrange
    mock_resolver = create_autospec(CheckResolverProtocol)
    runner = CheckRunner(
        doc_manager=create_autospec(DocumentManagerProtocol),
        sig_manager=create_autospec(SignatureManagerProtocol),
        fingerprint_strategy=create_autospec(FingerprintStrategyProtocol),
        index_store=create_autospec(IndexStoreProtocol),
        analyzer=create_autospec(CheckAnalyzerProtocol),
        resolver=mock_resolver,
        reporter=create_autospec(CheckReporterProtocol),
    )
    mock_results = [FileCheckResult(path="src/main.py")]
    mock_conflicts = [
        InteractionContext(file_path="src/main.py", fqn="func", conflict_type="TEST")
    ]

    # Act
    runner.resolve_conflicts(
        mock_results, mock_conflicts, force_relink=True, reconcile=True
    )

    # Assert
    mock_resolver.resolve_conflicts.assert_called_once_with(
        mock_results, mock_conflicts, force_relink=True, reconcile=True
    )
~~~~~

### 下一步建议

我们已经为 `Check` 命令的核心逻辑建立了单元测试的滩头阵地。下一步，我建议：

1.  **重构集成测试**: 逐步将 `packages/stitcher-application/tests/integration/test_check_*.py` 中的复杂测试用例，用新创建的单元测试方式来重写。保留少数几个高层次的集成测试作为冒烟测试。
2.  **扩展到 Pump 命令**: 遵循相同的模式，为 `PumpRunner`、`PumpAnalyzer` 和 `PumpExecutor` 创建单元测试。
3.  **完善 `test-utils`**: 在 `stitcher-test-utils` 包中添加用于创建协议 Mock 的工厂函数（例如 `create_mock_index_store`），以减少单元测试中的重复代码。
