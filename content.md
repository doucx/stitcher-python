## [WIP] feat: Implement Sidecar Indexing Logic

### 用户需求
Upgrade the indexing subsystem to support `.stitcher.yaml` (Sidecar) files as first-class citizens. This involves parsing these files during the indexing phase (Write Path) and storing their content in the newly created `doc_entries` table. This is a prerequisite for the "Zero-IO" Read Path.

### 评论
This plan executes the core logic changes required by the architecture analysis. It spans across `stitcher-spec` (data structures), `stitcher-index` (storage logic), and `stitcher-lang-sidecar` (parsing logic). By handling the heavy lifting of YAML parsing and SURI generation during indexing, we enable subsequent operations to be extremely fast.

### 目标
1.  Define `DocEntryRecord` in `stitcher-spec`.
2.  Update `IndexStore` to handle writing to `doc_entries`.
3.  Update `FileIndexer` to support adapters returning document entries.
4.  Upgrade `SidecarAdapter` to parse YAML content into `DocEntryRecord`s.

### 基本原理
We introduce `DocEntryRecord` as the data transfer object for Sidecar content. `IndexStore.update_analysis` is extended to atomically update this new data alongside symbols and references. `FileIndexer` acts as the coordinator, detecting if the adapter returns this new data type. Finally, `SidecarAdapter` is enhanced to perform full YAML parsing (using `ruamel.yaml`) and SURI generation, serializing the result to JSON for storage.

### 标签
#intent/build #flow/ready #priority/high #comp/index #comp/spec #comp/sidecar #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/sidecar-index #task/action/implementation #task/state/continue #task/status/active

---

### Script

#### Acts 1: Define DocEntryRecord in stitcher-spec

We add the `DocEntryRecord` dataclass to the specification.

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/index.py
~~~~~
~~~~~python.old
@dataclass
class DependencyEdge:
    source_path: str
    target_fqn: str
    kind: str
    lineno: int
~~~~~
~~~~~python.new
@dataclass
class DependencyEdge:
    source_path: str
    target_fqn: str
    kind: str
    lineno: int


@dataclass
class DocEntryRecord:
    symbol_id: str
    content_hash: str
    ir_data_json: str
    lineno: int
    file_id: Optional[int] = None
    id: Optional[int] = None
~~~~~

#### Acts 2: Update LanguageAdapter Protocol

We update the `LanguageAdapter` protocol to allow returning `DocEntryRecord`. We use a `Union` to maintain backward compatibility with existing adapters (like Python) that only return a 2-tuple.

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/registry.py
~~~~~
~~~~~python.old
from typing import Protocol, List, Tuple
from pathlib import Path
from stitcher.spec.index import SymbolRecord, ReferenceRecord


class LanguageAdapter(Protocol):
    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]: ...
~~~~~
~~~~~python.new
from typing import Protocol, List, Tuple, Union
from pathlib import Path
from stitcher.spec.index import SymbolRecord, ReferenceRecord, DocEntryRecord


class LanguageAdapter(Protocol):
    def parse(
        self, file_path: Path, content: str
    ) -> Union[
        Tuple[List[SymbolRecord], List[ReferenceRecord]],
        Tuple[List[SymbolRecord], List[ReferenceRecord], List[DocEntryRecord]],
    ]: ...
~~~~~

#### Acts 3: Update IndexStore to handle doc_entries

We update `update_analysis` in `IndexStore` to clear and insert `doc_entries`.

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
    def update_analysis(
        self,
        file_id: int,
        symbols: List[SymbolRecord],
        references: List[ReferenceRecord],
    ) -> None:
        with self.db.get_connection() as conn:
            # 1. Clear old data for this file
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            conn.execute(
                "DELETE FROM 'references' WHERE source_file_id = ?", (file_id,)
            )

            # 2. Insert new symbols
            if symbols:
~~~~~
~~~~~python.new
    def update_analysis(
        self,
        file_id: int,
        symbols: List[SymbolRecord],
        references: List[ReferenceRecord],
        doc_entries: List["DocEntryRecord"] = [],
    ) -> None:
        with self.db.get_connection() as conn:
            # 1. Clear old data for this file
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            conn.execute(
                "DELETE FROM 'references' WHERE source_file_id = ?", (file_id,)
            )
            conn.execute("DELETE FROM doc_entries WHERE file_id = ?", (file_id,))

            # 2. Insert new symbols
            if symbols:
