很好，测试通过意味着我们的重构和逻辑修复都已经达到预期目标。现在我们将这一系列变更作为完整的逻辑单元进行提交。

## [COMMIT] refactor: 引入 SidecarUpdateMixin 以实现统一的元数据同步逻辑

### 错误分析

在重构过程中，由于 `RenameSymbolOperation` 增加了对 `SemanticGraph` 内部属性 `_modules` 的依赖，导致现有的单元测试因 Mock 配置不完整而失败。此外，`SidecarUpdateMixin` 的初始逻辑在处理模块重命名时的短名称识别过于激进，导致无关的 FQN 被错误转换。通过增强 Mock 配置和引入基于项目前缀的启发式识别逻辑，这些问题均已得到解决。

### 用户需求

消除 `RenameSymbolOperation` 和 `MoveFileOperation` 中关于 Sidecar 文件更新和路径解析的重复逻辑，建立一个稳健、统一的元数据同步机制。

### 评论

这次重构不仅提高了代码质量，还通过 `SidecarUpdateMixin` 定义了重构引擎中元数据变更的“标准协议”。这为未来引入更多类型的重构操作（如内联、提取等）提供了坚实的基础，确保了 Stitcher 核心的“代码-文档-签名”一致性。

### 目标

1.  成功引入 `SidecarUpdateMixin` 并整合进 `AbstractOperation` 体系。
2.  完成了 `RenameSymbolOperation` 和 `MoveFileOperation` 的去重重构。
3.  修正了 `RenameSymbolOperation` 的逻辑，使其仅针对定义文件更新 Sidecar。
4.  建立了完善的 Mixin 单元测试套件，覆盖了复杂的重命名场景。

### 基本原理

通过 Mixin 模式将“元数据同步”这一横切关注点（Cross-cutting Concern）从具体的操作实现中剥离。Mixin 封装了复杂的 FQN 路径计算和 Sidecar 键转换算法，使得具体的 `Operation` 类可以更专注于代码结构的变换。

### 标签

#intent/refine #flow/ready #priority/medium #comp/runtime #concept/executor #scope/core #ai/instruct #task/domain/refactoring #task/object/sidecar-updater-mixin #task/action/design #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有受影响的文件添加到暂存区，并创建一个详尽的提交记录。

~~~~~act
git_add
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
packages/stitcher-refactor/tests/unit/test_rename_operation.py
packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: introduce SidecarUpdateMixin for unified metadata sync

Introduces 'SidecarUpdateMixin' to encapsulate repetitive logic for path-to-FQN resolution and sidecar file (doc/signature) updating during refactoring.

Key changes:
- Created 'SidecarUpdateMixin' in operations/base.py with robust FQN transformation logic.
- Refactored 'RenameSymbolOperation' and 'MoveFileOperation' to use the mixin.
- Optimized 'RenameSymbolOperation' to only update sidecars for the file where the symbol is defined, reducing unnecessary I/O.
- Improved 'MoveFileOperation' by using semantic FQN updates for sidecars instead of simple string replacement.
- Added a comprehensive unit test suite for the mixin covering complex module rename and short-name scenarios.
- Fixed existing unit tests affected by internal refactoring.

This abstraction ensures consistent metadata handling across all current and future refactoring operations.
~~~~~

### 下一步建议

- **功能验证**: 建议在实际的大型项目（如 Cascade 本身）上运行一次测试迁移，验证 `MoveFile` 结合新 Mixin 逻辑在多层级目录移动时的表现。
- **扩展应用**: 可以考虑将 `MoveDirectoryOperation` 也重构为使用此 Mixin，虽然它目前已有一套实现，但统一使用 Mixin 可以进一步减少维护成本。
