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
            Violation(kind=L.check.state.signature_drift, fqn="func", context={})
        ],
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
    mock_resolver.auto_reconcile_docs.assert_called_once_with(results, mock_modules)
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
