这是由于我们在之前的 Act 中对 `CheckRunner` 及其数据模型进行了激进的重构，但测试用例仍然停留在旧的“字典模式”导致的。

根据 **ADAP v1.0** 协议，我们现在是在执行“彻底消除兼容层”的过程，测试用例必须同步升级到新的 `Violation` 对象模型。

## [WIP] test(app): 升级 CheckRunner 单元测试以适配新的 Violation 模型

### 错误分析

测试 `test_check_runner.py` 失败的根本原因是：测试代码在 Arrange 阶段混合使用了 `stitcher.app.types.FileCheckResult`（旧字典模型）和 `stitcher.analysis.schema.FileCheckResult`（新对象模型）。在 Assert 阶段，测试代码尝试访问 `.errors` 属性，而这个属性在重构后的 `CheckRunner` 返回的对象中已经不复存在。

### 用户需求

更新 `packages/stitcher-application/tests/unit/runners/check/test_check_runner.py`，移除对旧 `FileCheckResult` 的引用，并根据新的 `Violation` 列表逻辑重写断言。

### 评论

这是一个必要的“测试回归”，确保我们的测试套件与最新的架构契约保持一致。在这次更新中，我们将完全转向基于 `SemanticPointer` 的断言。

### 目标

1.  从测试文件中移除对 `stitcher.app.types.FileCheckResult` 的导入和使用。
2.  将所有 mock 的结果对象统一为 `stitcher.analysis.schema.FileCheckResult` (别名为 `AnalysisResult`)。
3.  更新断言，通过检查 `violations` 列表或 `error_count` 属性来验证分析结果，而不是访问已删除的 `errors` 字典。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/test-check-runner #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 更新 `test_check_runner.py`

我们将重构测试用例，使其完全适配新的 `Violation` 驱动的架构。

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

    # Mock Engine 行为
    mock_engine = MagicMock()
    mock_analysis_result = AnalysisResult(
        path="src/main.py",
        violations=[
            Violation(kind=L.check.state.signature_drift, fqn="func", context={})
        ],
    )
    mock_engine.analyze.return_value = mock_analysis_result

    mock_resolver.resolve_conflicts.return_value = True
    mock_reporter.report.return_value = True

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
    runner.engine = mock_engine

    # 执行分析
    results, conflicts = runner.analyze_batch(mock_modules)

    # 3. Assert: 验证结果
    assert len(results) == 1
    assert results[0].path == "src/main.py"
    
    # 验证违反项是否正确识别
    assert len(results[0].violations) == 1
    assert results[0].violations[0].kind == L.check.state.signature_drift
    assert results[0].error_count == 1 # signature_drift 默认是 error
    
    # 验证交互冲突是否正确提取
    assert len(conflicts) == 1
    assert conflicts[0].violation_type == L.check.state.signature_drift

    # 继续执行工作流
    runner.auto_reconcile_docs(results, mock_modules)
    resolution_success = runner.resolve_conflicts(results, conflicts)
    report_success = runner.report(results)

    # 验证与 mock 的交互
    mock_engine.analyze.assert_called_once()
    mock_resolver.auto_reconcile_docs.assert_called_once_with(results, mock_modules)
    mock_resolver.resolve_conflicts.assert_called_once_with(
        results, conflicts, force_relink=False, reconcile=False
    )
    mock_reporter.report.assert_called_once_with(results)

    assert resolution_success is True
    assert report_success is True


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
    # 使用新的 AnalysisResult
    mock_results = [AnalysisResult(path="src/main.py")]
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

测试用例更新后，你应该再次运行测试以确认修复。如果通过，接下来的工作是：

1.  **清理遗留包引用**: 检查 `packages/stitcher-application/src/stitcher/app/types.py`，如果 `FileCheckResult` 已经不再被任何生产代码使用，应该将其删除，以彻底清除架构中旧时代的痕迹。
2.  **协议同步**: 移除 `packages/stitcher-application/src/stitcher/app/runners/check/protocols.py` 中重复的 `CheckSubject` 协议定义，改为引用 `stitcher.analysis.protocols.AnalysisSubject`。
