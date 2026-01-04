好的，我们来为 `check` 命令添加全面的交互式回归测试，以防止未来出现类似的问题。

我将遵循我们刚刚建立的 `Mock Handler` 模式，为 `check` 命令处理的两种核心交互式冲突（`SIGNATURE_DRIFT` 和 `CO_EVOLUTION`）创建完整的测试用例。这包括验证用户选择“修复”和“跳过”两种情况下的系统行为。

## [WIP] test(app): 添加 check 命令的交互式回归测试

### 用户需求
为 `check` 命令添加交互式回归测试，覆盖所有核心冲突场景（如签名漂移、协同演进），确保在用户做出不同选择（修复或跳过）时，系统状态能正确变更。

### 评论
这是巩固 CLI 稳定性的关键一步。通过为 `check` 命令的交互式状态机添加全面的测试，我们可以确保这个核心用户工作流的行为是可预测且健壮的，有效防止未来的代码变更破坏这些复杂的交互逻辑。

### 目标
1.  **扩展 `test_check_interactive_flow.py`**: 在现有的测试文件中添加新的测试用例。
2.  **测试 `SIGNATURE_DRIFT`**:
    *   添加测试验证用户选择 `RELINK` (修复) 后，签名漂移被解决。
    *   添加测试验证用户选择 `SKIP` (跳过) 后，检查失败并报告错误。
3.  **测试 `CO_EVOLUTION`**:
    *   添加测试验证用户选择 `RECONCILE` (修复) 后，协同演进冲突被解决。
    *   添加测试验证用户选择 `SKIP` (跳过) 后，检查失败并报告错误。
4.  **验证状态持久化**: 所有“修复”场景的测试都必须断言 `.stitcher/signatures` 文件中的哈希值被正确更新。

### 基本原理
我们将创建多个 `pytest.fixture` 来精确模拟导致特定冲突（签名漂移、协同演进）的项目状态。然后，通过注入一个预设好行为的 `MockResolutionHandler`，我们可以模拟用户的交互选择。

断言将分为两部分：
1.  **行为验证**: 使用 `SpyBus` 确认系统发出了正确的语义消息（例如 `L.check.state.relinked`）。
2.  **状态验证**: 直接读取 `.stitcher/signatures/*.json` 文件，确认底层的状态数据已被正确、持久地修改。

这种“行为+状态”的双重验证确保了测试的完整性和可靠性。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/tests #comp/runtime #scope/core
#ai/instruct
#task/domain/testing #task/object/check-command #task/action/add-regression-tests
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 为 `check` 命令添加交互测试

我们将向 `packages/stitcher-application/tests/integration/test_check_interactive_flow.py` 文件中追加新的测试场景。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
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
        .with_source("src/app.py", 'def func(a: int): ...')
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
        .with_source("src/app.py", 'def func(a: int): ...')
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

### 下一步建议
我们已经为 `check` 命令添加了全面的交互式回归测试。

1.  **运行测试**: 请运行 `pytest packages/stitcher-application/tests/integration/test_check_interactive_flow.py` 确保所有新旧测试都能通过。
2.  **创建提交**: 测试通过后，我将为你生成一个 `[COMMIT]` 计划，将这些重要的测试固化到代码库中。
