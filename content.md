好的，所有的功能开发和测试验证都已经顺利完成。现在我将生成一个 `[COMMIT]` 计划，将这些变更作为一个完整的逻辑单元提交到仓库中。

## [COMMIT] feat: 实现 stitcher hydrate 命令与冲突解决机制

### 用户需求
将已实现的 `stitcher hydrate` 功能及其冲突解决模式（Default, Force, Reconcile）和相关的集成测试提交到代码库。

### 评论
该功能不仅提升了开发者的日常工作流效率，还通过灵活的冲突解决模式（特别是为 AI 场景设计的 `--reconcile` 模式）极大地增强了工具在现代开发环境下的适应能力。

### 目标
1.  将所有相关的文件变更添加到 Git 暂存区。
2.  创建一个包含详细说明的 Git 提交。

### 基本原理
遵循“原子提交”原则，将属于同一个功能特性的变更（资产、逻辑、测试）合并在一个提交中。

### 标签
#intent/build #flow/ready #comp/cli #comp/runtime #comp/tests #scope/ux #task/domain/cli #task/object/command-hydrate #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有涉及到的文件添加到暂存区并执行提交。

~~~~~act
git_add
packages/stitcher-common/src/stitcher/common/assets/needle/en/hydrate/main.json
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/main.json
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/src/stitcher/cli/main.py
tests/integration/test_hydrate_command.py
tests/integration/test_check_conflict.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): implement stitcher hydrate command with conflict resolution

Added the 'hydrate' command to enable smart syncing of docstrings from source code to YAML files.

Key improvements:
- Implemented three conflict resolution strategies: Default (abort), --force (code-first), and --reconcile (YAML-first).
- Enhanced 'check' command to detect and report content conflicts between source and YAML.
- Integrated with 'strip' logic to allow one-step 'hydrate and clean' workflow.
- Added comprehensive integration tests for all hydration scenarios.

This command bridges the gap between 'init' and 'check', allowing developers to write docs in code during development and sync them to the authoritative YAML source seamlessly.
~~~~~

### 下一步建议
- **文档更新**: 建议更新项目的 `CONTRIBUTING.md` 或用户手册，详细解释 `hydrate` 命令的三种模式及其适用场景，特别是 `--reconcile` 如何帮助管理 AI 生成的代码。
- **自我管理 (Dogfooding)**: 可以在 `stitcher-python` 项目自身上试用 `hydrate --strip` 流程，以验证其在真实 Monorepo 环境下的表现。
