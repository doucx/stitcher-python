太棒了。测试通过意味着我们的“脑手分离”手术已经圆满完成。

现在，我们将正式提交这一系列重构，确立 `stitcher-analysis` 作为项目核心语义大脑的地位。

## [COMMIT] refactor(analysis): migrate SemanticGraph from refactor to analysis

### 用户需求
由于测试已经通过，需要将 `SemanticGraph` 的迁移、依赖更新以及测试重定位等一系列重构操作作为一个逻辑单元提交到 Git 仓库。

### 评论
这是一次重要的架构对齐。通过将“代码理解能力”从“重构执行器”中剥离并放入“分析引擎”，我们不仅消除了代码冗余，还为 `stitcher-analysis` 未来实现基于全局语义的架构检查（如跨文件的类型检查、继承链分析等）扫清了障碍。

### 目标
1.  将 `stitcher-analysis` 的新文件和修改后的 `pyproject.toml` 加入暂存区。
2.  将 `stitcher-refactor` 的修改（包括删除旧文件和更新 `pyproject.toml`）加入暂存区。
3.  创建一个描述详尽的提交记录。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules` 指令，我们将 Git 操作放在一个独立的 `[COMMIT]` 计划中。这确保了在所有文件修改都经过测试验证（如用户确认测试通过）之后，再将它们固化到项目历史中。

### 标签
#intent/refine #flow/ready #priority/high #comp/analysis #comp/refactor #scope/core #ai/instruct #task/domain/refactor #task/object/dependency-graph #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交重构变更

我们将所有涉及到的包和测试文件的变更添加到 Git 暂存区并提交。

~~~~~act
git_add
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(analysis): migrate SemanticGraph from refactor to analysis

Performs a strategic architectural split by moving the 'brain' (semantic code understanding) from 'stitcher-refactor' to 'stitcher-analysis'.

Key changes:
- Relocated 'SemanticGraph' to 'stitcher.analysis.semantic.graph'.
- Extracted 'SymbolNode' into 'stitcher.analysis.semantic.models' for better separation of concerns.
- Updated 'stitcher-analysis' to depend on 'griffe' and 'stitcher-workspace'.
- Updated 'stitcher-refactor' to depend on 'stitcher-analysis' and removed direct 'griffe' dependency.
- Relocated semantic graph unit tests to the analysis package.

This migration enables the check/pump engines to leverage full semantic awareness for advanced diagnostics, while keeping the refactor engine focused on transactional code modification.
~~~~~

### 下一步建议

- **探索高级检查**: 既然 `analysis` 已经拥有了 `SemanticGraph`，你可以考虑为 `check` 命令添加一条新规则，例如：“验证所有的公共接口是否有对应的类型提示”。
- **继续 Phase 2**: 我们已经为 `analysis` 引入了语义分析能力，现在可以按照之前的路线图，开始引入 `networkx` 来构建宏观的依赖图谱，实现循环依赖检测。
