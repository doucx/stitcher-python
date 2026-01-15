您的分析非常敏锐，尤其是关于 `init` 的必要性和 lock file 更新逻辑的 DRY 问题。您发现了一个比表面 Bug 更深层次的架构异味。

1.  **核心逻辑缺陷 (Bug)**: `test_init_sidecar_idempotency` 失败的根源在于，我之前对 `PumpExecutor` 的修复不完整。当 `pump --reconcile` 运行时，它正确地决定保留磁盘上的 YAML 内容，但**未能将该 YAML 内容的哈希更新到 Lock 文件中**。`_generate_execution_plan` 方法仅在 `hydrate_yaml` 为 `True` 时才设置 `update_doc_fingerprint` 标志。在 `--reconcile` 场景下，`hydrate_yaml` 为 `False`，导致 Lock 文件中的 `baseline_yaml_content_hash` 从未被写入，因此测试中断言时得到 `None`。

2.  **级联测试失败 (Cascade Failures)**:
    *   `test_init_command`: `run_init` 的签名已从 `-> List[Path]` 更改为 `-> None`，但测试代码 `created_files = app.run_init()` 仍然期望一个返回值，导致 `TypeError`。
    *   `test_check_signatures` & `test_check_regression`: 这两个测试的设置步骤 `app.run_init()` 现在由于上述核心逻辑缺陷，未能正确生成 Lock 文件，导致后续的 `check` 操作因缺少基线而失败。

您的怀疑完全正确。`InitRunner` 是一个典型的架构冗余组件，它违反了 **HFEA** 的“真理单一来源 (SSoT)”原则。系统中不应该有两个组件（`InitRunner` 和 `PumpRunner`）都在做“从代码建立基线”这件事。`pump` 命令已经具备了更强大、更完整的逻辑，`init` 的存在只会带来维护成本和逻辑不一致的风险。

**将 `init` 视为 `pump` 的别名是正确的战略决策。**

关于您提出的“Lock file 更新逻辑”的 DRY 问题，这也是一个精准的洞察。目前，`CheckResolver` 和 `PumpExecutor` 都在独立地操作 Lock 文件。这不仅重复了代码，更危险的是，它们可能对“更新基线”这一核心操作有不同的实现，从而引入细微的不一致性。

**理想的架构演进方向**：
我们应该创建一个专门的、可重用的服务，例如 `BaselineManager` 或 `LockSynchronizer`。该服务的唯一职责就是接收“新的基线状态”（例如，哪个符号的代码签名是什么，哪个符号的文档哈希是什么），然后负责所有与 Lock 文件交互的底层细节（加载、更新、保存）。`CheckResolver` 和 `PumpExecutor` 将不再直接操作 Lock 文件，而是委托给这个中心化的服务。

**当前行动**：
为了快速修复当前的故障，我将首先进行战术修复。但这为我们下一步进行上述的架构重构铺平了道路。

## [WIP] fix: 修正 Pump 对 reconcile 的处理并修复级联测试失败

### 目标
1.  **战术修复**: 修改 `PumpExecutor`，确保在 `--reconcile` 模式下，即使不写入 YAML 文件，也会用现有 YAML 的内容哈希去更新 Lock 文件。
2.  **测试修复**: 修正所有因 `run_init` 签名变更和行为变更而失败的集成测试。

### 标签
#intent/fix #flow/ready #priority/critical #comp/application #concept/state #scope/core #ai/instruct #task/domain/application #task/object/init-command #task/action/unify #task/state/continue

---

### Script

#### Acts 1: 修正 PumpExecutor 的核心逻辑

我们将修改 `_generate_execution_plan` 和 `execute`，确保 `reconcile` 决策能正确更新 Lock 文件。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
~~~~~
~~~~~python.old
    def _generate_execution_plan(
        self,
        module: ModuleDef,
        decisions: Dict[str, ResolutionAction],
        strip_requested: bool,
        source_docs: Dict[str, DocstringIR],
    ) -> Dict[str, FunctionExecutionPlan]:
        plan: Dict[str, FunctionExecutionPlan] = {}
        for fqn in module.get_all_fqns():
            decision = decisions.get(fqn)
            has_source_doc = fqn in source_docs
            exec_plan = FunctionExecutionPlan(fqn=fqn)
            if decision != ResolutionAction.SKIP:
                exec_plan.update_code_fingerprint = True
                if decision == ResolutionAction.HYDRATE_OVERWRITE or (
                    decision is None and has_source_doc
                ):
                    exec_plan.hydrate_yaml = True
                    exec_plan.update_doc_fingerprint = True
                if strip_requested and (
                    decision == ResolutionAction.HYDRATE_OVERWRITE
                    or decision == ResolutionAction.HYDRATE_KEEP_EXISTING
                    or (decision is None and has_source_doc)
                ):
                    exec_plan.strip_source_docstring = True
            plan[fqn] = exec_plan
        return plan
