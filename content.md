测试结果仍然显示出大量失败，这表明我们的重构虽然恢复了部分功能，但在处理“静默成功”和“警告”之间的界限时存在逻辑漏洞。特别是，当文档有改进（`doc_improvement`）或仅存在警告（`warning`）时，`run_check` 的行为不符合测试预期。

具体分析如下：
1.  **`is_clean` 属性的逻辑问题**：在 `test_check_state_machine.py` 中，`test_state_synchronized` 失败是因为它检测到了 `check.issue.redundant` 警告。这意味着即使在“同步”状态下，如果代码中保留了 docstring，`check_module` 也会报告 Redundant。这符合预期，但测试断言“无警告”则过于严格，或需要调整以允许 Redundant 警告（这是非阻塞的）。
2.  **`success` vs `success_with_warnings`**：在 `test_state_doc_improvement_auto_reconciled` 和 `test_state_signature_drift_force_relink` 中，测试期望 `success`（完全干净），但实际上可能因为 Redundant 或其他非阻塞性警告而返回 `success_with_warnings`（也是 True，但消息 ID 不同），或者因为 `is_clean` 判断失误导致返回 False。
3.  **Redundant Warning 的干扰**：目前的测试用例中，代码里往往保留了旧的 docstring，这在 `check_module` 看来就是 Redundant。这会污染测试结果，使原本干净的测试变为“带警告的成功”。

我将采取以下措施：
1.  **调整 `FileCheckResult` 逻辑**：确保 `auto_reconciled_count` 不会阻止 `is_clean` 为 True（如果是静默修复的话），或者明确 `run_check` 在有自动修复时的行为。
2.  **优化测试数据**：在需要“干净”状态的测试中，确保代码中的 docstring 已被移除（或与 YAML 完全一致且预期为 Redundant），以避免意外的 Redundant 警告干扰核心逻辑测试。或者，调整断言以接受 Redundant 警告。
3.  **精确断言**：修改测试，允许 `check.run.success` 或 `check.run.success_with_warnings`，只要整体结果 `success` 为 True。

特别是对于 `test_state_synchronized`，如果我们在 `init` 后没有 `strip` 代码中的 docstring，那么 `check` 必然会报 Redundant。这是一个特性而非 Bug。我将修改测试以适应这一行为：在 `init` 后手动清空代码 docstring，或者更新测试以期望 Redundant 警告。为了测试的纯粹性，**清空代码 docstring** 是更好的选择，模拟真实的“文档已迁移”状态。

## [WIP] fix: 修复状态机测试中的 Redundant 干扰与断言逻辑

### 错误分析
1.  **Redundant 干扰**: 在测试 `test_state_synchronized` 等场景中，我们在 `init` 后没有移除代码中的 docstring。因此 `check_module` 正确地报告了 `redundant` 警告。这导致 `is_clean` 为 False，并且测试断言“无警告”失败。
2.  **断言过严**: 测试期望 `check.run.success`，但在有 Redundant 警告时，系统发出的是 `check.run.success_with_warnings`。两者都代表命令执行成功（返回 True），但消息 ID 不同。
3.  **YAML 写入方式**: 在测试中我们简单地用 `json.dumps` 写入 YAML 文件（模拟），但这可能导致格式差异（如缩进），虽然 `YamlAdapter` 能读，但不够严谨。

### 解决方案
1.  **清理测试环境**: 在 `run_init` 后，更新源代码以移除 docstring，模拟真实的“文档分离”状态。这将消除 `redundant` 警告，使我们能专注于测试状态机逻辑。
2.  **更新测试断言**: 在 `test_check_state_machine.py` 中，确保在 `setup` 阶段构造一个“干净”的基线（无 Redundant）。
3.  **统一成功消息**: 确认 `run_check` 的逻辑：如果有 `auto_reconciled`（INFO），这本身不应被视为 Warning，应允许 `success`。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/validation #task/object/state-machine #task/state/end

---
### Script

#### Acts 1: 修正 `test_check_state_machine.py`

我将重写这个文件，确保在每个测试的 `Act` 阶段之前，源代码中的 docstring 都已被移除，从而消除 Redundant 警告的干扰。

~~~~~act
write_file
tests/integration/test_check_state_machine.py
~~~~~
~~~~~python
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
~~~~~

#### Acts 2: 修正 `test_check_signatures.py`

同样地，我们需要在 `test_check_signatures.py` 中移除 docstring，以避免 Redundant 警告导致测试失败（或使用 `success_with_warnings`）。为了保持测试的一致性，我将修改该文件以移除代码中的 docstring。

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

    # 3. Modify Code: Change signature AND remove docstring to avoid Redundant warning
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
    
    # 2. Modify Code: Signature change
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
