好的，我们已经成功完成了 `stitcher-refactor` 引擎的核心架构升级，并修复了测试套件。这是一个里程碑式的改进，将系统从基于路径猜测转变为由元数据驱动。

现在，我将生成一个 `[COMMIT]` 计划，将这些变更作为一个完整的逻辑单元提交到仓库中。

## [COMMIT] refactor: 实现元数据驱动的重构引擎架构

### 用户需求

将过去几个步骤中完成的 `stitcher-refactor` 架构升级及其相关的测试修复进行 Git 提交。

### 评论

这次重构彻底解决了 `stitcher-refactor` 在面对复杂 monorepo 和命名空间包时的脆弱性问题。通过引入 `Workspace` 和 `SidecarManager` 抽象，我们将代码语义分析、项目结构发现和存储布局解析这三个关注点完全解耦。这是一次重大的架构演进，显著提升了系统的稳定性、可维护性和扩展性，为后续更复杂的重构功能奠定了坚实的基础。

### 目标

1.  将所有新增和修改的文件添加到 Git 暂存区。
2.  创建一个详尽的提交说明，记录此次重构的核心动机、设计决策和影响范围。

### 基本原理

遵循 `d3-constraint-quipu-plan-script-rules` 规范，这是一个纯粹的提交计划。我们首先通过一系列 `git_add` 操作精确覆盖受影响的包（`refactor`, `cli`, `test-utils`）及其对应的测试文件。随后，我们将执行 `git_commit`，提供符合 Conventional Commits 规范的说明，确保项目历史的清晰和可追溯性。

### 标签

#intent/refine #flow/ready #priority/high 
#comp/refactor #comp/cli #comp/test-utils #scope/core 
#ai/instruct 
#task/domain/refactor-engine #task/object/metadata-architecture #task/action/implementation #task/state/continue #task/status/active

---

### Script

#### Acts 1: 提交引擎重构与测试修复

我们将把所有涉及架构升级和测试对齐的变更打包提交。

~~~~~act
git_add
packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
packages/stitcher-refactor/tests/unit/refactor/test_workspace.py
packages/stitcher-refactor/src/stitcher/refactor/sidecar/manager.py
packages/stitcher-refactor/tests/unit/sidecar/test_manager.py
packages/stitcher-refactor/src/stitcher/refactor/engine/context.py
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~

~~~~~act
git_add
packages/stitcher-refactor/tests/integration/test_usage_registry.py
packages/stitcher-refactor/tests/integration/test_semantic_graph.py
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(refactor): implement metadata-driven engine architecture

Significant architectural overhaul of 'stitcher-refactor' to support complex Python monorepos and namespace packages. 

Key changes:
1. Introduced 'Workspace' class: Centralized project structure discovery driven by pyproject.toml metadata. It maps top-level import names to physical source directories, handling namespace packages (one-to-many mappings) correctly.
2. Introduced 'SidecarManager': Decoupled sidecar (.stitcher.yaml and .json signatures) path resolution from refactoring operations. This eliminates hardcoded path logic across the engine.
3. Evolved 'RefactorContext': Now serves as a service container injecting Workspace and SidecarManager into operations.
4. Refactored 'SemanticGraph': Now depends on Workspace for authoritative search paths instead of guessing.
5. Decoupled Operations: Move and Rename operations now use SidecarManager for path logic, adhering to DRY principles.
6. Test Suite Alignment: Systematically updated the entire test suite to match the new DI-based constructor signatures.

This refactor transforms the engine from a path-guessing script into a robust, industrial-strength architecture governance platform.
~~~~~

### 下一步建议

代码已经安全提交。现在我们处于一个非常稳定的状态。

下一步，我建议按照路线图执行 **任务 3.1**，编写那个针对 `Cascade` 类复杂场景的端到端集成测试，以最终确证新架构的实战威力。如果你准备好了，请告诉我。
