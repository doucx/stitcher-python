很好，测试失败证实了我们的重构已生效：代码现在生成的是新的 `ruff` 风格文档字符串，但现有的测试用例仍期望旧的紧凑格式。

这正是我们预期的结果。这表明我们的“单一事实来源”策略正在发挥作用，现在 `eject`（通过 `InjectorTransformer`）和 `generate`（通过 `StubGenerator`）都在生成完全相同的、标准化的输出。

现在，我们需要做的就是更新这些旧的测试用例，让它们接受这个新的、更好的格式标准。

## [WIP] test: 更新 scanner 测试以匹配 ruff 格式标准

### 用户需求
更新 `stitcher-scanner` 的测试用例，使其期望的输出符合新的、统一的 `ruff` 文档字符串格式标准（多行字符串的引号单独成行）。

### 评论
这是标准化的最后一步。我们已经不仅在代码层面实现了 DRY，还在测试层面建立了统一的“黄金标准”。现在，无论是生成的 `.pyi` 文件还是注入回 `.py` 文件的文档，都将遵循完全相同的、高质量的格式规范。

### 目标
1.  修改 `packages/stitcher-scanner/tests/test_transformer_multiline.py`。
2.  更新 `test_inject_preserves_multiline_indentation` 和 `test_inject_preserves_indentation_nested_class` 中的 `expected_code` 字符串，使其匹配新的多行文档字符串格式。

### 基本原理
测试断言必须反映代码的预期行为。既然我们已经决定在全项目范围内采纳 `ruff` 风格，测试数据就必须随之更新，以验证代码是否正确执行了这一标准。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/scanner #comp/tests #scope/dx
#ai/instruct
#task/domain/testing #task/object/injector-transformer #task/action/update
#task/state/continue

---
### Script

#### Acts 1: 更新 `test_transformer_multiline.py` 中的断言

我们将更新这两个测试用例中的 `expected_code`，将原本紧凑的多行字符串改为新的展开格式。

~~~~~act
patch_file
packages/stitcher-scanner/tests/test_transformer_multiline.py
~~~~~
~~~~~python.old
    # 3. The expected, correctly formatted output
    expected_code = dedent("""
    def my_func(arg1: int):
        \"\"\"This is the first line.
        This is the second line.\"\"\"
        pass
    """).strip()
~~~~~
~~~~~python.new
    # 3. The expected, correctly formatted output
    expected_code = dedent("""
    def my_func(arg1: int):
        \"\"\"
        This is the first line.
        This is the second line.
        \"\"\"
        pass
    """).strip()
~~~~~

~~~~~act
patch_file
packages/stitcher-scanner/tests/test_transformer_multiline.py
~~~~~
~~~~~python.old
    # Expected: Line 2 should have 8 spaces indentation (4 for class + 4 for method)
    expected_code = dedent("""
    class MyClass:
        def my_method(self):
            \"\"\"Line 1.
            Line 2.\"\"\"
            pass
    """).strip()
~~~~~
~~~~~python.new
    # Expected: Line 2 should have 8 spaces indentation (4 for class + 4 for method)
    expected_code = dedent("""
    class MyClass:
        def my_method(self):
            \"\"\"
            Line 1.
            Line 2.
            \"\"\"
            pass
    """).strip()
~~~~~
### 下一步建议
更新测试后，请再次运行完整的测试套件。此时，`stitcher-io` 和 `stitcher-scanner` 的所有相关测试都应该通过。

这将标志着我们彻底完成了对“pyi 写回机制不正确”这一严重问题的修复：
1.  我们消除了重复代码（DRY）。
2.  我们建立了统一的格式化代理。
3.  我们实施了高标准的格式规范（ruff style）。
4.  我们确保了 `generate` 和 `eject` 的行为完全一致。

一旦测试通过，您就可以放心地提交这些更改了。
