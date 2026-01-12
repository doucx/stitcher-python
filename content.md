好的，我们已经完成了核心逻辑和 CLI 的迁移。现在是至关重要的一步：更新测试套件以确保我们的重构是正确且健壮的。

我将生成一个计划，一次性更新所有受影响的测试文件，以反映 `InteractionContext` 的新结构，并确保所有测试断言都使用 `SemanticPointer`。

## [WIP] refactor: 迁移测试用例以使用 violation_type 指针

### 用户需求

根据路线图，需要执行 Phase 3，更新 `stitcher-application` 包中的所有相关单元测试和集成测试。这包括修改 `InteractionContext` 的实例化方式，以及更新所有断言，使其从检查 `conflict_type` (Enum) 变为检查 `violation_type` (`SemanticPointer`)。

### 评论

这是确保重构质量的关键一步。测试是架构的“活文档”，必须与实现保持严格同步。通过更新测试用例，我们不仅能验证迁移的正确性，还能为未来的开发者提供清晰、准确的示例，展示如何与新的、基于 `SemanticPointer` 的冲突处理系统进行交互。

### 目标

1.  在所有测试文件中，将 `InteractionContext` 的实例化从 `conflict_type=` 更新为 `violation_type=`。
2.  在所有测试文件中，将断言逻辑从 `assert context.conflict_type == ConflictType.ENUM` 更新为 `assert context.violation_type == L.pointer.path`。
3.  在所有受影响的测试文件中添加 `from needle.pointer import L` 的导入，并移除不再需要的 `ConflictType` 导入。

### 基本原理

测试文件的修改同样分散且涉及多个方面（导入、对象实例化、断言）。为了确保整个测试套件的修改是一致且原子化的，我将对每一个需要修改的测试文件使用 `write_file` 指令。这可以避免因遗漏某个修改点而导致测试失败或产生误导性结果。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/refactor #task/object/conflict-type #task/action/migration #task/state/continue

---

### Script

#### Acts 1: 修复集成测试 `test_check_interactive_flow.py`

更新交互流程测试，使其断言 `violation_type`。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python
import pytest
import yaml
from typing import List
from stitcher.test_utils import create_test_app
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction
from stitcher.test_utils import WorkspaceFactory, SpyBus, get_stored_hashes
from needle.pointer import L


class MockResolutionHandler(InteractionHandler):
    """A handler that returns a pre-defined sequence of actions."""

    def __init__(self, actions: List[ResolutionAction]):
        self.actions = actions
        self.called_with: List[InteractionContext] = []

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        self.called_with = contexts
        # Return the pre-programmed sequence of actions
        return self.actions * len(contexts) if len(self.actions) == 1 else self.actions


def test_check_workflow_mixed_auto_and_interactive(tmp_path, monkeypatch):
    """
    Ensures that auto-reconciliation and interactive decisions can co-exist
    and are executed correctly in their respective phases.
    """
    factory = WorkspaceFactory(tmp_path)
    # 1. Setup: A module with two functions
    # func_a: will have doc improvement (auto)
    # func_b: will have signature drift (interactive)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/app.py",
            '''
def func_a():
    """Old Doc A."""
    pass
def func_b(x: int):
    """Doc B."""
    pass
''',
        )
        .build()
    )

    app_for_init = create_test_app(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.common.bus"):
        app_for_init.run_init()

    # 2. Trigger Changes
    # Change A: Modify YAML directly (Doc Improvement)
    doc_file = project_root / "src/app.stitcher.yaml"
    doc_file.write_text('func_a: "New Doc A."\nfunc_b: "Doc B."\n', encoding="utf-8")

    # Change B: Modify Source Code (Signature Drift)
    (project_root / "src/app.py").write_text("""
def func_a():
    pass
def func_b(x: str): # int -> str
    pass
""")

    # 3. Define Interactive Decision and inject Handler
    handler = MockResolutionHandler([ResolutionAction.RELINK])
    app = create_test_app(root_path=project_root, interaction_handler=handler)

    # 4. Run Check
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 5. Assertions
    assert success is True
    # Verify Auto-reconcile report for func_a
    doc_updated_msg = next(
        (
            m
            for m in spy_bus.get_messages()
            if m["id"] == str(L.check.state.doc_updated)
        ),
        None,
    )
    assert doc_updated_msg is not None
    assert doc_updated_msg["params"]["key"] == "func_a"

    # Verify Interactive resolution report for func_b
    spy_bus.assert_id_called(L.check.state.relinked, level="success")

    # Verify Hashes are actually updated in storage
    final_hashes = get_stored_hashes(project_root, "src/app.py")

    # func_a should have updated yaml hash
    expected_doc_a_hash = app.doc_manager.compute_yaml_content_hash("New Doc A.")
    assert final_hashes["func_a"]["baseline_yaml_content_hash"] == expected_doc_a_hash

    # func_b should have updated code hash due to RELINK
    assert "baseline_code_structure_hash" in final_hashes["func_b"]
    assert final_hashes["func_b"]["baseline_code_structure_hash"] is not None


@pytest.fixture
def dangling_doc_workspace(tmp_path):
    """Creates a workspace with a doc file containing an extra key."""
    factory = WorkspaceFactory(tmp_path)
    return (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "def func_a(): pass")
        .with_docs(
            "src/app.stitcher.yaml",
            {"func_a": "Doc A.", "dangling_func": "This one is extra."},
        )
        .build()
    )


