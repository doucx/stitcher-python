好的，我们立即开始。

正如我们所分析的，问题的根源在于 `StubGenerator` 中不完善的文档字符串格式化逻辑。我将生成一个计划来修正这个问题。

更重要的是，为了遵循您提出的、符合 `ruff` 等现代工具的最佳实践，我将同时更新我们刚刚编写的测试用例，使其期望的“黄金标准”输出也采用新的格式（即 `"""` 单独成行）。这样，我们的修复和测试将共同确立一个新的、更高质量的标准。

## [WIP] fix(io): 修正 StubGenerator 的 docstring 格式化逻辑以符合 ruff 标准

### 用户需求
修复 `stitcher-io` 包中的 `StubGenerator`，使其能够正确格式化 `.pyi` 文件中的文档字符串，特别是要解决多行文本的缩进问题，并采纳 `ruff`/`black` 的主流格式化风格。

### 评论
这是一个关键的修复，它不仅解决了导致测试失败的 bug，还将代码生成器的输出质量提升到了一个与业界最佳实践对齐的新水平。通过修正测试用例以匹配新标准，我们确保了修复的正确性，并为项目未来的代码生成行为奠定了坚实的基础。这是解决 DRY 违规问题的第一步，具有很高的价值。

### 目标
1.  **更新测试标准**：修改 `packages/stitcher-io/tests/test_stub_generator.py` 中的 `test_generate_pyi_with_correct_docstring_formatting` 测试用例，使其期望的 `.pyi` 格式遵循 `ruff` 风格（多行 docstring 的 `"""` 单独成行）。
2.  **修复实现逻辑**：重写 `packages/stitcher-io/src/stitcher/io/stub_generator.py` 中的 `_format_docstring` 方法。
3.  **确保一致性**：新的实现必须能够正确处理单行和多行文档字符串，并为多行版本生成符合新测试标准的、精确缩进的输出。

### 基本原理
当前 `_format_docstring` 方法的逻辑过于简单，它将整个文档字符串作为一个单元进行缩进，导致只有第一行被正确处理。

我们将用一个新的、更健壮的实现替换它。新逻辑将：
1.  区分单行和多行文档字符串。
2.  对于单行字符串，生成紧凑的 `"""doc"""` 格式。
3.  对于多行字符串，将其拆分为行，对每一行应用正确的上下文缩进，然后用 `"""` 将其包裹在独立的行上，从而完美匹配 `ruff` 的输出风格。

通过先更新测试，再修复实现，我们严格遵循了 TDD 的精神，确保了修复的精确性和完整性。

### 标签
#intent/fix #flow/ready #priority/high
#comp/io #comp/tests #scope/dx
#ai/instruct
#task/domain/testing #task/object/stub-generator #task/action/bug-fix
#task/state/continue

---
### Script

#### Acts 1: 更新测试用例以采纳 ruff 格式标准

首先，我们将修改 `test_stub_generator.py`，使其期望的输出符合我们新的、更高质量的格式化标准。

~~~~~act
patch_file
packages/stitcher-io/tests/test_stub_generator.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
    # The "golden" output with correct formatting, following ruff/black style
    expected_pyi = dedent("""
        def multiline_doc():
            \"\"\"
            First line.
            Second line should be indented.
            \"\"\"
            ...

        def quotes_doc():
            \"\"\"This docstring contains "quotes".\"\"\"
            ...
    """).strip()
~~~~~

#### Acts 2: 修复 `StubGenerator` 的格式化逻辑

现在，我们将修复 `stub_generator.py` 中的核心逻辑，使其能够通过上面更新后的测试。

~~~~~act
patch_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python.old
    def _format_docstring(self, doc: str, level: int) -> str:
        indent = self._indent(level)
        # Simplified handling: always use triple quotes
        # In a robust implementation, we might handle escaping quotes inside docstring
        if "\n" in doc:
            # multiline
            return f'{indent}"""\n{indent}{doc}\n{indent}"""'
        return f'{indent}"""{doc}"""'
~~~~~
~~~~~python.new
    def _format_docstring(self, doc: str, level: int) -> str:
        indent = self._indent(level)
        # In a robust implementation, we might handle escaping quotes inside docstring

        # Strip leading/trailing whitespace from the docstring itself to handle
        # potential formatting from YAML loader.
        doc = doc.strip()
        lines = doc.split("\n")

        if len(lines) == 1:
            # Single line: keep it compact and escape internal quotes
            processed_doc = doc.replace('"""', '\\"\\"\\"')
            return f'{indent}"""{processed_doc}"""'

        # Multi-line: adopt the ruff/black style for readability
        # Re-indent all lines to match the current level.
        indented_body = "\n".join(f"{indent}{line}" for line in lines)
        return f'{indent}"""\n{indented_body}\n{indent}"""'
~~~~~
### 下一步建议
我们已经完成了对 `StubGenerator` 的修复。执行此计划后，请再次运行测试套件。我们期望所有测试，包括 `test_generate_pyi_with_correct_docstring_formatting`，现在都能够成功通过。

测试通过后，我们将着手解决 DRY 违规的另一半问题：重构 `stitcher-scanner` 包中的 `InjectorTransformer`，并创建一个所有格式化逻辑都可以依赖的、统一的工具函数。
