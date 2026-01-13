好的，我们完全达成了一致。这套新的指导原则——保真性、意图区分、职责分离——是构建一个健壮且值得信赖的工具的正确基石。我将立即开始执行您制定的新路线图。

这是实现第一步的计划。

## [WIP] refactor(sidecar): 实现意图感知的 SidecarAdapter

### 用户需求

根据新的实施路线图，我们需要实现第一步：重构 `SidecarAdapter`，使其具备“意图感知”能力，能够智能地区分“创建 (CREATE)”和“更新 (UPDATE)”两种操作，并采取截然不同的文件写入策略。

### 评论

这是一个至关重要的架构修正。它将工具的行为从“机器便利”转向了“尊重用户意图”，彻底解决了之前版本中因隐式自动格式化而导致的数据保真性丢失问题。这是构建一个真正专业的开发工具所必需的。

### 目标

1.  重构 `SidecarAdapter.save_doc_irs` 方法，为其增加区分文件存在与否的逻辑分支。
2.  **创建路径 (CREATE)**: 当目标文件不存在时，生成一个键已排序、格式标准（使用 `|-` 块风格）的全新文件。
3.  **更新路径 (UPDATE)**: 当目标文件已存在时，加载其完整内容（包括格式、注释和键序），仅在加载的对象上进行追加或修改，然后写回，从而实现高保真更新。
4.  为新的 `save_doc_irs` 行为编写全面的单元测试，覆盖 CREATE 和 UPDATE 两种场景。

### 基本原理

我们将利用 `ruamel.yaml` 库强大的“往返 (round-trip)”能力。在更新现有文件时，我们先加载它，这会将 YAML 内容解析为一个保留了所有元数据（注释、顺序等）的特殊对象。我们对这个对象进行修改，然后再将其写回。`ruamel.yaml` 会确保所有未被触及的部分都保持原样。而在创建新文件时，我们则从一个标准的 Python 字典开始，这允许我们施加确定性的排序和格式化规则，以建立一个干净的基线。

### 标签

#intent/refine #flow/ready #priority/high #scope/core #ai/instruct #task/domain/architecture #task/object/sidecar-adapter #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重构 SidecarAdapter

