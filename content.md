[简要回答]
我们将修正集成测试和单元测试，以适配 `init` 命令的返回值变更以及 `PumpExecutor` 在调和模式下主动更新指纹的逻辑修正。

## [WIP] fix: 适配 PumpExecutor 指纹逻辑变更并修正测试

### 用户需求
修复由于核心逻辑变更导致的测试失败：
1. `test_init_extracts_docs_to_yaml`: `init` 命令不再返回文件列表，需改为断言文件存在。
2. `test_execution_planner`: 单元测试需更新，以反映“调和模式下更新指纹”这一预期行为。

### 评论
这些测试失败实际上验证了我们的修改生效了（行为发生了改变），只是测试本身过时了。特别是 `PumpExecutor` 的单元测试，现在必须断言 `update_doc_fingerprint` 为 `True`，这正是修复指纹缺失问题的关键。

### 目标
1. 修改 `test_init_command.py`，不再依赖 `run_init` 的返回值。
2. 更新 `test_execution_planner.py`，将 `HYDRATE_KEEP_EXISTING` 场景下的 `update_doc_fingerprint` 预期值改为 `True`。

### 基本原理
测试应反映系统的预期行为。既然我们明确决定在 `HYDRATE_KEEP_EXISTING`（调和）模式下更新指纹以修复基线漂移问题，那么断言该标志为 `False` 的旧测试就必须更新。同理，`run_init` 现在的实现是委托给 `run_pump`，其返回值行为已改变，测试应适配。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/test-suite #task/action/update #task/state/continue

---

### Script

#### Acts 1: 修正 init 命令集成测试

不再断言返回值，而是直接检查文件系统状态。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_init_command.py
~~~~~
~~~~~python.old
    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        created_files = app.run_init()

    # 3. Assert
    expected_yaml = project_root / "src/main.stitcher.yaml"
    assert expected_yaml in created_files

    content = expected_yaml.read_text()
~~~~~
~~~~~python.new
    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    # 3. Assert
    expected_yaml = project_root / "src/main.stitcher.yaml"
    assert expected_yaml.exists()

    content = expected_yaml.read_text()
~~~~~

#### Acts 2: 更新 PumpExecutor 单元测试预期

将 `HYDRATE_KEEP_EXISTING` 场景下的 `update_doc_fingerprint` 断言改为 `True`。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_execution_planner.py
~~~~~
~~~~~python.old
def test_plan_for_keep_existing_with_strip(executor, sample_module):
    """Scenario: YAML-first (`HYDRATE_KEEP_EXISTING`) + strip requested."""
    decisions = {"func_a": ResolutionAction.HYDRATE_KEEP_EXISTING}
    source_docs = executor.doc_manager.flatten_module_docs(sample_module)
    plan = executor._generate_execution_plan(
        sample_module, decisions, strip_requested=True, source_docs=source_docs
    )

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is False
    assert p_a.update_doc_fingerprint is False
    assert p_a.strip_source_docstring is True
    assert p_a.update_code_fingerprint is True


def test_plan_for_keep_existing_without_strip(executor, sample_module):
    """Scenario: YAML-first (`HYDRATE_KEEP_EXISTING`) + no strip requested."""
    decisions = {"func_a": ResolutionAction.HYDRATE_KEEP_EXISTING}
    source_docs = executor.doc_manager.flatten_module_docs(sample_module)
    plan = executor._generate_execution_plan(
        sample_module, decisions, strip_requested=False, source_docs=source_docs
    )

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is False
    assert p_a.update_doc_fingerprint is False
    assert p_a.strip_source_docstring is False
    assert p_a.update_code_fingerprint is True
~~~~~
~~~~~python.new
def test_plan_for_keep_existing_with_strip(executor, sample_module):
    """Scenario: YAML-first (`HYDRATE_KEEP_EXISTING`) + strip requested."""
    decisions = {"func_a": ResolutionAction.HYDRATE_KEEP_EXISTING}
    source_docs = executor.doc_manager.flatten_module_docs(sample_module)
    plan = executor._generate_execution_plan(
        sample_module, decisions, strip_requested=True, source_docs=source_docs
    )

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is False
    # We update doc fingerprint to record the existing YAML content as the new baseline
    assert p_a.update_doc_fingerprint is True
    assert p_a.strip_source_docstring is True
    assert p_a.update_code_fingerprint is True


def test_plan_for_keep_existing_without_strip(executor, sample_module):
    """Scenario: YAML-first (`HYDRATE_KEEP_EXISTING`) + no strip requested."""
    decisions = {"func_a": ResolutionAction.HYDRATE_KEEP_EXISTING}
    source_docs = executor.doc_manager.flatten_module_docs(sample_module)
    plan = executor._generate_execution_plan(
        sample_module, decisions, strip_requested=False, source_docs=source_docs
    )

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is False
    # We update doc fingerprint to record the existing YAML content as the new baseline
    assert p_a.update_doc_fingerprint is True
    assert p_a.strip_source_docstring is False
    assert p_a.update_code_fingerprint is True
~~~~~

### 下一步建议

执行测试。如果 `test_init_sidecar_idempotency.py` 仍然失败（返回 None），则需要进一步深入检查 `LockSession` 的写入路径。但理论上，只要 `update_doc_fingerprint` 为 True，指纹就会被记录，随后被 `run_pump` 中的 `lock_session.commit_to_transaction` 提交。
