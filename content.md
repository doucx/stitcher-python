好的，测试已通过。现在我将创建提交。

## [COMMIT] test(application): 为 CheckRunner 和 CheckAnalyzer 添加单元测试

### 用户需求

用户要求开始编写单元测试，利用已定义的协议接口来隔离和测试 `stitcher-application` 中的核心组件，以提高测试套件的质量和效率，并在单元测试通过后创建提交。

### 评论

本次提交引入了 `CheckRunner` 和 `CheckAnalyzer` 的单元测试。通过使用 Mocking 和 `FakeCheckSubject`，这些测试实现了与文件系统和底层服务的完全解耦，显著提高了测试速度和稳定性，并严格遵循了测试隔离原则。

### 目标

1.  在 `packages/stitcher-application/tests/` 目录下创建 `unit/` 子目录结构。
2.  为 `CheckAnalyzer` 编写单元测试，覆盖同步、缺失、待处理、签名漂移、协同演进、悬空文档以及两种未追踪文件警告（简单和详细）的全部核心逻辑。
3.  为 `CheckRunner` 编写单元测试，验证其作为编排器的角色。
4.  修正了单元测试中由于文件系统 Mock 缺失和协议方法使用错误导致的初始失败。

### 基本原理

新的单元测试专注于组件间的协议契约，而非其实现细节，从而大大提升了测试套件的鲁棒性。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/application #scope/dx #ai/instruct #task/domain/testing #task/object/unit-tests #task/action/implementation #task/state/end

---

### Script

#### Acts 1: 提交变更

将所有新增的单元测试文件添加到 Git 暂存区，并进行一次完整的提交。

~~~~~act
git_add
packages/stitcher-application/tests/unit/runners/check/test_analyzer.py
packages/stitcher-application/tests/unit/runners/check/test_runner.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
test(application): Add unit tests for CheckRunner and CheckAnalyzer

Introduces dedicated unit test suites for the core `CheckRunner` and `CheckAnalyzer` components in `stitcher-application`.

This moves core conflict detection and orchestration logic verification away from slow, brittle E2E tests, drastically improving stability and speed.

Key improvements:
- **Isolation**: Tests use Mock objects (`create_autospec`) and a custom `FakeCheckSubject` to fully isolate the components from the file system and Index Store.
- **Coverage**: `CheckAnalyzer` tests now cover the full matrix of states: synchronized, missing, pending, content conflict, signature drift, co-evolution, dangling doc, and both detailed/simple untracked file warnings.
- **Orchestration**: `CheckRunner` tests verify that the component correctly calls its dependencies (Analyzer, Resolver, Reporter) in the correct sequence.
~~~~~

### 下一步建议

我们已经完成了 `Check` 命令核心逻辑的单元测试。为了继续践行我们的重构策略，下一步应该转向 `pump` 流程：

1.  **扩展到 Pump 命令**: 遵循相同的模式，为 `PumpRunner`、`PumpAnalyzer` 和 `PumpExecutor` 创建单元测试。这将确保我们的核心数据提取和合并逻辑在隔离环境中是可验证的。
2.  **完善 `test-utils`**: 在 `stitcher-test-utils` 包中添加创建协议 Mock 的工厂函数，以减少后续单元测试中的重复代码和 Mock 配置。

我建议现在开始着手 `Pump` 命令的单元测试。
