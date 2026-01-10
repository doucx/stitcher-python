好的，测试已经成功地将隐藏的错误暴露了出来。现在我们进入 TDD 周期的 "GREEN" 阶段，开始修复。

正如我们分析的那样，修复分为两部分：首先增强 `SemanticGraph` 使其能可靠地查找符号，然后修复 `RenameSymbolOperation` 以使用新方法并移除静默异常。

## [WIP] fix: 修复 RenameSymbolOperation 中的静默异常并增强 Graph

### 错误分析

我们编写的单元测试 `test_collect_intents_raises_error_if_symbol_not_found` 失败并提示 `Failed: DID NOT RAISE <class 'ValueError'>`。这**完美地证实**了我们的诊断：`RenameSymbolOperation.collect_intents` 方法中的 `except ValueError: pass` 块正在静默地吞噬当 `_find_definition_node` 找不到符号时抛出的 `ValueError`，从而掩盖了根本问题，并导致了下游 E2E 测试的连锁失败。

### 用户需求

修复 `RenameSymbolOperation` 中存在的静默异常处理问题，并解决其依赖的 `_find_definition_node` 方法在 `SemanticGraph` API 变更后失效的问题，最终使所有相关测试通过。

### 评论

移除静默的 `try...except` 块是提升代码质量和可维护性的关键一步。一个健壮的系统应该让错误尽早、尽明确地暴露出来，而不是隐藏它们。通过为 `SemanticGraph` 添加一个正式的 `find_symbol` 公共 API，我们不仅修复了当前的 Bug，还提升了该核心组件的封装性和可用性，使其 API 更加清晰和可靠。

### 目标

1.  **增强 `SemanticGraph`**: 为 `SemanticGraph` 类添加一个公共方法 `find_symbol(fqn: str)`，使其能够可靠地在所有已加载的包中查找符号的定义节点。
2.  **修复 `RenameSymbolOperation`**:
    *   修改 `_find_definition_node` 方法，使其调用 `SemanticGraph` 新增的 `find_symbol` 方法。
    *   **移除** `collect_intents` 方法中隐藏错误的 `try...except ValueError: pass` 块，让符号未找到的错误能够正常传播。

### 基本原理

我们将首先强化 `SemanticGraph` 的能力，为其提供一个明确的、用于符号查找的公共接口。然后，`RenameSymbolOperation` 将被重构为这个新接口的客户端。最后，通过移除有害的静默异常处理块，我们恢复了系统的错误传递链路。当 `find_symbol` 返回 `None` 时，`_find_definition_node` 将会显式地抛出一个 `ValueError`，这个错误现在会被正确地传递出去，从而被我们的 TDD 测试捕获，并为 E2E 测试提供有意义的失败信息。

### 标签

#intent/fix #flow/ready #priority/critical #comp/engine #comp/tests #scope/core #scope/dx #ai/instruct #task/domain/refactoring #task/object/workspace-discovery #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 在 SemanticGraph 中添加 `find_symbol` 方法

我们首先为 `SemanticGraph` 添加一个健壮的公共 API，用于在整个加载的图中查找符号。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def iter_members(self, package_name: str) -> List[SymbolNode]:
        module = self.get_module(package_name)
        if not module:
            return []
~~~~~
~~~~~python.new
    def find_symbol(self, fqn: str) -> Optional[SymbolNode]:
        for pkg_name in self._modules.keys():
            for member in self.iter_members(pkg_name):
                if member.fqn == fqn:
                    return member
        return None

    def iter_members(self, package_name: str) -> List[SymbolNode]:
        module = self.get_module(package_name)
        if not module:
            return []
~~~~~

#### Acts 2: 更新 `RenameSymbolOperation` 以使用新方法并移除静默异常

现在，我们将 `RenameSymbolOperation` 重构为使用 `graph.find_symbol`，并移除那个有害的 `try...except` 块。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
    def _find_definition_node(self, ctx: RefactorContext) -> SymbolNode:
        # Heuristic: Find the first matching symbol node across all loaded packages
        for pkg_name in ctx.graph._modules.keys():
            for member in ctx.graph.iter_members(pkg_name):
                if member.fqn == self.old_fqn:
                    return member
        raise ValueError(f"Could not find definition for symbol: {self.old_fqn}")

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # 1. Declare the core intent: rename the symbol everywhere.
        # The Planner will be responsible for finding usages and transforming code.
        intents.append(RenameIntent(old_fqn=self.old_fqn, new_fqn=self.new_fqn))

        # 2. Declare intents to update sidecar files.
        # The Planner will aggregate these and perform the file modifications.
        try:
            definition_node = self._find_definition_node(ctx)
            if definition_node and definition_node.path:
                definition_file_path = definition_node.path
                module_fqn = self._path_to_fqn(
                    definition_file_path, ctx.graph.search_paths
                )

                # Doc file intent
                doc_path = ctx.sidecar_manager.get_doc_path(definition_file_path)
                if doc_path.exists():
                    intents.append(
                        SidecarUpdateIntent(
                            sidecar_path=doc_path,
                            module_fqn=module_fqn,
                            old_fqn=self.old_fqn,
                            new_fqn=self.new_fqn,
                        )
                    )

                # Signature file intent
                sig_path = ctx.sidecar_manager.get_signature_path(definition_file_path)
                if sig_path.exists():
                    intents.append(
                        SidecarUpdateIntent(
                            sidecar_path=sig_path,
                            module_fqn=module_fqn,
                            old_fqn=self.old_fqn,
                            new_fqn=self.new_fqn,
                        )
                    )
        except ValueError:
            # Symbol not found, might be a module rename. The Planner will handle this.
            pass

        return intents
~~~~~
~~~~~python.new
    def _find_definition_node(self, ctx: RefactorContext) -> SymbolNode:
        node = ctx.graph.find_symbol(self.old_fqn)
        if node is None:
            raise ValueError(f"Could not find definition for symbol: {self.old_fqn}")
        return node

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # 1. Declare the core intent: rename the symbol everywhere.
        # The Planner will be responsible for finding usages and transforming code.
        intents.append(RenameIntent(old_fqn=self.old_fqn, new_fqn=self.new_fqn))

        # 2. Declare intents to update sidecar files.
        # Let the ValueError propagate if the symbol is not found.
        definition_node = self._find_definition_node(ctx)
        if definition_node and definition_node.path:
            definition_file_path = definition_node.path
            module_fqn = self._path_to_fqn(
                definition_file_path, ctx.graph.search_paths
            )

            # Doc file intent
            doc_path = ctx.sidecar_manager.get_doc_path(definition_file_path)
            if doc_path.exists():
                intents.append(
                    SidecarUpdateIntent(
                        sidecar_path=doc_path,
                        module_fqn=module_fqn,
                        old_fqn=self.old_fqn,
                        new_fqn=self.new_fqn,
                    )
                )

            # Signature file intent
            sig_path = ctx.sidecar_manager.get_signature_path(definition_file_path)
            if sig_path.exists():
                intents.append(
                    SidecarUpdateIntent(
                        sidecar_path=sig_path,
                        module_fqn=module_fqn,
                        old_fqn=self.old_fqn,
                        new_fqn=self.new_fqn,
                    )
                )

        return intents
~~~~~

### 下一步建议

我们已经修复了问题的根源。现在请重新运行测试套件。我预期我们新加的单元测试和之前失败的 E2E 测试现在都应该能成功通过。

一旦确认所有测试都恢复到绿色状态，我们就可以继续执行路线图的下一步：**4.2 调整 Planner 策略**。