def test_check_interactive_purge_removes_dangling_doc(
    dangling_doc_workspace, monkeypatch
):
    """
    Verify that choosing [P]urge correctly removes the dangling entry from the YAML file.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Purge'
    handler = MockResolutionHandler([ResolutionAction.PURGE_DOC])
    app = create_test_app(root_path=dangling_doc_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True, "Check should succeed after interactive purge."

    # Assert correct context was passed to handler
    assert len(handler.called_with) == 1
    assert handler.called_with[0].fqn == "dangling_func"
    assert handler.called_with[0].violation_type == L.check.issue.extra

    # Assert correct bus message was sent
    spy_bus.assert_id_called(L.check.state.purged, level="success")

    # Assert YAML file was modified
    doc_file = dangling_doc_workspace / "src/app.stitcher.yaml"
    with doc_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "dangling_func" not in data
    assert "func_a" in data

    # A subsequent check should be clean
    app_verify = create_test_app(root_path=dangling_doc_workspace)
    spy_verify = SpyBus()
    with spy_verify.patch(monkeypatch, "stitcher.common.bus"):
        assert app_verify.run_check() is True
    spy_verify.assert_id_called(L.check.run.success)


def test_check_interactive_skip_dangling_doc_fails(dangling_doc_workspace, monkeypatch):
    """
    Verify that skipping a dangling doc conflict results in a check failure.
    """
    # 1. Arrange: Handler simulates choosing 'Skip'
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=dangling_doc_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False
    spy_bus.assert_id_called(L.check.issue.extra, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")

    # Assert YAML was not changed
    doc_file = dangling_doc_workspace / "src/app.stitcher.yaml"
    with doc_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "dangling_func" in data


def test_check_interactive_purge_deletes_empty_yaml(tmp_path, monkeypatch):
    """
    Verify that if purging the last entry makes the YAML file empty, the file is deleted.
    """
    # 1. Arrange: Workspace with only a dangling doc
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "")
        .with_docs("src/app.stitcher.yaml", {"dangling": "doc"})
        .build()
    )
    doc_file = project_root / "src/app.stitcher.yaml"
    assert doc_file.exists()

    handler = MockResolutionHandler([ResolutionAction.PURGE_DOC])
    app = create_test_app(root_path=project_root, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.state.purged, level="success")
    assert not doc_file.exists(), (
        "YAML file should have been deleted after last entry was purged."
    )


# --- Test Suite for Signature Drift ---


@pytest.fixture
def drift_workspace(tmp_path):
    """Creates a workspace with a signature drift conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "def func(a: int): ...")
        .with_docs("src/app.stitcher.yaml", {"func": "Doc"})
        .build()
    )
    # Run init to create baseline
    app = create_test_app(root_path=project_root)
    app.run_init()
    # Introduce drift
    (project_root / "src/app.py").write_text("def func(a: str): ...")
    return project_root


