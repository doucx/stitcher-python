好的，既然测试已经验证了重构的正确性，我们现在将这些变更作为一个完整的逻辑单元提交到版本库。

## [COMMIT] refactor(workspace): merge stitcher-config into stitcher-workspace

### 用户需求
由于测试已通过，需要将合并 `stitcher-config` 与 `stitcher-workspace` 相关的变更创建 Git 提交。

### 评论
这是架构演进中的一个重要里程碑。通过消除包冗余，我们不仅简化了代码结构，还为后续更深层次的逻辑归一化（如合并根路径寻找算法）扫清了障碍。

### 目标
1. 暂存所有变更，包括新增文件、修改文件以及删除的 `stitcher-config` 包。
2. 创建一个符合规范的、详细的提交信息。

### 基本原理
根据“高保真工程公理协议”，我们将这次重构视为对系统物理实现与逻辑模型一致性的提升。在 `[COMMIT]` 计划中，我们仅执行 Git 操作，以确保提交的原子性和可追溯性。

### 标签
#intent/refine #flow/ready #priority/high #comp/workspace #comp/config #scope/core #ai/instruct #task/domain/architecture #task/object/package-merge #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将暂存所有受影响的文件并提交。由于涉及大量文件的删除和移动，我们将使用 `git add .` 来捕获整个工作区的状态变更。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(workspace): merge stitcher-config into stitcher-workspace

Merged the 'stitcher-config' package into 'stitcher-workspace' to reduce architectural redundancy and unify environment context management.

Key changes:
- Moved config loading logic from 'stitcher-config' to 'stitcher/workspace/config.py'.
- Renamed 'stitcher/workspace/workspace.py' to 'stitcher/workspace/core.py' for better internal structure.
- Updated all monorepo imports from 'stitcher.config' to 'stitcher.workspace'.
- Updated all pyproject.toml files to reflect the removal of the separate config package.
- Deleted the redundant 'packages/stitcher-config' directory.

This consolidation ensures a Single Source of Truth for project root discovery and configuration loading, simplifying the initialization of 'StitcherApp'.
~~~~~

### 下一步建议

架构重组的物理阶段已完成。接下来，我们可以进行更有意义的**逻辑归一化**：

- **算法去重**: 观察到 `find_workspace_root` (来自原 workspace) 和 `_find_pyproject_toml` (来自原 config) 逻辑高度相似。
- **重构建议**: 在 `packages/stitcher-workspace/src/stitcher/workspace/config.py` 中，废弃 `_find_pyproject_toml`，改为调用 `core.py` 中的 `find_workspace_root`。这将使系统在寻找根目录时只有一种声音。

如果你准备好了，我们可以开始这个“照明”式的逻辑清理任务。
