核心指令：**在不改变现有业务行为的前提下**。

当前的测试失败揭示了两个主要问题：
1.  **逻辑回退 (Logic Regression)**: `CheckRunner` 在将新的 `Violation` 对象翻译回旧的 `FileCheckResult` 格式时，对于 `untracked_with_details` 类型的违规处理不当，导致报告了文件路径而非具体的未文档化符号。
2.  **测试过时 (Test Staleness)**: 单元测试 `test_check_runner.py` 尚未根据 `CheckRunner` 构造函数的签名变更进行更新。

我们必须修复这两个问题以恢复测试通过状态。

## [WIP] fix: 修复 CheckRunner 结果翻译逻辑及单元测试

### 用户需求

1.  修复 `CheckRunner._translate_results` 方法，使其能正确处理 `untracked_with_details` 类型的违规，还原旧版行为（即在 `warnings` 中填充具体的符号 Key，而非文件路径）。
2.  更新 `test_check_runner.py` 以匹配 `CheckRunner` 新的构造函数签名，消除 `TypeError`。

### 评论

这是一个精确的逻辑修复。
在 `stitcher-analysis` 的 `UntrackedRule` 中，`untracked_with_details` 违规携带了 `keys` 列表在 `context` 中。旧版的 `CheckReporter` 期望在 `result.warnings["untracked_detailed"]` 中读到这些 keys。目前的通用翻译逻辑错误地将 `violation.fqn` (文件路径) 放入了该列表。我们需要为这种特殊情况添加专门的分支逻辑。

### 目标

1.  修改 `stitcher/app/runners/check/runner.py`，为 `untracked_with_details` 添加特殊的翻译逻辑。
2.  修改 `tests/unit/runners/check/test_check_runner.py`，更新 Mock 对象的注入方式。

### 基本原理

通过修正翻译层的映射逻辑，我们确保了下层的 `Reporter` 能接收到它预期的数据结构，从而修复集成测试中的断言错误。同时，更新单元测试是维护测试套件健康度的基本要求。

### 标签

#intent/fix #flow/ready #priority/high #comp/application #scope/core #ai/instruct #task/domain/testing #task/object/check-runner #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `CheckRunner` 的结果翻译逻辑

我们需要在 `_translate_results` 中拦截 `untracked_with_details` 并进行特殊处理。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
        for violation in analysis_result.violations:
            kind_str = str(violation.kind)

            # 1. Populate legacy result dictionaries
            if kind_str in KIND_TO_LEGACY_MAP:
                category, key = KIND_TO_LEGACY_MAP[kind_str]
                target_dict = getattr(legacy_result, category)
                target_dict[key].append(violation.fqn)

            # 2. Create InteractionContext for resolvable conflicts
~~~~~
~~~~~python.new
        for violation in analysis_result.violations:
            kind_str = str(violation.kind)

            # 1. Populate legacy result dictionaries
            if kind_str in KIND_TO_LEGACY_MAP:
                category, key = KIND_TO_LEGACY_MAP[kind_str]
                target_dict = getattr(legacy_result, category)

                # Special handling for untracked_with_details:
                # The reporter expects a list of symbol keys, which are passed in context['keys'].
                if kind_str == str(L.check.file.untracked_with_details):
                    keys = violation.context.get("keys", [])
                    target_dict[key].extend(keys)
                else:
                    target_dict[key].append(violation.fqn)

            # 2. Create InteractionContext for resolvable conflicts
~~~~~

#### Acts 2: 更新 `test_check_runner.py`

我们需要更新测试以匹配新的构造函数签名（移除 `analyzer`，添加 `differ` 和 `root_path`）。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python
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
from stitcher.app.types import FileCheckResult
from stitcher.spec.interaction import InteractionContext
from stitcher.analysis.schema import FileCheckResult as AnalysisResult, Violation
from needle.pointer import L


def test_check_runner_orchestrates_analysis_and_resolution():
    """
    Verifies that CheckRunner correctly calls its dependencies in order:
    1. Engine (via analyze_batch)
    2. Resolver (auto_reconcile, then resolve_conflicts)
    3. Reporter
    """
    # 1. Arrange: Create autospec'd mocks for all dependencies
    mock_doc_manager = create_autospec(DocumentManagerProtocol, instance=True)
    mock_sig_manager = create_autospec(SignatureManagerProtocol, instance=True)
    mock_fingerprint_strategy = create_autospec(
        FingerprintStrategyProtocol, instance=True
    )
    mock_index_store = create_autospec(IndexStoreProtocol, instance=True)
    mock_differ = create_autospec(DifferProtocol, instance=True)
    mock_resolver = create_autospec(CheckResolverProtocol, instance=True)
    mock_reporter = create_autospec(CheckReporterProtocol, instance=True)

    # Configure mock return values
    mock_modules = [ModuleDef(file_path="src/main.py")]
    
    # Mock Engine behavior: The engine is created internally, so we mock the analyze method
    # indirectly or via mocking the engine attribute after creation if we can't inject it easily.
    # However, create_consistency_engine creates a concrete class. 
    # For unit testing the Runner logic *around* the engine, we can mock the engine instance on the runner.
    
    mock_engine = MagicMock()
    mock_analysis_result = AnalysisResult(
        path="src/main.py",
        violations=[
            Violation(
                kind=L.check.state.signature_drift,
                fqn="func",
                context={}
            )
        ]
    )
    mock_engine.analyze.return_value = mock_analysis_result
    
    mock_resolver.resolve_conflicts.return_value = True
    mock_reporter.report.return_value = True

    # 2. Act: Instantiate the runner
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
    # Inject mock engine
    runner.engine = mock_engine

    # The public API of the runner is `analyze_batch`.
    results, conflicts = runner.analyze_batch(mock_modules)
    
    # Verify translation results
    assert len(results) == 1
    assert results[0].path == "src/main.py"
    assert "func" in results[0].errors["signature_drift"]
    assert len(conflicts) == 1
    assert conflicts[0].violation_type == L.check.state.signature_drift

    # Continue workflow
    runner.auto_reconcile_docs(results, mock_modules)
    resolution_success = runner.resolve_conflicts(results, conflicts)
    report_success = runner.report(results)

    # 3. Assert: Verify the interaction with mocks
    mock_engine.analyze.assert_called_once()
    mock_resolver.auto_reconcile_docs.assert_called_once_with(
        results, mock_modules
    )
    mock_resolver.resolve_conflicts.assert_called_once_with(
        results, conflicts, force_relink=False, reconcile=False
    )
    mock_reporter.report.assert_called_once_with(results)

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
        differ=create_autospec(DifferProtocol),
        resolver=mock_resolver,
        reporter=create_autospec(CheckReporterProtocol),
        root_path=Path("/tmp"),
    )
    mock_results = [FileCheckResult(path="src/main.py")]
    mock_conflicts = [
        InteractionContext(
            file_path="src/main.py",
            fqn="func",
            violation_type=L.check.state.signature_drift,
        )
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

执行完此修复后，`untracked` 相关的测试用例应该会通过。`test_check_runner.py` 也应该通过。

对于 `signature_drift` 相关的集成测试失败（如 `test_check_generates_signature_diff`），如果在修复了上述问题后仍然失败，那可能涉及到 Indexer 数据与 Baseline 数据不一致的问题，我们将需要单独进行深入调查。目前先解决已知的逻辑错误。
