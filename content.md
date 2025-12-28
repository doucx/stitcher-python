You are absolutely right. The test failure is a direct result of a flaw in my previous plan. I physically deleted the `stitcher-scanner` package, but `stitcher-application`'s `core.py` still retained an import from it. This is a critical oversight.

The function `parse_plugin_entry` is a special case. Unlike the general-purpose parser, it's inherently tied to Python's runtime introspection (`importlib`, `inspect`) and therefore correctly belongs with the Python-specific logic. I should have moved it, not deleted it.

## [WIP] fix: Repair broken imports post-refactor

### 错误分析
1.  **根本原因**: `ModuleNotFoundError: No module named 'stitcher.scanner'`.
2.  **具体分析**: 在上一步中，我删除了 `stitcher-scanner` 包，但 `stitcher-application` 中的 `core.py` 仍然保留了 `from stitcher.scanner import parse_plugin_entry, InspectionError`。
3.  **架构问题**: `parse_plugin_entry` 的逻辑是 Python 特有的，它应该被迁移到 `stitcher-python-adapter` 中，而不是被删除。
4.  **依赖缺失**: `stitcher-application` 现在逻辑上依赖于语言适配器来提供插件解析功能，因此需要在其 `pyproject.toml` 中声明对 `stitcher-python-adapter` 的依赖。

### 用户需求
修复因 `stitcher-scanner` 被删除而导致的 `ImportError`，使测试套件能够重新通过。

### 评论
这是一个典型的重构后清理失误。通过将 `inspector.py` 的逻辑（插件解析）正式迁移到 `stitcher-python-adapter` 中，我们不仅修复了错误，而且进一步巩固了新架构的正确性——所有 Python 特定的代码现在都集中在一个地方。

### 目标
1.  将 `inspector.py` 的逻辑物理地迁移到 `stitcher-python-adapter` 中。
2.  从 `stitcher-python-adapter` 中导出 `parse_plugin_entry` 和 `InspectionError`。
3.  为 `stitcher-application` 添加对 `stitcher-python-adapter` 的依赖。
4.  修复 `stitcher-application/src/stitcher/app/core.py` 中的 import 语句。

### 基本原理
我们将 `inspector.py` 视为 Python 适配器提供的一项服务。`StitcherApp` 消费这项服务，因此需要从适配器导入它，并且其所在的包 (`stitcher-application`) 必须在其构建配置中声明这种依赖关系。

### 标签
#intent/fix #flow/ready #priority/critical #comp/runtime #comp/tests #scope/core #ai/instruct #task/domain/architecture #task/object/dependencies #task/action/fix-imports #task/state/end

---

### Script

#### Acts 1: 将插件检查逻辑迁移到 Adapter
我们将 `inspector.py` 的内容重新创建在 `stitcher-python-adapter` 中。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/inspector.py
~~~~~
~~~~~python
import inspect
import importlib
from typing import Callable, Any
from stitcher.spec import Argument, ArgumentKind, FunctionDef


class InspectionError(Exception):
    pass


def _map_param_kind(kind: inspect._ParameterKind) -> ArgumentKind:
    if kind == inspect.Parameter.POSITIONAL_ONLY:
        return ArgumentKind.POSITIONAL_ONLY
    if kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
        return ArgumentKind.POSITIONAL_OR_KEYWORD
    if kind == inspect.Parameter.VAR_POSITIONAL:
        return ArgumentKind.VAR_POSITIONAL
    if kind == inspect.Parameter.KEYWORD_ONLY:
        return ArgumentKind.KEYWORD_ONLY
    if kind == inspect.Parameter.VAR_KEYWORD:
        return ArgumentKind.VAR_KEYWORD
    raise ValueError(f"Unknown parameter kind: {kind}")


def _get_annotation_str(annotation: Any) -> str:
    if annotation == inspect.Parameter.empty:
        return ""

    # Handle generic types from typing module
    if hasattr(annotation, "__origin__"):
        return str(annotation).replace("typing.", "")

    if hasattr(annotation, "__name__"):
        return annotation.__name__

    return str(annotation)


def parse_plugin_entry(entry_point_str: str) -> FunctionDef:
    try:
        module_str, callable_str = entry_point_str.split(":", 1)
        module = importlib.import_module(module_str)
        target_callable: Callable = getattr(module, callable_str)
    except (ImportError, AttributeError, ValueError) as e:
        raise InspectionError(
            f"Could not load entry point '{entry_point_str}': {e}"
        ) from e

    try:
        signature = inspect.signature(target_callable)
        docstring = inspect.getdoc(target_callable)
    except (TypeError, ValueError) as e:
        raise InspectionError(
            f"Could not inspect signature of '{entry_point_str}': {e}"
        ) from e

    # Build arguments
    args: list[Argument] = []
    for param in signature.parameters.values():
        default_val = None
        if param.default != inspect.Parameter.empty:
            default_val = repr(param.default)

        args.append(
            Argument(
                name=param.name,
                kind=_map_param_kind(param.kind),
                annotation=_get_annotation_str(param.annotation) or None,
                default=default_val,
            )
        )

    # Build FunctionDef
    return_annotation = _get_annotation_str(signature.return_annotation)
    func_name = target_callable.__name__

    return FunctionDef(
        name=func_name,
        args=args,
        docstring=docstring,
        return_annotation=return_annotation or None,
        is_async=inspect.iscoroutinefunction(target_callable),
    )
~~~~~

#### Acts 2: 从 Adapter 导出插件检查功能
更新 `stitcher-python-adapter` 的 `__init__.py`。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~
~~~~~python.old
from .parser import PythonParser
from .transformer import PythonTransformer
from .generator import PythonStubGenerator
from .fingerprint import PythonFingerprintStrategy

__all__ = [
    "PythonParser",
    "PythonTransformer",
    "PythonStubGenerator",
    "PythonFingerprintStrategy",
]
~~~~~
~~~~~python.new
from .parser import PythonParser
from .transformer import PythonTransformer
from .generator import PythonStubGenerator
from .fingerprint import PythonFingerprintStrategy
from .inspector import parse_plugin_entry, InspectionError

__all__ = [
    "PythonParser",
    "PythonTransformer",
    "PythonStubGenerator",
    "PythonFingerprintStrategy",
    "parse_plugin_entry",
    "InspectionError",
]
~~~~~

#### Acts 3: 修复 Application 的依赖
在 `stitcher-application/pyproject.toml` 中添加对适配器的依赖。

~~~~~act
patch_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-scanner",
    "stitcher-io",
    "stitcher-config",
    "pyneedle",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
stitcher-config = { workspace = true }
pyneedle = { workspace = true }
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-config",
    "stitcher-python-adapter",
    "pyneedle",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-config = { workspace = true }
stitcher-python-adapter = { workspace = true }
pyneedle = { workspace = true }
~~~~~

#### Acts 4: 修复 core.py 中的导入
最后，修正 `core.py` 中错误的 import 语句。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from stitcher.scanner import (
    parse_plugin_entry,
    InspectionError,
)

from stitcher.spec import (
~~~~~
~~~~~python.new
from stitcher.adapter.python import (
    parse_plugin_entry,
    InspectionError,
)

from stitcher.spec import (
~~~~~

### 下一步建议
再次运行测试套件。这次，`ImportError` 应该已经解决，所有测试应该会通过。
