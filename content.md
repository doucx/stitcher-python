我已分析了 Pyright 报告的 8 个类型错误。这些错误主要源于类型提示不够明确，导致静态分析器无法推断出变量在特定代码路径下的确切类型。我将通过添加类型断言和实现缺失的协议方法来逐一修复这些问题。

## [WIP] fix: 修复 stitcher-application 中的 Pyright 类型错误

### 错误分析

Pyright 在 `stitcher-application` 包的三个测试文件中发现了 8 个类型错误，具体如下：

1.  **`test_parser_robustness.py`**: 测试代码试图访问 `LanguageAdapter` 协议上的 `.parser` 属性，但该属性仅存在于其具体实现 `PythonAdapter` 中。Pyright 只看到了协议，因此报错。
2.  **`test_doc_manager.py`**: `MockAdapter` 类继承自 `DocumentAdapter` 协议，但未能实现协议要求的所有方法，具体是缺失了 `dump` 方法。
3.  **`test_doc_manager_strategies.py`**:
    *   多个错误表明 Pyright 无法确定一个 `Union` 类型变量在特定上下文中是字典还是字符串，导致在使用字典键访问时报错。
    *   最后一个错误指出，在一个 `Union[str, List[DocstringItem]]` 类型的变量上进行迭代时，Pyright 无法确认迭代的元素是 `DocstringItem` 对象，从而导致访问 `.name` 属性时报错。

### 用户需求

修复 `stitcher-application` 包中由 `pyright` 命令报告的所有类型错误，确保静态类型检查通过。

### 评论

这些是典型的静态类型检查问题，修复它们可以提高代码的健壮性和可维护性。通过添加明确的类型断言 (`assert isinstance(...)`) 和补全协议实现，我们可以向类型检查器提供足够的信息来验证代码的正确性，而无需修改核心逻辑。

### 目标

1.  在 `test_parser_robustness.py` 中，将 `LanguageAdapter` 类型强制转换为 `PythonAdapter`，以便安全地访问其 `.parser` 属性。
2.  在 `test_doc_manager.py` 中，为 `MockAdapter` 实现缺失的 `dump` 方法。
3.  在 `test_doc_manager_strategies.py` 中，添加类型断言以消除 `Union` 类型带来的歧义，确保 Pyright 能够正确推断变量类型。

### 基本原理

我们将采用最小侵入性的方式来修复这些类型错误：
-   对于协议与实现之间的属性差异，使用 `isinstance` 断言来告知类型检查器我们正在处理的是哪个具体的实现类。
-   对于未完全实现的协议，补全缺失的方法以满足协议要求。
-   对于因 `Union` 类型导致的访问错误，在访问特定类型的方法或属性前，使用 `isinstance` 断言来收窄变量的类型范围。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/type-checking #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修复 `test_parser_robustness.py` 中的属性访问错误

我们将添加一个 `isinstance` 断言，以告知 Pyright `python_adapter` 是 `PythonAdapter` 的一个实例，从而使其能够识别 `.parser` 属性。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_parser_robustness.py
~~~~~
~~~~~python.old
    python_adapter = app.file_indexer.adapters[".py"]
    # Verify we got the adapter (the key might vary if not registered as .py, but StitcherApp does register it as .py)
    assert python_adapter is not None

    real_parse = python_adapter.parser.parse

    def failing_parse(source_code, file_path=""):
        if "core.py" in str(file_path):
            raise ValueError("Simulated parser crash for testing")
        return real_parse(source_code, file_path)

    monkeypatch.setattr(python_adapter.parser, "parse", failing_parse)
~~~~~
~~~~~python.new
    from stitcher.lang.python.adapter import PythonAdapter

    python_adapter = app.file_indexer.adapters[".py"]
    # Verify we got the adapter and it's the concrete type we expect
    assert isinstance(python_adapter, PythonAdapter)

    real_parse = python_adapter.parser.parse

    def failing_parse(source_code, file_path=""):
        if "core.py" in str(file_path):
            raise ValueError("Simulated parser crash for testing")
        return real_parse(source_code, file_path)

    monkeypatch.setattr(python_adapter.parser, "parse", failing_parse)
~~~~~

#### Acts 2: 修复 `test_doc_manager.py` 中未实现的协议方法

在 `MockAdapter` 中实现 `dump` 方法，以满足 `DocumentAdapter` 协议的要求。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_doc_manager.py
~~~~~
~~~~~python.old
    def save(self, path: Path, data: dict):
        self.saved_path = path
        self.saved_data = data
~~~~~
~~~~~python.new
    def save(self, path: Path, data: dict):
        self.saved_path = path
        self.saved_data = data

    def dump(self, data: dict) -> str:
        # Not used in these tests, but required by the protocol
        return ""
~~~~~

#### Acts 3: 修复 `test_doc_manager_strategies.py` 中的类型歧义

通过添加 `isinstance` 断言，明确告知 Pyright 变量在特定代码路径下的具体类型，解决字典键访问和列表迭代的错误。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_doc_manager_strategies.py
~~~~~
~~~~~python.old
        # 3. Assert serialized format
        assert serialized_data["Summary"] == "This is a summary."
        assert serialized_data["Extended"] == "This is an extended description."
        assert expected_params_key in serialized_data
        assert "Addon.Test" in serialized_data
        params = serialized_data[expected_params_key]
        assert params["param1"] == "Description for param1."
        assert params["param2"] == "Description for param2."

        # 4. Deserialize
        deserialized_ir = doc_manager._deserialize_ir(serialized_data)
~~~~~
~~~~~python.new
        # 3. Assert serialized format
        assert isinstance(serialized_data, dict)
        assert serialized_data["Summary"] == "This is a summary."
        assert serialized_data["Extended"] == "This is an extended description."
        assert expected_params_key in serialized_data
        assert "Addon.Test" in serialized_data
        params = serialized_data[expected_params_key]
        assert isinstance(params, dict)
        assert params["param1"] == "Description for param1."
        assert params["param2"] == "Description for param2."

        # 4. Deserialize
        deserialized_ir = doc_manager._deserialize_ir(serialized_data)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_doc_manager_strategies.py
~~~~~
~~~~~python.old
        param_section = next(
            s for s in deserialized_ir.sections if s.kind == SectionKind.PARAMETERS
        )
        assert len(param_section.content) == 2
        # Note: Order is not guaranteed in dicts, so we check names
        param_names = {item.name for item in param_section.content}
        assert param_names == {"param1", "param2"}
~~~~~
~~~~~python.new
        param_section = next(
            s for s in deserialized_ir.sections if s.kind == SectionKind.PARAMETERS
        )
        assert isinstance(param_section.content, list)
        assert len(param_section.content) == 2
        # Note: Order is not guaranteed in dicts, so we check names
        param_names = {item.name for item in param_section.content}
        assert param_names == {"param1", "param2"}
~~~~~

### 下一步建议

所有已知的类型错误都已在此计划中修复。在执行此计划后，建议重新运行 `pyright packages/stitcher-application/` 命令，以确认所有问题都已解决。之后，我们可以将这些修复作为一个完整的逻辑单元进行提交。
