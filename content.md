好的，我将生成一个 `[COMMIT]` 计划，将目前的架构变更——包括 `stitcher-analysis` 包的建立以及对 `InteractionContext` 的规格升级——记录到 Git 历史中。

## [COMMIT] feat(arch): introduce stitcher-analysis and upgrade InteractionContext | refactor: 迁移 conflict_type 到 violation_type 指针并清理旧模型

### 用户需求
记录当前系统的中间状态。目前已完成 `stitcher-analysis` 包的骨架搭建、规则提取及引擎实现，并完成了 `stitcher-spec` 中 `InteractionContext` 的语义化升级。

### 评论
当前状态是一个重要的里程碑。我们不仅建立了一个独立的分析层，还迈出了统一系统语义语言（从 Enum 转向 SemanticPointer）的关键一步。虽然这一步暂时打破了应用层和 CLI 层的兼容性，但它为后续的高保真集成扫清了障碍。

### 目标
1.  提交所有与 `stitcher-analysis` 包相关的文件。
2.  提交对根目录和 `stitcher-spec` 的配置及代码修改。

### 基本原理
按照规范，`[COMMIT]` 计划仅包含 Git 操作，用于固化当前工作成果。

### 标签
#intent/architect #flow/done #priority/high #comp/build #comp/analysis #comp/interfaces #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有新增和修改的文件添加到 Git 仓库并创建提交。

~~~~~act
git_add
packages/stitcher-analysis
packages/stitcher-spec/pyproject.toml
packages/stitcher-spec/src/stitcher/spec/interaction.py
pyproject.toml
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(arch): introduce stitcher-analysis and upgrade InteractionContext

This commit establishes the physical and logical foundation for the new analysis engine and unifies the system's semantic language.

1.  Created 'stitcher-analysis' package:
    - Implemented a rule-based consistency engine.
    - Extracted check logic from the app layer into discrete, testable Rules (Signature, Content, Existence, Untracked).
    - Introduced 'Violation' and 'FileCheckResult' schemas using SemanticPointers as error codes.
2.  Upgraded 'stitcher-spec':
    - Modified 'InteractionContext' to use 'SemanticPointer' (violation_type) instead of 'ConflictType' enum.
    - Added 'pyneedle-pointer' dependency to the spec package.
3.  Monorepo integration:
    - Updated root 'pyproject.toml' to include the new analysis package in workspace, dev dependencies, and tool configurations (pytest, pyright, stitcher).

Note: This is a breaking change that requires subsequent refactoring of 'stitcher-application' and 'stitcher-cli' to adapt to the new InteractionContext structure.
~~~~~

### 下一步建议

现在状态已安全记录。根据路线图，我们应立即开始 **Phase 1: 修复 stitcher-application 核心逻辑**。

第一步是修改 `CheckAnalyzer` 和 `PumpAnalyzer`，让它们产出带有 `violation_type=L...` 的 `InteractionContext`。这将开始修复测试中出现的 `AttributeError`。如果你准备好了，请指示我开始。

---

好的，我们已经完成了整个迁移路线图的所有阶段，并且所有测试都已通过。现在是时候将这些变更作为一个完整的逻辑单元提交到版本控制系统中了。

我将生成一个 `[COMMIT]` 计划，其中包含 `git add` 和 `git commit` 指令。

## [COMMIT] refactor: 迁移 conflict_type 到 violation_type 指针并清理旧模型

### 用户需求

将完成的 `conflict_type` -> `violation_type` 迁移工作（包括核心逻辑、CLI、测试用例的重构以及旧模型的清理）提交到 Git。

### 评论

这次提交代表了冲突处理架构现代化的一个重要里程碑。通过引入 `SemanticPointer` 并移除过时的 Enum 模型，我们极大地提升了系统的灵活性和可维护性。代码库现在更加整洁，且完全对齐了新的设计规范。

### 目标

1.  将所有受影响的文件添加到 Git 暂存区。
2.  创建一个包含详细说明的提交，记录此次重构的范围和动机。

### 基本原理

根据 [COMMIT] 计划规范，此步骤仅执行 Git 操作，以持久化之前步骤中已经验证过的文件变更。

### 标签

#intent/refine #flow/ready #priority/high #comp/engine #comp/cli #comp/interfaces #scope/core #scope/api #task/domain/refactor #task/object/conflict-type #task/action/migration #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交重构变更

我们将所有修改过的文件添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/runners/check/analyzer.py
packages/stitcher-application/src/stitcher/app/runners/pump/analyzer.py
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
packages/stitcher-application/src/stitcher/app/handlers/noop_handler.py
packages/stitcher-cli/src/stitcher/cli/handlers.py
packages/stitcher-cli/src/stitcher/cli/interactive.py
packages/stitcher-spec/src/stitcher/spec/models.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-spec/src/stitcher/spec/interaction.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: migrate conflict_type to violation_type pointers and cleanup models

This commit completes the migration of the conflict handling system from a fixed Enum-based approach to a flexible SemanticPointer-based architecture.

Key changes:
- Updated `InteractionContext` to use `violation_type: SemanticPointer` instead of `conflict_type: ConflictType`.
- Refactored `CheckAnalyzer`, `PumpAnalyzer`, and `CheckResolver` to generate and consume semantic pointers (`L.check.state.*`, `L.check.issue.*`).
- Updated `TyperInteractionHandler` and `TyperInteractiveRenderer` in the CLI to support interactive resolution and rendering based on semantic pointers.
- Updated the entire test suite (unit and integration) to align with the new contract.
- Removed deprecated `ConflictType` Enum, `Resolution`, and `ResolutionPlan` data classes from `stitcher-spec`.
- Cleaned up the public API in `stitcher.spec.__init__`.

This transition decouples the core logic from concrete error definitions, enabling easier extensibility and better support for localized feedback in the future.
~~~~~

### 下一步建议

- **文档更新**: 既然核心架构发生了变化，建议更新开发者文档中关于“冲突处理”和“添加新检查规则”的部分，反映如何使用 `SemanticPointer`。
- **扩展检测规则**: 利用新架构的灵活性，现在可以更容易地添加更多细粒度的检查规则（如类型不匹配、参数重命名等），并为它们定义专门的 `L` 指针和交互逻辑。
