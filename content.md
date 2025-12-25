好的，我们正式启动 `stitcher-io` 的 TDD 循环。

**RED 阶段**：我们将为 `.pyi` 文件生成器（`StubGenerator`）编写第一个测试。这个测试的核心是定义一个“黄金标准”——对于一个给定的、手动构造的 `ModuleDef` IR 对象，我们期望生成什么样的 `.pyi` 文件内容。

## [WIP] test(io): 添加 StubGenerator 单元测试 (Red Phase)

### 用户需求
采用 TDD 模式开始 `stitcher-io` 的开发。首先创建一个测试用例，该用例通过断言一个手动创建的 `ModuleDef` 对象能被 `StubGenerator` 转换为一个精确的、格式正确的 `.pyi` 字符串，来定义 `StubGenerator` 的行为契约。

### 评论
这是一个完美的单元测试场景。通过手动构造 `ModuleDef`，我们**将 `stitcher-io` 的测试与 `stitcher-scanner` 的实现完全解耦**。无论 Scanner 未来如何变化，只要它产出的 IR 符合 `spec`，我们的 Generator 测试就依然有效。

我们将使用 `textwrap.dedent` 来清晰地定义多行的期望输出，避免因缩进问题导致测试脆弱。

### 目标
1.  在 `packages/stitcher-io/tests/` 目录下创建测试文件 `test_stub_generator.py`。
2.  在该文件中，手动构建一个包含模块文档、属性、函数和类的 `ModuleDef` 实例。
3.  定义一个与该 `ModuleDef` 实例对应的、格式完美的 `.pyi` 字符串。
4.  调用（尚未实现的）`StubGenerator.generate()` 并断言其输出与预期完全一致。

### 基本原理
此测试驱动了 `StubGenerator` 的 API 设计 (`generate(module_def: ModuleDef) -> str`) 和其核心逻辑的实现。测试用例本身就是一份清晰的需求文档，详细说明了 IR 到 `.pyi` 字符串的转换规则。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/tests #comp/io #scope/core #ai/instruct
#task/domain/testing #task/object/stub-generator-tests #task/action/create-case
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 创建测试目录和占位符实现
我们首先创建测试目录和 `stub_generator.py` 文件，以便 `import` 能够找到目标模块。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-io/tests
~~~~~

~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python
from stitcher.spec import ModuleDef


class StubGenerator:
    def generate(self, module: ModuleDef) -> str:
        """
        Generates the content of a .pyi file from a ModuleDef IR.
        """
        # TODO: Implement generation logic
        return ""
~~~~~

~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .stub_generator import StubGenerator

__all__ = ["StubGenerator"]
~~~~~

#### Acts 2: 编写 Generator 的测试用例 (RED)
这是核心部分，我们在这里精确定义了生成器的目标。

~~~~~act
write_file
packages/stitcher-io/tests/test_stub_generator.py
~~~~~
~~~~~python
import pytest
from textwrap import dedent
from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
)
from stitcher.io import StubGenerator


def test_generate_simple_pyi():
    # 1. Arrange: Manually construct a comprehensive ModuleDef IR object.
    module_def = ModuleDef(
        file_path="my_module.py",
        docstring="This is a test module.",
        attributes=[
            Attribute(name="VERSION", annotation="str", value='"0.1.0"')
        ],
        functions=[
            FunctionDef(
                name="my_function",
                args=[
                    Argument(name="arg1", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="int"),
                    Argument(name="arg2", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="str", default="'default'"),
                ],
                return_annotation="bool",
                docstring="A test function.",
                is_async=True,
                decorators=["@my_decorator"],
            )
        ],
        classes=[
            ClassDef(
                name="MyClass",
                bases=["Base"],
                docstring="A test class.",
                attributes=[
                    Attribute(name="CLASS_VAR", annotation="Optional[int]", value="None")
                ],
                methods=[
                    FunctionDef(
                        name="__init__",
                        args=[
                            Argument(name="self", kind=ArgumentKind.POSITIONAL_OR_KEYWORD),
                            Argument(name="val", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="float"),
                        ],
                        return_annotation="None",
                    ),
                    FunctionDef(
                        name="do_work",
                        args=[
                            Argument(name="self", kind=ArgumentKind.POSITIONAL_OR_KEYWORD),
                        ],
                        return_annotation="str",
                        docstring="Does some work.",
                    )
                ]
            )
        ]
    )

    # 2. Arrange: Define the expected golden .pyi output string.
    expected_pyi = dedent("""
        \"\"\"This is a test module.\"\"\"
        
        VERSION: str
        
        @my_decorator
        async def my_function(arg1: int, arg2: str = 'default') -> bool:
            \"\"\"A test function.\"\"\"
            ...

        class MyClass(Base):
            \"\"\"A test class.\"\"\"
            CLASS_VAR: Optional[int]
            
            def __init__(self, val: float) -> None: ...
            
            def do_work(self) -> str:
                \"\"\"Does some work.\"\"\"
                ...
    """).strip()

    # 3. Act
    generator = StubGenerator()
    generated_code = generator.generate(module_def).strip()

    # 4. Assert
    assert generated_code == expected_pyi
~~~~~

### 下一步建议
运行 `pytest`。测试将因 `generate()` 返回空字符串而失败。
接下来，我们将进入 **GREEN** 阶段：在 `StubGenerator` 中实现 IR 到字符串的转换逻辑，这会涉及大量的字符串拼接和格式化。
