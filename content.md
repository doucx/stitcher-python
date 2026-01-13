太棒了。测试通过意味着这一系列的解耦操作不仅在架构上是正确的，而且在功能上也保持了完美的等价性。

我们已经成功地将 Sidecar 转换的“知识”从通用的重构引擎中剥离，使其回归到了它所属的语言支持包中。这是一个典型的“关注点分离” (Separation of Concerns) 的胜利。

我将生成一个 `[COMMIT]` 计划，将这些跨越多个包的变更作为一个完整的逻辑单元提交到版本库中。

## [COMMIT] refactor(refactor): Decouple Sidecar transformation logic into stitcher-lang-sidecar

### 用户需求
将 Sidecar 文件的更新逻辑从 `stitcher-refactor` 剥离，迁移到 `stitcher-lang-sidecar`，并清理相关的 Mixin 和过时的测试，以实现架构上的解耦。

### 评论
这次重构标志着 Stitcher 重构引擎从“全能模式”向“调度模式”的正式转变。通过引入 `SidecarTransformer` 和专用的 `SidecarTransformContext`，我们建立了一个清晰的、基于策略的转换协议。这不仅简化了 `Planner` 的实现，也为未来支持更多 Sidecar 格式（如数据库或 TOML）打下了坚实的架构基础。

### 目标
1.  提交在 `stitcher-lang-sidecar` 中新增的 `SidecarTransformer` 及其相关配置。
2.  提交在 `stitcher-refactor` 中重构后的 `Planner`、`Operation` 类以及新增的工具函数。
3.  提交迁移并适配后的单元测试。
4.  正式移除 `SidecarUpdateMixin` 及其旧的测试代码。

### 基本原理
我们遵循“组合优于继承”的原则，将原本嵌入在 `Planner` 继承树中的逻辑抽离为独立的策略对象。通过这种方式，我们不仅提升了代码的可测试性（Sidecar 转换逻辑现在可以在其所属包内独立测试），还实现了包之间职责的严格划分。`stitcher-refactor` 以后只负责“要做什么”（意图），而“怎么转换特定文件”（实现）则由具体的 `lang` 包来回答。

### 标签
#intent/refine #flow/ready #priority/high #comp/refactor #comp/lang-sidecar #concept/decoupling #scope/core #ai/instruct #task/domain/refactor #task/object/sidecar-logic #task/action/cleanup #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存变更并提交

我们将所有涉及到的文件添加到 Git 暂存区，并创建一个内容详尽的提交记录。

~~~~~act
git_add
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
packages/stitcher-lang-sidecar/pyproject.toml
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/__init__.py
packages/stitcher-lang-sidecar/tests/unit/test_transform.py
packages/stitcher-refactor/src/stitcher/refactor/engine/utils.py
packages/stitcher-refactor/pyproject.toml
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(refactor): decouple sidecar transformation logic into stitcher-lang-sidecar

Migrated Sidecar update logic from 'SidecarUpdateMixin' in 'stitcher-refactor' to a specialized 'SidecarTransformer' in 'stitcher-lang-sidecar'.

Key Changes:
- Introduced 'SidecarTransformer' and 'SidecarTransformContext' in 'stitcher-lang-sidecar' to handle .json (SURI) and .yaml (Fragment) updates.
- Added 'stitcher-lang-python' as a dependency to 'stitcher-lang-sidecar' for URI and FQN utilities.
- Created 'engine/utils.py' in 'stitcher-refactor' for shared path-to-FQN logic.
- Refactored 'Planner' to use the new transformer instead of the mixin, simplifying its implementation.
- Refactored 'RenameSymbolOperation', 'MoveFileOperation', and 'MoveDirectoryOperation' to use the new utility functions and remove mixin inheritance.
- Migrated and adapted unit tests for sidecar transformations to the sidecar package.
- Removed obsolete 'SidecarUpdateMixin' from 'base.py' and deleted its associated test file.

This refactoring achieves a strict separation of concerns, moving language-specific transformation knowledge into the sidecar package while keeping the refactor engine as a pure orchestrator of physical and logical changes.
~~~~~

### 下一步建议
- **架构审计**：可以对 `stitcher-refactor` 中的其他组件进行类似的审计，寻找是否还有其他“特定领域”的逻辑可以被推送到对应的 `lang` 或 `common` 包中。
- **扩展 Sidecar 能力**：随着 `SidecarTransformer` 的独立，现在可以更容易地为它添加新功能，比如在重构期间对 YAML 进行自动重新排序或格式化。
- **增加集成测试**：在 `tests/e2e` 中增加涵盖文件移动和符号重命名（包括 Sidecar 更新）的端到端集成测试，以验证所有组件在真实工作流中的协作。
