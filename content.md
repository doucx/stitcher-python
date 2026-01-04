好的，既然测试已全部通过，我们将把这次关于 `MoveFileOperation` 的完整实现及相关修复作为一个逻辑单元进行提交。

## [COMMIT] feat(refactor): implement MoveFileOperation with sidecar synchronization

### 用户需求
用户在验证了 `MoveFileOperation` 的功能和相关 Bug 修复后，要求创建一个 Git 提交以持久化这些变更。

### 评论
这次提交涵盖了重构引擎的一个核心功能（文件移动）以及对基础设施（Import 解析）的重要增强。通过解决 Sidecar 同步和导入解析的边界情况，我们显著提升了 `stitcher-refactor` 的健壮性。

### 目标
1.  将所有相关修改（核心代码与测试）添加到 Git 暂存区。
2.  创建一个符合 Conventional Commits 规范的提交，详细说明所做的与集成测试。

### 基本原理
我们通过以下三个层面的协同工作达成了目标：
1.  **解析层**: 增强 Visitor，利用 LibCST 的 helper 函数解析模块路径。
2.  **逻辑层**: 移除 `RenameSymbolOperation` 的过早优化，并让 `MoveFileOperation` 显式管理其移动文件的边车内容转换。
3.  **执行层**: 采用“先修改内容，后移动改进和修复。

### 基本原理
按照 Quipu 协议，我们将所有验证过的非稳定变更（WIP）聚合为一个稳定的工作单元（COMMIT）。这确保了项目历史的清晰性和可追溯性。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/refactor #comp/tests #scope/core #ai/instruct #task/domain/refactor #task/object/git-commit #task/action/submit #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交重文件”的事务顺序，确保操作的幂等性和正确性。

### 标签
#intent/build #flow/ready #priority/high #comp/refactor #concept/transaction #scope/core #ai/构引擎的变更

我们将把涉及 `SemanticGraph` 增强、`MoveFileOperation` 实现、`RenameSymbolOperation` 修复以及相关测试的文件全部提交。

~~~~~act
git_add .
~~~~~

---

### Script

#### Acts 1: 提交重构引擎的核心增强src/stitcher/refactor/operations/move_file.py
~~~~~act
git_commit
~~~~~
~~~~~text
feat(refactor): implement MoveFileOperation and enhance import resolution

This commit introduces the `MoveFileOperation` to the refactoring engine,
enabling atomic file moves that synchronize both source code references 
and sidecar metadata (YAML docs and JSON signatures).

Key improvements: updates.

Key improvements:
- Implemented MoveFileOperation with path-to-FQN derivation.
- Enhanced _UsageVisitor in SemanticGraph to accurately resolve absolute and
  relative imports using LibCST helpers, enabling cross-file refactoring.
- Fixed a bug in RenameSymbolOperation where sidecar updates were skipped
  if the symbol's short name remained unchanged (critical for file moves).
- Fixed the execution order in MoveFileOperation to ensure content updates
  are applied before files are moved on disk.
- Added comprehensive unit tests for import resolution and integration tests
  for end-to-end move scenarios.
~~~~~

### 下一步建议
- **性能优化**: 随着重构操作变得复杂，可以考虑对 `SemanticGraph` 的全量扫描进行增量优化。
- **UI 集成**: 下一步可以将这些操作暴露给 CLI，允许用户通过 `stitcher refactor` 命令行界面执行这些强大的操作。