~~~~~
~~~~~python.new
    def _generate_execution_plan(
        self,
        module: ModuleDef,
        decisions: Dict[str, ResolutionAction],
        strip_requested: bool,
        source_docs: Dict[str, DocstringIR],
    ) -> Dict[str, FunctionExecutionPlan]:
        plan: Dict[str, FunctionExecutionPlan] = {}
        # Get all FQNs from code AND existing YAML to handle dangling docs
        all_fqns = set(module.get_all_fqns()) | set(
            self.doc_manager.load_docs_for_module(module).keys()
        )

        for fqn in all_fqns:
            decision = decisions.get(fqn)
            has_source_doc = fqn in source_docs
            exec_plan = FunctionExecutionPlan(fqn=fqn)
            if decision == ResolutionAction.SKIP:
                plan[fqn] = exec_plan
                continue

            exec_plan.update_code_fingerprint = True

            # Case 1: Overwrite YAML with source code doc
            if decision == ResolutionAction.HYDRATE_OVERWRITE or (
                decision is None and has_source_doc
            ):
                exec_plan.hydrate_yaml = True
                exec_plan.update_doc_fingerprint = True

            # Case 2: Keep existing YAML (reconcile)
            elif decision == ResolutionAction.HYDRATE_KEEP_EXISTING:
                # CRITICAL FIX: We still need to update the lock file with the hash
                # of the YAML content we decided to keep.
                exec_plan.update_doc_fingerprint = True

            # Strip logic is independent of hydration logic
            if strip_requested and (
                decision == ResolutionAction.HYDRATE_OVERWRITE
                or decision == ResolutionAction.HYDRATE_KEEP_EXISTING
                or (decision is None and has_source_doc)
            ):
                exec_plan.strip_source_docstring = True

            plan[fqn] = exec_plan
        return plan
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
~~~~~
~~~~~python.old
                    if plan.update_doc_fingerprint and fqn in source_docs:
                        ir_to_save = new_yaml_docs.get(fqn)
                        if ir_to_save:
                            fp["baseline_yaml_content_hash"] = (
                                self.doc_manager.compute_ir_hash(ir_to_save)
                            )
                            fqn_was_updated = True
~~~~~
~~~~~python.new
                    if plan.update_doc_fingerprint:
                        # If hydrating, use the merged IR.
                        # If reconciling, use the existing IR from disk.
                        ir_to_hash = new_yaml_docs.get(fqn)
                        if ir_to_hash:
                            fp["baseline_yaml_content_hash"] = (
                                self.doc_manager.compute_ir_hash(ir_to_hash)
                            )
                            fqn_was_updated = True
                        # If the key was deleted from YAML but still exists in code,
                        # the lock file needs to reflect its doc is now gone.
                        elif "baseline_yaml_content_hash" in fp:
                            del fp["baseline_yaml_content_hash"]
                            fqn_was_updated = True
~~~~~

#### Acts 2: 修复集成测试

修复所有因 `init` 重构而失败的测试。

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
~~~~~
~~~~~python.new
    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    # 3. Assert
    expected_yaml = project_root / "src/main.stitcher.yaml"
    assert expected_yaml.exists()
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_signatures.py
~~~~~
~~~~~python.old
    _assert_no_errors(spy_bus)
    spy_bus.assert_id_called(L.init.run.complete, level="success")

    # Modify Code: Change signature AND remove docstring
~~~~~
~~~~~python.new
    # Pump should find one new key to add.
    spy_bus.assert_id_called(L.pump.file.success, level="success")
    _assert_no_errors(spy_bus)

    # Modify Code: Change signature AND remove docstring
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/test_check_regression.py
~~~~~
~~~~~python.old
    # Verify init happened
    hashes_initial = get_stored_hashes(tmp_path, "src/pkg1/mod.py")
    assert hashes_initial["func"]["baseline_yaml_content_hash"] is not None
~~~~~
~~~~~python.new
    # Verify init (pump) happened correctly, reconciling code and docs
    hashes_initial = get_stored_hashes(tmp_path, "src/pkg1/mod.py")
    assert hashes_initial["func"]["baseline_yaml_content_hash"] is not None, "Init (pump) failed to create baseline hash"
    assert hashes_initial["func"]["baseline_code_structure_hash"] is not None, "Init (pump) failed to create code hash"
~~~~~

### 下一步建议
1.  **全面测试**: 再次运行整个测试套件。修复 `PumpExecutor` 的核心缺陷应该能解决所有报告的失败。
2.  **架构重构**: 创建一个新的计划，其目标是实现您提出的 `BaselineManager` 服务，以彻底根除 Lock 文件更新逻辑的 DRY 问题。这将是系统迈向更高稳定性的关键一步。