~~~~~

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
            # 3. Insert new references
            if references:
                conn.executemany(
                    """
                    INSERT INTO 'references' (
                        source_file_id, target_fqn, target_id, kind, 
                        lineno, col_offset, end_lineno, end_col_offset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            file_id,
                            r.target_fqn,
                            r.target_id,
                            r.kind,
                            r.lineno,
                            r.col_offset,
                            r.end_lineno,
                            r.end_col_offset,
                        )
                        for r in references
                    ],
                )

            # 4. Mark as indexed
            conn.execute(
                "UPDATE files SET indexing_status = 1 WHERE id = ?", (file_id,)
            )
~~~~~
~~~~~python.new
            # 3. Insert new references
            if references:
                conn.executemany(
                    """
                    INSERT INTO 'references' (
                        source_file_id, target_fqn, target_id, kind, 
                        lineno, col_offset, end_lineno, end_col_offset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            file_id,
                            r.target_fqn,
                            r.target_id,
                            r.kind,
                            r.lineno,
                            r.col_offset,
                            r.end_lineno,
                            r.end_col_offset,
                        )
                        for r in references
                    ],
                )

            # 4. Insert new doc entries
            if doc_entries:
                conn.executemany(
                    """
                    INSERT INTO doc_entries (
                        file_id, symbol_id, content_hash, ir_data_json, lineno
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            file_id,
                            d.symbol_id,
                            d.content_hash,
                            d.ir_data_json,
                            d.lineno,
                        )
                        for d in doc_entries
                    ],
                )

            # 5. Mark as indexed
            conn.execute(
                "UPDATE files SET indexing_status = 1 WHERE id = ?", (file_id,)
            )
~~~~~

#### Acts 4: Import DocEntryRecord in IndexStore

Need to make sure `DocEntryRecord` is available.

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
from .linker import Linker
from stitcher.spec.index import (
    FileRecord,
    SymbolRecord,
    ReferenceRecord,
    DependencyEdge,
)
~~~~~
~~~~~python.new
from .linker import Linker
from stitcher.spec.index import (
    FileRecord,
    SymbolRecord,
    ReferenceRecord,
    DependencyEdge,
    DocEntryRecord,
)
~~~~~

#### Acts 5: Update FileIndexer to handle 3-tuple return

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
        # Let exceptions bubble up to be caught by the caller
        symbols, references = adapter.parse(abs_path, text_content)
        self.store.update_analysis(file_id, symbols, references)
~~~~~
~~~~~python.new
        # Let exceptions bubble up to be caught by the caller
        result = adapter.parse(abs_path, text_content)
        if len(result) == 3:
            symbols, references, doc_entries = result  # type: ignore
        else:
            symbols, references = result  # type: ignore
            doc_entries = []

        self.store.update_analysis(file_id, symbols, references, doc_entries)
~~~~~

#### Acts 6: Update SidecarAdapter

We implement the full parsing logic in `SidecarAdapter`. We need to import `DocEntryRecord`, `RawSerializer`, `json`, and `hashlib`.

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python.old
import io
from pathlib import Path
from typing import List, Tuple, Dict, Union, Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from stitcher.spec import DocstringIR, URIGeneratorProtocol
from stitcher.spec.protocols import DocstringSerializerProtocol
from stitcher.spec.registry import LanguageAdapter
from stitcher.spec.index import SymbolRecord, ReferenceRecord

from .parser import (
    parse_doc_references,
    parse_signature_references,
)
from stitcher.common.services import AssetPathResolver
from stitcher.lang.python.analysis.models import ReferenceType


class SidecarAdapter(LanguageAdapter):
~~~~~
~~~~~python.new
import io
import json
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict, Union, Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from stitcher.spec import DocstringIR, URIGeneratorProtocol
from stitcher.spec.protocols import DocstringSerializerProtocol
from stitcher.spec.registry import LanguageAdapter
from stitcher.spec.index import SymbolRecord, ReferenceRecord, DocEntryRecord

from .parser import (
    parse_doc_references,
    parse_signature_references,
)
from stitcher.common.services import AssetPathResolver
from stitcher.lang.python.analysis.models import ReferenceType
from stitcher.lang.python.docstring import RawSerializer


class SidecarAdapter(LanguageAdapter):
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python.old
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
                    suri = self.uri_generator.generate_symbol_uri(rel_py_path, fragment)
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
~~~~~
~~~~~python.new
    def parse(
        self, file_path: Path, content: str
    ) -> Union[
        Tuple[List[SymbolRecord], List[ReferenceRecord]],
        Tuple[List[SymbolRecord], List[ReferenceRecord], List[DocEntryRecord]],
    ]:
        symbols: List[SymbolRecord] = []
        references: List[ReferenceRecord] = []
        doc_entries: List[DocEntryRecord] = []

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
            return symbols, references

        elif file_path.suffix in (".yaml", ".yml"):
            try:
                if not file_path.name.endswith(".stitcher.yaml"):
                    return symbols, references

                py_name = file_path.name.replace(".stitcher.yaml", ".py")
                py_path = file_path.with_name(py_name)

                if not py_path.exists():
                    return symbols, references

                rel_py_path = py_path.relative_to(self.root_path).as_posix()

                # Full parsing for DocEntryRecord
                # We use ruamel.yaml to load the structure, then serialize to JSON
                data = self._yaml.load(content)
                serializer = RawSerializer()

                if isinstance(data, dict):
                    for fragment, raw_ir in data.items():
                        # 1. Determine location (line/col)
                        lineno = 0
                        lc = getattr(data, "lc", None)
                        if lc and hasattr(lc, "item"):
                            pos = lc.item(fragment)
                            if pos:
                                lineno = pos[0] + 1

                        # 2. Generate SURI
                        suri = self.uri_generator.generate_symbol_uri(
                            rel_py_path, str(fragment)
                        )

                        # 3. Create DocstringIR and serialize to JSON
                        try:
                            ir = serializer.from_yaml(raw_ir)
                            # Serialize to dict first using serializer (which handles IR structure)
                            # RawSerializer.to_yaml returns a dict or str suitable for YAML
                            # We want a standard JSON representation for the DB
                            # Since from_yaml/to_yaml are isomorphic for RawSerializer,
                            # we can re-use the raw_ir or re-serialize.
                            # To be safe and canonical (e.g. if we change serializer later),
                            # let's re-serialize to a clean dict.
                            # Actually, ir is a dataclass. Let's dump it as json directly?
                            # No, IR might contain objects. Better to use serializer.to_yaml output
                            # but ensure it's JSON serializable (literal strings etc).
                            # Since we use RawSerializer, to_yaml returns simple dicts/strings.
                            # We need to be careful with Ruamel's ScalarString in raw_ir.
                            # It's better to reconstruct IR then dump.
                            
                            # However, for the DB `ir_data_json`, we want a format that we can
                            # easily load back into DocstringIR. 
                            # stitcher.spec doesn't enforce JSON schema, but assumes serializer handles it.
                            # Let's store the dict form produced by serializer.
                            ir_dict = serializer.to_yaml(ir)
                            
                            # Use a custom encoder if necessary, or just rely on json.dumps
                            # assuming serializer output is simple.
                            # Note: to_yaml might return LiteralScalarString which json doesn't like.
                            # We need to stringify them.
                            def json_safe(obj):
                                if hasattr(obj, "__str__"):
                                    return str(obj)
                                return obj
                            
                            ir_json = json.dumps(ir_dict, default=json_safe, sort_keys=True)
                            
                            # 4. Compute Hash (Consistency Check)
                            # We use the JSON string for hashing to be consistent with DB
                            content_hash = hashlib.sha256(
                                ir_json.encode("utf-8")
                            ).hexdigest()

                            doc_entries.append(
                                DocEntryRecord(
                                    symbol_id=suri,
                                    content_hash=content_hash,
                                    ir_data_json=ir_json,
                                    lineno=lineno,
                                )
                            )

                            # 5. Add Reference (for backward compat / linking graph)
                            references.append(
                                ReferenceRecord(
                                    target_id=suri,
                                    kind=ReferenceType.SIDECAR_DOC_ID.value,
                                    lineno=lineno,
                                    col_offset=0,
                                    end_lineno=lineno,
                                    end_col_offset=len(str(fragment)),
                                )
                            )

                        except Exception:
                            # Skip malformed entries
                            continue

            except (ValueError, FileNotFoundError, Exception):
                pass

        return symbols, references, doc_entries
~~~~~

### 下一步建议
The indexing infrastructure is now capable of digesting Sidecar files. The next step is to update the `stitcher-application` to register the `SidecarAdapter` with the `FileIndexer`. After that, we can implement the "Zero-IO" `CheckRunner` that leverages this new index.