def test_check_interactive_relink_fixes_drift(drift_workspace, monkeypatch):
    handler = MockResolutionHandler([ResolutionAction.RELINK])
    app = create_test_app(root_path=drift_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    initial_hashes = get_stored_hashes(drift_workspace, "src/app.py")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is True

    spy_bus.assert_id_called(L.check.state.relinked, level="success")

    final_hashes = get_stored_hashes(drift_workspace, "src/app.py")
    assert (
        final_hashes["func"]["baseline_code_structure_hash"]
        != initial_hashes["func"]["baseline_code_structure_hash"]
    )

    # Verify that a subsequent check is clean
    app_verify = create_test_app(root_path=drift_workspace)
    spy_verify = SpyBus()
    with spy_verify.patch(monkeypatch, "stitcher.common.bus"):
        assert app_verify.run_check() is True
    spy_verify.assert_id_called(L.check.run.success)


def test_check_interactive_skip_drift_fails_check(drift_workspace, monkeypatch):
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=drift_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is False

    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


# --- Test Suite for Co-Evolution ---


@pytest.fixture
def co_evolution_workspace(tmp_path):
    """Creates a workspace with a co-evolution conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "def func(a: int): ...")
        .with_docs("src/app.stitcher.yaml", {"func": "Old Doc"})
        .build()
    )
    app = create_test_app(root_path=project_root)
    app.run_init()
    # Introduce co-evolution
    (project_root / "src/app.py").write_text("def func(a: str): ...")
    (project_root / "src/app.stitcher.yaml").write_text('func: "New Doc"')
    return project_root


def test_check_interactive_reconcile_fixes_co_evolution(
    co_evolution_workspace, monkeypatch
):
    handler = MockResolutionHandler([ResolutionAction.RECONCILE])
    app = create_test_app(root_path=co_evolution_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    initial_hashes = get_stored_hashes(co_evolution_workspace, "src/app.py")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is True

    spy_bus.assert_id_called(L.check.state.reconciled, level="success")

    final_hashes = get_stored_hashes(co_evolution_workspace, "src/app.py")
    assert (
        final_hashes["func"]["baseline_code_structure_hash"]
        != initial_hashes["func"]["baseline_code_structure_hash"]
    )
    assert (
        final_hashes["func"]["baseline_yaml_content_hash"]
        != initial_hashes["func"]["baseline_yaml_content_hash"]
    )

    # Verify that a subsequent check is clean
    app_verify = create_test_app(root_path=co_evolution_workspace)
    spy_verify = SpyBus()
    with spy_verify.patch(monkeypatch, "stitcher.common.bus"):
        assert app_verify.run_check() is True
    spy_verify.assert_id_called(L.check.run.success)


def test_check_interactive_skip_co_evolution_fails_check(
    co_evolution_workspace, monkeypatch
):
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=co_evolution_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is False

    spy_bus.assert_id_called(L.check.state.co_evolution, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")
~~~~~

#### Acts 2: 修复集成测试 `test_viewdiff_flow.py`

更新视图差异测试，使其断言 `violation_type`。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_viewdiff_flow.py
~~~~~
~~~~~python
from typing import List
from stitcher.test_utils import create_test_app
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L


class CapturingHandler(InteractionHandler):
    """A handler that captures the contexts passed to it and returns SKIP."""

    def __init__(self):
        self.captured_contexts: List[InteractionContext] = []

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        self.captured_contexts.extend(contexts)
        return [ResolutionAction.SKIP] * len(contexts)


def test_check_generates_signature_diff(tmp_path, monkeypatch):
    """
    Verifies that when a signature changes, 'check' generates a unified diff
    and passes it in the InteractionContext.
    """
    # 1. Arrange: Init project with baseline
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(a: int): ...")
        .build()
    )

    # Run init to save baseline signature and TEXT
    app_init = create_test_app(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.common.bus"):
        app_init.run_init()

    # 2. Modify code to cause signature drift
    (project_root / "src/main.py").write_text("def func(a: str): ...", encoding="utf-8")

    # 3. Run check with capturing handler
    handler = CapturingHandler()
    app_check = create_test_app(root_path=project_root, interaction_handler=handler)

    with SpyBus().patch(monkeypatch, "stitcher.common.bus"):
        app_check.run_check()

    # 4. Assert
    assert len(handler.captured_contexts) == 1
    ctx = handler.captured_contexts[0]

    assert ctx.violation_type == L.check.state.signature_drift
    assert ctx.signature_diff is not None

    # Check for unified diff markers
    assert "--- baseline" in ctx.signature_diff
    assert "+++ current" in ctx.signature_diff
    assert "-def func(a: int):" in ctx.signature_diff
    assert "+def func(a: str):" in ctx.signature_diff


def test_pump_generates_doc_diff(tmp_path, monkeypatch):
    """
    Verifies that when doc content conflicts, 'pump' generates a unified diff
    and passes it in the InteractionContext.
    """
    # 1. Arrange: Project with conflicting docs
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code Doc"""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML Doc"})
        .build()
    )

    # 2. Run pump with capturing handler
    handler = CapturingHandler()
    app_pump = create_test_app(root_path=project_root, interaction_handler=handler)

    with SpyBus().patch(monkeypatch, "stitcher.common.bus"):
        app_pump.run_pump()

    # 3. Assert
    assert len(handler.captured_contexts) == 1
    ctx = handler.captured_contexts[0]

    assert ctx.violation_type == L.check.issue.conflict
    assert ctx.doc_diff is not None

    # Check for unified diff markers
    assert "--- yaml" in ctx.doc_diff
    assert "+++ code" in ctx.doc_diff
    assert "-YAML Doc" in ctx.doc_diff
    assert "+Code Doc" in ctx.doc_diff
