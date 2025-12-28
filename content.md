好的，我们已经顺利完成了“交互式引导与调和模式”的所有开发环节，包括领域模型构建、应用层解耦重构、CLI 交互向导实现以及自动化修复逻辑的补回。现在，我们将这些改动作为一个完整的逻辑单元提交到 Git 仓库。

## [COMMIT] feat(cli): 实现 'check' 命令的交互式调和模式

### 用户需求
用户需要一种高效、直观且容错性高的方式来处理 `stitcher check` 检测到的冲突。

### 评论
这是一次重大的开发者体验 (DX) 升级。通过引入交互式向导，我们将原来繁琐的“查看错误 -> 手动附加标志 -> 重新运行”循环简化为“一站式”决策过程。这种设计不仅提高了处理效率，更通过撤销支持和粘性默认值，极大地降低了误操作的风险和心智负担。

### 目标
1.  提交在 `stitcher-spec` 中定义的新领域模型。
2.  提交在 `stitcher-application` 中实现的 `InteractionHandler` 协议及其自动执行/非交互式逻辑。
3.  提交在 `stitcher-cli` 中实现的高级交互向导及其与核心逻辑的装配。
4.  包含所有相关的文档更新和标志位增强。

### 基本原理
我们将这组横跨三个子包（Spec, Application, CLI）的修改合并为一个原子提交。这组修改在逻辑上是高度内聚的：Spec 定义了数据契约，Application 实现了执行逻辑，CLI 提供了用户入口。作为一个完整的特性交付，这样做有利于保持 Git 历史的清晰和特性的可追溯性。

### 标签
#intent/build #flow/ready #comp/cli #comp/application #comp/spec #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/interactive-check #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有涉及到的文件添加到暂存区，并创建一个详尽的提交记录。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/models.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-spec/src/stitcher/spec/models.stitcher.yaml
packages/stitcher-application/src/stitcher/app/protocols.py
packages/stitcher-application/src/stitcher/app/handlers/noop_handler.py
packages/stitcher-application/src/stitcher/app/handlers/__init__.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/src/stitcher/cli/handlers.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-cli/src/stitcher/cli/assets/needle/en/commands.json
packages/stitcher-cli/src/stitcher/cli/assets/needle/zh/commands.json
packages/stitcher-cli/src/stitcher/cli/main.stitcher.yaml
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): implement interactive reconciliation mode for 'check' command

This commit introduces a comprehensive interactive "Reconciliation Wizard"
to resolve conflicts (Signature Drift and Co-evolution) during 'stitcher check'.

Key improvements:
- Decoupled application logic from UI via a new 'InteractionHandler' protocol.
- Implemented 'TyperInteractionHandler' with support for:
    - Single-key interaction (no Enter required for choices).
    - Undo support ('z' key) to revisit and change previous decisions.
    - Sticky defaults: the last choice becomes the default for next similar conflicts.
    - Recorded defaults: when going back via Undo, the already chosen action is shown as default.
- Redesigned 'StitcherApp.run_check' into a robust 4-phase model:
    1. Analysis: Scan all files for conflicts.
    2. Auto-Execution: Automatically reconcile doc improvements without user input.
    3. Decision: Use the handler to gather user decisions for all conflicts.
    4. Execution: Batch-apply all confirmed resolutions.
- Added '--non-interactive' flag to explicitly disable interactivity in TTY environments.
- Updated documentation and added i18n support for the new interactive features.

This major DX upgrade makes conflict resolution much more efficient and less error-prone for developers during large-scale refactorings.
~~~~~

### 下一步建议
- **回归测试**: 建议在各种环境下（交互式 TTY, 非交互式 TTY, `--non-interactive` 标志）运行 `stitcher check` 以确保行为符合预期。
- **UI 优化**: 未来可以考虑在冲突展示中加入更详细的差异对比（Diff view），帮助用户做更明智的决策。
- **CI 集成**: 检查 CI 流程是否能正确处理由于 `--non-interactive` 引起的静默失败。
