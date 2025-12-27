Excellent. It's crucial to update the tests to validate our refactoring, ensuring the new behavior is correct and preventing future regressions.

I will now generate a plan to update the integration tests. This plan will focus on two key areas:
1.  Verifying the new `check --update-signatures` workflow.
2.  Ensuring that `extra` (dangling) docstrings are correctly reported as non-blocking warnings.

## [WIP] test(integration): Update tests for signature reconciliation and policy changes

### 用户需求
更新集成测试套件，以验证 `check` 命令的新功能和策略变更：
1.  添加测试用例来覆盖 `check --update-signatures` 的完整工作流。
2.  修改现有测试，以确认 `extra` (dangling) 文档定义现在被视为警告（Warning），而不是阻塞性错误（Error）。
3.  移除或修改因 `generate` 命令不再更新签名而失效的旧测试。

### 评论
这是一次至关重要的测试更新。通过为新功能添加专门的验证场景，我们不仅能确保代码按预期工作，还能将这些测试用例作为新功能的“活文档”。同时，调整策略相关的测试可以锁定新的行为（例如，`extra` 只是警告），防止未来不经意的改动破坏我们精心设计的开发者体验。

### 目标
1.  **修改 `tests/integration/test_check_signatures.py`**:
    -   删除过时的 `test_generate_updates_signatures` 测试，因为它验证的是现已移除的功能。
    -   添加一个新的测试 `test_check_with_update_signatures_flag_reconciles_changes`，该测试将模拟从“代码变更”到“运行 `check --update-signatures`”再到“确认同步”的完整生命周期。
2.  **修改 `tests/integration/test_check_policy.py`**:
    -   更新 `test_ghost_keys_trigger_extra_error` 测试，将其断言逻辑从验证“失败”和“错误”改为验证“成功”和“警告”。

### 基本原理
我们将通过精确的 `patch_file` 操作来更新测试代码。对于 `test_check_signatures.py`，我们将首先移除一个现在完全错误的测试用例，然后在其原位置注入一个全新的、更全面的测试用例。对于 `test_check_policy.py`，我们将直接修改现有测试的断言部分，使其与 `check` 命令的新策略保持一致。这些修改将确保我们的测试套件能够准确反映并保护我们刚刚完成的重构工作。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/cli #task/object/check-command #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新签名检查相关的测试

首先，我们处理 `test_check_signatures.py`。我们将删除旧的、不正确的测试，并添加一个验证新工作流的测试。

~~~~~act
patch_file
tests/integration/test_check_signatures.py
~~~~~
~~~~~python.old
def test_generate_updates_signatures(tmp_path, monkeypatch):
    """
    Verify that running 'generate' updates the signature baseline.
    """
    # 1. Setup Workspace
    factory = WorkspaceFactory(tmp_path)
    # Simple one-liner to avoid any parsing ambiguity
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(a: int): ...")
        .with_docs("src/main.stitcher.yaml", {"func": "doc"})
        .build()
    )

    app = StitcherApp(root_path=project_root)

    # 2. Run Init
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # 3. Modify Code
    (project_root / "src/main.py").write_text("def func(a: str): ...", encoding="utf-8")

    # 4. Run Generate (Should update signatures)
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    _assert_no_errors(spy_bus)
    spy_bus.assert_id_called(L.generate.run.complete, level="success")

    # Verify fingerprint file timestamp or content?
    # Better to verify via Check.

    # 5. Run Check (Should now pass)
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    assert success is True, "Check failed but should have passed after Generate"
    spy_bus.assert_id_called(L.check.run.success, level="success")
~~~~~
~~~~~python.new
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
    spy_bus_check.assert_id_called(L.check.issue.mismatch, level="error")


