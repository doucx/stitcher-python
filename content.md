好的，测试通过。现在我们将这些关键的重构引擎修复作为一个完整的逻辑单元进行提交。

## [COMMIT] fix(refactor): 增强目录移动与命名空间重命名的健壮性

### 错误分析

在 `stitcher-refactor` 的初步实现中，我们发现了以下阻断性问题：
1.  **竞态条件**: `MoveDirectoryOperation` 在遍历目录时会重复处理同一 Sidecar 文件（一次作为 Python 文件的附属品，一次作为普通文件），导致第二次移动时触发 `FileNotFoundError`。
2.  **架构脆弱性**: `RenameNamespaceOperation` 依赖于向 LibCST 注入自定义 Metadata Provider 来识别节点。这种方式不仅由于类型不匹配导致了 `AttributeError`，而且与系统现有的位置匹配模式不统一。
3.  **逻辑缺陷**: 命名空间重命名的分析循环中存在变量引用错误，导致无法正确收集受影响节点的上下文。
4.  **环境模拟不准**: 单元测试中 `UsageLocation` 的构造未随数据结构同步更新；集成测试中未正确声明 Python 命名空间包，导致 Griffe 无法加载完整的语义图谱。

### 用户需求
提交对重构引擎核心 Bug 的修复，确保 `stitcher refactor` 能够在复杂项目中稳定运行。

### 评论
这次修复不仅解决了报错，更重要的是统一了重构引擎内部的节点匹配逻辑（转向显式的位置映射），这极大地提升了系统的可测试性和确定性。

### 目标
1.  将所有相关修复代码并入版本库。
2.  创建一个详尽的提交记录，记录架构变更的理由。

### 基本原理
我们遵循“先验证，后提交”的原则。在所有集成测试（包括 monorepo 场景）通过后，我们确信当前的重构引擎状态是稳定的。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #concept/refactor #scope/core #ai/instruct #task/domain/refactoring #task/object/engine #task/action/fix-bugs #task/state/end

---

### Script

#### Acts 1: 提交变更

我们将所有涉及到的操作算子、转换器以及测试用例的修复添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_namespace.py
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
packages/stitcher-refactor/src/stitcher/refactor/operations/transforms/rename_namespace_transformer.py
packages/stitcher-refactor/tests/unit/test_rename_operation.py
packages/stitcher-refactor/tests/unit/test_rename_transformer.py
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(refactor): improve directory move and namespace renaming robustness

This commit fixes several critical issues in the refactoring engine:

1. MoveDirectoryOperation: Fixed a FileNotFoundError caused by double-processing
   sidecar files. Introduced a two-pass scan to ensure each file is moved exactly once.
2. RenameNamespaceOperation: Rewrote the analysis and transformation logic.
   Switched from brittle metadata provider injection to explicit location-based
   matching in the transformer, consistent with SymbolRenamerTransformer.
3. NamespaceRenamerTransformer: Added support for position-based node identification
   to fix AttributeErrors during CST traversal.
4. Testing infrastructure: Updated unit tests to match the latest UsageLocation
   schema and fixed the monorepo integration test by correctly declaring
   namespace packages using pkgutil.

These changes ensure that directory moves correctly propagate FQN changes across
multiple packages and their associated sidecars without crashing.
~~~~~

### 下一步建议
- **回归测试**: 建议在真实的大型项目中（如 Stitcher 自身）进行一次模拟重构，验证 `MoveDirectoryOperation` 在多层级嵌套下的表现。
- **性能优化**: 目前 `SemanticGraph` 的全量加载在超大型项目中可能会变慢，后续可以考虑引入增量加载或并发解析机制。
