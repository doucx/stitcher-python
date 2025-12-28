好的，我们来将这些已经完成的重构和功能实现提交。这个提交将包含 CLI 模块化重构和 `viewdiff` 功能的核心逻辑。

## [COMMIT] feat(cli, app): 实现 viewdiff 并重构 CLI 以实现模块化

### 用户需求
1.  在交互式冲突解决中，为用户提供代码/文档的差异（`viewdiff`）。
2.  将 `stitcher-cli` 的实现从单个大文件重构为模块化的 `commands` 和 `factories` 结构。

### 评论
这是一个重要的里程碑。`viewdiff` 功能极大地提升了开发者体验，将 `stitcher` 从一个状态检查工具转变为真正的开发辅助工具。同时，对 CLI 的架构重构遵循了“关注点分离”原则，为未来的功能扩展（如更复杂的 UI 交互）打下了坚实、可维护的基础。

### 目标
1.  提交 `viewdiff` 的核心实现，包括在 `StitcherApp` 中生成 diff 数据和在 `TyperInteractionHandler` 中渲染 diff。
2.  提交 CLI 的新架构，包括 `commands/` 子包和 `factories.py` 模块。
3.  提交所有相关的测试重构和新增的 `viewdiff` 测试。

### 基本原理
通过一个原子提交，将 `viewdiff` 功能及其促成的架构重构作为一个完整的逻辑单元记录到版本历史中。提交信息详细记录了功能价值和重构的动机与具体方案，为后续的代码维护者提供了清晰的上下文。

### 标签
#intent/build #intent/refine #flow/ready #priority/high #comp/cli #comp/runtime #comp/tests #scope/ux #scope/dx #ai/instruct #task/domain/ui #task/object/viewdiff #task/action/implementation #task/state/end

---

### Script

#### Acts 1: 暂存所有相关变更

我们将暂存所有应用层、CLI 层、规约层以及测试文件的变更。

~~~~~act
git_add
packages/stitcher-application/
packages/stitcher-cli/
packages/stitcher-spec/
packages/stitcher-scanner/tests/
packages/stitcher-io/tests/
packages/stitcher-common/tests/
packages/stitcher-config/tests/
~~~~~

#### Acts 2: 创建提交

现在，我们将这些变更作为一个逻辑单元提交。

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli, app): Implement viewdiff and refactor CLI for modularity

Implements the `viewdiff` feature, providing users with contextual diffs during interactive conflict resolution in `check` and `pump` commands. This resolves a major DX pain point where users had to manually inspect files to understand conflicts.

- **Check Diff**: For `SIGNATURE_DRIFT` and `CO_EVOLUTION`, a diff of the function signature is now displayed.
- **Pump Diff**: For `DOC_CONTENT_CONFLICT`, a diff between the source and YAML docstrings is shown.
- **UI**: Diffs are rendered directly in the terminal with color-coded additions and deletions.
- **Infrastructure**: The `Fingerprint` model now stores signature text alongside hashes to enable diff generation.

To support this and improve maintainability, the `stitcher-cli` package was significantly refactored.

**CLI Refactoring Details:**

The CLI was restructured from a single "God file" (`main.py`) into a modular architecture to eliminate code duplication and improve extensibility.

1.  **Command Modularization**: All command logic was moved from `main.py` into a new `commands/` directory, with files organized by complexity (`check.py`, `pump.py`, `basics.py`).
2.  **Factory Pattern**: A new `factories.py` module was introduced to centralize the creation of `StitcherApp` and `InteractionHandler` instances, removing boilerplate from command files.
3.  **Slim Entrypoint**: `main.py` is now a lean entry point responsible only for Typer app setup and command registration.

This refactoring paves the way for future UI enhancements and makes the CLI codebase cleaner and easier to maintain.
~~~~~
