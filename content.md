好的，任务 1.4 和 1.5 的开发、集成以及国际化润色已经全部完成。现在我将生成一个 `[COMMIT]` 计划来正式提交这些更改。

## [COMMIT] feat(cli): 完整集成持久化索引系统并提供 Python 支持

### 用户需求
完成任务 1.4 和 1.5：实现 Python 语言适配器并将增量索引构建功能集成到 CLI 中。

### 评论
这标志着 Stitcher 2.0 第一阶段“语义中枢构建”的圆满完成。我们现在拥有了一个能够感知 Python 语义、支持增量更新、并且可以通过命令行进行管理的持久化知识库。

### 目标
1.  提交 `PythonAdapter` 及其 SURI 生成逻辑，支持将 Python AST 投影到索引记录。
2.  提交 `IndexRunner` 及其在 `StitcherApp` 中的集成逻辑。
3.  提交 `stitcher index build` 命令及其多语言支持。

### 基本原理
*   **投影模式 (Projection Pattern)**: 通过封装现有的 `GriffePythonParser`，我们确保了索引数据与代码分析逻辑的单一事实来源 (SSoT)。
*   **组合根集成**: 在 `StitcherApp` 中统一装配数据库、扫描器和适配器，确保了架构的整洁和可扩展性。
*   **语义唯一性**: 引入 SURI 规范，确保了跨文件、跨语言的符号标识一致性。

### 标签
#intent/build #flow/ready #priority/high 
#comp/cli #comp/runtime #comp/index #concept/state #scope/core 
#ai/instruct 
#task/domain/storage #task/object/index-system #task/action/integration 
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交适配器与 CLI 集成代码

我们将所有涉及的文件添加到 Git 暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-python-adapter/pyproject.toml
packages/stitcher-python-adapter/src/stitcher/adapter/python/uri.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
packages/stitcher-python-adapter/tests/test_index_adapter.py
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
feat(cli): integrate persistent index system with Python support

Completed the integration of the semantic indexing subsystem (Tasks 1.4 & 1.5):

1. Python Adapter: Implemented `PythonAdapter` using a projection pattern. It maps `ModuleDef` objects to `SymbolRecord` and `ReferenceRecord` types. 
2. SURI Generation: Introduced `SURIGenerator` for consistent, cross-platform `py://` URIs using dotted fragments (e.g., `py://path/to/file.py#ClassName.method`).
3. App Integration: Enhanced `StitcherApp` to act as the composition root for `DatabaseManager`, `IndexStore`, `WorkspaceScanner`, and `IndexRunner`.
4. CLI Commands: Exposed `stitcher index build` for incremental index updates.
5. Internationalization: Added full English and Chinese support for index logs and CLI help texts.

The system now correctly persists Python symbol identity, type, and signature hashes into a local SQLite-WAL database, providing a high-performance foundation for cross-file analysis and refactoring.
~~~~~

### 下一步建议

**第一阶段：语义中枢构建** 已正式宣告结束。

我们现在进入 **阶段 2: 全系统集成 (System-Wide Integration)**。
首要任务是 **任务 2.1: 重构 `stitcher-application` 中的 `CheckRunner`**。

目前的 `CheckRunner` 仍然依赖于实时解析和手动哈希对比。我们的目标是将其改造为：**完全依赖索引查询符号的哈希值**。如果文件在索引中被标记为 Clean（状态为 1），`check` 命令应实现亚秒级的瞬时返回。

如果你准备好了，我们可以开始讨论 `CheckRunner` 的重构方案。
