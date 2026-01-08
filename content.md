好的，我们已经完成了重构路线图中阶段一的核心任务：**统一文件事务系统**，并且修复了受影响的集成测试。现在我们将这些变更作为一个完整的逻辑单元提交。

## [COMMIT] refactor(app): integrate unified transaction system and enable dry-run

### 用户需求

为已完成的“统一文件事务系统”集成工作创建 Git 提交。

### 评论

这次提交实现了重构路线图 v1.0 中的第 1.1 步。通过将 `stitcher-application` 的各个 Runner 接入 `TransactionManager`，我们成功地实现了 IO 逻辑的集约化，并为系统引入了原生的 `--dry-run` 支持。这是构建稳健、可预测的重构平台的基石。

### 目标

1.  将所有涉及事务系统增强、Runner 适配和测试修复的文件添加到暂存区。
2.  创建一个清晰、符合规范的 Git 提交。

### 基本原理

遵循原子提交原则，将这一组紧密相关的架构变更合并为一个提交。这包括了底层基础设施的增强（`TransactionManager`）、中间层服务的适配（`StubPackageManager` 等）、上层逻辑的重构（Runners）以及验证层的更新（Tests）。

### 标签

#intent/refine #flow/ready #priority/high
#comp/application #comp/common #concept/state #scope/core
#ai/instruct
#task/domain/architecture #task/object/transaction-system #task/action/integration #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交事务系统集成变更

我们将把所有修改过的文件添加到 Git，并创建一个详细的提交。

~~~~~act
git_add
packages/stitcher-common/src/stitcher/common/transaction.py
packages/stitcher-common/src/stitcher/common/assets/needle/en/refactor/run.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/refactor/run.json
packages/stitcher-application/src/stitcher/app/runners/transform.py
packages/stitcher-application/src/stitcher/app/runners/generate.py
packages/stitcher-application/src/stitcher/app/runners/pump.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
packages/stitcher-application/tests/integration/test_end_to_end.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(app): integrate unified transaction system and enable dry-run

This commit implements step 1.1 of the "Stitcher Refactoring Roadmap v1.0". It migrates all file-writing operations from direct I/O to a centralized, transactional system.

Key changes:
- Enhanced `TransactionManager` with `dry_run` support and semantic logging via the `bus`.
- Refactored `PumpRunner`, `GenerateRunner`, and `TransformRunner` to collect `FileOp` intents instead of executing writes immediately.
- Updated `StubPackageManager` to participate in the transaction.
- Coordinated the transaction lifecycle (instantiation, injection, and commitment) within `StitcherApp`.
- Added `dry_run` parameters to core application entry points.
- Fixed and enhanced integration tests to reflect the new transactional architecture and verify physical file creation.

This refactoring eliminates I/O redundancy and provides a consistent, safe mechanism for previewing changes across all major commands.
~~~~~

### 下一步建议

-   **CLI 集成**: 在 `stitcher-cli` 中为相关子命令添加 `--dry-run` 开关，并将该布尔值传递给 `StitcherApp`。
-   **路线图推进**: 开始执行阶段一的第 1.2 步：“统一资产路径解析”，在 `stitcher-common` 中创建 `AssetPathResolver` 来集中管理 Sidecar 文件的映射规则。
