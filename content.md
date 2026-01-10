好的，任务 1.5 及其润色工作已经完成。我们现在将这些更改作为一个完整的逻辑单元提交。

## [COMMIT] feat(cli): 集成增量索引扫描器并添加 `stitcher index build` 命令

### 用户需求
用户需要能够通过命令行界面启动项目的语义索引构建和更新，并且希望获得多语言的帮助文档和进度反馈。

### 评论
这标志着 Stitcher 2.0 第一阶段（语义中枢构建）的正式收官。我们现在拥有了一个可以运行的、具有增量扫描能力的持久化索引系统。

### 目标
1.  提交 `IndexRunner` 及其在 `StitcherApp` 中的集成代码。
2.  提交 `index` CLI 及其 `build` 子命令的实现。
3.  提交英文和中文的 I18N 资源文件。

### 基本原理
*   **端到端贯通**: 将底层的 `WorkspaceScanner` 通过 `IndexRunner` 暴露给 `StitcherApp`，最后由 `stitcher-cli` 进行包装。
*   **国际化支持**: 通过 Needle 协议提供了完整的 EN/ZH 支持。
*   **增量反馈**: CLI 会展示详细的统计信息（新增、更新、删除、跳过），让用户了解索引的最新状态。

### 标签
#intent/build #flow/ready #priority/high 
#comp/cli #comp/runtime #concept/state #scope/ux 
#ai/instruct 
#task/domain/storage #task/object/cli-command #task/action/integration 
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交集成代码与国际化资源

我们将集成逻辑和资源文件添加到暂存区。

~~~~~act
git_add
packages/stitcher-common/src/stitcher/common/assets/needle/en/index/run.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/index/run.json
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/command.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/command.json
packages/stitcher-application/src/stitcher/app/runners/index.py
packages/stitcher-application/src/stitcher/app/runners/__init__.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/src/stitcher/cli/commands/index.py
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): integrate incremental index scanner and add 'index build' command

Completed the integration of the `stitcher-index` subsystem into the main application and CLI.

Key changes:
- Created `IndexRunner` in `stitcher-application` to orchestrate database initialization and workspace scanning.
- Integrated `WorkspaceScanner`, `IndexStore`, and `PythonAdapter` into the `StitcherApp` composition root.
- Added a new `index` command group to the CLI with a `build` subcommand.
- Provided comprehensive internationalization (I18N) support for the new command, including help text and progress logs in both English and Chinese.
- Ensured consistent directory structure by hardcoding the index database location to `.stitcher/index/index.db`.

Users can now run `stitcher index build` to maintain a persistent, high-performance semantic index of their projects.
~~~~~

### 下一步建议

我们已经圆满完成了 **阶段 1：语义中枢构建**。

接下来的宏观目标是 **阶段 2：全系统集成 (System-Wide Integration)**。
其核心任务是将现有的命令（`check`, `refactor`, `stubgen` 等）从“即时扫描模式”切换到“索引模式”。

我建议从 **任务 2.1 (重构 `CheckRunner`)** 开始，因为它能最直观地体现出索引带来的性能优势（将 $O(N)$ 的文件解析变为 $O(1)$ 的数据库查询）。如果你准备好了，请告知我，我们将启动阶段 2 的第一个计划。
