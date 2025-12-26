这是一个 `[COMMIT]` 计划，用于提交上一步的修复和重构工作。

## [COMMIT] fix(core, cli): 移除 CLI 中错误的 patch 并为 Needle 启用懒加载

### 用户需求
将上一个计划中执行的文件修改（移除抽象泄漏的 `render_to_string_patch`、实现 `Needle` 运行时懒加载）作为一个完整的逻辑单元提交。

### 评论
本次提交包含了两个核心架构修正：
1.  修复了 `stitcher-cli` 中错误的 API 调用和冗余的 `bus.render_to_string` 补丁，使 CLI 依赖于 `MessageBus` 的原生功能。
2.  在 `stitcher-needle` 运行时中实现了项目根目录的懒加载，避免了在仅导入模块时进行不必要的磁盘 I/O 搜索。
这些变更提高了系统的健壮性和启动性能。

### 目标
将以下四个文件的变更加入暂存区并创建一次提交。

### 基本原理
按照 Quipu 协议，文件修改和 Git 提交必须隔离。此计划专门用于将经过验证的文件修改提交到版本控制系统。

### 标签
#intent/fix #intent/refine #flow/ready #priority/high
#comp/cli #comp/common #comp/needle #scope/core #scope/dx
#ai/instruct
#task/domain/messaging #task/object/needle-singleton #task/action/fix #task/state/end

---

### Script

#### Acts 1: 添加所有修改文件到暂存区

将所有因修复 `TypeError` 和实现懒加载而修改的文件加入暂存区。

~~~~~act
git_add
packages/stitcher-common/pyproject.toml
packages/stitcher-common/src/stitcher/common/__init__.py
packages/stitcher-needle/src/stitcher/needle/runtime.py
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~

#### Acts 2: 创建提交

创建描述此次修复和重构的提交。

~~~~~act
git_commit
~~~~~
~~~~~text
fix(core, cli): Remove leaky CLI patch and enable Needle lazy-loading

This commit addresses two critical architectural issues:

1.  **Fixes `TypeError` in CLI (`strip` and `eject` commands)**: The CLI incorrectly patched `bus.render_to_string`, leading to a `TypeError` by attempting to call a `SemanticPointer`. The entire redundant `render_to_string_patch` helper and its application have been removed, relying entirely on the native implementation within `MessageBus`.
2.  **Needle Lazy Loading**: The `Needle` runtime instance's project root discovery (`_find_project_root`) is now lazy-loaded, preventing expensive disk I/O when modules are merely imported.
3.  **Refactoring**: `stitcher-common` now explicitly depends on and exports the global `needle` singleton, centralizing semantic core access.
~~~~~
