好的，我们开始实施路线图的第一步：**1.1. 增强 `SidecarAdapter` 的能力**。

此步骤的核心是将 `SidecarAdapter` 提升为处理 Sidecar 文件（`.stitcher.yaml`）的核心服务，使其具备高保真的读写 `DocstringIR` 的能力。这将为后续移除 `common` 包中的旧 `YamlAdapter` 奠定基础。

我将执行以下操作：

1.  **重写 `stitcher-lang-sidecar` 中的 `SidecarAdapter`**：为其增加加载和保存 `DocstringIR` 的方法，并强制使用 `ruamel.yaml` 以确保格式和注释的无损圆整。
2.  **重构 `stitcher-application` 中的 `DocumentManager`**：使其不再依赖旧的 `YamlAdapter`，而是将所有 Sidecar 文件的 I/O 操作委托给新的、功能更强大的 `SidecarAdapter`。

这将把 Sidecar 文件的处理逻辑完全内聚到 `stitcher-lang-sidecar` 包中，实现我们“唯一事实来源 (SSoT)”的架构目标。

---

### Script

#### Acts 1: 升级 SidecarAdapter 以处理 DocstringIR

我们将重写 `SidecarAdapter`，赋予其完整的 YAML 文件处理能力。它现在将成为一个无状态的服务，能够根据传入的序列化策略，高保真地加载、保存和序列化 `DocstringIR` 对象。

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python
import io
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union, Any

from ruamel.yaml import YAML
from stitcher.spec import DocstringIR
from stitcher.spec.protocols import DocstringSerializerProtocol
from stitcher.spec.registry import LanguageAdapter
from stitcher.spec.index import SymbolRecord, ReferenceRecord
from stitcher.lang.sidecar.parser import (
    parse_doc_references,
    parse_signature_references,
)
from stitcher.common.services import AssetPathResolver
from stitcher.lang.python.uri import SURIGenerator
from stitcher.lang.python.analysis.models import ReferenceType


class SidecarAdapter(LanguageAdapter):
    def __init__(
        self,
        root_path: Path,
    ):
        self.root_path = root_path
        self.resolver = AssetPathResolver(root_path)
        self._yaml = YAML()
        self._yaml.indent(mapping=2, sequence=4, offset=2)
        self._yaml.preserve_quotes = True
        self._yaml.width = 1000  # Avoid line wrapping for readability

    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]:
        symbols: List[SymbolRecord] = []
        references: List[ReferenceRecord] = []

        if file_path.suffix == ".json":
            refs = parse_signature_references(content)
            for suri, line, col in refs:
                references.append(
                    ReferenceRecord(
                        target_fqn=None,
                        target_id=suri,
                        kind=ReferenceType.SIDECAR_ID.value,
                        lineno=line,
                        col_offset=col,
                        end_lineno=line,
                        end_col_offset=col + len(suri),
                    )
                )

        elif file_path.suffix in (".yaml", ".yml"):
            try:
                if not file_path.name.endswith(".stitcher.yaml"):
                    return symbols, references

                py_name = file_path.name.replace(".stitcher.yaml", ".py")
                py_path = file_path.with_name(py_name)

                if not py_path.exists():
                    return symbols, references

                rel_py_path = py_path.relative_to(self.root_path).as_posix()

                refs = parse_doc_references(content)
                for fragment, line, col in refs:
                    suri = SURIGenerator.for_symbol(rel_py_path, fragment)
                    references.append(
                        ReferenceRecord(
                            target_id=suri,
                            kind=ReferenceType.SIDECAR_DOC_ID.value,
                            lineno=line,
                            col_offset=col,
                            end_lineno=line,
                            end_col_offset=col + len(fragment),
                        )
                    )
            except (ValueError, FileNotFoundError):
                pass

        return symbols, references

    def load_doc_irs(
        self, path: Path, serializer: DocstringSerializerProtocol
    ) -> Dict[str, DocstringIR]:
        if not path.exists():
            return {}

        try:
            with path.open("r", encoding="utf-8") as f:
                raw_data = self._yaml.load(f)
            if not isinstance(raw_data, dict):
                return {}

            return {
                fqn: serializer.from_yaml(val) for fqn, val in raw_data.items()
            }
        except Exception:
            return {}

    def save_doc_irs(
        self,
        path: Path,
        irs: Dict[str, DocstringIR],
        serializer: DocstringSerializerProtocol,
    ) -> None:
        sorted_irs = dict(sorted(irs.items()))
        yaml_data = {fqn: serializer.to_yaml(ir) for fqn, ir in sorted_irs.items()}

        path.parent.mkdir(parents=True, exist_ok=True)

        original_content = ""
        if path.exists():
            try:
                original_content = path.read_text("utf-8")
            except (OSError, UnicodeDecodeError):
                pass

        string_stream = io.StringIO()
        self._yaml.dump(yaml_data, string_stream)
        new_content = string_stream.getvalue()

        if original_content != new_content:
            with path.open("w", encoding="utf-8") as f:
                f.write(new_content)

    def dump_to_string(self, data: Dict[str, Any]) -> str:
        string_stream = io.StringIO()
        self._yaml.dump(data, string_stream)
        return string_stream.getvalue()

    def serialize_ir(
        self, ir: DocstringIR, serializer: DocstringSerializerProtocol
    ) -> Union[str, Dict[str, Any]]:
        return serializer.to_yaml(ir)