def test_check_with_update_signatures_flag_reconciles_changes(tmp_path, monkeypatch):
    """
    Verify the complete workflow of reconciling signature changes with `check --update-signatures`.
    """
    # 1. Arrange: Setup and Init to establish a baseline
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(a: int): ...")
        .build()
    )
    app = StitcherApp(root_path=project_root)
    with SpyBus().patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_init()

    # 2. Modify the code to create a signature mismatch
    (project_root / "src/main.py").write_text("def func(a: str): ...")

    # 3. Act I: Run check with the --update-signatures flag
    spy_bus_reconcile = SpyBus()
    with spy_bus_reconcile.patch(monkeypatch, "stitcher.app.core.bus"):
        success_reconcile = app.run_check(update_signatures=True)

    # 4. Assert I: The reconciliation check should succeed and report the update
    assert success_reconcile is True, "Check with --update-signatures failed"
    spy_bus_reconcile.assert_id_called(L.check.run.signatures_updated, level="success")
    # Crucially, it should NOT have reported a mismatch error
    mismatch_errors = [
        m for m in spy_bus_reconcile.get_messages() if m["id"] == str(L.check.issue.mismatch)
    ]
    assert not mismatch_errors, "Mismatch error was reported during reconciliation"

    # 5. Act II: Run a normal check again to verify the baseline was updated
    spy_bus_verify = SpyBus()
    with spy_bus_verify.patch(monkeypatch, "stitcher.app.core.bus"):
        success_verify = app.run_check()

    # 6. Assert II: The verification check should now pass cleanly
    assert success_verify is True, "Verification check failed after reconciliation"
    spy_bus_verify.assert_id_called(L.check.run.success, level="success")
~~~~~

#### Acts 2: 更新策略检查相关的测试

现在，我们修改 `test_check_policy.py` 来验证 `extra` 问题现在是警告级别。

~~~~~act
patch_file
tests/integration/test_check_policy.py
~~~~~
~~~~~python.old
def test_ghost_keys_trigger_extra_error(tmp_path, monkeypatch):
    """
    Policy Test: Keys in YAML that do not exist in code (even privately)
    MUST trigger EXTRA error.
    """
    # 1. Arrange: Docs pointing to non-existent code
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/ghost.py", "def real(): pass")
        .with_docs(
            "src/ghost.stitcher.yaml",
            {
                "real": "Exists",
                "ghost_func": "Does not exist",
                "_ghost_private": "Does not exist either",
            },
        )
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False

    # We expect EXTRA errors for both ghost keys
    spy_bus.assert_id_called(L.check.issue.extra, level="error")

    # Verify specific keys
    extra_msgs = [
        m for m in spy_bus.get_messages() if m["id"] == str(L.check.issue.extra)
    ]
    keys = sorted([m["params"]["key"] for m in extra_msgs])
    assert keys == ["_ghost_private", "ghost_func"]
~~~~~
~~~~~python.new
def test_ghost_keys_trigger_extra_warning(tmp_path, monkeypatch):
    """
    Policy Test: Keys in YAML that do not exist in code should trigger
    a non-blocking EXTRA warning.
    """
    # 1. Arrange: Docs pointing to non-existent code
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/ghost.py", "def real(): pass")
        .with_docs(
            "src/ghost.stitcher.yaml",
            {
                "real": "Exists",
                "ghost_func": "Does not exist",
                "_ghost_private": "Does not exist either",
            },
        )
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True, "Check should pass even with EXTRA warnings."

    # We expect EXTRA warnings for both ghost keys
    spy_bus.assert_id_called(L.check.issue.extra, level="warning")
    spy_bus.assert_id_called(L.check.run.success_with_warnings, level="success")

    # Verify specific keys
    extra_msgs = [
        m for m in spy_bus.get_messages() if m["id"] == str(L.check.issue.extra)
    ]
    keys = sorted([m["params"]["key"] for m in extra_msgs])
    assert keys == ["_ghost_private", "ghost_func"]
~~~~~

### 下一步建议
我们已经成功地重构了核心逻辑并更新了测试以验证新行为。现在，所有相关的代码和测试都已同步。

是时候将这些变更作为一个完整的逻辑单元提交了。我将生成一个 `[COMMIT]` 计划，其中包含 `git add` 和 `git commit` 指令，并提供一份清晰的提交信息。
