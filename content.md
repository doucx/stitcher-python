太棒了！所有测试均已通过，这意味着我们的架构重构——将 Pump 分析逻辑下沉到 `stitcher-analysis` 层，并成功构建了 `PumpEngine`——已经圆满完成。

现在，我们将把这些变更作为一个完整的逻辑单元提交到 Git 仓库。

## [COMMIT] refactor(pump): 将 PumpAnalyzer 迁移至 stitcher-analysis 并构建 PumpEngine

### 用户需求

根据架构设计，将 `PumpAnalyzer` 逻辑从应用层 (`stitcher-application`) 迁移到分析层 (`stitcher-analysis`)，并以 `PumpEngine` 的形式重新实现。

### 评论

这次重构显著提升了系统的架构质量。通过将“分析源代码与 YAML 文档之间的同步需求”这一逻辑下沉，我们使 `stitcher-analysis` 包成为了系统所有语义分析逻辑的中心。同时，`PumpRunner` 现在的职责变得更加纯粹，仅负责分析与执行的编排，这极大增强了代码的可维护性和可测试性。

### 目标

1.  固化 `stitcher-analysis` 中 `PumpEngine` 的实现。
2.  固化 `stitcher-application` 中 `PumpRunner` 的重构以及与新引擎的集成。
3.  正式删除已废弃的旧版 `PumpAnalyzer` 实现及协议。
4.  固化迁移后的测试套件。

### 基本原理

我们遵循了“分析（是什么）与执行（做什么）分离”的核心架构原则。
-   **分析层 (`stitcher-analysis`)**: `PumpEngine` 现在是一个纯粹的函数式组件，它通过 `AnalysisSubject` 观察系统状态，并识别出需要“抽出”的文档冲突。它不再依赖于复杂的管理器或 I/O，使其非常易于在隔离环境中测试。
-   **应用层 (`stitcher-application`)**: `PumpRunner` 升级为使用 `ASTCheckSubjectAdapter` 为引擎准备数据，并编排后续的交互和执行流程。

通过将测试也同步迁移，我们确保了在代码结构发生重大变化时，测试覆盖率没有丢失，且测试代码本身也得到了优化和精简。

### 标签
#intent/refine #flow/ready #priority/high #comp/analysis #comp/application #concept/executor #scope/core #ai/instruct #task/domain/architecture #task/object/pump-engine #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交架构重构变更

我们将所有新增、修改和删除的文件添加到暂存区，并创建一个详细的提交。

~~~~~act
git_add
packages/stitcher-analysis/src/stitcher/analysis/engines/pump/__init__.py
packages/stitcher-analysis/src/stitcher/analysis/engines/pump/engine.py
packages/stitcher-analysis/src/stitcher/analysis/engines/__init__.py
packages/stitcher-analysis/tests/unit/engines/test_pump_engine.py
packages/stitcher-application/src/stitcher/app/runners/pump/runner.py
packages/stitcher-application/src/stitcher/app/runners/pump/protocols.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(pump): migrate PumpAnalyzer to stitcher-analysis as PumpEngine

This commit implements a significant architectural refinement by moving the Pump analysis logic from the application layer to the analysis layer.

Key Changes:
- Created 'PumpEngine' in 'stitcher-analysis': A specialized engine that identifies docstring synchronization needs (pumping) between source code and YAML.
- Refactored 'PumpEngine' to depend on the 'AnalysisSubject' protocol instead of specific application services, making it more robust and easier to test in isolation.
- Updated 'PumpRunner' in 'stitcher-application': It now orchestrates the pumping flow by adapting 'ModuleDef' to 'AnalysisSubject' and delegating the core analysis to 'PumpEngine'.
- Cleaned up: Removed obsolete 'PumpAnalyzer' implementation and 'PumpAnalyzerProtocol'.
- Migrated Tests: Moved and refactored pump analyzer unit tests to 'stitcher-analysis/tests' to align with the new package structure.

This change reinforces the separation of concerns between 'analysis' (identifying what needs to be done) and 'application' (orchestrating the execution).
~~~~~

### 下一步建议

-   **持续重构**: 随着 `PumpEngine` 的就绪，我们可以考虑进一步统一所有 Engine 的基类或接口，以实现更高程度的抽象。
-   **性能分析**: 现在分析逻辑已经解耦，我们可以更容易地引入并行分析或增量分析策略，以提升大型项目的 `pump` 速度。
-   **文档更新**: 建议更新内部开发者指南，记录新的引擎架构模式，以便后续添加新功能时参考。
