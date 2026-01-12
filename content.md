Excellent. Let's proceed with extending our unit testing strategy to the `pump` command's core components.

Following the established pattern, I will create isolated unit tests for `PumpAnalyzer`, `PumpExecutor`, and `PumpRunner`. This will involve creating the necessary directory structure and then writing the test files, using mocks extensively to verify the internal logic of each component without relying on the filesystem or other parts of the application.

## [WIP] test(application): Add unit tests for Pump command components

### 用户需求

用户要求遵循与 `Check` 命令相同的模式，为 `PumpRunner`、`PumpAnalyzer` 和 `PumpExecutor` 创建单元测试，以确保核心的数据提取和合并逻辑在隔离环境中是可验证的。

### 评论

这是一个正确的方向。`pump` 命令的逻辑，特别是涉及到状态合并（`DocstringMerger`）、冲突解决和文件系统事务的部分，本质上比 `check` 命令更为复杂和关键。为其编写独立的单元测试，可以确保这些具有副作用的操作在各种场景下（如强制覆盖、保留现有、附带剥离等）都能按预期工作，从而极大地提高该功能的可靠性。

### 目标

1.  在 `packages/stitcher-application/tests/unit/runners/` 目录下创建 `pump/` 子目录。
2.  为 `PumpAnalyzer` 编写单元测试，验证它能否在 `hydrate_module(dry_run=True)` 的帮助下正确识别出源码与 YAML 之间的内容冲突。
3.  为 `PumpExecutor` 编写单元测试，验证它能否根据不同的用户决策（`ResolutionAction`）和配置（如 `strip`），正确地调用 `TransactionManager` 来生成预期的文件系统操作（写 YAML、写签名、写源码）。
4.  为 `PumpRunner` 编写单元测试，验证其作为编排器的角色，确保它能正确地调用分析器、交互处理器和执行器。

### 基本原理

我们将继续深化对协议和依赖注入的运用：
-   **`PumpAnalyzer` 测试**: 将 Mock `DocumentManager` 的 `hydrate_module` 方法，使其在 `dry_run=True` 模式下返回预设的冲突结果。然后断言 `PumpAnalyzer` 是否能将这些结果正确地包装成 `InteractionContext` 对象。
-   **`PumpExecutor` 测试**: 将 Mock `TransactionManager`、`DocumentManager`、`SignatureManager` 和 `LanguageTransformerProtocol`。测试的核心是调用 `executor.execute` 后，验证 `mock_tm.add_write` 等方法是否被以正确的路径和内容参数调用，从而验证其执行计划的正确性。
-   **`PumpRunner` 测试**: Mock `PumpAnalyzer` 和 `PumpExecutor`。测试将验证当 `analyzer` 返回冲突时，`InteractionHandler` 是否被调用，以及从 `handler` 返回的决策是否被正确地传递给了 `executor`。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/application #scope/dx #ai/instruct #task/domain/testing #task/object/unit-tests #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建 Pump 的单元测试目录

与 `check` 命令类似，我将首先创建存放 `pump` 相关单元测试的目录。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-application/tests/unit/runners/pump
~~~~~

#### Acts 2: 编写 PumpAnalyzer 的单元测试

`PumpAnalyzer` 的核心职责是发现冲突。这个测试将通过 Mock `DocumentManager` 来模拟冲突场景，并验证分析器是否能正确报告它们。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/pump/test_analyzer.py
~~~~~
~~~~~python
from unittest.mock import create_autospec, MagicMock

import pytest

