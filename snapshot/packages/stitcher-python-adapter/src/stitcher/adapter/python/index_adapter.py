from pathlib import Path
from typing import List, Tuple, Optional

from stitcher.spec import ModuleDef
from stitcher.index.protocols import LanguageAdapter
from stitcher.index.types import SymbolRecord, ReferenceRecord

import libcst as cst
from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.adapter.python.fingerprint import PythonFingerprintStrategy
from stitcher.python.analysis.cst.usage_visitor import UsageScanVisitor, UsageRegistry
from stitcher.python.analysis.scope import ScopeAnalyzer
from stitcher.python.analysis.utils import path_to_logical_fqn
from stitcher.refactor.workspace import Workspace
from .uri import SURIGenerator


class PythonAdapter(LanguageAdapter):
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.root_path = workspace.root_path
        self.parser = GriffePythonParser()
        self.hasher = PythonFingerprintStrategy()

    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]:
        # 1. Calculate relative path for SURI (from project root)
        try:
            suri_rel_path = file_path.relative_to(self.root_path).as_posix()
        except ValueError:
            suri_rel_path = file_path.name

        # 2. Determine the correct logical FQN based on workspace search paths
        source_root = self.root_path
        longest_match = -1
        # Find the most specific source root for this file
        for search_path in self.workspace.get_search_paths():
            try:
                if (
                    file_path.is_relative_to(search_path)
                    and len(search_path.parts) > longest_match
                ):
                    source_root = search_path
                    longest_match = len(search_path.parts)
            except ValueError:  # is_relative_to is Python 3.9+
                if str(file_path).startswith(str(search_path)):
                    if len(search_path.parts) > longest_match:
                        source_root = search_path
                        longest_match = len(search_path.parts)

        logical_rel_path = file_path.relative_to(source_root).as_posix()
        logical_module_fqn = path_to_logical_fqn(logical_rel_path)

        # 3. Parse into ModuleDef
        module_def = self.parser.parse(content, file_path=suri_rel_path)

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

        # 0. Module Symbol (The file/module itself)
        # This allows other files to import this module.
        module_name = logical_module_fqn.split(".")[-1]
        module_suri = SURIGenerator.for_file(rel_path)
        
        symbols.append(
            SymbolRecord(
                id=module_suri,
                name=module_name,
                kind="module",
                lineno=0,
                col_offset=0,
                end_lineno=0,
                end_col_offset=0,
                logical_path=None, # Module root has no logical path suffix
                canonical_fqn=logical_module_fqn,
                alias_target_fqn=None,
                alias_target_id=None,
                signature_hash=None,
            )
        )

        # Helper to add symbol
        def add(
            name: str,
            kind: str,
            entity_for_hash: Optional[object] = None,
            parent_fragment: str = "",
        ):
            fragment = f"{parent_fragment}.{name}" if parent_fragment else name
            suri = SURIGenerator.for_symbol(rel_path, fragment)
            canonical_fqn = f"{logical_module_fqn}.{fragment}"

            # Compute Hash
            sig_hash = None
            if entity_for_hash:
                fp = self.hasher.compute(entity_for_hash)  # type: ignore
                sig_hash = fp.get("current_code_structure_hash")

            # Location Handling
            loc = getattr(entity_for_hash, "location", None)

            # Alias Handling
            alias_target_fqn: Optional[str] = None
            final_kind = kind

            # Check for alias target in the entity
            target_attr = getattr(entity_for_hash, "alias_target", None)
            if target_attr:
                final_kind = "alias"
                alias_target_fqn = target_attr

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=final_kind,
                    lineno=loc.lineno if loc else 0,
                    col_offset=loc.col_offset if loc else 0,
                    end_lineno=loc.end_lineno if loc else 0,
                    end_col_offset=loc.end_col_offset if loc else 0,
                    logical_path=fragment,
                    canonical_fqn=canonical_fqn,
                    alias_target_fqn=alias_target_fqn,
                    alias_target_id=None,  # Decoupled: Linker will fill this
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

        # 1. Build local_symbols map using the centralized analyzer
        analyzer = ScopeAnalyzer()
        # Note: ScopeAnalyzer returns a map of {local_name: target_fqn}
        # We don't need to manually use it here because UsageScanVisitor uses it internally?
        # Wait, UsageScanVisitor takes local_symbols as input.
        local_symbols = analyzer.build_from_ir(module, logical_module_fqn)

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
            for target_fqn, locations in registry.get_all_usages().items():
                for loc in locations:
                    refs.append(
                        ReferenceRecord(
                            target_fqn=target_fqn,  # Store the logical intent directly
                            target_id=None,  # Decoupled: Linker will fill this
                            kind=loc.ref_type.value,
                            lineno=loc.lineno,
                            col_offset=loc.col_offset,
                            end_lineno=loc.end_lineno,
                            end_col_offset=loc.end_col_offset,
                        )
                    )

        except Exception:
            # If CST parsing fails (syntax error), we just return empty refs
            pass

        return refs
