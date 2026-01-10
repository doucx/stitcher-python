太棒了。所有的测试都已通过，这意味着我们这次重大的架构重构——将存根生成逻辑解耦到专门的 `stitcher-stubgen` 包中——已经圆满完成，并且保持了系统的完整性。

我将生成一个 `[COMMIT]` 计划，将这些变更作为一个完整的逻辑单元提交到版本控制中。

## [COMMIT] refactor(arch): decouple stub generation into a specialized package

### 用户需求

将过去分散在多个包中的存根生成逻辑整合并提取到一个新的独立包 `stitcher-stubgen` 中，并完成相关的清理和集成工作。

### 评论

这次重构是项目演进过程中的一个重要里程碑。它不仅将 `stitcher-application` 的职责精简为纯粹的应用编排，还通过引入 `StubgenService` 外观模式，为存根生成这一复杂领域建立了一个清晰、稳定的 API 边界。虽然过程中遇到了一些由于 monorepo 复杂性导致的集成挑战（如命名空间冲突和类型不一致），但我们通过静态分析和自动化测试逐一克服了它们，最终使项目结构变得更加稳健和易于扩展。

### 目标

1.  将所有变更（包括新包的创建、代码迁移、API 切换、类型修复以及冗余清理）添加到 Git 暂存区。
2.  创建一个包含详细说明的提交记录，阐述这次架构重构的核心变动和意义。

### 基本原理

通过 Git 指令将目前工作区中所有经过验证的更改永久化。提交信息将详细列出重构的关键点，包括新服务的引入、协议的修正以及对 monorepo 构建配置的微调，以便未来的维护者能够清晰地理解这次变动的意图和范围。

### 标签

#intent/architect #flow/ready #priority/high #comp/build #comp/stubgen #comp/application #scope/core #ai/delegate #task/domain/architecture #task/object/stubgen-package #task/action/cleanup #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交架构重构变更

我们将所有经过验证的变更添加到暂存区，并创建一个内容详尽的原子提交。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(arch): decouple stub generation into a specialized package

This major structural refactoring extracts all stub generation logic from 'stitcher-python-adapter' and 'stitcher-application' into a new, dedicated 'stitcher-stubgen' package.

Key Changes:
- Extracted 'GenerateRunner', 'StubPackageManager', and 'PythonStubGenerator' into 'stitcher-stubgen'.
- Introduced 'StubgenService' as a clean, high-level facade for the stub generation domain, significantly reducing 'StitcherApp's internal complexity.
- Refactored 'StitcherApp' constructor and updated all associated factories, command handlers, and test utilities (including 'create_test_app').
- Standardized namespace package declarations across the project using 'pkgutil.extend_path' to resolve cross-package integration issues.
- Fixed several type-safety issues and protocol mismatches identified by Pyright during the transition.
- Refined root 'pyproject.toml' configuration to exclude the 'migrations' directory from setuptools discovery, preventing build ambiguity.
- Removed now-redundant files and dead code in original packages to maintain a lean codebase.

This move aligns the project with HFEA principles by enforcing strict domain boundaries and providing a specialized environment for the stub generation engine to evolve independently.
~~~~~

### 下一步建议

架构已经焕然一新。下一步，我建议：
-   **文档更新**：如果项目中存在架构说明文档或 README，建议更新它们以反映 `stitcher-stubgen` 包的引入和新 API。
-   **探索新功能**：既然存根生成现在已经是一个独立的模块，我们可以更容易地为其添加新特性，例如支持更复杂的模板、支持不同的输出格式，或者优化大规模项目的并行生成性能。
