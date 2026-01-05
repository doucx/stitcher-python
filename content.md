好的，分析非常到位。我们现在开始解决引擎的鲁棒性问题。

## [WIP] feat(refactor): 增强 `SemanticGraph` 以主动扫描孤儿文件

### 错误分析
在 `test_debug_rename_failure_analysis` 中，重命名操作失败是因为目标文件 `bus.py` 位于一个缺少 `__init__.py` 的目录 (`stitcher/common/messaging`) 中。
1.  **Python 导入规则**: 如果父包 (`stitcher.common`) 是常规包，子目录必须有 `__init__.py` 才能被视为子包。
2.  **Griffe 的行为**: Griffe 严格遵循此规则，因此在扫描时忽略了 `messaging` 目录及其内容。
3.  **后果**: `SemanticGraph` 未能加载 `bus.py`，`class MessageBus` 的定义也就没有被注册到 `UsageRegistry` 中，导致重命名操作无法找到该定义。

虽然这源于项目结构的不规范，但重构工具应当具有更强的鲁棒性，能够处理处于“中间状态”或“破损状态”的代码库。

### 用户需求
修改 `SemanticGraph` 的加载逻辑，使其不再仅仅依赖 Griffe 的标准导入发现机制，而是主动扫描工作区中的所有源文件。对于那些被 Griffe 忽略的“孤儿文件”（如位于非包目录下的 `.py` 文件），应通过文件系统遍历进行发现，并手动触发 CST 扫描，以确保其中的符号定义（如类、函数）能被正确索引。

### 评论
这是一种“Design for Failure”的策略。通过实施主动扫描，即使在项目结构不完美的情况下，Stitcher 也能提供基本的重构能力（至少能找到并重命名定义），而不是默默失败。

### 目标
1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py`。
2.  在 `SemanticGraph` 中引入 `_processed_files` 集合，用于跟踪已由 Griffe 处理的文件。
3.  提取 CST 扫描逻辑到独立的 `_scan_file` 方法。
4.  实现 `_scan_orphans` 方法，遍历源目录查找未处理的 `.py` 文件，推断其 FQN，并进行补漏扫描。
5.  在 `load` 方法及其递归逻辑完成后，调用 `_scan_orphans`。

### 基本原理
我们利用 `Workspace` 已经掌握的“源目录根路径”信息。在 Griffe 完成标准的、基于导入的扫描后，我们遍历这些根路径下的所有 `.py` 文件。如果发现某个文件没有被 Griffe 处理过（即不在 `_processed_files` 中），我们就认为它是“孤儿文件”。我们根据文件路径相对于源根的路径推断出它的逻辑 FQN，然后手动对其进行 CST 解析。虽然对于孤儿文件我们可能缺乏完整的符号表（无法解析复杂的引用），但我们足以识别出 `ClassDef` 和 `FunctionDef`，这足以解决当前的重命名 Bug。

### 标签
#intent/refine #flow/ready #priority/high #comp/engine #concept/state #scope/core #ai/instruct #task/domain/refactoring #task/object/semantic-graph #task/action/robustness #task/state/continue

---

### Script

#### Acts 1: 重构 `SemanticGraph` 以支持孤儿文件扫描

我们将对 `SemanticGraph` 类进行结构性重构。

1.  **添加 `_processed_files`**: 用于记录被 Griffe 成功处理的文件路径。
2.  **重构 `_scan_module_usages` -> `_scan_file`**: 将扫描逻辑从依赖 `griffe.Module` 对象改为依赖文件路径和推断的 FQN，使其更通用。
3.  **实现 `_path_to_fqn`**: 一个辅助方法，用于从文件路径推断其模块 FQN。
4.  **实现 `_scan_orphans`**: 核心新功能，用于发现并处理 Griffe 遗漏的文件。
5.  **更新 `load` 和 `_build_registry`**: 将它们与新逻辑集成。

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
from typing import List, Dict, Optional, DefaultDict, Set
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

    def _register_node(self, node: cst.CSTNode, fqn: str, ref_type: ReferenceType):
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

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        if self.current_module_fqn:
            class_fqn = f"{self.current_module_fqn}.{node.name.value}"
            self._register_node(node.name, class_fqn, ReferenceType.SYMBOL)
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        if self.current_module_fqn:
            func_fqn = f"{self.current_module_fqn}.{node.name.value}"
            self._register_node(node.name, func_fqn, ReferenceType.SYMBOL)
        return True

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
        self._processed_files: Set[Path] = set()

    def load(self, package_name: str, submodules: bool = True) -> None:
        try:
            module = self._griffe_loader.load(package_name, submodules=submodules)
            self._modules[package_name] = module
            self._griffe_loader.resolve_aliases()
            self._build_registry(module)
        except griffe.exceptions.ModuleNotFoundError:
            # If Griffe can't find it, it might be an orphan module.
            # We'll rely on _scan_orphans to pick it up.
            pass
        finally:
            # Always scan for orphans to ensure full coverage
            self._scan_orphans()

    def _build_registry(
        self, module: griffe.Module, visited: Optional[Set[str]] = None
    ):
        if visited is None:
            visited = set()

        if module.path in visited:
            return
        visited.add(module.path)

        for member in module.members.values():
            if isinstance(member, griffe.Module):
                self._build_registry(member, visited)
        if module.filepath:
            self._scan_file(
                module.filepath, module_fqn=module.path, griffe_module=module
            )

    def _path_to_fqn(self, path: Path) -> Optional[str]:
        base_path = None
        for sp in sorted(self.search_paths, key=lambda p: len(p.parts), reverse=True):
            try:
                if path.is_relative_to(sp):
                    base_path = sp
                    break
            except AttributeError:  # Compatibility for older Python
                try:
                    path.relative_to(sp)
                    base_path = sp
                    break
                except ValueError:
                    continue

        if base_path is None:
            return None

        rel_path = path.relative_to(base_path)
        parts = list(rel_path.parts)

        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts.pop()

        return ".".join(parts)

    def _scan_orphans(self):
        for search_path in self.search_paths:
            if not search_path.is_dir():
                continue
            for py_file in search_path.rglob("*.py"):
                if py_file not in self._processed_files:
                    self._scan_file(py_file)

    def _scan_file(
        self,
        file_path: Path,
        module_fqn: Optional[str] = None,
        griffe_module: Optional[griffe.Module] = None,
    ):
        if file_path in self._processed_files:
            return
        self._processed_files.add(file_path)

        local_symbols: Dict[str, str] = {}
        inferred_fqn = module_fqn or self._path_to_fqn(file_path)

        if griffe_module:
            for name, member in griffe_module.members.items():
                try:
                    target_fqn = (
                        member.target_path if member.is_alias else member.path
                    )
                    local_symbols[name] = target_fqn
                except Exception:
                    pass

        try:
            source = file_path.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            is_init = file_path.name == "__init__.py"
            visitor = _UsageVisitor(
                file_path,
                local_symbols,
                self.registry,
                current_module_fqn=inferred_fqn,
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
我们已经对 `SemanticGraph` 进行了彻底的重构，使其能够主动发现并索引那些因项目结构不规范而被 Griffe 忽略的文件。

现在请重新运行 `test_debug_rename_failure_analysis` 测试。理论上，即使测试用例中的项目结构仍然是“破损”的（缺少 `__init__.py`），测试也应该能够通过，因为我们的新 `_scan_orphans` 逻辑会捕获并处理 `bus.py`。
