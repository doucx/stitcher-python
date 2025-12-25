
Before we can move on, we must fix the bug you found. I will generate a plan to correct the function naming.

## [WIP] fix(scanner): Correctly name plugin functions in stubs

### 错误分析
集成测试 `test_app_generates_stubs_for_plugins_and_sources` 失败，因为它断言生成的 stub 文件中应包含 `def dynamic_util()...`，而实际生成的是 `def dynamic.utils()...`。

根本原因是我们将插件的入口点键（`dynamic.utils`）错误地用作了函数的名称，而不是通过 `inspect` 模块获取到的函数的实际名称（`dynamic_util`）。

### 用户需求
修复此 bug，确保为插件生成的 `.pyi` 文件使用正确的函数名。

### 评论
这是一个关键的修复，它确保了我们生成的类型存根文件的正确性和可用性。通过将入口点“键”的职责（定义路径）和“值”的职责（提供可内省的对象）清晰地分开，我们使插件机制的行为更加直观和正确。

### 目标
1.  修改 `stitcher.scanner.inspector.parse_plugin_entry`，使其不再接收 `name` 参数，并始终使用内省到的 `__name__` 作为 `FunctionDef` 的名称。
2.  修改 `stitcher.app.core.StitcherApp._process_plugins`，调整其调用 `parse_plugin_entry` 的方式，并正确地将返回的 `FunctionDef` 放入由插件键派生出的虚拟模块中。

### 基本原理
我们将调整 `parse_plugin_entry` 的函数签名，使其只关注于其核心职责：内省一个入口点并返回一个准确的 IR 对象。然后，调用方 `_process_plugins` 将负责决定如何组织这些 IR 对象——它将使用入口点的键来构建文件和目录结构，并将从内省器返回的、带有正确名称的 `FunctionDef` 放入其中。这使得两个组件的职责更加单一和清晰。

### 标签
#intent/fix #flow/ready #priority/high #comp/scanner #comp/application #scope/core #ai/instruct #task/domain/plugins #task/object/introspection-engine #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `inspector` 以使用正确的函数名

我们修改 `parse_plugin_entry`，让它从被检查的对象中提取真实的函数名。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/inspector.py
~~~~~
~~~~~python.old
def parse_plugin_entry(name: str, entry_point_str: str) -> FunctionDef:
    """
    Dynamically imports and inspects a callable from an entry point string
    and converts it into a Stitcher FunctionDef IR object.

    Args:
        name: The logical name of the plugin (from the entry point key).
        entry_point_str: The import string (e.g., "my_pkg.main:my_func").

    Returns:
        A FunctionDef instance representing the inspected callable.
    
    Raises:
        InspectionError: If the entry point cannot be loaded or inspected.
    """
~~~~~
~~~~~python.new
def parse_plugin_entry(entry_point_str: str) -> FunctionDef:
    """
    Dynamically imports and inspects a callable from an entry point string
    and converts it into a Stitcher FunctionDef IR object.

    Args:
        entry_point_str: The import string (e.g., "my_pkg.main:my_func").

    Returns:
        A FunctionDef instance representing the inspected callable.
    
    Raises:
        InspectionError: If the entry point cannot be loaded or inspected.
    """
~~~~~

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/inspector.py
~~~~~
~~~~~python.old
    # Build FunctionDef
    return_annotation = _get_annotation_str(signature.return_annotation)

    return FunctionDef(
        name=name,
        args=args,
        docstring=docstring,
        return_annotation=return_annotation or None,
        is_async=inspect.iscoroutinefunction(target_callable)
    )
~~~~~
~~~~~python.new
    # Build FunctionDef
    return_annotation = _get_annotation_str(signature.return_annotation)
    func_name = target_callable.__name__

    return FunctionDef(
        name=func_name,
        args=args,
        docstring=docstring,
        return_annotation=return_annotation or None,
        is_async=inspect.iscoroutinefunction(target_callable)
    )
~~~~~

#### Acts 2: 修复 `StitcherApp` 以正确组织插件模块

