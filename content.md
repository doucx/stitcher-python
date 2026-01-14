Your analysis is correct. The test failures are a direct and expected consequence of the protocol refactoring we just performed. A cascading series of failures is a sign of a deep, cross-cutting architectural change, which is exactly what we are doing.

Following the **HFEA (High-Fidelity Engineering Axioms)**, we must not patch the symptoms. We must address the root cause, which is the partially completed migration to the Zero-IO architecture. The failing tests are our guide, showing us precisely which components are still coupled to the old, file-based IO-heavy logic.

I will generate a plan to fix the immediate, low-level test breakages caused by the protocol change. Then, as a next step, I will outline the plan to complete the refactoring of the `check` command, which will resolve the remaining widespread integration test failures.

## [WIP] test: Adapt tests to new DocstringSerializerProtocol

### 用户需求

Fix the test suite failures that are a direct result of the `DocstringSerializerProtocol` refactoring. This involves updating test code that was calling the old `to_yaml`/`from_yaml` methods and was not correctly handling the updated return signature of `SidecarAdapter.parse`.

### 评论

This plan addresses the immediate fallout from our last architectural change. By fixing the unit tests for the serializers and the sidecar adapter, we re-establish a stable foundation at the lower levels of the system. This is a necessary prerequisite before we can confidently proceed with the higher-level refactoring of the `check` command's logic. These fixes are not a workaround; they are the required updates to align our test suite with the new, more robust architecture.

### 目标

1.  Update `packages/stitcher-lang-python/tests/adapter/unit/docstring/test_serializers.py` to use the new `to_yaml_object` and `from_yaml_object` methods.
2.  Update `packages/stitcher-lang-sidecar/tests/unit/test_sidecar_adapter.py` to correctly handle the new 3-tuple return value of `SidecarAdapter.parse` and adjust the test data to be compatible with the default `RawSerializer`.

### 基本原理

We will apply a series of precise patches:
-   A global replacement of method names in `test_serializers.py` to align with the new protocol.
-   A targeted modification of `test_sidecar_adapter.py` to unpack the new `doc_entries` from the `parse` method's result, simplify the test's YAML fixture to align with `RawSerializer`'s expectations, and add assertions to verify the correctness of the generated `DocEntryRecord`s.

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/python #comp/sidecar #scope/dx #ai/instruct #task/domain/storage #task/object/sidecar-index #task/action/implementation #task/state/continue #task/status/active

---

### Script

#### Acts 1: Update Serializer Tests to Use New Protocol

We'll replace all instances of the old method names in the serializer test suite.

~~~~~act
patch_file
packages/stitcher-lang-python/tests/adapter/unit/docstring/test_serializers.py
~~~~~
~~~~~python.old
class TestRawSerializer:
    def test_roundtrip_simple(self):
        serializer = RawSerializer()
        ir = DocstringIR(summary="Simple doc.")
        serialized = serializer.to_yaml(ir)
        assert serialized == "Simple doc."
        deserialized = serializer.from_yaml(serialized)
        assert deserialized == ir

    def test_roundtrip_hybrid(self):
        serializer = RawSerializer()
        ir = DocstringIR(summary="Hybrid doc.", addons={"Addon.Test": "Data"})
        serialized = serializer.to_yaml(ir)
        assert serialized == {"Raw": "Hybrid doc.", "Addon.Test": "Data"}
        deserialized = serializer.from_yaml(serialized)
        assert deserialized == ir
