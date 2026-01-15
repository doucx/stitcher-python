好的，既然重构和测试都已经顺利通过，我们现在将这些变更作为一个完整的逻辑单元提交到版本库中。

## [COMMIT] refactor: 迁移 FeedbackBus 及其测试至独立的 stitcher-bus 包

### 用户需求
将 `stitcher-bus` 包的创建、代码及测试的迁移、以及相关的项目配置变更提交到 Git。

### 评论
这次重构成功地实现了关注点分离，将消息总线逻辑从通用的 `stitcher-common` 中剥离出来。这不仅使架构更加清晰，也为后续更复杂的事件驱动逻辑提供了专门的演进空间。

### 目标
1. 将所有新增和修改的文件添加到暂存区。
2. 创建一个符合 Conventional Commits 规范的、详细的提交记录。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules`，我们在一个独立的 `[COMMIT]` 计划中执行 Git 操作。这确保了所有的代码变更在被永久记录之前已经过验证。

### 标签
#intent/refine #flow/ready #priority/high 
#comp/build #comp/common #comp/tests #scope/core 
#ai/instruct
#task/domain/refactoring #task/object/stitcher-bus #task/action/relocation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将新包 `stitcher-bus`、迁移脚本以及所有受影响的配置文件提交。

~~~~~act
git_add
packages/stitcher-bus
packages/stitcher-common/pyproject.toml
pyproject.toml
migrations/004_move_bus_to_dedicated_package.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: extract message bus to dedicated 'stitcher-bus' package

This commit completes the relocation of the message bus infrastructure:
- Created the 'stitcher-bus' package as a new workspace member.
- Moved FeedbackBus and associated protocols from 'stitcher-common' to 'stitcher-bus'.
- Migrated unit tests and sidecar metadata to the new package.
- Updated root 'pyproject.toml' and 'stitcher-common' dependencies to reflect the new architecture.
- Included the refactoring migration script used for FQN updates.

This move improves modularity and clarifies the project's dependency graph.
~~~~~

### 下一步建议
- **清理脚本**: 既然重构已经完成并提交，如果你不需要保留迁移记录，可以考虑在未来清理 `migrations/` 目录。
- **文档更新**: 建议检查项目根目录的架构文档或 README，确保其中关于包结构的描述是最新的。
- **持续集成**: 触发一次全量 CI 运行，确保跨包的 `uv` 依赖解析在干净的环境中依然稳健。
