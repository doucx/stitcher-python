我们已经完成了对核心 `check` 命令的架构性重构和所有必要的 Bug 修复。测试套件现在已同步并验证了新的行为模式。

现在是时候将这个完整的逻辑单元提交到版本控制。

## [COMMIT] refactor(cli, app): Implement Report Card pattern for check command and decouple signature updates

完成了 `stitcher check` 命令的核心重构，并修复了控制流混乱的问题，使其行为更加健壮和可预测。

### 基本原理
1.  **解耦签名更新**: 将签名指纹的更新逻辑从纯构建命令 `generate` 中彻底剥离，移入 `check` 命令并由新的 `--update-signatures` 标志控制。这使得 `generate` 成为一个幂等的、纯粹的构建器。
2.  **Report Card 模式**: 重构 `StitcherApp.run_check`，采用结构化的 `FileCheckResult` 模型。这隔离了复杂的分析逻辑与副作用（如消息报告），解决了先前版本中由于复杂的 `continue`/`else` 结构导致的控制流混乱问题（例如，成功更新后发送错误的警告）。
3.  **策略修正**: 确认并将 `extra` (YAML 中存在但代码中已删除的定义) 的级别恢复为 **Error**，以强制用户处理潜在的冗余文档，保护文档资产的完整性。
4.  **测试加固**: 更新了集成测试，以验证新的签名协调工作流，并确保在测试过程中正确设置了文件追踪状态，避免了测试环境下的误报。

### 标签
#intent/refine #flow/done #priority/high
#comp/cli #comp/application #comp/tests #concept/state
#scope/dx
#ai/instruct
#task/domain/cli #task/object/check-command #task/action/refactor
#task/state/end

---

### Script

#### Acts 1: 添加所有修改的文件到暂存区

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-cli/src/stitcher/cli/assets/needle/en/commands.json
packages/stitcher-cli/src/stitcher/cli/assets/needle/zh/commands.json
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/main.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/main.json
tests/integration/test_check_signatures.py
tests/integration/test_check_policy.py
~~~~~

#### Acts 2: 提交变更

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(cli, app): Implement Report Card pattern for check command and decouple signature updates

This commit introduces a major refactoring of the `stitcher check` command's internal logic and corrects core policy decisions, addressing both architectural debt and functional bugs.

Key changes:

1.  **Decoupled Signature Updates**: Removed signature saving logic from `generate` (making it a pure builder) and introduced the new CLI flag `check --update-signatures` to explicitly manage fingerprint reconciliation.
2.  **Report Card Pattern**: Refactored `StitcherApp.run_check` to use a structured `FileCheckResult` dataclass. This separates the complex analysis/reconciliation logic from the side-effect-heavy reporting logic, resolving confusing control flow bugs where successful reconciliation incorrectly resulted in a redundant warning message.
3.  **Policy Reversion**: Reverted the policy for `extra` (dangling) documentation back to an **Error** level. This is critical for ensuring the `.stitcher.yaml` remains the Single Source of Truth, preventing asset degradation over time.
4.  **Test Fixes**: Updated integration tests (`test_check_signatures` and `test_check_policy`) to correctly reflect the new behavior and ensure tracking files are created during setup.
~~~~~
