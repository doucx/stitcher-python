好的，我们已经成功解决了 `LockSession` 的状态污染问题，修正了 `PumpExecutor` 在调和模式下的指纹更新逻辑，并完成了测试套件的全面适配。现在系统状态已经稳定，所有的集成测试和单元测试都已恢复正常。

我将生成一个 `[COMMIT]` 计划，将这些关键的稳定性修复提交到仓库。

## [COMMIT] fix: 稳定 LockSession 状态管理与调和逻辑

### 错误分析
在引入基于 `LockSession` 的增量更新机制后，发现了以下关键问题：
1.  **状态持久化竞态**: `StitcherApp` 在执行命令时未清理 `LockSession` 缓存，导致在长生命周期的应用实例（如测试运行器）中，旧的内存状态会覆盖后续操作的磁盘结果。
2.  **基线更新缺失**: 在 `pump --reconcile` (现 `init` 的底层实现) 模式下，系统虽然决定保留 YAML 内容，但未将其记录为新的指纹基线，导致状态机始终处于“待调和”状态。
3.  **自动调和冲突**: `CheckResolver` 之前的 `auto_reconcile_docs` 逻辑绕过了 `LockSession` 直接操作磁盘，在 `StitcherApp` 命令结束提交时被缓存状态覆盖。
4.  **测试脆弱性**: 多个集成测试因 `init` 到 `pump` 的架构迁移导致的输出消息变化而失败，且部分测试源码存在导致解析失败的 Python 语法错误。

### 用户需求
确保 Stitcher 的状态机在各种命令切换和复杂冲突场景下保持绝对的确定性，并使 `init` 逻辑完全对齐到 `pump` 流程。

### 评论
这次修复通过在 `LockSession` 中引入显式的生命周期管理 (`clear`)，并将所有状态变更动作收敛到统一的 Session 接口，彻底消除了内存与磁盘状态不一致的隐患。

### 目标
1.  持久化 `LockSession` 的清理机制。
2.  确保所有同步路径（Pump, Reconcile, Auto-reconcile）均正确触发指纹更新。
3.  对齐测试套件的断言与新的命令体系。

### 基本原理
根据 **SSoT (单一事实来源)** 原则，我们将 `StitcherApp` 塑造为一个受控的环境。每个命令的执行都是一个独立的事务单元，在开始前确保环境干净，在结束后确保状态已提交并重置。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #comp/tests #concept/state #scope/core #ai/instruct #task/domain/runtime #task/object/state-management #task/action/fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交稳定性修复

我们将所有受影响的核心组件和测试文件添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/services/lock_session.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
packages/stitcher-application/tests/integration/test_check_signatures.py
packages/stitcher-application/tests/integration/test_init_command.py
packages/stitcher-application/tests/unit/test_execution_planner.py
packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(runtime): stabilize lock state management and reconciliation logic

This commit fixes several critical issues in the state management and 
reconciliation workflow that were causing integration test failures:

1. Lifecycle Control: Added `LockSession.clear()` and integrated it into 
   `StitcherApp` command entries (run_check, run_pump) to prevent stale 
   memory state from polluting subsequent operations in the same process.
2. Baseline Updates: Fixed `PumpExecutor` to ensure doc fingerprints are 
   updated even in 'reconcile' (YAML-first) mode, preventing perpetual 
   out-of-sync states.
3. Resolver Refactoring: Rebuilt `CheckResolver.auto_reconcile_docs` to 
   operate through the `LockSession` instead of direct disk I/O, ensuring 
   atomic commits and consistent state.
4. Test Alignment: Updated integration tests to match the new 'init-as-pump' 
   message IDs and return values. Fixed Python syntax errors in test source 
   templates that caused parser failures.

These changes ensure that the state machine remains deterministic across 
multiple command invocations.
~~~~~

### 下一步建议
- **回归测试**: 建议在不同的操作系统（特别是 Windows，涉及路径分隔符）上运行全量测试套件。
- **并发审计**: 考虑 `LockSession` 在多线程环境下的安全性（虽然当前 CLI 是单线程执行）。
- **文档更新**: 内部架构文档应记录 `LockSession` 的生命周期要求，告知后续开发者在添加新的 Runner 时必须遵守清理协议。
