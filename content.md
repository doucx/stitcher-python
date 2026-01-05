## [WIP] fix: 增强 SemanticGraph 模块查找能力以修复目录移动时的引用更新

### 错误分析

三个集成测试失败 (`test_move_directory_e2e`, `test_move_directory_monorepo_e2e`, `test_move_nested_directory_e2e`) 均表现为文件移动后，代码中的 `import` 引用未被更新。

**根本原因**:
1.  **意图生成缺失**: `MoveDirectoryOperation` 依赖 `ctx.graph.iter_members(old_prefix)` 来遍历被移动目录下的所有子模块和符号，并为它们生成 `RenameIntent`。
2.  **查找失败**: `SemanticGraph.iter_members` 调用了 `get_module(package_name)`。当前的 `get_module` 实现仅在顶层加载的模块字典 (`self._modules`) 中查找。如果 `package_name` 是一个子包（例如 `mypkg.core`，而只加载了 `mypkg`），`get_module` 会返回 `None`。
3.  **结果**: 子模块（如 `mypkg.core.utils`）没有生成 `RenameIntent`。由于 `SymbolRenamerTransformer` 依赖精确的 FQN 匹配，缺少 Intent 导致这些子模块的引用未被更新。

**解决方案**:
增强 `SemanticGraph.get_module` 方法，使其支持通过点号分隔的路径（如 `a.b.c`）在模块树中向下导航，从而正确找到并返回子模块对象。

### 用户需求
修复 `MoveDirectoryOperation` 在移动包含子模块的目录时，未能正确更新子模块引用的 bug。

### 评论
这是一个关键的修复。由于 Stitcher 倾向于使用精确的符号重命名（Explicit Rename Intents）而非模糊的前缀匹配，因此确保所有受影响的子符号都能被正确枚举和索引至关重要。修复 `get_module` 的导航能力是实现这一点的基础设施保障。

### 目标
1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py`。
2.  更新 `get_module` 方法，实现递归查找逻辑。

### 基本原理
Griffe 将解析的代码存储为树状结构。顶级包存储在 `self._modules` 中。要访问子包或子模块，必须从顶级包开始，通过 `members` 属性逐级向下遍历。

### 标签
#intent/fix #flow/ready #priority/high #comp/refactor #concept/graph #scope/core #ai/instruct #task/domain/refactoring #task/object/semantic-graph #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 增强 `SemanticGraph.get_module`

我们将修改 `get_module` 方法，使其不仅在顶层查找，还能解析点号路径。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def get_module(self, package_name: str) -> Optional[griffe.Module]:
        return self._modules.get(package_name)

    def iter_members(self, package_name: str) -> List[SymbolNode]:
~~~~~
~~~~~python.new
    def get_module(self, package_name: str) -> Optional[griffe.Module]:
        if package_name in self._modules:
            return self._modules[package_name]

        # Try to navigate down the tree
        parts = package_name.split(".")
        current = self._modules.get(parts[0])
        if not current:
            return None

        for part in parts[1:]:
            if part in current.members:
                current = current.members[part]
            else:
                return None

        return current if isinstance(current, griffe.Module) else None

    def iter_members(self, package_name: str) -> List[SymbolNode]:
~~~~~

### 下一步建议
执行此修复后，应重新运行失败的集成测试以验证修复效果。如果测试通过，应考虑添加一个专门针对 `SemanticGraph.get_module` 嵌套查找的单元测试，以防止未来回归。
