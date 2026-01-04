简要回答
问题在于 Python 标准库的 `ast` 模块在解析 `ClassDef` 和 `FunctionDef` 时，其 `name` 属性只是一个原始字符串，而不是一个可遍历的 `ast.Name` 节点。因此，`_UsageVisitor` 的 `visit_Name` 方法根本不会在定义处触发，导致 definitions 没有被注册为 usages。

为了解决这个问题，并确保扫描出的位置信息与后续 `SymbolRenamerTransformer`（基于 LibCST）所需的精确位置完全一致，我们将把扫描逻辑从 `ast` 迁移到 `libcst`。LibCST 将定义名称视为标准的 `Name` 节点进行遍历，这将自然地解决定义缺失的问题。

## [WIP] fix: 使用 LibCST 替换 AST 进行 Usage 扫描

### 错误分析
测试失败显示 `core.py` 中的 `Helper` 类定义没有被注册为 Usage。
**原因**: `ast.NodeVisitor.visit_Name` 不会访问类或函数的定义名称（因为在 AST 中它们是字符串属性）。
**解决方案**: 切换到 `libcst`。在 CST 中，`ClassDef.name` 和 `FunctionDef.name` 都是 `Name` 节点，会被正常遍历。此外，LibCST 提供的 `PositionProvider` 能提供更精确的行列号，与我们后续的重命名操作完美对齐。

### 用户需求
修复 `UsageRegistry` 无法识别符号定义处 Usage 的问题，确保重命名操作能修改定义本身。

### 评论
使用 LibCST 进行扫描是“同构”的正确选择。既然我们的写入端（Transformer）使用 LibCST，读取端（Scanner）也应该使用 LibCST，以消除位置偏差。

### 目标
1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py`。
2.  将 `_UsageVisitor` 重构为 `cst.CSTVisitor`。
3.  使用 `cst.MetadataWrapper` 和 `PositionProvider` 获取精确位置。

### 基本原理
-   **一致性**: Scanner 和 Transformer 使用相同的解析器（LibCST），保证 (line, col) 坐标系的一致性。
-   **完整性**: LibCST 将所有标识符（包括定义、引用、别名）统一视为 `Name` 节点，简化了访问逻辑。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #task/domain/refactor #task/object/usage-registry #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 重构 graph.py 使用 LibCST

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python
import libcst as cst
from libcst.metadata import PositionProvider
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Set, DefaultDict
from collections import defaultdict
import griffe


@dataclass
class UsageLocation:
    """
    Represents a specific usage of a symbol in the codebase.
    """
    file_path: Path
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    
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
    """
    Scans a file's CST for Name nodes and resolves them using a local symbol table.
    Uses LibCST to ensure positions match the Transformer exactly.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, file_path: Path, local_symbols: Dict[str, str], registry: UsageRegistry):
        self.file_path = file_path
        self.local_symbols = local_symbols  # map: local_name -> target_fqn
        self.registry = registry

    def visit_Name(self, node: cst.Name):
        # In LibCST, Name nodes appear in definitions (ClassDef.name), 
        # references (a = 1), and aliases (import x as y).
        target_fqn = self.local_symbols.get(node.value)
        if target_fqn:
            pos = self.get_metadata(PositionProvider, node)
            # CodeRange is 1-based line, 0-based column.
            loc = UsageLocation(
                file_path=self.file_path,
                lineno=pos.start.line,
                col_offset=pos.start.column,
                end_lineno=pos.end.line,
                end_col_offset=pos.end.column
            )
            self.registry.register(target_fqn, loc)


class SemanticGraph:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._griffe_loader = griffe.GriffeLoader(search_paths=[self.root_path])
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()

    def load(self, package_name: str, submodules: bool = True) -> None:
        # 1. Load with Griffe (resolves aliases)
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module
        
        # 2. Resolve aliases to ensure we have full resolution
        self._griffe_loader.resolve_aliases()

        # 3. Build Usage Registry
        self._build_registry(module)

    def _build_registry(self, module: griffe.Module):
        """
        Walks the module tree, builds local symbol tables from Griffe Aliases,
        and scans CST for usages.
        """
        # Recursively process members that are modules
        for member in module.members.values():
            if isinstance(member, griffe.Module) and not member.is_alias:
                self._build_registry(member)

        # Process the current module
        if module.filepath:
            self._scan_module_usages(module)

    def _scan_module_usages(self, module: griffe.Module):
        # 1. Build Local Symbol Table (Name -> FQN)
        local_symbols: Dict[str, str] = {}
        
        for name, member in module.members.items():
            if member.is_alias:
                try:
                    target_fqn = member.target_path
                    local_symbols[name] = target_fqn
                except Exception:
                    pass
            else:
                # It's a definition (Class, Function) in this module.
                local_symbols[name] = member.path

        # 2. Parse CST and scan
        try:
            source = module.filepath.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            visitor = _UsageVisitor(module.filepath, local_symbols, self.registry)
            wrapper.visit(visitor)
        except Exception:
            # Handle syntax errors or IO errors gracefully
            pass

    def get_module(self, package_name: str) -> Optional[griffe.Module]:
        return self._modules.get(package_name)

    def iter_members(self, package_name: str) -> List[SymbolNode]:
        module = self.get_module(package_name)
        if not module:
            return []
        nodes = []
        def _collect(obj: griffe.Object):
            path = obj.filepath if obj.filepath else Path("")
            kind = "unknown"
            if obj.is_module: kind = "module"
            elif obj.is_class: kind = "class"
            elif obj.is_function: kind = "function"
            elif obj.is_attribute: kind = "attribute"
            nodes.append(SymbolNode(fqn=obj.path, kind=kind, path=path))
            if hasattr(obj, "members"):
                for member in obj.members.values():
                    if not member.is_alias:
                        _collect(member)
        _collect(module)
        return nodes
~~~~~

### 下一步建议
测试通过后，我们的 `SemanticGraph` 就具备了查找所有引用的能力。
接下来的核心步骤是实现 **`RenameSymbolOperation`**：
1.  创建一个 Operation 类，接收 `old_fqn` 和 `new_fqn`。
2.  在 `analyze` 阶段，查询 `SemanticGraph.registry` 获取所有 Usages。
3.  按文件分组 Usages，为每个文件实例化一个 `SymbolRenamerTransformer`。
4.  返回一组 `WriteFileOp`（包含修改后的代码），提交给 `TransactionManager`。
