简要回答
我们遇到了大规模的 "Could not resolve alias" 错误。这表明 Griffe 在解析源代码时，无法正确通过 `griffe.visit` 在内存中构建模块与其导入之间的依赖关系。

## [WIP] test(adapter): 增强 Griffe 集成测试以复现 Alias Resolution 错误

### 错误分析
Griffe 作为一个基于静态分析的工具，非常依赖于对模块结构的完整理解。
1.  **路径问题**: 错误日志显示模块名被解析为 `packages.stitcher-application.src...`，这显然是因为我们在 `_map_module` 中构造 `module_name` 时使用了文件路径，而没有考虑到 Python 的包搜索路径 (PYTHONPATH)。Griffe 对此非常敏感，因为它需要通过模块名来解析导入关系。
2.  **上下文缺失**: `griffe.visit` 是针对单个文件的。当它遇到 `from typing import List` 时，它需要知道 `typing` 是什么。对于标准库通常没问题，但对于项目内部的引用，如果模块名结构错误，Griffe 就无法找到对应的定义，从而在解析 Alias 时失败。

错误信息 `Could not resolve alias ... pointing at ...` 实际上是 Griffe 在尝试解析一个 `Alias` 对象（即导入的名称）并获取其目标对象时抛出的异常，或者我们在代码中尝试访问此 Alias 的某些属性时触发的。

### 用户需求
创建一个重现此问题的集成测试，模拟真实的包结构和导入关系，以便我们后续修复模块名解析和搜索路径配置问题。

### 评论
当前的单元测试过于简单，只测试了单一的字符串代码片段，没有模拟多模块、跨文件引用的场景。我们需要一个基于文件系统的集成测试。

### 目标
在 `packages/stitcher-python-adapter/tests/integration` 下创建 `test_griffe_resolution.py`，复现跨模块导入和标准库导入时的解析错误。

### 基本原理
我们将使用 `WorkspaceFactory` 构建一个包含两个模块的迷你项目：
1.  `models.py`: 定义一个类。
2.  `main.py`: 导入 `models.py` 中的类和标准库 `typing.List`。
然后使用 `GriffePythonParser` 解析 `main.py`，这应该会触发类似的 Alias Resolution 错误，验证我们的假设。

### 标签
#intent/test #flow/ready #priority/high #comp/tests #concept/parser #scope/core #ai/instruct
#task/domain/testing #task/object/integration-test #task/action/create #task/state/continue

---

### Script

#### Acts 1: 创建集成测试目录

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-python-adapter/tests/integration
~~~~~

#### Acts 2: 编写复现测试

在这个测试中，我们不 mock 任何东西，而是真实地创建文件。我们需要确保存储库根目录（Project Root）被正确识别，以便 Griffe 能理解模块路径。

~~~~~act
write_file
packages/stitcher-python-adapter/tests/integration/test_griffe_resolution.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from stitcher.test_utils import WorkspaceFactory
from stitcher.adapter.python import GriffePythonParser

def test_griffe_resolves_imports(tmp_path):
    """
    Integration test to reproduce 'Could not resolve alias' error.
    Simulates a project with local imports and standard library imports.
    """
    # 1. Setup specific project structure
    # src/
    #   pkg/
    #     __init__.py
    #     models.py  (Defines User)
    #     main.py    (Imports User and List)
    
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/pkg/__init__.py", "")
        .with_source(
            "src/pkg/models.py", 
            """
class User:
    name: str = "Alice"
            """
        )
        .with_source(
            "src/pkg/main.py",
            """
from typing import List
from .models import User

def get_users() -> List[User]:
    return [User()]
            """
        )
        .build()
    )

    parser = GriffePythonParser()
    
    # We simulate what StitcherApp does: iterate files and parse them.
    # The critical part is what we pass as 'file_path'.
    # In the app, it is relative to root, e.g., "src/pkg/main.py"
    
    main_py_path = "src/pkg/main.py"
    source_code = (project_root / main_py_path).read_text(encoding="utf-8")
    
    # 2. Act
    # This might fail or return a ModuleDef with broken annotations depending on 
    # how Griffe handles the missing context if we don't config search paths.
    try:
        module = parser.parse(source_code, file_path=main_py_path)
    except Exception as e:
        pytest.fail(f"Griffe parsing crashed: {e}")

    # 3. Assert
    assert len(module.functions) == 1
    func = module.functions[0]
    
    # If alias resolution fails, Griffe might return the Alias object string rep 
    # or crash when we try to str() it in our parser implementation.
    # We want to see if the return annotation is correctly resolved to a string "List[User]"
    # or at least a string representation that doesn't crash.
    
    # Note: Griffe 1.0+ might resolve this to "typing.List[src.pkg.models.User]" or similar
    # if paths are correct. If not, it might explain the crash.
    print(f"Return annotation: {func.return_annotation}")
    assert func.return_annotation is not None
    assert "List" in func.return_annotation
~~~~~

### 下一步建议

运行此测试。如果它通过了，说明问题可能出在 `stitcher check` 运行时的特定**文件路径传递方式**或**PYTHONPATH 环境**上。如果它失败（带着类似的 `Could not resolve alias` 或具体的 Crash），我们就成功复现了问题，并可以着手修复 `GriffePythonParser` 中的模块名计算逻辑和 `griffe.Loader` 的搜索路径配置。
