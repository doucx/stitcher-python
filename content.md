太棒了。测试通过意味着我们的重构逻辑完全符合预期的状态矩阵。现在我们将这些变更作为一个完整的功能单元提交到仓库。

## [COMMIT] refactor(check): implement fine-grained document state matrix

### 用户需求
测试通过，创建提交。

### 评论
这次重构极大地提升了 `check` 命令的表达能力。通过引入 `PENDING`（待同步）和 `REDUNDANT`（冗余）状态，我们不仅解决了用户对 "MISSING" 含义的困惑，还为用户提供了更明确的操作指导（如提示运行 `hydrate` 或 `strip`）。

### 目标
1.  将所有相关修改（i18n 资源、核心服务、应用逻辑及集成测试）提交到 Git。

### 基本原理
遵循 ACA 协议中的“指令级约束：脚本与 Git 操作互斥”原则，我们将文件修改与 Git 提交分在不同的计划中执行。当前计划专注于将已验证的变更持久化到版本历史中。

### 标签
#intent/refine #flow/ready #priority/medium #comp/application #comp/cli #scope/ux #task/domain/documentation #task/object/check-logic #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有涉及到的包和测试文件添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/main.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/main.json
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/src/stitcher/app/core.py
tests/integration/test_check_command.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(check): implement fine-grained document state matrix

Refactored the 'check' command logic to provide more precise feedback
based on a 5-state matrix of entity and docstring existence:

1. MISSING (Warning): Entity exists, but no docstring in code or YAML.
2. PENDING (Error): Docstring exists in code but not in YAML (needs hydration).
3. REDUNDANT (Warning): Identical docstring exists in both (suggests stripping).
4. CONFLICT (Error): Different docstrings exist in both.
5. EXTRA (Error): Docstring in YAML points to a non-existent entity.

This resolves ambiguity where users were confused by the generic "MISSING"
message which previously conflated "unwritten" and "unsynced" states.
Updated English and Chinese assets and added a comprehensive integration
test for all matrix states.
~~~~~

### 下一步建议
- **文档更新**: 建议更新项目的 README 或用户手册，解释这些新状态的含义以及如何根据提示进行后续操作（如 `hydrate` 或 `strip`）。
- **CI 集成**: 检查 CI 流程中是否使用了 `stitcher check`，新逻辑可能会导致原本被视为“警告”的情况现在变成了“错误”（如 PENDING），需要评估是否需要调整 CI 策略。
