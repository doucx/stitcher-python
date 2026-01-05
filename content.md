好的，测试全部通过。这标志着 `stitcher-refactor` 已经具备了处理复杂 monorepo 结构以及同步维护测试代码的能力，极大地提升了重构引擎的实用价值。

我将生成一个 `[COMMIT]` 计划，将这些改进作为一个完整的逻辑单元提交到 Git 仓库。

## [COMMIT] feat(refactor): 支持 Monorepo 架构并实现测试文件自动更新

### 用户需求

增强重构引擎，使其能够自动识别 monorepo 结构（`packages/*/src`），并在执行文件移动等重构操作时，自动发现并同步更新所有相关引用，包括跨包的业务代码和各级测试文件。

### 评论

这是一个重大的架构增强。通过将重构的范围从单一包扩展到整个 monorepo，并从业务代码扩展到测试代码，我们确保了重构操作的原子性和完整性。这不仅减少了开发者的手动维护工作，也显著增强了其对工具的信任度。

### 目标

1.  将 `SemanticGraph` 和 `MoveFileOperation` 的增强代码添加到 Git 暂存区。
2.  将新创建的 monorepo 端到端测试用例添加到 Git 暂存区。
3.  创建一个详细的 Git Commit，记录本次功能的演进。

### 基本原理

根据 `d3-constraint-quipu-plan-script-rules`，在代码修改并通过验证后，我们通过一个独立的 `[COMMIT]` 计划来持久化这些变更。这确保了代码库历史的整洁和可追溯性。

### 标签

#intent/build #flow/done #priority/high #comp/engine #comp/tests #concept/state #scope/core #scope/dx #ai/delegate #task/domain/testing #task/object/monorepo-support #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交 Monorepo 与测试支持的变更

我将把所有修改和新增的文件添加到 Git，并提交。

~~~~~act
git_add
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(refactor): support monorepo and automatic test file updates

Enhanced the refactoring engine to handle complex project structures and ensure full-codebase consistency during transformations.

Key changes:
- Updated `SemanticGraph` to automatically discover and include source and test directories in monorepo structures (e.g., `packages/*/src`, `packages/*/tests`).
- Improved `MoveFileOperation`'s FQN resolution to correctly map file paths to module names across multiple source roots.
- Ensured that refactoring operations (like moving a file) now automatically find and update references within test files, whether they are package-local or top-level integration tests.
- Added comprehensive E2E tests to verify cross-package and test-file reference updates in a monorepo environment.

This change ensures that refactoring is a truly atomic and holistic operation, leaving the entire codebase in a consistent and green state.
~~~~~

### 下一步建议

- **探索大规模重构性能**: 对于拥有数十个包的超大型 monorepo，可以评估 `griffe` 加载全量图谱的性能表现，必要时引入多进程或缓存机制。
- **支持更多重构算子**: 现在的 monorepo 支持主要在 `MoveFileOperation` 中得到了验证，接下来可以为 `RenameSymbolOperation` 等其他算子编写类似的 monorepo 测试，确保一致性。
- **重构自身的 L 对象**: 作为一个实战演练，可以使用 `stitcher-refactor` 来优化项目内部的命名空间或结构。
