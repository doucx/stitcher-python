好的，既然测试已经全部通过，我们现在将这些改动作为一个完整的逻辑单元进行提交。

## [COMMIT] fix: 实现属性文档字符串剥离并修复白名单过滤逻辑

### 用户需求
1. 修复 `stitcher strip` 无法处理 dataclass 字段或类/模块属性文档字符串的问题。
2. 修复 `stitcher pump --strip` 中由于 `StripperTransformer` 重构导致的白名单失效和回归错误。

### 评论
这次提交不仅增强了 `strip` 命令的能力（现在它可以清理变量/属性后的文档），还通过引入基于作用域栈的 FQN 追踪机制，完善了转换器的白名单过滤功能。这使得 `pump --strip` 能够安全地仅剥离已提取的实体，维持了系统的原子性和数据一致性。

### 目标
1. 提交新增的集成测试用例。
2. 提交修复后的 `StripperTransformer` 实现。

### 基本原理
我们首先将受影响的文件添加到 Git 暂存区。然后创建一个详细的提交说明，解释修复的动机（支持属性剥离）以及如何解决回归问题（通过 `scope_stack` 重建 FQN 校验逻辑）。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #comp/tests #scope/core #ai/instruct #task/domain/cli #task/object/stripper-transformer #task/action/commit #task/state/end

---

### Script

#### Acts 1: 提交变更

~~~~~act
git_add
packages/stitcher-application/tests/integration/test_lifecycle_commands.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/transformer.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix: implement attribute docstring stripping and fix whitelist regression

This commit addresses two key issues in the StripperTransformer:
1. Capability Gap: Previously, the stripper only handled container-level docstrings (modules, classes, functions). It now correctly identifies and removes docstrings following assignment (Assign) and annotated assignment (AnnAssign) nodes, covering dataclass fields and variables.
2. Whitelist Regression: A previous refactoring broke the whitelist support used by 'pump --strip'. We've implemented a scope-stack based FQN tracking mechanism that allows the transformer to validate whether a specific entity's docstring (including attributes) is authorized for stripping.

Added integration tests to verify attribute stripping in both global and whitelisted modes.
~~~~~

### 下一步建议
- **性能评估**: 虽然 LibCST 的遍历效率很高，但在处理超大型项目时，增加的 FQN 计算逻辑可能会有轻微开销。可以考虑在未来引入缓存机制。
- **文档同步**: 建议更新用户文档，明确说明 `stitcher strip` 现在支持变量和属性的文档清理。
