好的，重构后的 `PumpRunner` 已经通过了单元测试验证。现在，我将生成一个 `[COMMIT]` 计划，将这些旨在提升性能的重大架构变更正式提交到仓库中。

## [COMMIT] refactor(pump): implement index-assisted docstring hydration

### 用户需求
将完成的 `PumpRunner` 索引辅助重构及其相关的测试修复进行提交。

### 评论
此次提交标志着 "Index-First" 架构在核心业务逻辑中的首次落地。通过利用索引哈希，我们成功将 `pump` 的复杂度从“全量文件处理”降低到了“增量变更处理”，显著提升了性能。同时，修复了由此产生的测试回归，确保了代码库的健康。

### 目标
1.  提交对 `IndexStore` 的扩展，增加按路径查询符号的能力。
2.  提交对 `StitcherApp` 初始化顺序的修正及依赖注入的更新。
3.  提交 `PumpRunner` 的重构逻辑，包括新增的 `_get_dirty_source_docs` 内部方法。
4.  提交已适配新接口的 `DocumentManager` 修改。
5.  提交修复后的 `test_execution_planner.py` 单元测试文件。

### 标签
#intent/refine #flow/ready #comp/engine #comp/index #comp/tests #concept/state #scope/core #ai/delegate #task/domain/refactor #task/object/pump-runner #task/action/index-first-optimization #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将把所有涉及重构和修复的文件添加到暂存区，并创建一个符合 Conventional Commits 规范的提交记录。

~~~~~act
git_add
packages/stitcher-index/src/stitcher/index/store.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/src/stitcher/app/runners/pump.py
packages/stitcher-application/tests/unit/test_execution_planner.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(pump): implement index-assisted docstring hydration

This commit implements a major performance optimization for the 'pump' command by leveraging the semantic index as the primary source of truth for identifying changes.

Key Changes:
- Extended 'IndexStore' with 'get_symbols_by_file_path' for efficient batch symbol retrieval.
- Refactored 'PumpRunner' to use 'docstring_hash' from the index to identify "dirty" symbols.
- Implemented lazy AST extraction: Full AST docstring parsing is now only performed for symbols whose hashes have changed since the last baseline.
- Updated 'StitcherApp' to ensure 'IndexStore' is initialized before being injected into runners.
- Adapted 'DocumentManager.hydrate_module' to support source docstring overrides.
- Updated unit tests to align with the new 'PumpRunner' dependencies and method signatures.

This optimization significantly reduces I/O and CPU overhead by skipping unchanged files entirely during the hydration phase.
~~~~~

### 下一步建议

随着 `PumpRunner` 重构的圆满完成，我们的“确定性链接实施路线图”已经取得了阶段性胜利。

下一步，我们将挑战路线图中最核心、也是难度最大的部分：**重构 `CheckRunner` (Query-First)**。

我们将按照以下步骤推进：
1.  **定义 `Check` 逻辑模型**: 明确如何仅通过数据库查询（Actual）和基准文件（Baseline）的对比来判定“状态”。
2.  **实现 `SignatureManager` 迁移**: 将基准文件的 Key 升级为 SURI，并引入 `baseline_code_signature_text` 存储，为离线 Diff 提供素材。
3.  **重构 `CheckRunner` 核心循环**: 移除对 `ScannerService` 实时扫描的依赖。

如果您准备好了，我将为您启动 `CheckRunner` 重构的第一个计划。
