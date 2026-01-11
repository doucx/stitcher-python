好的，我们已经完成了“从启发式猜测到确定性链接”路线图的前几个关键阶段，包括工具集中化、作用域分析抽象以及数据模型的初步解耦。现在是时候将这些基础性的重构作为一个完整的逻辑单元提交了。

## [COMMIT] refactor(index): 实现扫描-链接架构的第一阶段，解耦 SURI 猜测

### 用户需求
将目前完成的一系列架构改进（Phase A, B 和 Phase 1）提交到版本控制系统。

### 评论
这次提交标志着 Stitcher 架构的一个重大转型。我们成功地从“试图在扫描时解决一切”的单相模型，转变为“先诚实记录，后延迟链接”的二相模型。这为解决跨文件引用歧义、支持复杂项目布局提供了根本性的技术支持。代码库现在更加整洁，职责划分也更加清晰。

### 目标
1.  将所有新增和修改的文件添加到 Git 暂存区。
2.  创建一个符合 Conventional Commits 规范的、详尽的提交记录。

### 基本原理
遵循 `d3-quipu-plan-script-rules`，我们将提交操作放在一个独立的 `[COMMIT]` 计划中，以确保文件系统变更已稳定。这次提交记录了我们在消除“启发式猜测”方面的初步胜利。

### 标签
#intent/refine #flow/ready #priority/high #comp/index #comp/refactor #comp/python-analysis #scope/core #ai/instruct #task/domain/architecture #task/object/commit-milestone #task/action/git-commit #task/state/end

---

### Script

#### Acts 1: 提交架构重构

我们将所有涉及 FQN 统一、作用域抽象和 Schema 解耦的文件添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-python-analysis/src/stitcher/python/analysis/utils.py
packages/stitcher-python-analysis/tests/unit/test_utils.py
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
packages/stitcher-python-analysis/src/stitcher/python/analysis/scope.py
packages/stitcher-python-analysis/tests/unit/test_scope.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
packages/stitcher-index/src/stitcher/index/schema.sql
packages/stitcher-index/src/stitcher/index/types.py
packages/stitcher-index/src/stitcher/index/store.py
packages/stitcher-python-analysis/src/stitcher/python/analysis/cst/usage_visitor.py
packages/stitcher-index/tests/unit/test_store.py
packages/stitcher-python-adapter/tests/integration/test_index_adapter_references.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(index): implement Scan-Link phase 1 and decouple SURI guessing

This commit marks the first major milestone in the "Deterministic Linking" roadmap, shifting from a single-pass scan with heuristic guessing to a robust two-phase architecture.

Key changes:
- Centralized FQN calculation logic in a new `stitcher-python-analysis.utils` module, providing a single source of truth for path-to-package mapping.
- Abstracted scope analysis into `ScopeAnalyzer`, unifying how the refactor and index engines resolve local symbol tables for the CST visitor.
- Redesigned database schema for `symbols` and `references` to separate logical intent (FQN) from physical links (SURI).
- Updated `PythonAdapter` and `IndexStore` to record raw FQN targets during the scan phase while leaving SURI IDs null for later resolution.
- Enforced data integrity via SQLite foreign key constraints, preventing dangling references.
- Updated and strengthened the test suite to align with the new decoupled architecture.

This infrastructure is the prerequisite for the upcoming 'Linker' component, which will resolve cross-file references with absolute certainty.
~~~~~

### 下一步建议
- **立即执行**: 请务必手动删除 `.stitcher/index/index.db` 文件。因为我们修改了 Schema，旧的数据库文件会导致 SQL 错误。
- **展望 Phase 3**: 我们的下一步任务是编写 `Linker` 组件。它将通过执行 SQL 联表查询或内存匹配，将 `references` 表中空的 `target_id` 与 `symbols` 表中正确的 `id` (SURI) 缝合在一起。
