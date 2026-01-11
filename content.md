好的，测试仍然失败。这表明我的上一个修复虽然在逻辑上是正确的（将定义位置加入处理列表），但在实现层面存在更深层次的问题。直接猜测是无效的，现在必须进入诊断阶段。

根据你的指示，我将插入日志来追踪数据流，以确定问题到底出在哪里：是数据没有被正确获取，还是获取后没有被正确地传递给CST变换器，亦或是变换器内部的匹配逻辑有误。

我将在`SemanticGraph.find_usages`方法中添加详细的日志记录。这是数据从数据库出来后，转换成`UsageLocation`对象的关键枢纽。通过在这里打印日志，我们可以精确地看到`GlobalBatchRenamer`在执行代码转换前，究竟收到了哪些位置信息。

## [WIP] chore: 为重构引擎添加诊断日志以追踪失败的重命名

### 错误分析

尽管上一个计划旨在将符号的“定义”位置加入重构目标列表，但测试结果显示重命名操作依然只修改了“用法”而未修改“定义”。这说明存在以下几种可能性：
1.  `IndexStore.find_symbol_by_fqn`未能成功从数据库中检索到定义记录。
2.  `SemanticGraph.find_usages`在合并定义与用法时逻辑有误。
3.  `SymbolRenamerTransformer`（CST变换器）收到了定义的位置信息，但其内部的节点匹配逻辑未能正确识别并修改定义节点（例如，`cst.ClassDef`的名称节点）。

为了区分这些可能性，我们必须让数据流“可视化”。

### 用户需求

通过插入日志，观察`find_usages`方法返回给重构引擎的精确数据，以诊断重命名失败的根本原因。

### 评论

这是一个标准的、必要的调试步骤。在复杂的系统中，当一个看似正确的逻辑修复失败时，唯一的出路就是通过观测来验证每一步的假设。添加日志是成本最低且最有效的观测手段。

### 目标

1.  修改`stitcher.refactor.engine.graph.SemanticGraph.find_usages`方法。
2.  在该方法内部，添加详细的日志输出，打印正在查询的FQN、从`references`表查找到的引用位置、从`symbols`表查找到的定义位置，以及最终合并后的完整位置列表。

### 基本原理

通过在数据转换的关键节点（`find_usages`）打印日志，我们可以获得以下关键信息：
-   **输入验证**：确认我们正在为正确的FQN（如`stitcher.common.messaging.bus.MessageBus`）进行查询。
-   **数据源验证**：分别确认`find_references`和`find_symbol_by_fqn`是否返回了预期的记录。这将隔离问题是在`IndexStore`还是在`SemanticGraph`。
-   **输出验证**：确认最终返回给`GlobalBatchRenamer`的`UsageLocation`列表中是否**确实包含了定义的位置**。

如果日志显示定义位置已经包含在内，那么问题就几乎可以肯定地锁定在CST变换器的节点匹配逻辑上。反之，如果日志显示定义位置未能获取，问题就在数据检索层。

### 标签

#intent/tooling #flow/ready #priority/critical #comp/refactor #concept/refactor-engine #scope/dx #ai/instruct #task/domain/refactor #task/object/definition-renaming #task/action/debug #task/state/continue

---

### Script

#### Acts 1: 在 SemanticGraph 中注入诊断日志

我将修改`find_usages`方法，在其中加入详细的日志记录。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def find_usages(self, target_fqn: str) -> List[UsageLocation]:
        """
        Query the Index DB for ALL occurrences of an FQN, including its
        definition and all references. Maps DB records to UsageLocation objects.
        """
        usages = []

        # 1. Find all references (usages)
        db_refs = self.index_store.find_references(target_fqn)
        for ref, file_path_str in db_refs:
            abs_path = self.root_path / file_path_str
            try:
                ref_type = ReferenceType(ref.kind)
            except ValueError:
                ref_type = ReferenceType.SYMBOL  # Fallback

            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=ref.lineno,
                    col_offset=ref.col_offset,
                    end_lineno=ref.end_lineno,
                    end_col_offset=ref.end_col_offset,
                    ref_type=ref_type,
                    target_node_fqn=ref.target_fqn,
                )
            )

        # 2. Find the definition itself and treat it as a usage site
        definition_result = self.index_store.find_symbol_by_fqn(target_fqn)
        if definition_result:
            symbol, file_path_str = definition_result
            abs_path = self.root_path / file_path_str
            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=symbol.lineno,
                    col_offset=symbol.col_offset,
                    end_lineno=symbol.end_lineno,
                    end_col_offset=symbol.end_col_offset,
                    ref_type=ReferenceType.SYMBOL,  # A definition is a symbol site
                    target_node_fqn=symbol.canonical_fqn or target_fqn,
                )
            )

        return usages
~~~~~
~~~~~python.new
    def find_usages(self, target_fqn: str) -> List[UsageLocation]:
        """
        Query the Index DB for ALL occurrences of an FQN, including its
        definition and all references. Maps DB records to UsageLocation objects.
        """
        log.debug(f"--- RENAME DEBUG: Finding all usages for FQN: {target_fqn} ---")
        usages = []

        # 1. Find all references (usages)
        db_refs = self.index_store.find_references(target_fqn)
        log.debug(f"Found {len(db_refs)} references from DB:")
        for ref, file_path_str in db_refs:
            abs_path = self.root_path / file_path_str
            try:
                ref_type = ReferenceType(ref.kind)
            except ValueError:
                ref_type = ReferenceType.SYMBOL  # Fallback

            location = UsageLocation(
                file_path=abs_path,
                lineno=ref.lineno,
                col_offset=ref.col_offset,
                end_lineno=ref.end_lineno,
                end_col_offset=ref.end_col_offset,
                ref_type=ref_type,
                target_node_fqn=ref.target_fqn,
            )
            log.debug(f"  - REF: {location}")
            usages.append(location)

        # 2. Find the definition itself and treat it as a usage site
        definition_result = self.index_store.find_symbol_by_fqn(target_fqn)
        log.debug(f"Found definition from DB: {definition_result}")
        if definition_result:
            symbol, file_path_str = definition_result
            abs_path = self.root_path / file_path_str
            location = UsageLocation(
                file_path=abs_path,
                lineno=symbol.lineno,
                col_offset=symbol.col_offset,
                end_lineno=symbol.end_lineno,
                end_col_offset=symbol.end_col_offset,
                ref_type=ReferenceType.SYMBOL,  # A definition is a symbol site
                target_node_fqn=symbol.canonical_fqn or target_fqn,
            )
            log.debug(f"  - DEF: {location}")
            usages.append(location)

        log.debug(f"--- RENAME DEBUG: Total locations for '{target_fqn}': {len(usages)} ---")
        return usages
~~~~~

### 下一步建议

我们已经植入了诊断探针。现在，请重新运行失败的测试。`pytest`在捕获失败测试的输出时，会包含`stderr`和`stdout`，我们的日志将会被打印出来。

请使用以下命令，并通过 `-s` 标志确保日志能够被实时打印，而不是被pytest捕获：

```bash
pytest packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py -s
```

请将完整的、包含`--- RENAME DEBUG ---`标记的输出提供给我。这些日志将是解开谜题的关键。
