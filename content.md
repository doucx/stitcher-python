Excellent. Now that the feature is implemented and tested, I will create a commit to finalize this unit of work.

## [COMMIT] feat(check): Add interactive purging of dangling docs

### 用户需求
将已实现并通过测试的“交互式清除悬空文档”功能，作为一个完整的逻辑单元提交到版本控制中。

### 评论
这个功能及其配套的测试共同构成了一个完整的、可交付的工作单元。通过一个原子性的提交来记录这个变更，可以确保代码库历史的清晰和可追溯性。

### 目标
1.  将所有与此功能相关的已修改文件添加到 Git 暂存区。
2.  创建一个符合 Conventional Commits 规范的、内容详尽的 Git 提交。

### 基本原理
我们遵循“一个逻辑变更，一次提交”的最佳实践。该提交将把功能实现（spec, application, common, cli）和其验证（tests）捆绑在一起，形成一个独立的、有价值的变更集。

### 标签
#intent/build #flow/ready #priority/high
#comp/cli #comp/application #comp/spec #comp/tests #comp/common
#scope/ux #scope/dx
#ai/brainstorm
#task/domain/cli #task/object/interactive-check #task/action/feature-enhancement
#task/state/end #task/status/completed

---
### Script

#### Acts 1: 暂存所有相关变更

我们将所有被修改的文件添加到 Git 的暂存区。

~~~~~act
git_add
~~~~~
~~~~~
packages/stitcher-spec/src/stitcher/spec/models.py
packages/stitcher-application/src/stitcher/app/runners/check.py
packages/stitcher-common/src/stitcher/common/assets/needle/en/interactive.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/interactive.json
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/state.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/state.json
packages/stitcher-cli/src/stitcher/cli/handlers.py
packages/stitcher-cli/src/stitcher/cli/interactive.py
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~

#### Acts 2: 创建提交

现在，我们创建一个语义化的提交来记录这些变更。

~~~~~act
git_commit
~~~~~
~~~~~text
feat(check): Add interactive purging of dangling docs

Introduces a new interactive workflow in the `stitcher check` command to handle dangling documentation entries (previously reported as "extra" errors). This significantly improves the developer experience by allowing users to fix this common issue directly from the CLI without manually editing YAML files.

Key changes:
- **Spec**: Added `DANGLING_DOC` to `ConflictType` and `PURGE_DOC` to `ResolutionAction`.
- **Application**: The `CheckRunner` now identifies dangling docs as an interactive conflict. It has been enhanced to apply `PURGE_DOC` resolutions by removing entries from `.stitcher.yaml` files and deleting the file if it becomes empty.
- **CLI**: The interactive handler now presents a "[P]urge" option for `DANGLING_DOC` conflicts.
- **Common**: Added i18n assets for the new UI prompts and result messages.
- **Tests**: Included comprehensive integration tests to verify the purge, skip, and file-deletion-on-empty scenarios.
~~~~~

### 下一步建议
此功能已完成。我们可以考虑下一步工作，例如：
*   **更新文档**: 如果有用户手册或 `README.md`，可以更新它来介绍这个新的交互式功能。
*   **探索其他改进**: 审查 `check` 命令的其他错误类型，看看是否也可以提供类似的交互式修复方案。
