## [WIP] fix: 修正集成测试中的哈希计算与断言

### 用户需求
修正 `tests/integration/test_check_state_machine.py` 和 `tests/integration/test_check_signatures.py` 中的错误。
1.  **哈希一致性**: 在测试中，文档哈希的预期值不应硬编码，而应使用 `DocumentManager` 的内部逻辑动态生成，以匹配 `YamlAdapter` 的行为。
2.  **CLI 参数适配**: `test_check_signatures.py` 中过时的 `update_signatures` 参数必须替换为 `force_relink`。
3.  **状态持久化验证**: 确保 `check` 命令在执行 `force_relink` 后真正更新了磁盘上的签名文件。

### 评论
这次修复将解决“测试预期与实现细节不匹配”的问题。特别是对于哈希计算，我们必须承认 `YamlAdapter` 和文件系统读取可能引入微小的格式差异（如结尾换行符），因此在测试中使用生产代码相同的计算路径是唯一可靠的方法。

### 目标
1.  重写 `tests/integration/test_check_state_machine.py`：
    *   引入 `_hash_content` 辅助函数（通过实例化 `DocumentManager`）。
    *   在 `test_state_doc_improvement_auto_reconciled` 中使用该辅助函数计算预期哈希。
2.  重写 `tests/integration/test_check_signatures.py`：
    *   将 `update_signatures=True` 替换为 `force_relink=True`。
    *   确保在修改代码时移除 docstring 以避免 Redundant 干扰。

### 基本原理
通过让测试代码复用应用代码的哈希计算逻辑 (`doc_manager._hash_content`)，我们消除了“硬编码哈希”带来的脆弱性。同时，清理过时的 CLI 参数调用将使测试能够正确运行并验证新的状态机逻辑。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/validation #task/object/state-machine #task/state/end

---
### Script

#### Acts 1: 修正 `tests/integration/test_check_state_machine.py`

重点修复 `test_state_doc_improvement_auto_reconciled` 中的哈希断言，并确保所有测试在修改代码时都处于干净状态（无 Redundant 警告）。

~~~~~act
write_file
tests/integration/test_check_state_machine.py
~~~~~
~~~~~python
from textwrap import dedent
from pathlib import Path
import json
import hashlib
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

    # CRITICAL: Remove docstring from code to match "Synchronized" state
    (project_root / "src/module.py").write_text("def func(a: int):\n    pass")

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is True
    _assert_no_errors_or_warnings(spy_bus)
    spy_bus.assert_id_called(L.check.run.success, level="success")


def test_state_doc_improvement_auto_reconciled(tmp_path, monkeypatch):
    """
    State 2: Documentation Improvement - Signature matches, docstring changed.
    Expected: INFO message, auto-reconcile doc hash, pass.
    """
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

    # Modify YAML
    doc_file = project_root / "src/module.stitcher.yaml"
    # Note: YamlAdapter by default uses block style. When we manually write,
    # we simulate an external edit.
    new_doc_content = "New Doc."
    doc_file.write_text(f'__doc__: "Module Doc"\nfunc: "{new_doc_content}"\n', encoding="utf-8")
    
    initial_hashes = _get_stored_hashes(project_root, "src/module.py")
    
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is True
    spy_bus.assert_id_called(f"[Doc Updated] 'func': Documentation was improved.", level="info")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["signature_hash"] == initial_hashes["func"]["signature_hash"]
    
    # Use app's logic to calculate expected hash
    # We rely on DocumentManager._hash_content.
    expected_hash = app.doc_manager._hash_content(new_doc_content)
    assert final_hashes["func"]["document_hash"] == expected_hash


