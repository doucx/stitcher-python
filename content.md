好的，我已经准备好了。现在我们将把这些针对 `stitcher-cli` 的改进作为一个完整的逻辑单元提交到 Git 仓库中。

## [COMMIT] feat(cli): 为多个子命令添加 --dry-run 选项以预览变更

### 用户需求
在 `stitcher-cli` 的 `generate`, `pump`, `strip`, 和 `inject` 命令中支持 `--dry-run` 标志，以便用户能够安全地预览将要发生的文件系统变更。

### 评论
此提交完成了 CLI 层的“安全预览”功能集成。通过复用 `StitcherApp` 和 `TransactionManager` 已有的 `dry_run` 能力，我们确保了用户在执行关键操作前有清晰的预期，这大大降低了误操作风险，特别是在处理 `strip` 和 `inject` 等破坏性操作时。

### 目标
1.  将修改后的 `pump.py` 和 `basics.py` 添加到 Git 暂存区。
2.  创建一个清晰记录此功能改进的 Git 提交。

### 基本原理
遵循“意图明确”的提交规范。我们将记录受影响的命令以及在 `dry_run` 模式下自动跳过确认提示的 UX 改进。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/dry-run-feature #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将把 CLI 相关的修改添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-cli/src/stitcher/cli/commands/pump.py
packages/stitcher-cli/src/stitcher/cli/commands/basics.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): add --dry-run option to multiple commands

Introduces the '--dry-run' flag to 'generate', 'pump', 'strip', and 'inject' commands.
When enabled, the CLI previews all planned file system operations via the TransactionManager instead of applying them.

For 'strip' and 'inject' commands, the interactive confirmation prompt is automatically skipped when in dry-run mode to streamline the preview experience.
~~~~~

### 下一步建议
- **功能验证**: 你现在可以在终端运行 `stitcher strip --dry-run` 或 `stitcher pump --dry-run` 来实时观察预览输出。
- **集成测试**: 建议在 `packages/stitcher-cli/tests` 中增加针对 `--dry-run` 标志的集成测试，确保其能够正确触发 `TransactionManager` 的预览逻辑而不产生实际写入。
- **覆盖率检查**: 运行 `stitcher cov` 看看我们的项目文档覆盖率，确保新的 CLI 函数也得到了妥善的文档记录。