~~~~~

#### Acts 3: 修复单元测试 `test_check_analyzer.py`

更新分析器单元测试以使用 `L` 指针进行断言。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/check/test_check_analyzer.py
~~~~~
~~~~~python
from pathlib import Path
from unittest.mock import MagicMock, create_autospec
from typing import Dict

import pytest
from needle.pointer import L

from stitcher.app.runners.check.analyzer import CheckAnalyzer
from stitcher.app.runners.check.protocols import CheckSubject, SymbolState
from stitcher.spec import DifferProtocol


# Test Double: A Fake implementation of the CheckSubject protocol for controlled input.
class FakeCheckSubject(CheckSubject):
    def __init__(
        self, file_path: str, states: Dict[str, SymbolState], is_doc: bool = True
    ):
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
    # Use create_autospec for strict protocol adherence.
    return create_autospec(DifferProtocol, instance=True)


@pytest.fixture
def analyzer(mock_differ: DifferProtocol) -> CheckAnalyzer:
    return CheckAnalyzer(root_path=Path("/test-project"), differ=mock_differ)


def test_analyzer_synchronized_state(analyzer: CheckAnalyzer, monkeypatch):
    """Verify clean state when code, yaml, and baseline are synced."""
    # Mock filesystem to simulate a tracked file
    monkeypatch.setattr(Path, "exists", lambda self: True)

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


def test_analyzer_missing_doc_warning(analyzer: CheckAnalyzer, monkeypatch):
    """Verify warning for public symbol in code but not in YAML."""
    monkeypatch.setattr(Path, "exists", lambda self: True)

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
    assert conflict.violation_type == L.check.state.signature_drift
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
    assert conflicts[0].violation_type == L.check.state.co_evolution
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
    assert conflicts[0].violation_type == L.check.issue.extra


def test_analyzer_untracked_with_details(analyzer: CheckAnalyzer, monkeypatch):
    """
    Verify 'untracked_detailed' warning for an untracked file that has
    undocumented public APIs.
    """
    monkeypatch.setattr(Path, "exists", lambda self: False)

    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=False,
        source_doc_content=None,  # This makes it undocumented
        signature_hash=None,
        baseline_signature_hash=None,
        yaml_content_hash=None,
        baseline_yaml_content_hash=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state}, is_doc=True)

    result, conflicts = analyzer.analyze_subject(subject)

    # The analyzer correctly identifies 'missing' first, then adds 'untracked_detailed'.
    assert result.warning_count == 2
    assert "missing" in result.warnings
    assert "untracked_detailed" in result.warnings
    assert result.warnings["untracked_detailed"] == ["func"]
    assert "untracked" not in result.warnings  # Should not have the simple warning
    assert not conflicts


def test_analyzer_untracked_simple(analyzer: CheckAnalyzer, monkeypatch):
    """
    Verify simple 'untracked' warning for an untracked file where all
    public APIs are already documented in the source code.
    """
    monkeypatch.setattr(Path, "exists", lambda self: False)

    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=False,
        source_doc_content="I have a docstring.",  # This makes it documented
        signature_hash=None,
        baseline_signature_hash=None,
        yaml_content_hash=None,
        baseline_yaml_content_hash=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state}, is_doc=True)

    result, conflicts = analyzer.analyze_subject(subject)

    # In this case, there's no 'missing' doc, only 'pending' and 'untracked'.
    assert result.error_count == 1  # pending
    assert result.warning_count == 1  # untracked
    assert result.errors["pending"] == ["func"]
    assert result.warnings["untracked"] == ["all"]
    assert "untracked_detailed" not in result.warnings
    assert not conflicts
~~~~~

#### Acts 4: 修复单元测试 `test_check_runner.py`

更新运行器单元测试，使用 `violation_type` 实例化 `InteractionContext`。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
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
from needle.pointer import L


