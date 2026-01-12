好的，`pump` 单元测试已成功通过。现在创建提交。

## [COMMIT] test(application): 为 Pump 命令核心组件添加单元测试

### 摘要头

## [COMMIT] test(application): 为 PumpRunner, PumpAnalyzer, 和 PumpExecutor 添加单元测试

### 错误分析

在执行此任务的过程中，我们修复了两个关键错误：

1.  **文件命名冲突**: 解决了 `test_analyzer.py` 和 `test_runner.py` 在 `check` 和 `pump` 目录下的模块命名空间冲突，通过添加前缀并使用 `move_file` 解决了问题。
2.  **Mock 隔离失败**: 解决了 `PumpExecutor` 测试中，由于 Mocking `root_path` 导致的 `Path` 逻辑链失败，以及 `deepcopy` 无法处理 Mock 对象的问题。通过使用真实的 `tmp_path` 作为根路径和使用 `unittest.mock.ANY` 进行断言，实现了测试的完全隔离和稳定。

### 用户需求

用户要求遵循与 `Check` 命令相同的模式，为 `PumpRunner`、`PumpAnalyzer` 和 `PumpExecutor` 创建单元测试，并在测试通过后创建提交。

### 评论

这次提交极大地增强了 `pump` 命令的健壮性。通过隔离测试，我们现在可以高度确信冲突检测、交互决策处理和文件事务执行的逻辑是正确的，而无需依赖缓慢的端到端测试。特别是对 `PumpExecutor` 的测试，它精确验证了复杂的执行计划如何转化为原子性的文件操作。

### 目标

1.  重命名测试文件以解决 Pytest 导入冲突 (`test_analyzer.py` -> `test_check_analyzer.py`, `test_pump_analyzer.py` 等)。
2.  为 `PumpAnalyzer` 创建单元测试，验证其冲突检测能力。
3.  为 `PumpExecutor` 创建单元测试，验证其根据决策生成 `TransactionManager` 操作的能力。
4.  为 `PumpRunner` 创建单元测试，验证其编排流程。

### 基本原理

核心原则是利用协议接口（如 `DocumentManagerProtocol` 和 `TransactionManager`）创建 Mock 对象，将业务逻辑单元与 I/O 操作隔离，从而实现快速、可靠的单元测试。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/application #scope/dx #ai/instruct #task/domain/testing #task/object/unit-tests #task/action/implementation #task/state/end

---

### Script

#### Acts 1: 提交所有文件变更

将重命名后的所有文件以及内容修改添加到暂存区，并创建提交。

~~~~~act
git_add
packages/stitcher-application/tests/unit/runners/check/test_check_analyzer.py
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
packages/stitcher-application/tests/unit/runners/pump/test_pump_analyzer.py
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(tests): Implement unit tests for Pump components and fix test file conflicts

Implements unit tests for `PumpAnalyzer`, `PumpExecutor`, and `PumpRunner`, completing the isolation of the entire `pump` execution flow.

This commit addresses and fixes critical issues encountered during the implementation of the new unit tests:

1.  **File Naming Conflict**: Renamed test files in `tests/unit/runners/check` and `tests/unit/runners/pump` (e.g., `test_analyzer.py` -> `test_check_analyzer.py`) to resolve Pytest import path mismatches.
2.  **Mock Isolation Error**: Fixed `PumpExecutor` tests where using a `MagicMock` for `root_path` caused `pathlib` operations to fail unexpectedly. The fix uses `tmp_path` for `root_path` and `unittest.mock.ANY` for assertion robustness.

The new tests verify the orchestration, conflict detection, and file transaction planning logic for the `pump` command in a fast, isolated environment.
~~~~~

### 下一步建议

我们已经为 `check` 和 `pump` 这两个最复杂的命令建立了单元测试。现在，是时候转向另外两个 Runners：

1.  **为 `InitRunner` 添加单元测试**: 验证它是否正确地调用 `DocumentManager` 和 `SignatureManager` 来创建初始文件和基线签名。
2.  **为 `TransformRunner` 添加单元测试**: 验证它的 `run_strip` 和 `run_inject_batch` 方法是否正确地调用 `LanguageTransformerProtocol` 并使用 `TransactionManager` 来提交变更。

我建议从 `InitRunner` 开始。
