好的，我来分析并修复这些测试失败。

所有15个失败的测试都与重构操作（重命名、移动文件/目录）后，旁支文件（`stitcher.yaml` 和 `stitcher.lock`）的内容没有被正确更新有关。特别是，作为签名文件使用的`stitcher.lock`（其本质是JSON），里面的SURI（Stitcher Uniform Resource Identifier）键没有被正确转换。

## [WIP] 增强 `SidecarTransformer`, 清理单元测试

### 错误分析

经过分析，我定位到两个核心问题：

1.  **`SidecarTransformer` 逻辑缺陷**:
    *   **文件类型识别不完整**: `SidecarTransformer` 是更新旁支文件的核心组件。它的`transform`方法通过文件后缀来决定使用何种逻辑（JSON或YAML）。但它只检查了`.json`后缀，而新的签名文件标准是`stitcher.lock`。因此，当规划器（Planner）要求它转换`.lock`文件时，它直接跳过了所有逻辑，导致SURI键完全没有更新。这是导致所有集成测试失败的根本原因。
    *   **路径比较脆弱**: 在`_transform_json_data`方法中，用于判断SURI中的文件路径是否需要更新的逻辑 `current_path == old_file_path` 可能因为类型不匹配（例如 `Path` 对象 vs `str`）或路径格式问题而不稳定。

2.  **测试代码冗余**: `test_transform.py`中的一个测试用例包含了重复的、无意义的代码行，虽然不影响结果，但应予以清理。

### 解决方案

我将执行一个精确的计划来修复这些问题：

1.  **增强 `SidecarTransformer`**: 我将修改 `stitcher-lang-sidecar` 包中的 `transform.py`，使其能够识别并处理 `.lock` 文件，就像处理 `.json` 文件一样。同时，我将加强其内部的路径比较逻辑，使其更加健壮。
2.  **清理单元测试**: 我将编辑 `test_transform.py`，移除其中冗余的断言，以提高代码质量。

### Script

#### Acts 1: 修复 SidecarTransformer 的核心逻辑

我们将修改 `SidecarTransformer`，使其能够正确处理 `stitcher.lock` 文件，并加强其内部路径比较的健壮性。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
~~~~~
~~~~~python.old
        if sidecar_path.suffix == ".json":
            return self._transform_json_data(
                data,
                context.old_file_path,
                context.new_file_path,
                old_fragment,
                new_fragment,
            )
        elif sidecar_path.suffix in (".yaml", ".yml"):
            return self._transform_yaml_data(data, old_fragment, new_fragment)

        return data

    def _calculate_fragments(
        self,
        old_module_fqn: Optional[str],
~~~~~
~~~~~python.new
        if sidecar_path.suffix in (".json", ".lock"):
            return self._transform_json_data(
                data,
                context.old_file_path,
                context.new_file_path,
                old_fragment,
                new_fragment,
            )
        elif sidecar_path.suffix in (".yaml", ".yml"):
            return self._transform_yaml_data(data, old_fragment, new_fragment)

        return data

    def _calculate_fragments(
        self,
        old_module_fqn: Optional[str],
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
~~~~~
~~~~~python.old
            current_path, current_fragment = path, fragment

            if old_file_path and new_file_path and current_path == old_file_path:
                current_path = new_file_path

            if (
~~~~~
~~~~~python.new
            current_path, current_fragment = path, fragment

            if old_file_path and new_file_path and str(current_path) == str(old_file_path):
                current_path = new_file_path

            if (
~~~~~

#### Acts 2: 清理单元测试代码

现在，我们清理 `test_transform.py` 中重复的测试代码行。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/tests/unit/test_transform.py
~~~~~
~~~~~python.old
        )
        updated = transformer.transform(Path("src/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}
        updated = transformer.transform(Path("src/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_nested_symbol_rename(self, transformer):
        old_suri = "py://src/app.py#MyClass.old_method"
~~~~~
~~~~~python.new
        )
        updated = transformer.transform(Path("src/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_nested_symbol_rename(self, transformer):
        old_suri = "py://src/app.py#MyClass.old_method"
~~~~~

### 结论

通过上述修改，我们解决了 `SidecarTransformer` 无法识别新签名文件格式的根本问题，并提高了其路径处理的稳定性。这应该能够修复所有15个失败的测试用例，使重构引擎能够正确地维护代码库的一致性。
