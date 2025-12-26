Excellent analysis. Your reasoning is sound, and you've correctly identified the two most likely culprits:

1.  **Extraction (`parser.py`)**: The `get_docstring()` method from LibCST or our subsequent processing might be "un-indenting" the docstring before it's stored, stripping leading whitespace from each line.
2.  **Injection (`transformer.py`)**: The `InjectorTransformer` might be taking the multi-line string as-is and not re-applying the correct indentation to subsequent lines when writing it back into the AST.

Following best practices (and your request), the first step is to create a failing test case that precisely reproduces this bug. This will confirm the issue's existence and give us a clear target for the fix.

I will now generate a plan to add this new test file.

## [WIP] test: 为多行文档字符串缩进问题创建复现测试

### 用户需求
用户报告了一个在 `eject` 过程中，多行文档字符串（docstring）的缩进被错误处理的 bug。要求首先创建一个能够复现此问题的测试用例。

### 评论
这是一个影响代码格式和可读性的关键 bug。用户的假设——问题出在提取或注入阶段——非常准确。遵循测试驱动开发（TDD）的原则，创建一个能稳定复现该问题的失败测试是最高效、最正确的首要步骤。这个测试将成为后续修复工作的“验收标准”。

### 目标
1.  在 `stitcher-scanner` 包中创建一个新的测试文件 `test_transformer_multiline.py`。
2.  在该文件中实现一个名为 `test_inject_preserves_multiline_indentation` 的测试函数。
3.  此测试将模拟 `eject` 过程：取一个没有文档字符串的函数，并尝试注入一个从 YAML 文件中加载的多行字符串，然后断言生成的代码是否保留了正确的缩进格式。

### 基本原理
我们将创建一个独立的测试文件，以隔离这个问题。测试用例会精确地模拟用户描述的场景：一个包含换行符的文档字符串被 `inject_docstrings` 函数处理。我们将提供期望的、正确缩排的输出字符串，并与函数的实际输出进行比较。如果存在 bug，此测试将会失败，从而验证问题的存在。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/scanner #scope/dx #ai/instruct #task/domain/testing #task/object/docstring-indent #task/action/reproduce-bug #task/state/begin

---
### Script

#### Acts 1: 创建新的测试文件

我们将创建一个新的测试文件 `test_transformer_multiline.py`，其中包含一个专门用于复现多行文档字符串缩进问题的测试用例。

~~~~~act
write_file
packages/stitcher-scanner/tests/test_transformer_multiline.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.scanner.transformer import inject_docstrings


def test_inject_preserves_multiline_indentation():
    """
    Verifies that when injecting a multi-line docstring, all lines
    are correctly indented. This reproduces a bug where subsequent
    lines lost their indentation.
    """
    # 1. Source code as if after 'strip' command (no docstring)
    source_code_stripped = dedent("""
    def my_func(arg1: int):
        pass
    """).strip()

    # 2. The docstring as it would be loaded from the YAML file
    # Note the lack of leading indentation on the second line.
    doc_content = "This is the first line.\\nThis is the second line."
    docs_to_inject = {"my_func": doc_content}

    # 3. The expected, correctly formatted output
    expected_code = dedent("""
    def my_func(arg1: int):
        \"\"\"This is the first line.
        This is the second line.\"\"\"
        pass
    """).strip()

    # 4. Act
    result_code = inject_docstrings(source_code_stripped, docs_to_inject)

    # 5. Assert
    # We compare .strip() to ignore potential leading/trailing newlines
    # of the whole code block, focusing on the internal structure.
    assert result_code.strip() == expected_code
~~~~~
### 下一步建议
我们已经创建了复现问题的测试。请执行此计划。

下一步，请运行测试套件（特别是这个新文件），并确认它如预期一样失败。一旦失败被确认，我将继续分析 `stitcher-scanner` 的 `transformer.py` 和 `parser.py` 来定位并修复问题的根源。
