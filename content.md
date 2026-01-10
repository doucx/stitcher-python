Excellent analysis. Your conclusion that **Debt 1.3 (Alias Resolution)** is the blocking dependency for **Debt 1.2 (Reference Analysis)** is spot-on. The proposed implementation path is logical, incremental, and addresses the root cause of the problem.

I will now proceed with **Atomic Task 3**: modifying the `PythonAdapter` to process `Attribute` objects that represent aliases and correctly populate the `alias_target_id` field in the resulting `SymbolRecord`.

This change is foundational. By teaching the adapter to recognize and persist alias information, we create the necessary "anchors" in the index that will later allow the reference scanner to build a complete semantic graph.

Here is the plan to implement this change.

## [WIP] feat(index): Process alias symbols in PythonAdapter

### 用户需求

根据架构分析，需要修改 `PythonAdapter` 以识别并处理代表模块导入（别名）的 `Attribute` 对象。具体来说，当 `Attribute` 含有 `alias_target` 字段时，生成的 `SymbolRecord` 必须：
1.  将 `kind` 设置为 `alias`。
2.  将 `alias_target` (一个逻辑 FQN) 转换为 SURI，并填充到 `SymbolRecord` 的 `alias_target_id` 字段中。

### 评论

这是打通“别名解析”链路的关键一步。此修改将使符号索引首次能够持久化模块间的导入关系，为后续的引用分析和代码重构提供了基础数据。这是一个高价值的、纯粹的架构改进。

### 目标

1.  重构 `PythonAdapter.parse` 方法，将模块的逻辑 FQN (`logical_module_fqn`) 的计算提前，并将其作为参数传递给 `_extract_symbols` 和 `_extract_references`。
2.  修改 `_extract_symbols` 方法内部的 `add` 辅助函数，使其能够检查传入的实体对象是否包含 `alias_target` 属性。
3.  如果 `alias_target` 存在，则将符号的 `kind` 设为 `alias`，并调用 `_guess_suri` 方法将逻辑 FQN 转换为 SURI，填充到 `SymbolRecord` 的 `alias_target_id` 字段。

### 基本原理