我将修改 `SidecarAdapter.save_doc_irs` 方法，实现其意图感知能力。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
    def save_doc_irs(
        self,
        path: Path,
        irs: Dict[str, DocstringIR],
        serializer: DocstringSerializerProtocol,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            # --- UPDATE PATH ---
            # Load existing content to preserve formatting, comments, and key order.
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = self._yaml.load(f)
                original_content = path.read_text("utf-8")
            except Exception:
                # If we can't read/parse, treat it as a new file creation.
                data = {}
                original_content = ""

            if not isinstance(data, dict):
                data = {}

            # Update the loaded data with new/modified IRs.
            # NO SORTING is applied to preserve original key order.
            # New keys will be appended by ruamel.yaml.
            for fqn, ir in irs.items():
                yaml_val = serializer.to_yaml(ir)
                if isinstance(yaml_val, str):
                    formatted_val = LiteralScalarString(yaml_val)
                elif isinstance(yaml_val, dict):
                    formatted_val = self._to_literal_strings(yaml_val)
                else:
                    formatted_val = yaml_val
                data[fqn] = formatted_val

            string_stream = io.StringIO()
            self._yaml.dump(data, string_stream)
            new_content = string_stream.getvalue()

            # Compare with original content to avoid unnecessary writes/mtime changes.
            if original_content != new_content:
                with path.open("w", encoding="utf-8") as f:
                    f.write(new_content)
        else:
            # --- CREATE PATH ---
            # For new files, create a clean, sorted baseline for predictability.
            sorted_irs = dict(sorted(irs.items()))
            yaml_data = {
                fqn: serializer.to_yaml(ir) for fqn, ir in sorted_irs.items()
            }
            formatted_data = self._to_literal_strings(yaml_data)
            string_stream = io.StringIO()
            self._yaml.dump(formatted_data, string_stream)
            with path.open("w", encoding="utf-8") as f:
                f.write(string_stream.getvalue())
~~~~~

#### Acts 2: 增强单元测试

接下来，我将更新单元测试套件，以验证新的 CREATE 和 UPDATE 行为是否符合我们的原则。

~~~~~act
write_file
packages/stitcher-lang-sidecar/tests/unit/test_sidecar_adapter.py
~~~~~
~~~~~python
from pathlib import Path
from textwrap import dedent

from stitcher.lang.sidecar.adapter import SidecarAdapter
from stitcher.lang.sidecar.parser import parse_signature_references
from stitcher.lang.python.analysis.models import ReferenceType
from stitcher.spec import DocstringIR
from stitcher.lang.python.docstring import RawSerializer


def test_parse_signature_references():
    content = dedent("""
    {
      "py://src/mod.py#Func": {
        "hash": "abc"
      },
      "py://src/mod.py#Class": {
        "hash": "def"
      }
    }
    """).strip()

    refs = parse_signature_references(content)
    expected = [
        ("py://src/mod.py#Func", 2, 2),
        ("py://src/mod.py#Class", 5, 2),
    ]
    assert sorted(refs) == sorted(expected)


def test_adapter_json_dispatch(tmp_path: Path):
    adapter = SidecarAdapter(root_path=tmp_path)
    path = tmp_path / "test.json"
    content = dedent("""
    {
      "py://foo#bar": {}
    }
    """)

    symbols, refs = adapter.parse(path, content)

    assert len(symbols) == 0
    assert len(refs) == 1

    ref = refs[0]
    assert ref.kind == ReferenceType.SIDECAR_ID.value
    assert ref.target_id == "py://foo#bar"
    assert ref.target_fqn is None


def test_adapter_yaml_suri_computation(tmp_path: Path):
    # 1. ARRANGE: Create a mock file system
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    py_file = src_dir / "module.py"
    py_file.touch()

    yaml_file = src_dir / "module.stitcher.yaml"
    yaml_content = dedent("""
    MyClass:
      doc: hello
    my_func:
      doc: world
    """)
    yaml_file.write_text(yaml_content)

    # 2. ACT
    adapter = SidecarAdapter(root_path=tmp_path)
    symbols, refs = adapter.parse(yaml_file, yaml_content)

    # 3. ASSERT
    assert len(symbols) == 0
    assert len(refs) == 2

    refs_by_id = {ref.target_id: ref for ref in refs}

    # Verify first reference
    suri1 = "py://src/module.py#MyClass"
    assert suri1 in refs_by_id
    ref1 = refs_by_id[suri1]
    assert ref1.kind == ReferenceType.SIDECAR_DOC_ID.value
    assert ref1.lineno == 2
    assert ref1.col_offset == 0

    # Verify second reference
    suri2 = "py://src/module.py#my_func"
    assert suri2 in refs_by_id
    ref2 = refs_by_id[suri2]
    assert ref2.kind == ReferenceType.SIDECAR_DOC_ID.value
    assert ref2.lineno == 4
    assert ref2.col_offset == 0


def test_save_doc_irs_create_path_sorts_and_formats(tmp_path: Path):
    """
    Verifies that when creating a new file, the adapter sorts keys alphabetically
    and uses the standard block scalar format.
    """
    # ARRANGE
    adapter = SidecarAdapter(root_path=tmp_path)
    serializer = RawSerializer()
    doc_path = tmp_path / "new_module.stitcher.yaml"

    # Unsorted IRs
    irs = {
        "z_function": DocstringIR(summary="Doc for Z"),
        "a_function": DocstringIR(summary="Doc for A"),
        "c_class": DocstringIR(summary="Doc for C"),
    }

    # ACT
    adapter.save_doc_irs(doc_path, irs, serializer)

    # ASSERT
    content = doc_path.read_text()

    # 1. Check for standard block scalar format
    assert "a_function: |-\n  Doc for A" in content
    assert "c_class: |-\n  Doc for C" in content
    assert "z_function: |-\n  Doc for Z" in content

    # 2. Check for alphabetical sorting
    a_pos = content.find("a_function")
    c_pos = content.find("c_class")
    z_pos = content.find("z_function")

    assert a_pos < c_pos < z_pos


def test_save_doc_irs_update_path_preserves_order_and_comments(tmp_path: Path):
    """
    Verifies that when updating an existing file, the adapter preserves
    original key order and comments, and appends new keys.
    """
    # ARRANGE
    adapter = SidecarAdapter(root_path=tmp_path)
    serializer = RawSerializer()
    doc_path = tmp_path / "existing_module.stitcher.yaml"

    # Create an initial file with specific order and comments
    initial_content = dedent("""
        # A special comment that must be preserved
        z_function: |-
          Original doc for Z
        a_function: |-
          Original doc for A
    """).strip() + "\n"
    doc_path.write_text(initial_content)

    # New/updated IRs to "pump"
    irs = {
        "a_function": DocstringIR(summary="Updated doc for A"),  # Update existing
        "b_function": DocstringIR(summary="New doc for B"),  # Add new
    }

    # ACT
    adapter.save_doc_irs(doc_path, irs, serializer)

    # ASSERT
    content = doc_path.read_text()

    # 1. Check that the comment is preserved
    assert "# A special comment that must be preserved" in content

    # 2. Check that the original key order is preserved
    z_pos = content.find("z_function")
    a_pos = content.find("a_function")
    b_pos = content.find("b_function")

    assert z_pos != -1 and a_pos != -1 and b_pos != -1
    assert z_pos < a_pos < b_pos

    # 3. Check that values are updated/added correctly
    assert "z_function: |-\n  Original doc for Z" in content
    assert "a_function: |-\n  Updated doc for A" in content
    assert "b_function: |-\n  New doc for B" in content
~~~~~

### 下一步建议

我们已经成功完成了路线图的第一步。下一步是**第二步：净化 `DocumentManager` 与 `stitcher-common`**。

具体行动将是：
1.  审查 `DocumentManager`，确保它完全依赖我们刚刚重构的 `SidecarAdapter` 来处理所有 `.stitcher.yaml` 的 I/O 操作。
2.  在确认依赖关系解耦后，物理删除位于 `stitcher-common` 中的旧 `YamlAdapter`。

如果您同意，我将为您准备执行第二步的计划。