~~~~~
~~~~~python.new
class TestRawSerializer:
    def test_roundtrip_simple(self):
        serializer = RawSerializer()
        ir = DocstringIR(summary="Simple doc.")
        serialized = serializer.to_yaml_object(ir)
        assert serialized == "Simple doc."
        deserialized = serializer.from_yaml_object(serialized)
        assert deserialized == ir

    def test_roundtrip_hybrid(self):
        serializer = RawSerializer()
        ir = DocstringIR(summary="Hybrid doc.", addons={"Addon.Test": "Data"})
        serialized = serializer.to_yaml_object(ir)
        assert serialized == {"Raw": "Hybrid doc.", "Addon.Test": "Data"}
        deserialized = serializer.from_yaml_object(serialized)
        assert deserialized == ir
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-python/tests/adapter/unit/docstring/test_serializers.py
~~~~~
~~~~~python.old
class TestGoogleSerializer:
    def test_to_yaml(self, complex_ir):
        serializer = GoogleSerializer()
        data = serializer.to_yaml(complex_ir)

        assert data["Summary"] == "This is the summary."
        assert data["Extended"] == "This is the extended description."
        assert "Args" in data
        # Verification: No type info encoded in the value string
        assert data["Args"]["param1"] == "The first parameter."
        assert "Returns" in data
        assert data["Returns"]["bool"] == "True if successful, False otherwise."
        assert "Raises" in data
        assert "Examples" in data
        assert data["Addon.Test"] == {"key": "value"}
        assert data["Configuration"] == "This is a custom section."

    def test_from_yaml_roundtrip(self, complex_ir):
        serializer = GoogleSerializer()
        yaml_data = serializer.to_yaml(complex_ir)
        reconstructed_ir = serializer.from_yaml(yaml_data)

        # Due to fallback keys, we need to compare content carefully
        assert reconstructed_ir.summary == complex_ir.summary
        assert reconstructed_ir.extended == complex_ir.extended
        assert reconstructed_ir.addons == complex_ir.addons

        # A simple equality check might fail due to ordering or minor differences.
        # Let's check section by section.
        assert len(reconstructed_ir.sections) == len(complex_ir.sections)

    def test_graceful_fallback_from_string(self):
        serializer = GoogleSerializer()
        ir = serializer.from_yaml("Just a raw string.")
        assert ir.summary == "Just a raw string."
        assert not ir.sections
        assert not ir.addons
~~~~~
~~~~~python.new
class TestGoogleSerializer:
    def test_to_yaml(self, complex_ir):
        serializer = GoogleSerializer()
        data = serializer.to_yaml_object(complex_ir)

        assert data["Summary"] == "This is the summary."
        assert data["Extended"] == "This is the extended description."
        assert "Args" in data
        # Verification: No type info encoded in the value string
        assert data["Args"]["param1"] == "The first parameter."
        assert "Returns" in data
        assert data["Returns"]["bool"] == "True if successful, False otherwise."
        assert "Raises" in data
        assert "Examples" in data
        assert data["Addon.Test"] == {"key": "value"}
        assert data["Configuration"] == "This is a custom section."

    def test_from_yaml_roundtrip(self, complex_ir):
        serializer = GoogleSerializer()
        yaml_data = serializer.to_yaml_object(complex_ir)
        reconstructed_ir = serializer.from_yaml_object(yaml_data)

        # Due to fallback keys, we need to compare content carefully
        assert reconstructed_ir.summary == complex_ir.summary
        assert reconstructed_ir.extended == complex_ir.extended
        assert reconstructed_ir.addons == complex_ir.addons

        # A simple equality check might fail due to ordering or minor differences.
        # Let's check section by section.
        assert len(reconstructed_ir.sections) == len(complex_ir.sections)

    def test_graceful_fallback_from_string(self):
        serializer = GoogleSerializer()
        ir = serializer.from_yaml_object("Just a raw string.")
        assert ir.summary == "Just a raw string."
        assert not ir.sections
        assert not ir.addons
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-python/tests/adapter/unit/docstring/test_serializers.py
~~~~~
~~~~~python.old
class TestNumpySerializer:
    def test_to_yaml(self, complex_ir):
        serializer = NumpySerializer()
        data = serializer.to_yaml(complex_ir)

        assert data["Summary"] == "This is the summary."
        assert "Parameters" in data  # Key difference from Google
        assert data["Parameters"]["param1"] == "The first parameter."
        assert "Returns" in data
        assert "Raises" in data
        assert "Examples" in data
        assert data["Addon.Test"] == {"key": "value"}
        assert data["Configuration"] == "This is a custom section."

    def test_from_yaml_roundtrip(self, complex_ir):
        serializer = NumpySerializer()
        yaml_data = serializer.to_yaml(complex_ir)
        reconstructed_ir = serializer.from_yaml(yaml_data)

        assert reconstructed_ir.summary == complex_ir.summary
        assert reconstructed_ir.extended == complex_ir.extended
        assert reconstructed_ir.addons == complex_ir.addons
        assert len(reconstructed_ir.sections) == len(complex_ir.sections)
