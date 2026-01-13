我们将提交阶段 3 的所有核心重构成果。

## [COMMIT] refactor: switch core application to LockFileManager and global SURIs

### 用户需求
提交已完成的阶段 3 工作：应用层核心逻辑切换、旧签名管理器移除、以及测试套件的适配与对齐。

### 评论
这次提交完成了 Stitcher 历史上最重要的架构跃迁之一。我们已经成功切断了旧有的碎片化 JSON 签名系统，并全面采用了基于包级的 `stitcher.lock` 文件。虽然重构引擎（Phase 4）尚未完全简化，但整个应用层已经完全运行在新的定位坐标系之上。

### 目标
1.  提交应用层 Runners (`Init`, `Pump`, `Check`) 的重构代码。
2.  提交对 `stitcher-spec` 协议的更新和清理。
3.  提交对测试套件的修复和升级。
4.  记录当前系统的中间态。

### 基本原理
按照阶段性开发原则，在完成应用层核心逻辑的“大手术”后，及时提交代码可以固定当前通过了大部分单元测试的稳定状态。这为接下来的重构引擎简化（Phase 4）提供了坚实的后勤保障。

### 标签
#intent/refactor #flow/ready #priority/medium #comp/application #comp/interfaces #concept/state #ai/instruct #task/domain/storage #task/object/suri-lockfile #task/action/phase-3-completion #task/state/continue

---

### Script

#### Acts 1: 提交重构成果

我们将所有受影响的文件添加到暂存区。注意，这里包含了新创建的文件、修改的文件以及已删除的文件。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/protocols.py
packages/stitcher-spec/src/stitcher/spec/managers.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/lock_manager.py
packages/stitcher-application/src/stitcher/app/services/__init__.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/runners/init.py
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
packages/stitcher-application/src/stitcher/app/runners/pump/runner.py
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
packages/stitcher-application/tests/unit/test_execution_planner.py
packages/stitcher-refactor/tests/integration/test_refactor_move_updates_suri_in_signatures.py
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: switch core application to LockFileManager and global SURIs

Successfully completed Phase 3 of the SURI migration. This commit marks the removal of the old per-file JSON signature system in favor of package-level 'stitcher.lock' files.

Key Changes:
- Removed 'SignatureManager' and its associated protocol.
- Migrated 'InitRunner', 'PumpRunner', and 'CheckRunner' to interact with 'LockFileManager'.
- Updated 'SubjectAdapter' and 'CheckResolver' to use workspace-anchored SURIs for fingerprint lookups and updates.
- Standardized SURI generation across the application via the new 'URIGeneratorProtocol'.
- Aligned the test suite: fixed NameErrors, updated dependency injection in unit tests, and rewrote integration tests to target the new lockfile behavior.

The core application logic now operates on a logical coordinate system, significantly reducing I/O operations and providing a foundation for simpler refactoring operations.
~~~~~

### 下一步建议

我们已经固定了应用层的改动。下一步将进入 **阶段 4: 重构引擎简化 (Refactor Engine Lobotomy)**。

我们将重点处理 `stitcher-refactor` 包：
1.  删除 `MoveFileOperation` 中处理签名文件物理移动的冗余逻辑。
2.  引入 `LockUpdateIntent`。
3.  更新 `Planner` 以实现对 `stitcher.lock` 的内存内 SURI 更新，使我们新写的集成测试能够通过。
