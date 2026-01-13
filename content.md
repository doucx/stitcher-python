你的否决是完全正确的，这是一个关键的架构修正。我最初的解决方案为了让测试通过而绕过了核心问题，这违反了**高保真工程（HFEA）**公理。

## [WIP] **Sidecar 文件的可读性不是一个可选项，而是其本体论的一部分。** 使用 `|-` 块风格来呈现多行字符串，是确保 YAML 作为“人类可读的”元数据格式的核心契约。我的修改破坏了这一契约。

我已经重新分析了所有测试失败的原因，并制定了一个尊重此契约的修复计划。该计划将：
1.  **强制执行正确的 YAML 格式**：修改 `SidecarAdapter`，确保所有字符串在序列化时都使用 `|-` 块风格，以满足 `test_init_command` 的断言。
2.  **修复测试接口**：修复因我重构 `DocumentManager` 而导致的测试接口不匹配问题，包括 `__init__` 签名和内部序列化方法的 `AttributeError`。

我将立即执行这个新的、更正确的计划。

### Script

#### Acts 1: 强制 SidecarAdapter 使用高保真 YAML 格式

我将重写 `SidecarAdapter`，通过 `ruamel.yaml` 的 `LiteralScalarString` 来确保所有字符串值在保存时都采用用户期望的 `|-` 块格式，从而修复集成测试中的断言失败。

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python
import io
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union, Any

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

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

    def _to_literal_strings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively convert all string values to LiteralScalarString for block style."""
        processed = {}
        for k, v in data.items():
            if isinstance(v, str):
                processed[k] = LiteralScalarString(v)
            elif isinstance(v, dict):
                processed[k] = self._to_literal_strings(v)
            else:
                processed[k] = v
        return processed

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
        
        # Enforce block scalar style for all string values
        formatted_data = self._to_literal_strings(yaml_data)

        path.parent.mkdir(parents=True, exist_ok=True)

        original_content = ""
        if path.exists():
            try:
                original_content = path.read_text("utf-8")
            except (OSError, UnicodeDecodeError):
                pass

        string_stream = io.StringIO()
        self._yaml.dump(formatted_data, string_stream)
        new_content = string_stream.getvalue()

        if original_content != new_content:
            with path.open("w", encoding="utf-8") as f:
                f.write(new_content)

    def dump_to_string(self, data: Dict[str, Any]) -> str:
        string_stream = io.StringIO()
        self._yaml.dump(self._to_literal_strings(data), string_stream)
        return string_stream.getvalue()

    def serialize_ir(
        self, ir: DocstringIR, serializer: DocstringSerializerProtocol
    ) -> Union[str, Dict[str, Any]]:
        return serializer.to_yaml(ir)
~~~~~

#### Acts 2: 修复 DocumentManager 的单元测试

我将重写 `test_doc_manager.py`，移除因重构而已被废弃的 `MockAdapter`。新的测试将直接与文件系统交互，验证 `DocumentManager` 是否正确地调用 `SidecarAdapter` 生成了预期的 YAML 文件。

~~~~~act
write_file
packages/stitcher-application/tests/unit/test_doc_manager.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from ruamel.yaml import YAML
from stitcher.spec import ModuleDef, FunctionDef, ClassDef, Attribute
from stitcher.app.services import DocumentManager


@pytest.fixture
def sample_module_ir():
    return ModuleDef(
        file_path="src/main.py",
        docstring="Module doc",
        functions=[FunctionDef(name="func", docstring="Func doc")],
        classes=[
            ClassDef(
                name="MyClass",
                docstring="Class doc",
                attributes=[Attribute(name="attr", docstring="Attr doc")],
                methods=[FunctionDef(name="method", docstring="Method doc")],
            )
        ],
    )


def test_flatten_module_docs(tmp_path, sample_module_ir):
    manager = DocumentManager(root_path=tmp_path)
    docs = manager.flatten_module_docs(sample_module_ir)

    assert docs["__doc__"].summary == "Module doc"
    assert docs["func"].summary == "Func doc"
    assert docs["MyClass"].summary == "Class doc"
    assert docs["MyClass.method"].summary == "Method doc"
    assert docs["MyClass.attr"].summary == "Attr doc"


def test_save_docs_for_module(tmp_path, sample_module_ir):
    manager = DocumentManager(root_path=tmp_path)

    output_path = manager.save_docs_for_module(sample_module_ir)

    expected_path = tmp_path / "src/main.stitcher.yaml"
    assert output_path == expected_path
    assert expected_path.exists()

    # Load the content with a YAML parser to verify data correctness
    yaml = YAML()
    content = yaml.load(expected_path.read_text("utf-8"))
    assert content["MyClass.method"] == "Method doc"
    assert content["__doc__"] == "Module doc"
~~~~~

#### Acts 3: 恢复 DocumentManager 的内部序列化接口

为了修复策略测试中的 `AttributeError`，我将恢复 `DocumentManager` 的内部 `_serialize_ir` 和 `_deserialize_ir` 方法。这确保了单元测试可以在不触及文件系统的情况下，继续独立验证不同文档风格（google, numpy, raw）的序列化/反序列化逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        return self._sidecar_adapter.serialize_ir(ir, self.serializer)

    def compute_ir_hash(self, ir: DocstringIR) -> str:
        serialized = self.serialize_ir(ir)
        return self.compute_yaml_content_hash(serialized)
~~~~~
~~~~~python.new
    def _serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        return self._sidecar_adapter.serialize_ir(ir, self.serializer)

    def _deserialize_ir(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        """Internal method for testing strategy-based deserialization."""
        return self.serializer.from_yaml(data)

    def serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        return self._serialize_ir(ir)

    def compute_ir_hash(self, ir: DocstringIR) -> str:
        serialized = self._serialize_ir(ir)
        return self.compute_yaml_content_hash(serialized)
~~~~~
