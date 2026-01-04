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