现在我们更新 `_process_plugins` 的逻辑，使其正确地调用新的 `parse_plugin_entry` 并根据插件的键来组织文件结构。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def _process_plugins(self, plugins: Dict[str, str]) -> List[ModuleDef]:
        """Parses plugins and builds a virtual ModuleDef tree."""
        # A dictionary to hold our virtual modules, keyed by their intended file path
        virtual_modules: Dict[Path, ModuleDef] = defaultdict(
            lambda: ModuleDef(file_path="")
        )

        for name, entry_point in plugins.items():
            try:
                func_def = parse_plugin_entry(name, entry_point)
                
                # Convert dot-separated name to a file path
                parts = name.split(".")
                
                # The function itself goes into a file named after the last part
                func_path = Path(*parts).with_suffix(".py")
                
                # Ensure all intermediate __init__.py modules exist
                for i in range(len(parts)):
                    init_path = Path(*parts[:i], "__init__.py")
                    if not virtual_modules[init_path].file_path:
                         virtual_modules[init_path].file_path = init_path.as_posix()

                # Add the function to its module
                if not virtual_modules[func_path].file_path:
                    virtual_modules[func_path].file_path = func_path.as_posix()
                virtual_modules[func_path].functions.append(func_def)

            except InspectionError as e:
                bus.error("error.plugin.inspection", error=e)

        return list(virtual_modules.values())
~~~~~
~~~~~python.new
    def _process_plugins(self, plugins: Dict[str, str]) -> List[ModuleDef]:
        """Parses plugins and builds a virtual ModuleDef tree."""
        # A dictionary to hold our virtual modules, keyed by their intended file path
        virtual_modules: Dict[Path, ModuleDef] = defaultdict(
            lambda: ModuleDef(file_path="")
        )

        for name, entry_point in plugins.items():
            try:
                # The inspector now returns a FunctionDef with the *real* function name
                func_def = parse_plugin_entry(entry_point)
                
                # The logical name (key) determines the file path
                parts = name.split(".")
                
                # The function's definition goes into a .pyi file named after the last part
                # e.g., "dynamic.utils" -> dynamic/utils.pyi
                module_path_parts = parts[:-1]
                func_file_name = parts[-1]
                
                func_path = Path(*module_path_parts, f"{func_file_name}.py")
                
                # Ensure all intermediate __init__.py modules exist
                for i in range(len(module_path_parts) + 1):
                    init_path = Path(*parts[:i], "__init__.py")
                    if not virtual_modules[init_path].file_path:
                         virtual_modules[init_path].file_path = init_path.as_posix()

                # Add the function to its module
                if not virtual_modules[func_path].file_path:
                    virtual_modules[func_path].file_path = func_path.as_posix()
                
                # Now we add the FunctionDef with the correct name ('dynamic_util')
                # to the module determined by the key ('dynamic/utils.pyi')
                virtual_modules[func_path].functions.append(func_def)

            except InspectionError as e:
                bus.error("error.plugin.inspection", error=e)

        return list(virtual_modules.values())
~~~~~

#### Acts 3: 调整集成测试以匹配新的 inspector 签名

最后，我们需要更新 `test_inspector.py` 中对 `parse_plugin_entry` 的调用，因为它不再需要 `name` 参数。

~~~~~act
patch_file
packages/stitcher-scanner/tests/test_inspector.py
~~~~~
~~~~~python.old
def test_parse_plugin_entry_point(temp_module: str):
    """
    Test parsing a live, imported function via its entry point string
    into our FunctionDef IR.
    """
    # Act
    func_def = parse_plugin_entry("sample.plugin", temp_module)

    # Assert
    assert isinstance(func_def, FunctionDef)
    assert func_def.name == "sample.plugin" # Should use the name from the entry point key
    assert func_def.docstring and "This is a sample plugin function" in func_def.docstring
~~~~~
~~~~~python.new
def test_parse_plugin_entry_point(temp_module: str):
    """
    Test parsing a live, imported function via its entry point string
    into our FunctionDef IR.
    """
    # Act
    func_def = parse_plugin_entry(temp_module)

    # Assert
    assert isinstance(func_def, FunctionDef)
    assert func_def.name == "sample_plugin_func" # Should use the function's __name__
    assert func_def.docstring and "This is a sample plugin function" in func_def.docstring
~~~~~
