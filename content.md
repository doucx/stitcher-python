我将生成一个 `[COMMIT]` 计划，将所有关于测试工具和测试重构的修改提交到版本控制中。

## [COMMIT] test(testing): Standardize integration test setup using WorkspaceFactory

### 用户需求

提交所有关于测试工具增强和测试文件重构的变更。

### 评论

这次提交是关于测试基础设施和开发者体验的重大改进。我们成功地将：
1.  消息总线单元测试迁移到语义化验证模式，通过 `SpyBus` 验证消息 ID 而非字符串输出。
2.  增强了 `WorkspaceFactory`，使其支持创建任意原始文件（如签名 JSON）。
3.  使用增强后的 `WorkspaceFactory` 全面重构了 `stitcher-refactor` 包下的所有集成测试，大幅简化了测试环境的搭建过程，提高了测试的声明性和可读性。

### 目标

创建一个原子性提交，包含所有为了标准化测试环境而进行的工具和测试代码重构。

### 基本原理

为了确保测试套件的长期可维护性，我们强制推行了两个核心原则：
1.  **验证意图 (MessageBus)**: 确保测试不因 UI 文本的变更而失效。
2.  **声明式环境 (WorkspaceFactory)**: 将复杂的、命令式的文件系统设置逻辑抽象为清晰、简洁的声明式 API 调用，使得测试用例的输入/输出关系透明化。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/workspace-factory #task/action/integration #task/state/end #task/status/completed

---

### Script

#### Acts 1: 添加所有变更文件到暂存区

我们将所有重构过的测试文件和被修改的 `WorkspaceFactory` 文件添加到 Git 暂存区。

~~~~~act
git_add
packages/stitcher-common/tests/unit/test_message_bus.py
packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
~~~~~

#### Acts 2: 创建 Git 提交

创建描述本次测试重构的提交。

~~~~~act
git_commit
~~~~~
~~~~~text
test(testing): Standardize integration test setup using WorkspaceFactory

This commit completes the standardization of the project's testing utilities and applies the new patterns across key integration tests.

Key changes include:

1.  **`WorkspaceFactory` Enhancement**: Added `.with_raw_file()` to support declarative creation of arbitrary text files (crucial for `.stitcher/signatures/*.json`).
2.  **`SpyBus` Adoption**: Refactored `test_message_bus.py` to use `SpyBus`, aligning with the principle of verifying business intent (message IDs) rather than brittle UI output strings.
3.  **Refactor Engine Test Migration**: All integration tests under `stitcher-refactor` are now fully migrated to use the declarative `WorkspaceFactory`. This significantly improves the readability, robustness, and maintainability of our test suite by clearly separating the "Arrange" step from the "Act" and "Assert" steps.
~~~~~

### 下一步建议

这次关于测试基础设施的宏观任务已经完成。根据你最初提供的项目蓝图 (`MOC-用户反馈_P0-STI-NAV.md` 和 `MOC-用户反馈_P1-STI-NAV.md`)，项目的下一个高优先级目标可能涉及：

1.  **核心引擎与运行时**：集成 Griffe 或其他解析能力，这是实现 `stitcher-refactor` 架构蓝图中 `SemanticGraph` 的基础。
2.  **插件发现机制**：开始实现 `entry-points` 插件发现机制，解决 IDE 痛点。

我建议从 **集成 Griffe 以增强解析能力** (`P1`) 开始，这是构建语义感知重构引擎的前提。
