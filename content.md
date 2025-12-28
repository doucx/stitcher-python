我们将合并前两个步骤（实现 `hydrate` 交互模式和修复测试/消息统一）的所有变更，并将其作为一个完整的、逻辑封闭的工作单元进行提交。

## [COMMIT] feat(hydrate): 实现交互式冲突解决模式

### 用户需求
在 `stitcher hydrate` 命令中实现交互式冲突解决模式，以便用户能够在内容冲突发生时（代码文档与 YAML 文档不一致）实时选择是覆盖 YAML 还是保留 YAML，从而避免重新运行命令并手动输入标志。同时，统一所有交互式命令的 `abort` 消息。

### 评论
该提交代表了 Stitcher 核心开发者体验 (DX) 的一个重大飞跃。通过将交互式模型泛化并应用于 `hydrate`，我们显著改善了在处理文档内容漂移时的心流体验。同时，统一的“分析-决策-执行”三阶段模型增强了 `StitcherApp` 的架构一致性，并使 `NoOpHandler` 能够清晰地处理非交互模式下的所有 CLI 标志。

### 目标
1.  **模型扩展**: 在 `stitcher-spec` 中添加 `ConflictType.DOC_CONTENT_CONFLICT` 和 `ResolutionAction.HYDRATE_*`。
2.  **核心重构**: 重构 `DocumentManager.hydrate_module`，支持 `dry_run` 和基于 `resolution_map` 的细粒度执行。
3.  **应用层实现**: 在 `StitcherApp.run_hydrate` 中实现三阶段流程，并注入 `InteractionHandler`。
4.  **交互增强**: 扩展 `TyperInteractionHandler` 以显示 Hydrate 独有的菜单选项。
5.  **消息统一**: 将 `hydrate` 命令中的硬编码中止消息替换为语义指针 `L.hydrate.run.aborted`。
6.  **测试覆盖**: 引入新的集成测试，验证 `HYDRATE_OVERWRITE`, `HYDRATE_KEEP_EXISTING`, `SKIP`, 和 `ABORT` 四种交互式解决动作的端到端行为。

### 基本原理
通过将 `hydrate` 命令从简单的两步（分析并写入）操作提升为结构化的三阶段流程（分析冲突并创建 `InteractionContext` -> 通过 Handler 获取 `ResolutionAction` -> 根据决策执行写入），我们成功将业务核心逻辑与用户界面逻辑完全解耦。这一模式是 `check` 和 `hydrate` 统一交互体验的核心支柱。同时，对测试代码和国际化资源的修复确保了系统的鲁棒性。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #comp/runtime #concept/ui #concept/executor #scope/dx #task/domain/cli #task/object/interactive-mode #task/action/implementation #task/state/end

---

### Script

#### Acts 1: 添加所有修改的文件到暂存区

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/models.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/src/stitcher/app/handlers/noop_handler.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/src/stitcher/cli/handlers.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-application/tests/integration/test_hydrate_interactive_flow.py
packages/stitcher-common/src/stitcher/common/assets/needle/en/hydrate/main.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/hydrate/main.json
~~~~~

#### Acts 2: 创建提交

~~~~~act
git_commit
~~~~~
~~~~~text
feat(hydrate): Add interactive conflict resolution mode

This commit implements the "Unified Interactive Interaction Model" for the `hydrate` command, allowing users to resolve documentation conflicts (where source code docstring differs from YAML content) directly in an interactive TTY session.

Key Changes:

1.  **Model Extension (stitcher-spec)**: Introduced `ConflictType.DOC_CONTENT_CONFLICT` and new resolution actions: `HYDRATE_OVERWRITE` and `HYDRATE_KEEP_EXISTING`.
2.  **Hydrate Logic Refactor**: `DocumentManager.hydrate_module` now supports `dry_run` mode and accepts a `resolution_map` for key-specific decisions.
3.  **App Core (run_hydrate)**: Adopted the "Analysis -> Decision -> Execution" three-phase architecture, aligning it with `run_check`. This allows interaction handlers to intervene before file writes occur.
4.  **CLI/Handler Update**:
    *   `TyperInteractionHandler` now recognizes the doc content conflict type and renders a specific menu ([F]orce-hydrate, [R]econcile).
    *   `NoOpInteractionHandler` was updated to handle the new `--force`/`--reconcile` flags specific to `hydrate` in non-interactive environments.
5.  **Testing**: Added `test_hydrate_interactive_flow.py` and fixed an issue where the hardcoded "abort" message was not being tested semantically, replacing it with `L.hydrate.run.aborted` in both assets and application code.

This significantly enhances the Developer Experience (DX) by eliminating the tedious "fail, re-run with flag" loop for documentation maintenance.
~~~~~

### 下一步建议
我们已经为 `hydrate` 实现了交互模式，并为 `check` 奠定了交互框架（虽然目前它只处理签名相关的冲突）。

**建议的下一步是**:
1.  **集成测试覆盖**: 为 `check` 命令的交互式流程添加完整的集成测试，尤其是验证 `RELINK` 和 `RECONCILE` 的交互式行为（类似于我们为 `hydrate` 所做的）。
2.  **签名命名规范清理**: 遵循 `d1-principle-signature-long-names` 公理，全面审查并重构 `StitcherApp.run_init` 中签名哈希的保存逻辑，确保所有哈希字段都使用新的长命名规范 (`baseline_code_structure_hash` 等)。虽然在 `core.py` 中已经使用了长命名，但需要确保 `run_init` 和 `SignatureManager` 的调用完全符合规范。

如果你同意，我将开始创建针对 `check` 命令的交互式测试。