from stitcher.app.runners.pump.analyzer import PumpAnalyzer
from stitcher.spec import (
    DifferProtocol,
    IndexStoreProtocol,
    ModuleDef,
    DocstringIR,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec.interaction import ConflictType


@pytest.fixture
def mock_doc_manager() -> DocumentManagerProtocol:
    return create_autospec(DocumentManagerProtocol, instance=True)


@pytest.fixture
def mock_sig_manager() -> SignatureManagerProtocol:
    return create_autospec(SignatureManagerProtocol, instance=True)


@pytest.fixture
def mock_index_store() -> IndexStoreProtocol:
    return create_autospec(IndexStoreProtocol, instance=True)


@pytest.fixture
def mock_differ() -> DifferProtocol:
    return create_autospec(DifferProtocol, instance=True)


@pytest.fixture
def analyzer(
    mock_doc_manager: DocumentManagerProtocol,
    mock_sig_manager: SignatureManagerProtocol,
    mock_index_store: IndexStoreProtocol,
    mock_differ: DifferProtocol,
) -> PumpAnalyzer:
    return PumpAnalyzer(
        mock_doc_manager, mock_sig_manager, mock_index_store, mock_differ
    )


def test_analyzer_no_changes(analyzer: PumpAnalyzer, mock_doc_manager: DocumentManagerProtocol, mock_index_store: IndexStoreProtocol):
    """Verify analyzer returns no conflicts if hydrate dry_run is successful."""
    module = ModuleDef(file_path="src/main.py")
    mock_index_store.get_symbols_by_file_path.return_value = []
    mock_doc_manager.hydrate_module.return_value = {"success": True, "conflicts": []}

    conflicts = analyzer.analyze([module])

    assert not conflicts
    mock_doc_manager.hydrate_module.assert_called_once()


def test_analyzer_detects_conflict(
    analyzer: PumpAnalyzer,
    mock_doc_manager: DocumentManagerProtocol,
    mock_differ: DifferProtocol,
    mock_index_store: IndexStoreProtocol
):
    """Verify analyzer returns InteractionContext on hydrate dry_run failure."""
    module = ModuleDef(file_path="src/main.py")
    
    # Simulate a file with a docstring that is dirty (changed)
    mock_symbol = MagicMock()
    mock_symbol.logical_path = "func"
    mock_symbol.docstring_hash = "new_hash"
    mock_index_store.get_symbols_by_file_path.return_value = [mock_symbol]
    
    # Simulate that hydrate found a conflict for this dirty doc
    mock_doc_manager.hydrate_module.return_value = {
        "success": False,
        "conflicts": ["func"],
    }
    # Provide IRs for diff generation
    mock_doc_manager.flatten_module_docs.return_value = {
        "func": DocstringIR(summary="Code Doc")
    }
    mock_doc_manager.load_docs_for_module.return_value = {
        "func": DocstringIR(summary="YAML Doc")
    }
    mock_differ.generate_text_diff.return_value = "diff content"

    conflicts = analyzer.analyze([module])

    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.fqn == "func"
    assert conflict.file_path == "src/main.py"
    assert conflict.conflict_type == ConflictType.DOC_CONTENT_CONFLICT
    assert conflict.doc_diff == "diff content"
    mock_differ.generate_text_diff.assert_called_once_with(
        "YAML Doc", "Code Doc", "yaml", "code"
    )

~~~~~

#### Acts 3: 编写 PumpExecutor 的单元测试

`PumpExecutor` 的测试是核心。它验证了用户的决策如何转化为对 `TransactionManager` 的调用，从而确保文件系统的变更符合预期。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/pump/test_executor.py
~~~~~
~~~~~python
from unittest.mock import create_autospec, MagicMock

import pytest

from stitcher.app.runners.pump.executor import PumpExecutor
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


@pytest.fixture
def mock_doc_manager() -> DocumentManagerProtocol:
    # Configure flatten_module_docs to return a mock IR
    mock = create_autospec(DocumentManagerProtocol, instance=True)
    mock.flatten_module_docs.return_value = {
        "func_a": DocstringIR(summary="Source Doc A")
    }
    return mock


@pytest.fixture
def executor(
    mock_doc_manager: DocumentManagerProtocol,
) -> PumpExecutor:
    return PumpExecutor(
        root_path=MagicMock(),
        doc_manager=mock_doc_manager,
        sig_manager=create_autospec(SignatureManagerProtocol, instance=True),
        transformer=create_autospec(LanguageTransformerProtocol, instance=True),
        merger=create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=create_autospec(FingerprintStrategyProtocol, instance=True),
    )


@pytest.fixture
def sample_module() -> ModuleDef:
    return ModuleDef(
        file_path="src/main.py", functions=[FunctionDef(name="func_a")]
    )


def test_executor_hydrates_new_doc(executor: PumpExecutor, sample_module: ModuleDef):
    """Test standard pumping of a new docstring without conflicts."""
    mock_tm = create_autospec(TransactionManager, instance=True)

    executor.execute([sample_module], decisions={}, tm=mock_tm, strip=False)

    # Assert YAML file is written to
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", MagicMock())
    # Assert signature file is written to
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", MagicMock())


def test_executor_overwrite_and_strip(
    executor: PumpExecutor,
    sample_module: ModuleDef,
    mock_doc_manager: DocumentManagerProtocol,
):
    """Test HYDRATE_OVERWRITE decision with stripping enabled."""
    mock_tm = create_autospec(TransactionManager, instance=True)
    decisions = {"func_a": ResolutionAction.HYDRATE_OVERWRITE}
    
    # Mock transformer strip call
    executor.transformer.strip.return_value = "stripped content"
    
    # Mock read_text for the source file
    executor.root_path / "src/main.py".read_text.return_value = "original content"

    executor.execute([sample_module], decisions=decisions, tm=mock_tm, strip=True)
    
    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", MagicMock())
    # Assert signature is written
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", MagicMock())
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()
    mock_tm.add_write.assert_any_call("src/main.py", "stripped content")
~~~~~

#### Acts 4: 编写 PumpRunner 的单元测试

最后，`PumpRunner` 的测试确保了整个流程的正确编排。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/pump/test_runner.py
~~~~~
~~~~~python
from unittest.mock import create_autospec

from stitcher.app.runners.pump.runner import PumpRunner
from stitcher.app.runners.pump.protocols import (
    PumpAnalyzerProtocol,
    PumpExecutorProtocol,
)
from stitcher.spec import ModuleDef, ResolutionAction
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.config import StitcherConfig
from stitcher.common.transaction import TransactionManager


def test_runner_orchestrates_conflict_resolution_flow():
    """
    Verify that the runner correctly uses analyzer, handler, and executor
    when a conflict is detected.
    """
    # 1. Arrange: Mocks for all dependencies
    mock_analyzer = create_autospec(PumpAnalyzerProtocol, instance=True)
    mock_executor = create_autospec(PumpExecutorProtocol, instance=True)
    mock_handler = create_autospec(InteractionHandler, instance=True)
    mock_tm = create_autospec(TransactionManager, instance=True)

    # Configure mock return values
    mock_modules = [ModuleDef(file_path="src/main.py")]
    mock_conflicts = [
        InteractionContext(file_path="src/main.py", fqn="func", conflict_type="TEST")
    ]
    mock_decisions = {"func": ResolutionAction.HYDRATE_OVERWRITE}

    mock_analyzer.analyze.return_value = mock_conflicts
    mock_handler.process_interactive_session.return_value = [
        ResolutionAction.HYDRATE_OVERWRITE
    ]

    # 2. Act: Instantiate and run the runner
    runner = PumpRunner(
        analyzer=mock_analyzer, executor=mock_executor, interaction_handler=mock_handler
    )
    runner.run_batch(
        modules=mock_modules,
        config=StitcherConfig(),
        tm=mock_tm,
        strip=True,
        force=False,
        reconcile=False,
    )

    # 3. Assert: Verify the orchestration flow
    mock_analyzer.analyze.assert_called_once_with(mock_modules)
    mock_handler.process_interactive_session.assert_called_once_with(mock_conflicts)
    mock_executor.execute.assert_called_once_with(
        mock_modules, mock_decisions, mock_tm, True
    )

~~~~~

### 下一步建议

我们已经成功地为 `pump` 命令的核心组件建立了单元测试。现在，我们的测试金字塔底部变得更加坚实。

下一步，我建议：
1.  **重构 `pump` 集成测试**: 与 `check` 命令一样，现在可以安全地重构 `packages/stitcher-application/tests/integration/test_pump_*.py` 中的测试，移除那些已经被新单元测试覆盖的冗余和复杂的测试用例。
2.  **为 `InitRunner` 和 `TransformRunner` 添加单元测试**: 按照相同的模式，为 `init` 和 `strip`/`inject` 命令的 Runners 补充单元测试。
3.  **提交当前工作**: 在完成上述任务后，我们可以创建一个新的 `[COMMIT]` 计划来提交所有新的 `pump` 单元测试。
