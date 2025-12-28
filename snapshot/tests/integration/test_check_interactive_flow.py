import pytest
from stitcher.app import StitcherApp
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L

class MockResolutionHandler(InteractionHandler):
    """A handler that returns a pre-defined sequence of actions."""
    def __init__(self, actions: list[ResolutionAction]):
        self.actions = actions
        self.called_with = []

    def process_interactive_session(self, contexts: list[InteractionContext]) -> list[ResolutionAction]:
        self.called_with = contexts
        return self.actions

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
        .with_source("src/app.py", '''
def func_a():
    """Old Doc A."""
    pass
def func_b(x: int):
    """Doc B."""
    pass
''')
        .build()
    )
    
    app = StitcherApp(root_path=project_root)
    app.run_init()

    # 2. Trigger Changes
    # Change A: Modify YAML directly (Doc Improvement)
    doc_file = project_root / "src/app.stitcher.yaml"
    doc_file.write_text('func_a: "New Doc A."\nfunc_b: "Doc B."\n', encoding="utf-8")
    
    # Change B: Modify Source Code (Signature Drift)
    (project_root / "src/app.py").write_text('''
def func_a():
    pass
def func_b(x: str): # int -> str
    pass
''')

    # 3. Define Interactive Decision
    handler = MockResolutionHandler([ResolutionAction.RELINK])
    app.interaction_handler = handler

    # 4. Run Check
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 5. Assertions
    assert success is True
    # Verify Auto-reconcile report
    spy_bus.assert_id_called(L.check.state.doc_updated, level="info")
    # Verify Interactive resolution report
    spy_bus.assert_id_called(L.check.state.relinked, level="success")
    
    # Verify Hashes are actually updated in storage
    from tests.integration.test_check_state_machine import _get_stored_hashes
    final_hashes = _get_stored_hashes(project_root, "src/app.py")
    
    # func_a should have updated yaml hash
    expected_doc_a_hash = app.doc_manager.compute_yaml_content_hash("New Doc A.")
    assert final_hashes["func_a"]["baseline_yaml_content_hash"] == expected_doc_a_hash
    
    # func_b should have updated code hash due to RELINK
    assert final_hashes["func_b"]["baseline_code_structure_hash"] is not None