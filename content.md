好的，测试通过意味着逻辑迁移已经成功。现在我们将提交这些更改，完成重构任务。

## [COMMIT] refactor(app): 将重构逻辑从 CLI 下沉至 Application 层

### 用户需求
将重构命令的核心逻辑从 `stitcher-cli` 移动到 `stitcher-application` 包中，使 CLI 成为 Application 的薄包装层，并修复潜在的包循环依赖问题。

### 评论
这是一次重要的架构对齐。通过将逻辑下沉，我们不仅让 CLI 保持轻量，还使得重构功能可以被其他潜在的客户端（如 IDE 插件或自动化脚本）以编程方式调用，而无需通过命令行界面。

### 目标
1.  提交对 `pyproject.toml` 的修改，调整 `stitcher-refactor` 与 `stitcher-application` 之间的依赖关系。
2.  提交新创建的 `RefactorRunner` 及其在 `StitcherApp` 中的集成。
3.  提交已简化的 `stitcher-cli` 重构命令实现。

### 基本原理
遵循“CLI 是薄层包装”的原则。我们通过在 `run_refactor_apply` 方法中引入 `confirm_callback`，实现了在保持 Application 层纯净（不依赖 Typer）的同时，依然能支持 CLI 所需的交互式确认流程。

### 标签
#intent/refine #flow/ready #priority/medium #comp/cli #comp/application #scope/core #ai/instruct #task/domain/refactoring #task/object/logic-layer #task/action/move #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有涉及迁移和重构的文件添加到 Git 暂存区并进行提交。

~~~~~act
git_add
packages/stitcher-refactor/pyproject.toml
packages/stitcher-application/pyproject.toml
packages/stitcher-application/src/stitcher/app/runners/refactor.py
packages/stitcher-application/src/stitcher/app/runners/__init__.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(app): migrate refactor logic from CLI to application layer

This commit moves the core business logic of the 'refactor' command from 'stitcher-cli' into a new 'RefactorRunner' within 'stitcher-application'. 

Key changes:
- Created 'RefactorRunner' to encapsulate workspace discovery, graph loading, and transaction management.
- Integrated 'RefactorRunner' into 'StitcherApp' via 'run_refactor_apply' method.
- Implemented a callback-based confirmation mechanism to keep the application layer decoupled from CLI-specific UI libraries (Typer/Click).
- Fixed the dependency direction: 'stitcher-application' now depends on 'stitcher-refactor', and the reverse dependency was removed to prevent circularity.
- Simplified the CLI 'refactor' command to handle only parameter parsing and user interaction.

This ensures 'StitcherApp' remains the single source of truth for all orchestration logic while the CLI acts as a thin presentation layer.
~~~~~

### 下一步建议
- **清理与审查**: 审查 `stitcher-refactor` 中是否还有残留的对 `stitcher-application` 的隐式假设（例如文档字符串或注释）。
- **扩展重构能力**: 既然逻辑已经下沉，可以考虑在 `StitcherApp` 中增加更多原子化的重构 API，比如单独的 `plan_refactor` 和 `execute_refactor`。
