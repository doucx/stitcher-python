好的，收到指令。

我们将遵循测试驱动开发（TDD）的最佳实践，首先创建一个捕获 `stitcher generate` 命令中 `.pyi` 文件文档字符串格式错误的回归测试。这个测试目前应该会失败，从而验证问题的存在，并为我们后续的修复提供明确的目标。

根据问题描述，我们需要测试两点：
1.  多行文档字符串在 `.pyi` 文件中是否保持了正确的相对缩进。
2.  包含引号的文档字符串是否被正确处理，没有添加多余的引号。

我将生成一个计划，在 `stitcher-io` 包的测试文件 `test_stub_generator.py` 中添加一个新的测试用例来覆盖这些场景。

## [WIP] test: 为 pyi 生成中的 docstring 格式错误添加回归测试

### 用户需求
为 `stitcher generate` 流程中 `.pyi` 文件生成时出现的两个文档字符串格式错误，创建一个失败的回归测试。
1.  多行文档字符串的缩进不正确。
2.  包含引号的文档字符串末尾会多出一个额外的引号。

### 评论
这是一个关键且标准的步骤。通过测试先行，我们能确保：
1.  清晰地复现并隔离问题。
2.  为后续的修复工作提供一个明确的成功标准。
3.  防止未来对相关代码的修改无意中再次引入此缺陷。

### 目标
1.  在 `packages/stitcher-io/tests/test_stub_generator.py` 文件中添加一个新的测试函数 `test_generate_pyi_with_correct_docstring_formatting`。
2.  该测试将构造一个包含特殊文档字符串（多行、含引号）的 `ModuleDef` IR。
3.  断言由 `StubGenerator` 生成的 `.pyi` 内容与预期的、正确格式化的“黄金标准”字符串完全一致。

### 基本原理
我们将直接与 `stitcher-io` 包中的 `StubGenerator` 交互，因为它直接负责将 IR 转换为 `.pyi` 文件的字符串内容。通过为它提供一个精心构造的、包含问题场景的 `ModuleDef` 对象，我们可以精确地测试其 `_format_docstring` 方法（或相关逻辑）的行为。新的测试用例将与现有的 `test_generate_simple_pyi` 并存，专门用于验证这些棘手的边缘情况。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/io #comp/tests #scope/dx
#ai/instruct
#task/domain/testing #task/object/stub-generator #task/action/bug-fix
#task/state/begin

---
### Script

#### Acts 1: 在 `test_stub_generator.py` 中添加回归测试

我们将向 `packages/stitcher-io/tests/test_stub_generator.py` 文件追加一个新的测试函数，该函数专门用于验证多行和带引号的文档字符串能否被正确格式化。

~~~~~act
patch_file
packages/stitcher-io/tests/test_stub_generator.py
~~~~~
~~~~~python.old
    # 3. Act
    generator = StubGenerator()
    generated_code = generator.generate(module_def).strip()

    # 4. Assert
    assert generated_code == expected_pyi
~~~~~
~~~~~python.new
    # 3. Act
    generator = StubGenerator()
    generated_code = generator.generate(module_def).strip()

    # 4. Assert
    assert generated_code == expected_pyi


def test_generate_pyi_with_correct_docstring_formatting():
    # Arrange: Create an IR with problematic docstrings
    module_def = ModuleDef(
        file_path="formatter_test.py",
        functions=[
            FunctionDef(
                name="multiline_doc",
                docstring="First line.\nSecond line should be indented.",
            ),
            FunctionDef(
                name="quotes_doc",
                docstring='This docstring contains "quotes".',
            ),
        ],
    )

    # The "golden" output with correct formatting
    expected_pyi = dedent("""
        def multiline_doc():
            \"\"\"First line.
            Second line should be indented.\"\"\"
            ...

        def quotes_doc():
            \"\"\"This docstring contains "quotes".\"\"\"
            ...
    """).strip()

    # Act
    generator = StubGenerator()
    generated_code = generator.generate(module_def).strip()

    # Assert
    assert generated_code == expected_pyi
~~~~~
### 下一步建议
我们已经成功创建了用于捕获错误的测试用例。执行此计划后，下一步是在 `stitcher-io` 包中运行测试，并预期看到 `test_generate_pyi_with_correct_docstring_formatting` 测试失败。

一旦失败被确认，我将为您生成修复 `stitcher-io/src/stitcher/io/stub_generator.py` 中相关逻辑的计划。
