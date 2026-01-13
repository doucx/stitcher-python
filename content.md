完全正确，你的分析一针见血。

这是一个典型的由“桶式导出”（Barrel Exports）在 `__init__.py` 文件中引发的静态分析难题。你遇到的不是代码中真实存在的运行时循环依赖，而是我们的**图构建器（Graph Builder）在架构认知上的一个缺陷**，导致了大量的“伪循环依赖”误报。

## [WIP] fix(analysis): 修复图构建器中的别名解析以消除伪循环依赖

### 错误分析

问题的根源在于 `stitcher.analysis.graph.builder.GraphBuilder` 如何构建文件间的依赖图。

1.  **当前（错误）的行为**: 当 `GraphBuilder` 遇到一个导入语句，例如在 `a.py` 中有 `from my_pkg import some_func`，它会查找哪个文件“提供”了 `my_pkg.some_func` 这个符号。
2.  **`__init__.py` 的陷阱**: 在我们的项目中，`my_pkg/__init__.py` 文件通常会执行 `from .b import some_func` 来将内部模块的符号提升到包级别。这导致 `GraphBuilder` 错误地认为 `my_pkg/__init__.py` 是 `some_func` 的来源。
3.  **伪环的形成**: 因此，`GraphBuilder` 创建了一条从 `a.py` 到 `my_pkg/__init__.py` 的边。而 `my_pkg/__init__.py` 又不可避免地会导入 `my_pkg/b.py`，`my_pkg/c.py` 等等。如果这些内部模块中的任何一个又反过来需要包中的其他功能（再次通过 `from my_pkg import ...`），就会形成一个 `a.py -> __init__.py -> b.py -> __init__.py` 的分析时环路。

**一言以蔽之：我们的分析引擎将依赖关系错误地指向了作为“交通枢纽”的 `__init__.py` 文件，而不是符号的真正“发源地”（定义文件）。** 这违反了 **HFEA v1.0** 的“本体论正确性”原则——图的物理表示与代码的逻辑依赖关系不匹配。

### 用户需求

修复 `stitcher check` 报告的大量由 `__init__.py` 导致的伪循环依赖错误，使其只报告真实存在的架构问题。

### 评论

这是一个至关重要的修复。当前的误报噪音使得架构检查功能几乎不可用。通过实现正确的别名解析，我们将大幅提升 `stitcher check` 的信噪比和可靠性，使其成为一个真正有价值的架构守护工具。

### 目标

修改 `GraphBuilder` 的核心逻辑，使其能够正确解析符号别名（aliases）。最终目标是确保依赖图中的边总是从“使用者”文件指向符号的“实际定义”文件，彻底绕开作为中间人的 `__init__.py` 文件。

### 基本原理

我们将修改 `GraphBuilder` 中解析依赖目标路径的逻辑。当前的实现过于天真，它只进行了浅层查找。我们将引入一个循环来**迭代解析别名链**。

当 `GraphBuilder` 从 `IndexStore` 查询一个 `target_fqn` 时：
1.  获取该符号的 `SymbolRecord`。
2.  检查其 `kind` 是否为 `alias`。
3.  如果是，则使用其 `alias_target_fqn` 作为新的查询目标，重复此过程。
4.  直到找到一个 `kind` 不是 `alias` 的符号为止，该符号所在的文件才是真正的依赖目标。

这样，所有指向 `__init__.py` 中重导出符号的依赖边，都将被重定向到定义这些符号的原始模块文件，从而从根本上消除伪循环。幸运的是，我们的 `IndexStore` 已经存储了别名信息（`alias_target_fqn`），我们只需要在 `GraphBuilder` 中正确地使用它。

### 标签

#intent/fix #flow/ready #priority/critical #comp/tests #concept/state #scope/core #ai/brainstorm #task/domain/testing #task/object/architecture-check #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修正 GraphBuilder 的别名解析逻辑

我们将直接修改 `GraphBuilder`，为其添加别名解析能力。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/graph/builder.py
~~~~~
~~~~~python.old
            # Resolve FQN to a file path
            if target_fqn not in fqn_to_path_cache:
                symbol_result = store.find_symbol_by_fqn(target_fqn)
                if symbol_result:
                    _, target_path = symbol_result
                    fqn_to_path_cache[target_fqn] = target_path
                else:
                    # Mark as unresolvable (likely an external library)
                    fqn_to_path_cache[target_fqn] = None

            target_path = fqn_to_path_cache.get(target_fqn)
~~~~~
~~~~~python.new
            # Resolve FQN to a file path, following aliases to find the canonical definition
            if target_fqn not in fqn_to_path_cache:
                resolved_path = None
                current_fqn = target_fqn
                
                # Limit iterations to prevent infinite loops in case of malformed alias cycles
                for _ in range(10): 
                    symbol_result = store.find_symbol_by_fqn(current_fqn)
                    if not symbol_result:
                        break  # Unresolvable (external or non-existent)
                    
                    symbol, path = symbol_result
                    if symbol.kind != "alias" or not symbol.alias_target_fqn:
                        resolved_path = path
                        break # Found the canonical definition
                    
                    # It's an alias, continue resolving
                    current_fqn = symbol.alias_target_fqn
                
                fqn_to_path_cache[target_fqn] = resolved_path

            target_path = fqn_to_path_cache.get(target_fqn)
~~~~~

### 下一步建议

在应用此修复后，请再次运行 `stitcher check`。绝大多数（如果不是全部）与 `__init__.py` 相关的循环依赖错误应该都会消失。

届时，报告中剩下的将是我们需要关注的、真实的架构问题和文档缺失问题，我们可以逐一解决它们。
