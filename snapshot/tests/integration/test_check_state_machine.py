from textwrap import dedent
from pathlib import Path
import hashlib
import json
from stitcher.app import StitcherApp
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def _get_stored_hashes(project_root: Path, file_path: str) -> dict:
    sig_file = project_root / ".stitcher/signatures" / Path(file_path).with_suffix(".json")
    if not sig_file.exists():
        return {}
    with sig_file.open("r") as f:
        return json.load(f)


def _assert_no_errors_or_warnings(spy_bus: SpyBus):
    errors = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    warnings = [m for m in spy_bus.get_messages() if m["level"] == "warning"]
    assert not errors, f"Unexpected errors: {errors}"
    assert not warnings, f"Unexpected warnings: {warnings}"


def test_state_synchronized(tmp_path, monkeypatch):
    """
    State 1: Synchronized - Code and docs match stored hashes.
    Expected: Silent pass.
    """
    # 1. Arrange: Initial setup
    factory = WorkspaceFactory(tmp_path)
    # Start with code that HAS docstrings so init works
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Docstring."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)

    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # CRITICAL: Remove docstring from code to match "Synchronized" state (Docs in YAML, Code clean)
    # If we don't do this, we get REDUNDANT warning.
    (project_root / "src/module.py").write_text("def func(a: int):\n    pass")

    # Update the stored signature hash because we changed the file content? 
    # NO. Signature hash (compute_fingerprint) explicitly IGNORES docstrings. 
    # So removing docstring does NOT change signature hash. 
    # However, we DO need to ensure the YAML doc matches what we want.
    # init generated YAML with "Docstring.", so we are good.

    # 2. Act: Run check
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert: Should pass cleanly
    assert success is True
    _assert_no_errors_or_warnings(spy_bus)
    spy_bus.assert_id_called(L.check.run.success, level="success")


def test_state_doc_improvement_auto_reconciled(tmp_path, monkeypatch):
    """
    State 2: Documentation Improvement - Signature matches, docstring changed.
    Expected: INFO message, auto-reconcile doc hash, pass.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # Clean code to avoid redundant warning
    (project_root / "src/module.py").write_text("def func(a: int):\n    pass")

    # 2. Modify: Update only the docstring in the YAML file
    # We use YamlAdapter to write to ensure correct formatting if possible, or just mock it carefully
    # Since we are integration testing, we should write valid YAML.
    doc_file = project_root / "src/module.stitcher.yaml"
    # Using simple YAML format
    doc_file.write_text('__doc__: "Module Doc"\nfunc: "New Doc."\n', encoding="utf-8")

    initial_hashes = _get_stored_hashes(project_root, "src/module.py")
    
    # 3. Act: Run check
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 4. Assert: Should pass, report doc improvement
    assert success is True
    # Info message for doc improvement
    spy_bus.assert_id_called(f"[Doc Updated] 'func': Documentation was improved.", level="info")
    # Overall success (Clean pass because infos don't count as warnings)
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["signature_hash"] == initial_hashes["func"]["signature_hash"]
    # Doc hash should be updated
    assert final_hashes["func"]["document_hash"] == hashlib.sha256("New Doc.".encode("utf-8")).hexdigest()


def test_state_signature_drift_error(tmp_path, monkeypatch):
    """
    State 3: Signature Drift - Signature changed, docstring matches stored.
    Expected: ERROR message, check fails.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # Clean code AND modify signature
    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    # 2. Act
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False
    spy_bus.assert_id_called(f"[Signature Drift] 'func': Code changed, docs may be stale.", level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_signature_drift_force_relink(tmp_path, monkeypatch):
    """
    State 3 (Resolved): Signature Drift - Signature changed, docstring matches stored.
    Expected: SUCCESS message, update signature hash, pass.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # Clean code AND modify signature
    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    initial_hashes = _get_stored_hashes(project_root, "src/module.py")

    # 2. Act: Run check with --force-relink
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check(force_relink=True)

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(f"[OK] Re-linked signature for 'func' in src/module.py", level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["signature_hash"] != initial_hashes["func"]["signature_hash"]
    # Doc hash remains same
    assert final_hashes["func"]["document_hash"] == initial_hashes["func"]["document_hash"]


def test_state_co_evolution_error(tmp_path, monkeypatch):
    """
    State 4: Co-evolution - Both signature and docstring changed.
    Expected: ERROR message, check fails.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # Modify signature (and strip code doc)
    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")
    
    # Modify YAML doc
    doc_file = project_root / "src/module.stitcher.yaml"
    doc_file.write_text('__doc__: "Module Doc"\nfunc: "New YAML Doc."\n', encoding="utf-8")

    # 2. Act
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False
    spy_bus.assert_id_called(f"[Co-evolution] 'func': Both code and docs changed; intent unclear.", level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_co_evolution_reconcile(tmp_path, monkeypatch):
    """
    State 4 (Resolved): Co-evolution - Both signature and docstring changed.
    Expected: SUCCESS message, update both hashes, pass.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # Modify signature (and strip code doc)
    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")
    
    # Modify YAML doc
    doc_file = project_root / "src/module.stitcher.yaml"
    doc_file.write_text('__doc__: "Module Doc"\nfunc: "New YAML Doc."\n', encoding="utf-8")

    initial_hashes = _get_stored_hashes(project_root, "src/module.py")

    # 2. Act: Run check with --reconcile
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check(reconcile=True)

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(f"[OK] Reconciled changes for 'func' in src/module.py", level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["signature_hash"] != initial_hashes["func"]["signature_hash"]
    assert final_hashes["func"]["document_hash"] != initial_hashes["func"]["document_hash"]
    # Verify doc hash matches the new content
    assert final_hashes["func"]["document_hash"] == hashlib.sha256("New YAML Doc.".encode("utf-8")).hexdigest()