~~~~~

#### Acts 2: 重构 DocumentManager 以使用 SidecarAdapter

现在，我们将重构 `DocumentManager`，使其成为 `SidecarAdapter` 的客户端。它将不再包含任何文件 I/O 或 YAML 解析的实现细节，而是完全委托给 `SidecarAdapter`，从而实现职责的清晰分离。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Any, Union, List, TYPE_CHECKING

if TYPE_CHECKING:
    from stitcher.spec.index import SymbolRecord

from stitcher.spec import (
    ModuleDef,
    ClassDef,
    FunctionDef,
    DocstringIR,
    DocstringParserProtocol,
    DocstringSerializerProtocol,
)
from stitcher.lang.python.docstring import RawDocstringParser, RawSerializer
from stitcher.common.services import AssetPathResolver
from stitcher.lang.sidecar import SidecarAdapter


class DocumentManager:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.resolver = AssetPathResolver(root_path)
        self._sidecar_adapter = SidecarAdapter(root_path)
        # Defaults to Raw mode for backward compatibility
        self.parser: DocstringParserProtocol = RawDocstringParser()
        self.serializer: DocstringSerializerProtocol = RawSerializer()

    def set_strategy(
        self,
        parser: DocstringParserProtocol,
        serializer: DocstringSerializerProtocol,
    ):
        self.parser = parser
        self.serializer = serializer

    def serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        return self._sidecar_adapter.serialize_ir(ir, self.serializer)

    def compute_ir_hash(self, ir: DocstringIR) -> str:
        serialized = self.serialize_ir(ir)
        return self.compute_yaml_content_hash(serialized)

    def dump_data(self, data: Dict[str, Any]) -> str:
        return self._sidecar_adapter.dump_to_string(data)

    def _extract_from_function(
        self, func: FunctionDef, prefix: str = ""
    ) -> Dict[str, DocstringIR]:
        docs = {}
        full_name = f"{prefix}{func.name}"
        if func.docstring:
            docs[full_name] = self.parser.parse(func.docstring)
        return docs

    def _extract_from_class(
        self, cls: ClassDef, prefix: str = ""
    ) -> Dict[str, DocstringIR]:
        docs = {}
        full_name = f"{prefix}{cls.name}"
        if cls.docstring:
            docs[full_name] = self.parser.parse(cls.docstring)
        for method in cls.methods:
            docs.update(self._extract_from_function(method, prefix=f"{full_name}."))
        return docs

    def flatten_module_docs(self, module: ModuleDef) -> Dict[str, DocstringIR]:
        docs: Dict[str, DocstringIR] = {}
        if module.docstring:
            docs["__doc__"] = self.parser.parse(module.docstring)
        for func in module.functions:
            docs.update(self._extract_from_function(func))
        for cls in module.classes:
            docs.update(self._extract_from_class(cls))
        for attr in module.attributes:
            if attr.docstring:
                docs[attr.name] = self.parser.parse(attr.docstring)
        for cls in module.classes:
            for attr in cls.attributes:
                if attr.docstring:
                    docs[f"{cls.name}.{attr.name}"] = self.parser.parse(attr.docstring)
        return docs

    def save_docs_for_module(self, module: ModuleDef) -> Path:
        ir_map = self.flatten_module_docs(module)
        if not ir_map:
            return Path("")

        module_path = self.root_path / module.file_path
        output_path = self.resolver.get_doc_path(module_path)
        self._sidecar_adapter.save_doc_irs(output_path, ir_map, self.serializer)
        return output_path

    def load_docs_for_path(self, file_path: str) -> Dict[str, DocstringIR]:
        if not file_path:
            return {}
        module_path = self.root_path / file_path
        doc_path = self.resolver.get_doc_path(module_path)
        return self._sidecar_adapter.load_doc_irs(doc_path, self.serializer)

    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, DocstringIR]:
        return self.load_docs_for_path(module.file_path)

    def _apply_to_function(
        self, func: FunctionDef, docs: Dict[str, DocstringIR], prefix: str = ""
    ):
        full_name = f"{prefix}{func.name}"
        if full_name in docs:
            # Injecting back to code: we only care about the summary (content)
            func.docstring = docs[full_name].summary
            func.docstring_ir = docs[full_name]

    def _apply_to_class(
        self, cls: ClassDef, docs: Dict[str, DocstringIR], prefix: str = ""
    ):
        full_name = f"{prefix}{cls.name}"
        if full_name in docs:
            cls.docstring = docs[full_name].summary
            cls.docstring_ir = docs[full_name]
        for method in cls.methods:
            self._apply_to_function(method, docs, prefix=f"{full_name}.")
        for attr in cls.attributes:
            attr_key = f"{full_name}.{attr.name}"
            if attr_key in docs:
                attr.docstring = docs[attr_key].summary

    def apply_docs_to_module(self, module: ModuleDef) -> None:
        docs = self.load_docs_for_module(module)
        if not docs:
            return
        if "__doc__" in docs:
            module.docstring = docs["__doc__"].summary
            module.docstring_ir = docs["__doc__"]
        for func in module.functions:
            self._apply_to_function(func, docs)
        for cls in module.classes:
            self._apply_to_class(cls, docs)
        for attr in module.attributes:
            if attr.name in docs:
                attr.docstring = docs[attr.name].summary

    def check_module(self, module: ModuleDef) -> Dict[str, set]:
        public_keys = self._extract_keys(module, public_only=True)
        all_keys = self._extract_keys(module, public_only=False)
        source_docs = self.flatten_module_docs(module)
        yaml_docs = self.load_docs_for_module(module)
        yaml_keys = set(yaml_docs.keys())

        extra = yaml_keys - all_keys
        extra.discard("__doc__")

        missing_doc = set()
        pending_hydration = set()
        redundant_doc = set()
        doc_conflict = set()

        for key in all_keys:
            is_public = key in public_keys
            has_source_doc = key in source_docs
            has_yaml_doc = key in yaml_keys

            if not has_source_doc and not has_yaml_doc:
                if is_public:
                    missing_doc.add(key)
            elif has_source_doc and not has_yaml_doc:
                pending_hydration.add(key)
            elif has_source_doc and has_yaml_doc:
                # Compare SUMMARIES only.
                # Addons in YAML do not cause conflict with Source Code.
                src_summary = source_docs[key].summary or ""
                yaml_summary = yaml_docs[key].summary or ""

                if src_summary != yaml_summary:
                    doc_conflict.add(key)
                else:
                    redundant_doc.add(key)

        return {
            "extra": extra,
            "missing": missing_doc,
            "pending": pending_hydration,
            "redundant": redundant_doc,
            "conflict": doc_conflict,
        }

    def check_consistency_with_symbols(
        self, file_path: str, actual_symbols: List["SymbolRecord"]
    ) -> Dict[str, set]:
        # 1. Extract keys from symbols
        all_keys = set()
        public_keys = set()

        for sym in actual_symbols:
            key = None
            if sym.kind == "module":
                key = "__doc__"
            elif sym.logical_path:
                key = sym.logical_path

            if key:
                all_keys.add(key)
                # Check for visibility (simple underscore check on components)
                # logical_path 'A.B._c' -> parts ['A', 'B', '_c']
                parts = key.split(".")
                if not any(p.startswith("_") and p != "__doc__" for p in parts):
                    public_keys.add(key)

        # 2. Load YAML keys
        yaml_docs = self.load_docs_for_path(file_path)
        yaml_keys = set(yaml_docs.keys())

        # 3. Compare
        extra = yaml_keys - all_keys
        extra.discard(
            "__doc__"
        )  # __doc__ in yaml is fine even if not explicitly tracked sometimes?
        # Actually, if it's in yaml but not in code (e.g. empty file?), it is extra.
        # But 'module' symbol usually exists.

        missing_doc = set()

        for key in all_keys:
            if key in public_keys and key not in yaml_keys:
                missing_doc.add(key)

        return {
            "extra": extra,
            "missing": missing_doc,
            # Pending/Redundant/Conflict require source content comparison, skipped here.
            "pending": set(),
            "redundant": set(),
            "conflict": set(),
        }

    def hydrate_module(
        self,
        module: ModuleDef,
        force: bool = False,
        reconcile: bool = False,
        resolution_map: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        source_docs_override: Optional[Dict[str, DocstringIR]] = None,
    ) -> Dict[str, Any]:
        resolution_map = resolution_map or {}

        source_docs = (
            source_docs_override
            if source_docs_override is not None
            else self.flatten_module_docs(module)
        )
        if not source_docs:
            return {
                "success": True,
                "updated_keys": [],
                "conflicts": [],
                "reconciled_keys": [],
            }

        yaml_docs = self.load_docs_for_module(module)
        updated_keys = []
        conflicts = []
        reconciled_keys = []

        # Prepare new YAML state (we work with IRs)
        new_yaml_docs_ir = yaml_docs.copy()

        for key, source_ir in source_docs.items():
            if key not in yaml_docs:
                new_yaml_docs_ir[key] = source_ir
                updated_keys.append(key)
            else:
                existing_ir = yaml_docs[key]
                src_summary = source_ir.summary or ""
                yaml_summary = existing_ir.summary or ""

                if yaml_summary != src_summary:
                    # Check for specific resolution first
                    action = resolution_map.get(key)
                    should_force = force or (action == "HYDRATE_OVERWRITE")
                    should_reconcile = reconcile or (action == "HYDRATE_KEEP_EXISTING")

                    if should_reconcile:
                        reconciled_keys.append(key)
                        continue
                    elif should_force:
                        # CRITICAL: Preserve addons when overwriting from source
                        # Source IR has new summary, empty addons.
                        # Existing IR has old summary, existing addons.
                        source_ir.addons = existing_ir.addons
                        new_yaml_docs_ir[key] = source_ir
                        updated_keys.append(key)
                    else:
                        conflicts.append(key)

        if conflicts:
            return {
                "success": False,
                "updated_keys": [],
                "conflicts": conflicts,
                "reconciled_keys": [],
            }

        if updated_keys and not dry_run:
            module_path = self.root_path / module.file_path
            output_path = module_path.with_suffix(".stitcher.yaml")
            self._sidecar_adapter.save_doc_irs(output_path, new_yaml_docs_ir, self.serializer)

        return {
            "success": True,
            "updated_keys": updated_keys,
            "conflicts": [],
            "reconciled_keys": reconciled_keys,
        }

    def _extract_keys(self, module: ModuleDef, public_only: bool) -> set:
        keys = set()
        if module.docstring:
            keys.add("__doc__")

        def include(name: str) -> bool:
            if public_only:
                return not name.startswith("_")
            return True

        for func in module.functions:
            if include(func.name):
                keys.add(func.name)
        for cls in module.classes:
            if include(cls.name):
                keys.add(cls.name)
                for method in cls.methods:
                    if include(method.name):
                        keys.add(f"{cls.name}.{method.name}")
                for attr in cls.attributes:
                    if include(attr.name):
                        keys.add(f"{cls.name}.{attr.name}")
        for attr in module.attributes:
            if include(attr.name):
                keys.add(attr.name)
        return keys

    def compute_yaml_content_hash(self, content: Union[str, Dict[str, Any]]) -> str:
        if isinstance(content, str):
            return hashlib.sha256(content.encode("utf-8")).hexdigest()

        if isinstance(content, dict):
            # Canonicalize dict by sorting keys and ensuring JSON serialization
            canonical_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
            return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return hashlib.sha256(b"").hexdigest()

    def compute_yaml_hashes_for_path(self, file_path: str) -> Dict[str, str]:
        if not file_path:
            return {}
        module_path = self.root_path / file_path
        doc_path = self.resolver.get_doc_path(module_path)

        irs = self.load_docs_for_path(file_path)

        return {
            fqn: self.compute_ir_hash(ir) for fqn, ir in irs.items()
        }

    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]:
        return self.compute_yaml_hashes_for_path(module.file_path)

    def reformat_docs_for_module(self, module: ModuleDef) -> bool:
        if not module.file_path:
            return False
        module_path = self.root_path / module.file_path
        doc_path = self.resolver.get_doc_path(module_path)
        if not doc_path.exists():
            return False

        irs = self.load_docs_for_module(module)
        if not irs:
            return False

        self._sidecar_adapter.save_doc_irs(doc_path, irs, self.serializer)
        return True
~~~~~

### 下一步建议

我们已经完成了 Phase 1.1 的核心工作。`DocumentManager` 现在通过一个专用的、高保真的 `SidecarAdapter` 来处理所有文档 I/O，这为我们下一步删除 `common` 包中的冗余 `YamlAdapter` 铺平了道路。

我建议下一步执行 **Phase 1.2 & 1.3**:
1.  **审查 `stitcher-application` 中的其他模块**，确保没有其他地方直接使用了旧的 `common.YamlAdapter`。
2.  **物理删除 `packages/stitcher-common/src/stitcher/common/adapters/yaml_adapter.py` 文件**。
3.  **运行完整的测试套件**，确保系统的行为与重构前完全一致。

如果你同意，我将开始准备执行这些清理工作的计划。
