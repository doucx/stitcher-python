好的，我来修复这些由于 `hydrate`/`eject` 重构为 `pump`/`inject` 导致的测试失败。

## [WIP] 迁移所有相关的测试文件，以匹配新的方法名和行为

### 错误分析
测试失败的原因很明确：
1.  所有调用 `app.run_hydrate()` 的测试都失败了，因为该方法已被重命名为 `app.run_pump()`。
2.  调用 `app.run_eject()` 的测试失败了，因为该方法已被重命名为 `app.run_inject()`。
3.  `run_pump()` 的返回值和附带的消息总线事件也需要同步更新。

### 目标
1.  将所有与 `hydrate` 相关的测试文件重命名为 `pump`。
2.  更新这些测试文件中的方法调用、返回值检查和消息总线断言。
3.  更新生命周期测试以使用 `run_inject`。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #ai/instruct #task/domain/cli #task/object/command-pump #task/action/rename-and-refactor #task/state/continue

---

### Script

#### Acts 1: 迁移 `test_hydrate_command.py`

我们将 `test_hydrate_command.py` 重命名为 `test_pump_command.py`，并更新其内容以使用新的 API。

~~~~~act
move_file
packages/stitcher-application/tests/integration/test_hydrate_command.py
packages/stitcher-application/tests/integration/test_pump_command.py
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_pump_command.py
~~~~~
~~~~~python
import yaml
from stitcher.app import StitcherApp
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_pump_adds_new_docs_to_yaml(tmp_path, monkeypatch):
    """Scenario 1: Normal Pumping"""
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """New doc."""\n    pass')
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump()

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.file.success, level="success")
    spy_bus.assert_id_called(L.pump.run.complete, level="success")

    doc_path = project_root / "src/main.stitcher.yaml"
    assert doc_path.exists()
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "New doc."


def test_pump_fails_on_conflict(tmp_path, monkeypatch):
    """Scenario 2: Conflict Detection"""
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code doc."""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML doc"})
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump()

    # Assert
    assert result.success is False
    spy_bus.assert_id_called(L.pump.error.conflict, level="error")
    spy_bus.assert_id_called(L.pump.run.conflict, level="error")

    # Verify YAML was NOT changed
    doc_path = project_root / "src/main.stitcher.yaml"
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "YAML doc"


def test_pump_force_overwrites_conflict(tmp_path, monkeypatch):
    """Scenario 3: Force Overwrite"""
    # Arrange (same as conflict test)
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code doc."""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML doc"})
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump(force=True)

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.file.success, level="success")

    # Verify YAML was changed
    doc_path = project_root / "src/main.stitcher.yaml"
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "Code doc."


def test_pump_with_strip_removes_source_doc(tmp_path, monkeypatch):
    """Scenario 4: Strip Integration"""
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    source_path = "src/main.py"
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, 'def func():\n    """New doc."""\n    pass')
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump(strip=True)

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.file.success)
    spy_bus.assert_id_called(L.strip.file.success)
    spy_bus.assert_id_called(L.strip.run.complete)

    # Verify source was stripped
    final_code = (project_root / source_path).read_text()
    assert '"""' not in final_code