为了保持代码的 DRY (Don't Repeat Yourself) 原则，我们将修改 `_extract_symbols` 内部的 `add` 辅助函数。由于模块级属性和类属性都通过此函数创建 `SymbolRecord`，将别名处理逻辑集中在此处可以确保所有类型的别名（`import x`, `from y import z`）都能被统一处理。

同时，为了让 `add` 函数能够调用 `_guess_suri`，我们需要将 `logical_module_fqn` 从 `parse` 方法一路传递下来。这是一个小型的、必要的重构，可以提高数据流的清晰度。

### 标签

#intent/refine #flow/ready #priority/high #comp/tests #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/alias-resolution #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 更新 PythonAdapter 以处理别名

我们将使用 `write_file` 覆盖 `index_adapter.py`，因为修改涉及多个方法签名和内部逻辑的联动。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Tuple, Optional

from stitcher.spec import ModuleDef
from stitcher.index.protocols import LanguageAdapter
from stitcher.index.types import SymbolRecord, ReferenceRecord

import libcst as cst
from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.adapter.python.fingerprint import PythonFingerprintStrategy
from stitcher.python.analysis.cst.usage_visitor import UsageScanVisitor, UsageRegistry
from .uri import SURIGenerator


class PythonAdapter(LanguageAdapter):
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.parser = GriffePythonParser()
        self.hasher = PythonFingerprintStrategy()

    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]:
        # 1. Calculate relative path for SURI
        try:
            rel_path = file_path.relative_to(self.root_path).as_posix()
        except ValueError:
            # Fallback if file is not in root (should not happen in normal scan)
            rel_path = file_path.name

        # 2. Parse into ModuleDef
        module_def = self.parser.parse(content, file_path=rel_path)

        # Pre-calculate logical FQN for the module
        logical_module_fqn = rel_path.replace("/", ".").replace(".py", "")
        if logical_module_fqn.endswith(".__init__"):
            logical_module_fqn = logical_module_fqn[: -len(".__init__")]

        # 3. Project to Symbols
        symbols = self._extract_symbols(rel_path, module_def, logical_module_fqn)

        # 4. Project to References
        references = self._extract_references(
            rel_path, module_def, content, file_path, logical_module_fqn
        )

        return symbols, references

    def _extract_symbols(
        self, rel_path: str, module: ModuleDef, logical_module_fqn: str
    ) -> List[SymbolRecord]:
        symbols: List[SymbolRecord] = []

        # Helper to add symbol
        def add(
            name: str,
            kind: str,
            entity_for_hash: Optional[object] = None,
            parent_fragment: str = "",
        ):
            fragment = f"{parent_fragment}.{name}" if parent_fragment else name
            suri = SURIGenerator.for_symbol(rel_path, fragment)

            # Compute Hash
            sig_hash = None
            if entity_for_hash:
                fp = self.hasher.compute(entity_for_hash)  # type: ignore
                sig_hash = fp.get("current_code_structure_hash")

            # Location Handling
            loc = getattr(entity_for_hash, "location", None)

            # Alias Handling
            alias_target_id: Optional[str] = None
            final_kind = kind
            alias_target_fqn = getattr(entity_for_hash, "alias_target", None)
            if alias_target_fqn:
                final_kind = "alias"
                alias_target_id = self._guess_suri(
                    alias_target_fqn, logical_module_fqn, rel_path
                )

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=final_kind,
                    lineno=loc.lineno if loc else 0,
                    col_offset=loc.col_offset if loc else 0,
                    end_lineno=loc.end_lineno if loc else 0,
                    end_col_offset=loc.end_col_offset if loc else 0,
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
                    alias_target_id=alias_target_id,
                )
            )
            return fragment

        # 1. Functions
        for func in module.functions:
            add(func.name, "function", func)

        # 2. Classes
        for cls in module.classes:
            cls_frag = add(cls.name, "class", cls)

            # Methods
            for method in cls.methods:
                add(method.name, "method", method, parent_fragment=cls_frag)

            # Attributes
            for attr in cls.attributes:
                add(attr.name, "variable", attr, parent_fragment=cls_frag)

        # 3. Module-level Attributes
        for attr in module.attributes:
            add(attr.name, "variable", attr)

        return symbols

    def _extract_references(
        self,
        rel_path: str,
        module: ModuleDef,
        content: str,
        file_path: Path,
        logical_module_fqn: str,
    ) -> List[ReferenceRecord]:
        refs: List[ReferenceRecord] = []

        # 1. Build local_symbols map (Name -> FQN)
        # This helps the visitor distinguish between local usages and globals/builtins
        # The FQN here is logical (e.g. "pkg.mod.Class")
        local_symbols = {}

        # Helper to construct logical FQN for local symbols
        def register_local(name: str, parent_fqn: str = ""):
            fqn = (
                f"{parent_fqn}.{name}" if parent_fqn else f"{logical_module_fqn}.{name}"
            )
            local_symbols[name] = fqn
            return fqn

        for func in module.functions:
            register_local(func.name)

        for cls in module.classes:
            for method in cls.methods:
                # Assuming UsageScanVisitor handles attribute lookups,
                # strictly speaking we might not need to pass method names as locals
                # unless they are used unqualified (which they aren't, they are self.x),
                # but registering top-level classes/funcs is key.
                pass

        # 2. Parse CST and Run Visitor
        try:
            wrapper = cst.MetadataWrapper(cst.parse_module(content))
            registry = UsageRegistry()

            visitor = UsageScanVisitor(
                file_path=file_path,
                local_symbols=local_symbols,
                registry=registry,
                current_module_fqn=logical_module_fqn,
                is_init_file=rel_path.endswith("__init__.py"),
            )
            wrapper.visit(visitor)

            # 3. Convert Registry to ReferenceRecords
            # UsageRegistry structure: { target_fqn: [UsageLocation, ...] }
            for target_fqn, locations in registry._index.items():
                for loc in locations:
                    # Convert logical FQN target to SURI
                    # NOTE: This is a heuristic. We don't have a SourceMap yet.
                    # We assume standard python layout: a.b.c -> py://a/b.py#c (simplified)
                    # For local symbols, we can be precise. For external, we guess.

                    target_suri = self._guess_suri(
                        target_fqn, logical_module_fqn, rel_path
                    )

                    refs.append(
                        ReferenceRecord(
                            target_id=target_suri,
                            kind=loc.ref_type.value,
                            lineno=loc.lineno,
                            col_offset=loc.col_offset,
                            end_lineno=loc.end_lineno,
                            end_col_offset=loc.end_col_offset,
                        )
                    )

        except Exception:
            # If CST parsing fails (syntax error), we just return empty refs
            # Logging should happen higher up
            pass

        return refs

    def _guess_suri(
        self, fqn: str, current_module_fqn: str, current_rel_path: str
    ) -> str:
        # Case 1: Internal reference (same module)
        if fqn.startswith(current_module_fqn + "."):
            fragment = fqn[len(current_module_fqn) + 1 :]
            return SURIGenerator.for_symbol(current_rel_path, fragment)

        # Case 2: External reference
        # We naively convert dots to slashes.
        # This will be incorrect for complex package roots (src/),
        # but serves as a unique identifier for now.
        # e.g. "os.path.join" -> "py://os/path.py#join"

        parts = fqn.split(".")
        if len(parts) == 1:
            # Top level module or class
            return SURIGenerator.for_symbol(f"{parts[0]}.py", parts[0])

        # Guess: last part is symbol, rest is path
        path_parts = parts[:-1]
        symbol = parts[-1]
        guessed_path = "/".join(path_parts) + ".py"
        return SURIGenerator.for_symbol(guessed_path, symbol)
~~~~~

### 下一步建议

我们已经成功地将别名信息引入了符号索引层。现在，`SymbolRecord` 中包含了指向其原始定义的 `alias_target_id`。

下一步，也是 **Atomic Task 4**，是利用这些新信息来修复引用分析的断裂问题。我们需要修改 `_extract_references` 方法，将这些新发现的 `alias` 类型的符号也添加到 `local_symbols` 映射表中，这样 `UsageScanVisitor` 在扫描代码时就能正确解析出这些导入符号的用法了。

如果你同意，我将立即开始准备 **Atomic Task 4** 的计划。
