好的，我们已经完成了代码的修复和逻辑增强。现在的重构引擎不仅能正确处理跨包移动时的复杂导入路径，还能智能地识别并保护用户定义的别名引用。

我将生成一个 `[COMMIT]` 计划，将这些改进作为一个完整的逻辑单元提交到版本库中。

## [COMMIT] fix(refactor): 增强模块路径重命名能力并增加别名保护

### 用户需求
用户要求在测试通过后创建 Git 提交。

### 评论
这次提交涵盖了重构引擎核心能力的重大提升：从简单的符号替换进化到了具备语义感知的模块路径重组。引入的“名称匹配守卫”有效地解决了别名冲突问题，显著提升了工具的生产环境可靠性。

### 目标
1.  将所有修改后的核心重构引擎文件添加到 Git 暂存区。
2.  创建一个描述详尽的提交记录。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules`，本次计划仅包含 Git 操作。我们将修改后的图谱解析器、重构操作符和 LibCST 转换器打包提交，确保版本历史的清晰和逻辑完整性。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/engine #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/refactor-engine #task/action/bug-fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将暂存修改过的文件并创建正式提交。

~~~~~act
git_add
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
packages/stitcher-refactor/src/stitcher/refactor/operations/transforms/rename_transformer.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(refactor): enhance module path renaming and implement alias protection

This commit upgrades the refactoring engine to correctly handle cross-package moves and qualified references while ensuring that local aliases remain intact.

Key changes:
- Graph Engine: Updated _UsageVisitor to register full Attribute chains instead of just terminal Name nodes. This allows for whole-path replacement during refactoring.
- Rename Operation: Modified RenameSymbolOperation to pass full FQN mappings {old_fqn: new_fqn} to the transformer, enabling multi-level path updates.
- LibCST Transformer: 
    - Implemented a 'Name Match Guard' in SymbolRenamerTransformer to distinguish between direct symbol references and local aliases (e.g., 'import X as Y').
    - Added support for replacing Attribute nodes, allowing for the re-writing of deep module import paths (e.g., 'a.b.c' to 'x.y.z').

These improvements fix the AssertionError in 'test_move_nested_directory_e2e' and ensure robust behavior in complex project restructurings.
~~~~~

### 下一步建议
- **回归测试**: 建议在较大的内部项目上运行 `MoveDirectoryOperation` 的压力测试，以确保在大规模引用下的性能。
- **功能扩展**: 既然我们现在可以处理 `Attribute` 替换，可以考虑实现更复杂的重构，如“提取方法”或“内联属性”。
- **文档更新**: 可以在 `Stitcher Refactor` 的用户文档中增加关于“重构安全性与别名处理”的章节。