def test_state_signature_drift_error(tmp_path, monkeypatch):
    """
    State 3: Signature Drift - Signature changed, docstring matches stored.
    Expected: ERROR message, check fails.
    """
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

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(f"[Signature Drift] 'func': Code changed, docs may be stale.", level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_signature_drift_force_relink(tmp_path, monkeypatch):
    """
    State 3 (Resolved): Signature Drift - Signature changed, docstring matches stored.
    Expected: SUCCESS message, update signature hash, pass.
    """
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

    # Act: Run check with --force-relink
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check(force_relink=True)

    assert success is True
    spy_bus.assert_id_called(f"[OK] Re-linked signature for 'func' in src/module.py", level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    
    # Assert signature hash updated
    assert final_hashes["func"]["signature_hash"] != initial_hashes["func"]["signature_hash"]
    # Doc hash remains same
    assert final_hashes["func"]["document_hash"] == initial_hashes["func"]["document_hash"]


def test_state_co_evolution_error(tmp_path, monkeypatch):
    """
    State 4: Co-evolution - Both signature and docstring changed.
    Expected: ERROR message, check fails.
    """
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

    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(f"[Co-evolution] 'func': Both code and docs changed; intent unclear.", level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_co_evolution_reconcile(tmp_path, monkeypatch):
    """
    State 4 (Resolved): Co-evolution - Both signature and docstring changed.
    Expected: SUCCESS message, update both hashes, pass.
    """
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
    new_doc_content = "New YAML Doc."
    doc_file.write_text(f'__doc__: "Module Doc"\nfunc: "{new_doc_content}"\n', encoding="utf-8")

    initial_hashes = _get_stored_hashes(project_root, "src/module.py")

    # Act: Run check with --reconcile
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check(reconcile=True)

    assert success is True
    spy_bus.assert_id_called(f"[OK] Reconciled changes for 'func' in src/module.py", level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = _get_stored_hashes(project_root, "src/module.py")
    assert final_hashes["func"]["signature_hash"] != initial_hashes["func"]["signature_hash"]
    assert final_hashes["func"]["document_hash"] != initial_hashes["func"]["document_hash"]
    
    expected_doc_hash = app.doc_manager._hash_content(new_doc_content)
    assert final_hashes["func"]["document_hash"] == expected_doc_hash
~~~~~

#### Acts 2: 修正 `tests/integration/test_check_signatures.py`

替换过时的 `update_signatures` 参数，使用 `force_relink`。

~~~~~act
write_file
tests/integration/test_check_signatures.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.app import StitcherApp
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def _assert_no_errors(spy_bus):
    errors = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not errors, f"Unexpected errors: {errors}"


def test_check_detects_signature_change(tmp_path, monkeypatch):
    """
    End-to-End test verifying that modifying a function signature
    triggers a check failure/warning.
    """
    # 1. Setup Initial Workspace
    factory = WorkspaceFactory(tmp_path)
    initial_code = dedent("""
    def process(value: int) -> int:
        \"\"\"Process an integer.\"\"\"
        return value * 2
    """).strip()

    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/processor.py", initial_code)
        .build()
    )

    app = StitcherApp(root_path=project_root)

    # 2. Run Init (Baseline)
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    _assert_no_errors(spy_bus)
    spy_bus.assert_id_called(L.init.run.complete, level="success")

    # 3. Modify Code: Change signature AND remove docstring
    modified_code = dedent("""
    def process(value: str) -> int:
        return len(value) * 2
    """).strip()
    (project_root / "src/processor.py").write_text(modified_code, encoding="utf-8")

    # 4. Run Check
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 5. Assertions
    assert success is False, "Check passed but should have failed due to signature mismatch"
    msg = f"[Signature Drift] 'process': Code changed, docs may be stale."
    spy_bus.assert_id_called(msg, level="error")


def test_generate_does_not_update_signatures(tmp_path, monkeypatch):
    """
    Verify that running 'generate' is now pure and DOES NOT update the signature baseline.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(a: int): ...")
        .with_docs("src/main.stitcher.yaml", {"func": "doc"})
        .build()
    )
    app = StitcherApp(root_path=project_root)

    # 1. Run Init to set baseline
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()
    
    # 2. Modify Code
    (project_root / "src/main.py").write_text("def func(a: str): ...")

    # 3. Run Generate
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    # 4. Run Check - it should now FAIL because generate did not update anything.
    spy_bus_check = SpyBus()
    with spy_bus_check.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert not success, "Check passed, but it should have failed."
    msg = f"[Signature Drift] 'func': Code changed, docs may be stale."
    spy_bus_check.assert_id_called(msg, level="error")


def test_check_with_force_relink_reconciles_changes(tmp_path, monkeypatch):
    """
    Verify the complete workflow of reconciling signature changes with `check --force-relink`.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func(a: int):\n    """Doc."""\n    ...')
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # 2. Modify: Change signature, remove doc to be clean
    (project_root / "src/main.py").write_text("def func(a: str):\n    ...")

    # 3. Act I: Run check with the --force-relink flag
    spy_bus_reconcile = SpyBus()
    with spy_bus_reconcile.patch(monkeypatch, "stitcher.app.core.bus"):
        success_reconcile = app.run_check(force_relink=True)

    # 4. Assert I
    assert success_reconcile is True, "Check with --force-relink failed"
    spy_bus_reconcile.assert_id_called(f"[OK] Re-linked signature for 'func' in src/main.py", level="success")
    
    # 5. Act II: Run a normal check again to verify the baseline was updated
    spy_bus_verify = SpyBus()
    with spy_bus_verify.patch(monkeypatch, "stitcher.app.core.bus"):
        success_verify = app.run_check()

    # 6. Assert II
    assert success_verify is True, "Verification check failed after reconciliation"
    spy_bus_verify.assert_id_called(L.check.run.success, level="success")
~~~~~