def test_check_runner_orchestrates_analysis_and_resolution():
    """
    Verifies that CheckRunner correctly calls its dependencies in order:
    1. Analyzer (via analyze_batch)
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
    mock_analyzer = create_autospec(CheckAnalyzerProtocol, instance=True)
    mock_resolver = create_autospec(CheckResolverProtocol, instance=True)
    mock_reporter = create_autospec(CheckReporterProtocol, instance=True)

    # Configure mock return values
    mock_modules = [ModuleDef(file_path="src/main.py")]
    mock_results = [FileCheckResult(path="src/main.py")]
    mock_conflicts = [
        InteractionContext(
            file_path="src/main.py",
            fqn="func",
            violation_type=L.check.state.signature_drift,
        )
    ]
    # IMPORTANT: The runner calls analyze_subject internally. We mock that.
    mock_analyzer.analyze_subject.return_value = (mock_results[0], mock_conflicts)
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

    # The public API of the runner is `analyze_batch`.
    results, conflicts = runner.analyze_batch(mock_modules)
    runner.auto_reconcile_docs(results, mock_modules)
    resolution_success = runner.resolve_conflicts(results, conflicts)
    report_success = runner.report(results)

    # 3. Assert: Verify the interaction with mocks
    # The runner's `analyze_batch` should have called the analyzer's `analyze_subject`
    mock_analyzer.analyze_subject.assert_called_once()
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

#### Acts 5: 修复单元测试 `test_pump_analyzer.py`

更新 `pump` 分析器测试以断言 `violation_type`。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_analyzer.py
~~~~~
~~~~~python
from unittest.mock import create_autospec, MagicMock

import pytest
from needle.pointer import L

from stitcher.app.runners.pump.analyzer import PumpAnalyzer
from stitcher.spec import (
    DifferProtocol,
    IndexStoreProtocol,
    ModuleDef,
    DocstringIR,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol


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


def test_analyzer_no_changes(
    analyzer: PumpAnalyzer,
    mock_doc_manager: DocumentManagerProtocol,
    mock_index_store: IndexStoreProtocol,
    mock_sig_manager: SignatureManagerProtocol,
):
    """Verify analyzer returns no conflicts if a dirty doc is resolved by hydrate."""
    module = ModuleDef(file_path="src/main.py")

    # Arrange: Simulate a dirty docstring to trigger the hydrate_module call
    mock_symbol = MagicMock()
    mock_symbol.logical_path = "func"
    mock_symbol.docstring_hash = "new_hash"
    mock_index_store.get_symbols_by_file_path.return_value = [mock_symbol]
    mock_sig_manager.load_composite_hashes.return_value = {}  # Baseline is empty

    # Arrange: Configure hydrate_module to report success (no conflicts)
    mock_doc_manager.hydrate_module.return_value = {"success": True, "conflicts": []}
    mock_doc_manager.flatten_module_docs.return_value = {
        "func": DocstringIR(summary="New doc")
    }

    conflicts = analyzer.analyze([module])

    assert not conflicts
    mock_doc_manager.hydrate_module.assert_called_once()


def test_analyzer_detects_conflict(
    analyzer: PumpAnalyzer,
    mock_doc_manager: DocumentManagerProtocol,
    mock_differ: DifferProtocol,
    mock_index_store: IndexStoreProtocol,
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
    assert conflict.violation_type == L.check.issue.conflict
    assert conflict.doc_diff == "diff content"
    mock_differ.generate_text_diff.assert_called_once_with(
        "YAML Doc", "Code Doc", "yaml", "code"
    )
~~~~~

#### Acts 6: 修复单元测试 `test_pump_runner.py`

更新 `pump` 运行器测试，使用 `violation_type` 实例化 `InteractionContext`。

~~~~~act
write_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py
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
from needle.pointer import L


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
        InteractionContext(
            file_path="src/main.py", fqn="func", violation_type=L.check.issue.conflict
        )
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

我们已经成功完成了路线图的第三阶段，整个测试套件现在都已与新的 `violation_type` 契约对齐。这是迈向最终目标的关键一步。

现在，我们准备进入 **Phase 4: 清理与收尾**。这包括从 `stitcher-spec` 中安全地移除已废弃的 `ConflictType` 枚举和相关的 `Resolution` dataclass。这将是本次重构的收官之作，确保我们的代码库中不再有任何历史遗留的痕迹。

如果你同意，我将开始准备执行第四阶段的计划。
