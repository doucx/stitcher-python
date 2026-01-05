好的，我们立即开始第二阶段：**重写 `_UsageVisitor`**。

这是整个重构的核心，我们将用清晰的、基于语义的逻辑替换掉原来脆弱的实现。我将生成一个计划，使用 `write_file` 彻底重写 `graph.py` 中的 `_UsageVisitor`，使其能够正确地区分符号引用和导入路径，并使用我们在第一阶段引入的 `ReferenceType` 来标记它们。

## [WIP] refactor(engine): 重写 _UsageVisitor 以实现语义化导入解析

### 用户需求
根据战略分析的第二阶段计划，需要彻底重写 `_UsageVisitor`，使其能够准确地将 `import` 语句中的模块路径作为一个整体进行注册，并使用 `ReferenceType` 枚举来明确区分不同类型的代码引用，为后续的命名空间重构操作提供可靠的数据基础。

### 评论
这次重写是解决问题的关键。我们正在从“试图猜测导入路径的结构”转向“明确地将其识别为一个语义单元”。这消除了之前实现中的所有歧义，使得代码分析的结果变得精确且可预测。这是一个从“凑合能用”到“架构正确”的飞跃。

### 目标
1.  **重写 `_UsageVisitor`**: 替换 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py` 中的 `_UsageVisitor` 类。
2.  **更新注册逻辑**: 修改 `_register_node` 方法以接受并存储 `ref_type` 和 `target_node_fqn`。
3.  **实现语义化导入处理**:
    *   在 `visit_Import` 和 `visit_ImportFrom` 中，将整个模块路径节点注册为单一的 `UsageLocation`，类型为 `ReferenceType.IMPORT_PATH`。
    *   在 `visit_Name` 和 `visit_Attribute`（用于非导入上下文的符号引用）中，注册用法时使用 `ReferenceType.SYMBOL`。
4.  **移除过时代码**: 彻底删除不再需要的 `_register_module_parts` 方法。

### 基本原理
新的 `_UsageVisitor` 将遵循一个简单的原则：**节点类型决定引用类型**。
-   当访问 `Import` 或 `ImportFrom` 节点时，我们知道其子节点代表的是**模块路径**。我们使用 LibCST 的辅助函数来解析这个路径的完整 FQN，然后将该节点和 FQN 作为一个 `IMPORT_PATH` 类型的引用进行注册。
-   当访问代码主体中的 `Name` 或 `Attribute` 节点时，我们知道它们代表的是**符号**（变量、类、函数等）。我们通过本地符号表解析其 FQN，然后将其注册为 `SYMBOL` 类型的引用。
这种清晰的分离使得后续的 `Transformer` 可以轻松地选择合适的策略来处理不同类型的引用。

### 标签
#intent/refine #flow/ready #priority/critical #comp/engine #concept/parser #scope/core #ai/instruct #task/domain/refactor #task/object/refactor-engine #task/action/architectural-redesign #task/state/continue

---

### Script

#### Acts 1: 重写 `graph.py` 以实现新的 `_UsageVisitor`
由于 `_UsageVisitor` 的逻辑被完全重构，涉及多个方法的修改和删除，使用 `write_file` 是最清晰和安全的选择。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python
import libcst as cst
from libcst import helpers
from libcst.metadata import PositionProvider
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, DefaultDict
from collections import defaultdict
import griffe
from stitcher.refactor.workspace import Workspace
from libcst.helpers import (
    get_absolute_module_from_package_for_import,
    get_full_name_for_node,
)


class ReferenceType(Enum):
    SYMBOL = "symbol"
    IMPORT_PATH = "import_path"


@dataclass
class UsageLocation:
    file_path: Path
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    ref_type: ReferenceType
    target_node_fqn: str

    @property
    def range_tuple(self):
        return (self.lineno, self.col_offset)


@dataclass
class SymbolNode:
    fqn: str
    kind: str
    path: Path


class UsageRegistry:
    def __init__(self):
        # Key: Target FQN (The "Real" Name, e.g., "pkg.mod.Class")
        # Value: List of locations where this symbol is used/referenced
        self._index: DefaultDict[str, List[UsageLocation]] = defaultdict(list)

    def register(self, target_fqn: str, location: UsageLocation):
        self._index[target_fqn].append(location)

    def get_usages(self, target_fqn: str) -> List[UsageLocation]:
        return self._index.get(target_fqn, [])


class _UsageVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self,
        file_path: Path,
        local_symbols: Dict[str, str],
        registry: UsageRegistry,
        current_module_fqn: Optional[str] = None,
        is_init_file: bool = False,
    ):
        self.file_path = file_path
        self.local_symbols = local_symbols
        self.registry = registry
        self.current_module_fqn = current_module_fqn
        self.is_init_file = is_init_file

        self.current_package = None
        if current_module_fqn:
            if is_init_file:
                self.current_package = current_module_fqn
            elif "." in current_module_fqn:
                self.current_package = current_module_fqn.rsplit(".", 1)[0]
            else:
                self.current_package = ""

    def _register_node(
        self, node: cst.CSTNode, fqn: str, ref_type: ReferenceType
    ):
        pos = self.get_metadata(PositionProvider, node)
        loc = UsageLocation(
            file_path=self.file_path,
            lineno=pos.start.line,
            col_offset=pos.start.column,
            end_lineno=pos.end.line,
            end_col_offset=pos.end.column,
            ref_type=ref_type,
            target_node_fqn=fqn,
        )
        self.registry.register(fqn, loc)
        # Also register against prefixes for namespace refactoring
        if ref_type == ReferenceType.IMPORT_PATH:
            parts = fqn.split(".")
            for i in range(1, len(parts)):
                prefix_fqn = ".".join(parts[:i])
                self.registry.register(prefix_fqn, loc)

    def visit_Name(self, node: cst.Name):
        target_fqn = self.local_symbols.get(node.value)
        if target_fqn:
            self._register_node(node, target_fqn, ReferenceType.SYMBOL)

    def visit_Import(self, node: cst.Import) -> Optional[bool]:
        for alias in node.names:
            absolute_module = get_full_name_for_node(alias.name)
            if absolute_module:
                self._register_node(
                    alias.name, absolute_module, ReferenceType.IMPORT_PATH
                )
        return True

    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[bool]:
        absolute_module = None
        try:
            package_ctx = self.current_package if self.current_package else None
            absolute_module = get_absolute_module_from_package_for_import(
                package_ctx, node
            )
        except Exception:
            pass

        if absolute_module:
            if node.module:
                self._register_node(
                    node.module, absolute_module, ReferenceType.IMPORT_PATH
                )

            for alias in node.names:
                if isinstance(alias, cst.ImportAlias):
                    name_node = alias.name
                    imported_name = get_full_name_for_node(name_node)
                    if imported_name:
                        full_fqn = f"{absolute_module}.{imported_name}"
                        self._register_node(name_node, full_fqn, ReferenceType.SYMBOL)
        return True

    def visit_Attribute(self, node: cst.Attribute) -> Optional[bool]:
        full_name = helpers.get_full_name_for_node(node)
        if not full_name:
            return True

        parts = full_name.split(".")
        if not parts:
            return True

        root_name = parts[0]
        root_fqn = self.local_symbols.get(root_name)

        if root_fqn:
            suffix = ".".join(parts[1:])
            absolute_fqn = f"{root_fqn}.{suffix}" if suffix else root_fqn
            self._register_node(node, absolute_fqn, ReferenceType.SYMBOL)

        return True


class SemanticGraph:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.root_path = workspace.root_path
        self.search_paths = self.workspace.get_search_paths()
        self._griffe_loader = griffe.GriffeLoader(search_paths=self.search_paths)
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()

    def load(self, package_name: str, submodules: bool = True) -> None:
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module
        self._griffe_loader.resolve_aliases()
        self._build_registry(module)

    def _build_registry(self, module: griffe.Module):
        for member in module.members.values():
            if isinstance(member, griffe.Module) and not member.is_alias:
                self._build_registry(member)
        if module.filepath:
            self._scan_module_usages(module)

    def _scan_module_usages(self, module: griffe.Module):
        local_symbols: Dict[str, str] = {}
        for name, member in module.members.items():
            try:
                target_fqn = member.target_path if member.is_alias else member.path
                local_symbols[name] = target_fqn
            except Exception:
                pass

        try:
            source = module.filepath.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            is_init = module.filepath.name == "__init__.py"
            visitor = _UsageVisitor(
                module.filepath,
                local_symbols,
                self.registry,
                current_module_fqn=module.path,
                is_init_file=is_init,
            )
            wrapper.visit(visitor)
        except Exception:
            pass

    def get_module(self, package_name: str) -> Optional[griffe.Module]:
        return self._modules.get(package_name)

    def iter_members(self, package_name: str) -> List[SymbolNode]:
        module = self.get_module(package_name)
        if not module:
            return []
        nodes = []

        def _collect(obj: griffe.Object):
            path = obj.filepath or Path("")
            kind = "unknown"
            if obj.is_module:
                kind = "module"
            elif obj.is_class:
                kind = "class"
            elif obj.is_function:
                kind = "function"
            elif obj.is_attribute:
                kind = "attribute"
            nodes.append(SymbolNode(fqn=obj.path, kind=kind, path=path))
            if hasattr(obj, "members"):
                for member in obj.members.values():
                    if not member.is_alias:
                        _collect(member)

        _collect(module)
        return nodes
~~~~~

### 下一步建议
我们已经成功完成了第二阶段，现在 `UsageRegistry` 中包含了带有明确类型（`IMPORT_PATH` 或 `SYMBOL`）的引用信息，并且我们还为 `IMPORT_PATH` 注册了其所有的前缀。这是解决问题的关键一步。

接下来，我们将进入**第三阶段**和**第四阶段**，它们是紧密耦合的：
1.  **创建新的 `RenameNamespaceOperation` 和 `NamespaceRenamerTransformer`**：它们将专门利用 `IMPORT_PATH` 类型的引用和前缀匹配逻辑来重构导入语句。
2.  **修改 `MoveDirectoryOperation`**: 使其在分析阶段自动生成这个新的 `RenameNamespaceOperation`。

如果你准备好了，请指示开始下一阶段的工作。
