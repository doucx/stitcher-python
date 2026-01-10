from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set

import cst
import griffe
from stitcher.spec import ModuleDef
from stitcher.index.protocols import LanguageAdapter
from stitcher.index.types import SymbolRecord, ReferenceRecord
from stitcher.python.analysis.cst.usage_visitor import (
    UsageRegistry,
    UsageScanVisitor,
)

from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.adapter.python.fingerprint import PythonFingerprintStrategy
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

        # 2. Parse into ModuleDef (which also populates parser.last_griffe_module)
        module_def = self.parser.parse(content, file_path=rel_path)
        griffe_module = self.parser.last_griffe_module

        # 3. Project to Symbols
        symbols = self._extract_symbols(rel_path, module_def)

        # 4. Project to References
        references: List[ReferenceRecord] = []
        if griffe_module:
            references = self._extract_references(
                rel_path, content, griffe_module, file_path
            )

        return symbols, references

    def _extract_symbols(self, rel_path: str, module: ModuleDef) -> List[SymbolRecord]:
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
                # We reuse the strategy, but we need to adapt it because strategy returns a Fingerprint object
                # with multiple keys. We probably want 'current_code_structure_hash'.
                fp = self.hasher.compute(entity_for_hash)  # type: ignore
                sig_hash = fp.get("current_code_structure_hash")

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=kind,
                    location_start=0,  # Placeholder
                    location_end=0,  # Placeholder
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
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
                add(attr.name, "variable", None, parent_fragment=cls_frag)

        # 3. Module-level Attributes
        for attr in module.attributes:
            add(attr.name, "variable", None)

        return symbols

    def _build_local_symbols_map(
        self, griffe_module: griffe.Module
    ) -> Dict[str, str]:
        """Builds a map from local name to target SURI."""
        symbols: Dict[str, str] = {}

        def get_suri(obj: griffe.Object) -> Optional[str]:
            if not obj.filepath:
                return None
            try:
                rel_path = obj.filepath.relative_to(self.root_path).as_posix()
            except ValueError:
                return None

            module_path = obj.module.canonical_path
            canonical_path = obj.canonical_path
            fragment = None
            if canonical_path.startswith(module_path):
                fragment = canonical_path[len(module_path) :].lstrip(".")

            if fragment:
                return SURIGenerator.for_symbol(rel_path, fragment)
            return SURIGenerator.for_file(rel_path)

        for member in griffe_module.members.values():
            target = member.target if member.is_alias else member
            if not target:
                continue

            suri = get_suri(target)
            if suri:
                symbols[member.name] = suri
        return symbols

    def _get_definition_sites(
        self, griffe_module: griffe.Module
    ) -> Set[Tuple[int, int]]:
        """Collects all (lineno, column) tuples for symbol definitions."""
        sites: Set[Tuple[int, int]] = set()

        def collect(obj: griffe.Object):
            sites.add((obj.lineno, obj.column))
            for member in obj.members.values():
                if not member.is_alias:
                    collect(member)

        collect(griffe_module)
        return sites

    def _extract_references(
        self,
        rel_path: str,
        content: str,
        griffe_module: griffe.Module,
        abs_file_path: Path,
    ) -> List[ReferenceRecord]:
        # Step 1: Get all definition locations to filter them out later
        definition_sites = self._get_definition_sites(griffe_module)

        # Step 2: Build a map of local names to their resolved SURIs
        local_symbols = self._build_local_symbols_map(griffe_module)

        # Step 3: Parse with LibCST and run the usage visitor
        try:
            cst_module = cst.parse_module(content)
            wrapper = cst.MetadataWrapper(cst_module)
        except cst.ParserSyntaxError:
            return []  # Can't analyze syntax errors

        registry = UsageRegistry()
        module_fqn = rel_path.removesuffix(".py").replace("/", ".")
        is_init = abs_file_path.name == "__init__.py"

        visitor = UsageScanVisitor(
            file_path=abs_file_path,
            local_symbols=local_symbols,
            registry=registry,
            current_module_fqn=module_fqn,
            is_init_file=is_init,
        )
        wrapper.visit(visitor)

        # Step 4: Convert visitor results to ReferenceRecords, filtering out definitions
        references: List[ReferenceRecord] = []
        for target_suri, locations in registry._index.items():
            for loc in locations:
                if (loc.lineno, loc.col_offset) in definition_sites:
                    continue  # Skip self-referential definitions

                references.append(
                    ReferenceRecord(
                        target_id=target_suri,
                        kind=loc.ref_type.value,
                        location_start=loc.lineno,
                        location_end=loc.end_lineno,
                    )
                )
        return references