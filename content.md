1.  **`stitcher generate` 的使命：高保真还原**
    *   它的核心原则是 **“忠实于源码”**。它的任务是创建一个与 `.py` 文件接口**完全等价**的 `.pyi` 描述文件。
    *   在源码 (`.py`) 中，`_private_method` 是一个真实存在的、可被调用的成员（至少在模块或类内部）。
    *   因此，为了让静态分析工具（如 Pyright）能够正确理解模块的**完整接口**（包括内部接口），`generate` 命令必须在 `.pyi` 文件中也生成 `_private_method` 的定义。
    *   如果 `generate` 删除了私有成员，那么当你在同一个包的其他地方调用这个私有成员时，类型检查器就会报错，说“`_private_method` 不存在”，这显然是错误的。

2.  **`stitcher check` 的使命：执行文档策略**
    *   它的核心原则是 **“执行项目规范”**。它不关心生成什么，只关心“我们团队是否要求为这个东西写文档”。
    *   我们刚刚做的修改，正是定义了这样一个策略：“对于公开 API (`public_api`)，我们**要求**有文档（否则警告）；对于私有 API (`_private_api`)，我们**允许**有文档，但**不强制要求**。”

---

既然所有测试，包括新加的策略回归测试，都已通过，我们可以将这一系列关于 `check` 命令的改进作为一个完整的逻辑单元提交。

## [COMMIT] fix(core): Refine check policy to allow private docs and downgrade missing docs

### 用户需求
`stitcher check` 命令需要变得更加实用：
1.  不应因 YAML 文件中包含合法的私有成员文档而报错。
2.  不应因公开 API 缺少文档而阻断 CI 流程。

### 评论
这是一次关键的可用性改进。通过将 `check` 命令的行为从“强制全覆盖”调整为“保证正确性，鼓励覆盖率”，我们极大地降低了在现有项目中引入 `stitcher` 的门槛，使其成为一个辅助工具而非开发负担。

### 目标
1.  提交对 `DocumentManager` 中 Key 提取逻辑的重构。
2.  提交对 `StitcherApp` 中 `run_check` 判定逻辑的修改。
3.  提交对消息资源文件的更新。
4.  提交对受影响的测试用例的修正。
5.  提交新增的策略回归测试套件。

### 基本原理
通过实现“分层 Key 提取”（区分 Public 和 All Keys），我们能够精确地判定 `MISSING`（公开的但没有文档）和 `EXTRA`（文档指向完全不存在的代码）。同时，通过在应用层将 `MISSING` 路由到 `bus.warning`，我们实现了策略上的降级，使其不再影响命令的最终退出状态码。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #comp/tests #scope/core #ai/instruct #task/domain/linter #task/object/check-logic #task/action/refine #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交所有相关的代码和测试修改

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/main.json
packages/stitcher-io/tests/test_stub_generator.py
tests/integration/test_check_command.py
tests/integration/test_check_policy.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(core): Refine check policy to allow private docs and downgrade missing docs

This commit overhauls the `stitcher check` command's behavior to make it more pragmatic for real-world projects, especially during initial adoption (dogfooding).

Key Changes:
1.  **Private Member Docs Allowed**: The checker no longer flags docstrings for private members (e.g., `_my_func`) as 'EXTRA' errors. It now correctly validates that the documented member exists in the code, regardless of its visibility.
2.  **Missing Docs are Warnings**: The check for missing documentation on public APIs has been downgraded from a failure-inducing ERROR to a non-blocking WARNING. This allows teams to incrementally document their codebase without breaking CI.
3.  **New Regression Tests**: Added `test_check_policy.py` to specifically lock in these new behaviors and prevent future regressions.
~~~~~

### 下一步建议
Dogfooding 的核心技术障碍已经清除。现在是时候正式开始项目自身的文档化工作了：
1.  **重新初始化**: 运行 `stitcher init` 来根据新的、更干净的规则生成所有 `.stitcher.yaml` 文件。
2.  **文档完善**: 逐一查看 `stitcher check` 报告的 `MISSING` 警告，并开始为核心的公共 API（如 `StitcherApp`, `DocumentManager` 等）撰写高质量的文档。
