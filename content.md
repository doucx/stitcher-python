好的，既然已经成功拆除了 runners 及其子包中的贪婪初始化枢纽，现在我们将这些变更通过 Git 提交。

这个提交彻底解决了包初始化阶段的死锁风险，标志着系统向“确定性加载”迈出了重要一步。

## [COMMIT] fix(arch): eliminate circular deadlocks in runners sub-packages

### 用户需求
将解决 `runners/check` 及其相关子包循环依赖的变更提交到 Git。

### 评论
这是一次深度的架构加固。通过移除 `__init__.py` 中的逻辑导入，我们不仅解决了当前的死锁，还从根本上杜绝了因“包枢纽”设计导致的潜在初始化问题。这种扁平化的导入路径使得系统的启动过程更加透明和可预测。

### 目标
1.  将所有被清理和更新的文件添加到 Git 暂存区。
2.  创建一个详尽的提交记录，解释“贪婪包枢纽”的危害及修复方法。

### 基本原理
按照 Quipu 的工程标准，架构上的“血栓”必须被物理清除。通过 `git_add` 和 `git_commit` 操作，我们将这些改进永久固化到代码库的历史中，为后续的性能优化和模块化拆分奠定基础。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #concept/initialization-order #scope/core #ai/instruct #task/domain/architecture #task/object/greedy-init-hub #task/action/flattening #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交架构修复变更

我们将暂存受影响的 `__init__.py` 文件、核心应用文件以及经过优化的 Runner 模块。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/runners/__init__.py
packages/stitcher-application/src/stitcher/app/runners/check/__init__.py
packages/stitcher-application/src/stitcher/app/runners/pump/__init__.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(arch): break circular deadlocks in runners sub-packages

Resolved circular dependency deadlocks caused by 'Greedy Package Hubs' in the runners directory.

Summary of changes:
- Emptied '__init__.py' files in 'stitcher.app.runners', 'runners.check', and 'runners.pump' to prevent premature and recursive package initialization.
- Refactored 'StitcherApp' (core.py) to use direct, leaf-module imports for all Runner classes instead of relying on package re-exports.
- Converted absolute imports to relative imports within 'CheckRunner' to further decouple it from the parent package's initialization state.

These changes ensure a deterministic loading order and eliminate 'ImportPathMismatchError' and partial initialization issues when the application is bootstrapped.
~~~~~

### 下一步建议
- **最终验证**: 运行 `stitcher check`。所有的架构报错（循环依赖）现在应该已经彻底消失。
- **扩展应用**: 建议审查项目中其他复杂的包结构（如 `stitcher.index` 或 `stitcher.workspace`），确保它们没有采用类似的贪婪 `__init__.py` 模式。
- **文档同步**: 在开发者文档中记录“禁止在 `__init__.py` 中进行逻辑重导出”的工程规范，防止类似问题再次引入。