~~~~~
~~~~~python.new
class TestNumpySerializer:
    def test_to_yaml(self, complex_ir):
        serializer = NumpySerializer()
        data = serializer.to_yaml_object(complex_ir)

        assert data["Summary"] == "This is the summary."
        assert "Parameters" in data  # Key difference from Google
        assert data["Parameters"]["param1"] == "The first parameter."
        assert "Returns" in data
        assert "Raises" in data
        assert "Examples" in data
        assert data["Addon.Test"] == {"key": "value"}
        assert data["Configuration"] == "This is a custom section."

    def test_from_yaml_roundtrip(self, complex_ir):
        serializer = NumpySerializer()
        yaml_data = serializer.to_yaml_object(complex_ir)
        reconstructed_ir = serializer.from_yaml_object(yaml_data)

        assert reconstructed_ir.summary == complex_ir.summary
        assert reconstructed_ir.extended == complex_ir.extended
        assert reconstructed_ir.addons == complex_ir.addons
        assert len(reconstructed_ir.sections) == len(complex_ir.sections)
~~~~~

#### Acts 2: Update Sidecar Adapter Test

We will update the test to handle the 3-tuple return and add assertions for the `DocEntryRecord`s.

~~~~~act
patch_file
packages/stitcher-lang-sidecar/tests/unit/test_sidecar_adapter.py
~~~~~
~~~~~python.old
    yaml_file = src_dir / "module.stitcher.yaml"
    yaml_content = dedent("""
    MyClass:
      doc: hello
    my_func:
      doc: world
    """)
    yaml_file.write_text(yaml_content)

    # 2. ACT
    adapter = SidecarAdapter(root_path=tmp_path, uri_generator=PythonURIGenerator())
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
~~~~~
~~~~~python.new
    yaml_file = src_dir / "module.stitcher.yaml"
    yaml_content = dedent("""
    MyClass: hello
    my_func: world
    """)
    yaml_file.write_text(yaml_content)

    # 2. ACT
    adapter = SidecarAdapter(root_path=tmp_path, uri_generator=PythonURIGenerator())
    symbols, refs, doc_entries = adapter.parse(yaml_file, yaml_content)

    # 3. ASSERT
    assert len(symbols) == 0
    assert len(refs) == 2
    assert len(doc_entries) == 2

    refs_by_id = {ref.target_id: ref for ref in refs}
    doc_entries_by_id = {de.symbol_id: de for de in doc_entries}

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

    # Verify doc entries
    assert suri1 in doc_entries_by_id
    de1 = doc_entries_by_id[suri1]
    assert de1.lineno == 2
    assert de1.content_hash is not None
    assert '"summary": "hello"' in de1.ir_data_json

    assert suri2 in doc_entries_by_id
    de2 = doc_entries_by_id[suri2]
    assert de2.lineno == 4
    assert '"summary": "world"' in de2.ir_data_json
~~~~~

### 下一步建议
The low-level tests are now fixed and aligned with our new architecture. However, as the test results show, the high-level `check` command is still fundamentally broken.

**Analysis**: The `check` command's current implementation (`IndexCheckSubjectAdapter`) still relies on loading `.stitcher.yaml` files from the filesystem during its analysis. This is the IO-heavy process we aim to eliminate. The recent refactoring of the serialization layer has broken this old path.

**Strategic Solution**: Instead of patching the old, slow file-based logic, we must now complete the refactoring by replacing it with the new "Zero-IO" approach. This involves:
1.  **Creating a new `IndexStore` method**: `get_all_symbol_states_for_file(file_path: str)` that performs a single, efficient SQL `JOIN` between the `symbols` and `doc_entries` tables.
2.  **Deleting `IndexCheckSubjectAdapter`**: This class represents the old architecture and must be removed.
3.  **Refactoring `CheckRunner`**: The `analyze_paths` method will be simplified to call the new `IndexStore` method and pass the resulting data directly to the `ConsistencyEngine`.

This is the final step to realize our performance goals and fix the remaining tests in an architecturally sound manner. I will generate a plan to execute this if you agree.
