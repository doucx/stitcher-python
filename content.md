好的，我们已经成功解决了所有的循环依赖和架构层级的违例，并通过了 Pyright 的检查。现在我将生成一个计划，将这些更改作为一个完整的工作单元进行提交。

## [COMMIT] fix: resolve circular dependencies and architectural violations

### 用户需求
将之前为了修复循环依赖和架构违例所做的所有代码更改提交到 Git 仓库。

### 评论
这次重构非常重要，它通过消除包内和包间的循环引用，显著提升了系统的稳定性和可维护性。我们不仅修复了表象的导入问题，还纠正了一个关键的架构分层错误（Dependency Inversion），确保了底层操作不再依赖高层引擎。

### 目标
1. 将所有修改过的文件添加到 Git 暂存区。
2. 创建一个详细说明所有更改及其架构意义的提交记录。

### 基本原理
遵循 `[COMMIT]` 规范，本计划仅包含 Git 操作，以确保代码在被永久记录前已经过验证。我们将所有相关的架构修复合并为一个原子提交。

### 标签
#intent/fix #flow/ready #priority/high #comp/refactor #comp/lang-sidecar #scope/core #ai/instruct #task/domain/testing #task/object/architecture-linting #task/action/bug-fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有受影响的文件添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
packages/stitcher-refactor/src/stitcher/refactor/migration/spec.py
packages/stitcher-refactor/src/stitcher/refactor/migration/__init__.py
packages/stitcher-refactor/src/stitcher/refactor/utils.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix: resolve circular dependencies and architectural layering violations

This commit addresses several critical architectural issues identified by the 'stitcher check architecture' command across the stitcher-refactor and stitcher-lang-sidecar packages.

Key Changes:
- Package-Internal Cycles: Converted absolute imports to relative imports in sidecar adapter and refactor planner to break __init__.py cycles.
- Layering Violation: Moved the 'path_to_fqn' utility from 'engine/utils.py' to a new common 'refactor/utils.py'. This allows low-level refactoring operations to use the utility without creating an illegal dependency on the high-level engine.
- High-Level Decoupling: Moved user-facing type aliases (Rename, Move) from 'migration/spec.py' to 'migration/__init__.py'. This prevents the core data structures in 'spec.py' from depending on concrete operation implementations.
- Bug Fix: Resolved a NameError in 'MigrationSpec.add_map' introduced during refactoring by using a local, function-scoped import.
- Cleanup: Updated all import paths throughout the refactor package to reflect the utility relocation.

These changes result in a cleaner, strictly hierarchical dependency graph, satisfying both the internal architecture linter and external type checkers (Pyright).
~~~~~

### 下一步建议
- **架构监控**: 建议在 CI 流程中集成 `stitcher check architecture`，以防止未来再次引入类似的循环依赖。
- **文档更新**: 如果有相关的内部架构文档，建议同步更新关于 `migration` 包设计模式和 `utils` 放置规范的说明。