def test_pump_reconcile_ignores_source_conflict(tmp_path, monkeypatch):
    """Scenario 5: Reconcile (YAML-first) Mode"""
    # Arrange (same as conflict test)
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code doc."""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML doc"})
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump(reconcile=True)

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.info.reconciled, level="info")

    # Verify no errors were raised
    error_msgs = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not error_msgs

    # Verify YAML was NOT changed
    doc_path = project_root / "src/main.stitcher.yaml"
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "YAML doc"
~~~~~

#### Acts 2: 迁移 `test_hydrate_interactive_flow.py`

同样地，重命名并更新交互式流程测试。

~~~~~act
move_file
packages/stitcher-application/tests/integration/test_hydrate_interactive_flow.py
packages/stitcher-application/tests/integration/test_pump_interactive_flow.py
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_pump_interactive_flow.py
~~~~~
~~~~~python
import pytest
from typing import List
from stitcher.app import StitcherApp
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L


class MockResolutionHandler(InteractionHandler):
    """A handler that returns a pre-defined sequence of actions for testing."""

    def __init__(self, actions: List[ResolutionAction]):
        self.actions = actions
        self.called_with: List[InteractionContext] = []

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        self.called_with = contexts
        # Return the same action for all conflicts if only one is provided
        if len(self.actions) == 1:
            return self.actions * len(contexts)
        return self.actions


@pytest.fixture
def conflicting_workspace(tmp_path):
    """Creates a workspace with a doc content conflict."""
    factory = WorkspaceFactory(tmp_path)
    return (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", 'def func():\n    """Code Doc"""')
        .with_docs("src/app.stitcher.yaml", {"func": "YAML Doc"})
        .build()
    )


def test_pump_interactive_overwrite(conflicting_workspace, monkeypatch):
    """
    Verify that choosing [F]orce-hydrate (HYDRATE_OVERWRITE) correctly
    updates the YAML file with the content from the source code.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Force-hydrate'
    handler = MockResolutionHandler([ResolutionAction.HYDRATE_OVERWRITE])
    app = StitcherApp(root_path=conflicting_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is True, "Pumping should succeed after interactive resolution."
    spy_bus.assert_id_called(L.pump.file.success, level="success")

    # Verify file content was updated
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "Code Doc" in content
    assert "YAML Doc" not in content


def test_pump_interactive_reconcile(conflicting_workspace, monkeypatch):
    """
    Verify that choosing [R]econcile (HYDRATE_KEEP_EXISTING) preserves
    the existing content in the YAML file.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Reconcile'
    handler = MockResolutionHandler([ResolutionAction.HYDRATE_KEEP_EXISTING])
    app = StitcherApp(root_path=conflicting_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.info.reconciled, level="info")
    spy_bus.assert_id_called(L.pump.run.no_changes, level="info")

    # Verify file content was NOT changed
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "YAML Doc" in content
    assert "Code Doc" not in content


def test_pump_interactive_skip_leads_to_failure(conflicting_workspace, monkeypatch):
    """
    Verify that choosing [S]kip leaves the conflict unresolved and causes
    the command to fail.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Skip'
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = StitcherApp(root_path=conflicting_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is False, "Pumping should fail if conflicts are skipped."
    spy_bus.assert_id_called(L.pump.error.conflict, level="error")
    spy_bus.assert_id_called(L.pump.run.conflict, level="error")

    # Verify file content was NOT changed
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "YAML Doc" in content


def test_pump_interactive_abort_stops_process(conflicting_workspace, monkeypatch):
    """
    Verify that choosing [A]bort stops the pumping and fails the command.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Abort'
    handler = MockResolutionHandler([ResolutionAction.ABORT])
    app = StitcherApp(root_path=conflicting_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is False
    # Assert that the correct semantic 'aborted' message was sent.
    spy_bus.assert_id_called(L.pump.run.aborted, level="error")

    # Verify file content was NOT changed
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "YAML Doc" in content
~~~~~

#### Acts 3: 迁移 `test_hydrate_regression.py`

重命名并更新回归测试。

~~~~~act
move_file
packages/stitcher-application/tests/integration/test_hydrate_regression.py
packages/stitcher-application/tests/integration/test_pump_regression.py
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_pump_regression.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L


def test_pump_does_not_rewrite_synced_legacy_signatures(tmp_path: Path, monkeypatch):
    """
    Regression Test: Verifies that `pump` does not rewrite signature files
    when they are in sync but use a legacy key schema.

    Problem: `hydrate` was rewriting files because it didn't recognize the old
    `code_structure_hash` key, causing unnecessary git changes even when
    no docstrings were hydrated.
    """
    # 1. Arrange: Create a project and initialize it to get a baseline.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func(a: int):\n    """Doc."""')
        .build()
    )

    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # 2. Arrange: Manually convert the signature file to the legacy format.
    # This simulates the state of the project before the key name change.
    sig_file_path = project_root / ".stitcher/signatures/src/main.json"
    with sig_file_path.open("r") as f:
        data = json.load(f)

    # Convert to legacy format: baseline_code_structure_hash -> code_structure_hash
    legacy_data = {}
    for fqn, hashes in data.items():
        legacy_data[fqn] = {
            "code_structure_hash": hashes.get("baseline_code_structure_hash"),
            "yaml_content_hash": hashes.get("baseline_yaml_content_hash"),
        }
    with sig_file_path.open("w") as f:
        json.dump(legacy_data, f)

    # The project is now in a "synchronized" state, but with a legacy signature file.
    # We also strip the source docstring to ensure pump has nothing to do.
    (project_root / "src/main.py").write_text("def func(a: int): ...")

    spy_bus = SpyBus()

    # 3. Act: Run the pump command.
    # Because the signature file contains legacy keys ('code_structure_hash'),
    # the strict Fingerprint validation should fail, treating the file as corrupted/empty.
    # Pump will then treat the code as "new" and regenerate the signatures with
    # correct keys ('baseline_code_structure_hash').
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        result = app.run_pump()

    # 4. Assert
    data_after = json.loads(sig_file_path.read_text())

    assert result.success is True

    # Verify the new schema is present for the function
    fp_func = data_after.get("func", {})
    assert "baseline_code_structure_hash" in fp_func, (
        "New schema key 'baseline_code_structure_hash' missing."
    )
    assert "code_structure_hash" not in fp_func, (
        "Legacy schema key 'code_structure_hash' was not removed."
    )

    # Even though we migrated signatures, no docs were pumped, so user sees "no changes"
    # in terms of docstring updates.
    spy_bus.assert_id_called(L.pump.run.no_changes, level="info")
~~~~~

#### Acts 4: 修复 `test_lifecycle_commands.py`

最后，修复 `eject` 测试。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_lifecycle_commands.py
~~~~~
~~~~~python.old
def test_eject_command_injects_docstrings(tmp_path, monkeypatch):
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    source_path = "src/main.py"
    initial_code = "def func(): pass"
    docs_data = {"func": "Injected docstring."}

    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, initial_code)
        .with_docs("src/main.stitcher.yaml", docs_data)
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_eject()

    # Assert
    final_code = (project_root / source_path).read_text()
    assert '"""Injected docstring."""' in final_code

    spy_bus.assert_id_called(L.eject.file.success)
    spy_bus.assert_id_called(L.eject.run.complete)
~~~~~
~~~~~python.new
def test_inject_command_injects_docstrings(tmp_path, monkeypatch):
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    source_path = "src/main.py"
    initial_code = "def func(): pass"
    docs_data = {"func": "Injected docstring."}

    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, initial_code)
        .with_docs("src/main.stitcher.yaml", docs_data)
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_inject()

    # Assert
    final_code = (project_root / source_path).read_text()
    assert '"""Injected docstring."""' in final_code

    spy_bus.assert_id_called(L.inject.file.success)
    spy_bus.assert_id_called(L.inject.run.complete)
~~~~~
