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