好的，我来分析并修复 `pyrefly` 报告的这三个类型错误。

-   **第一个错误 (`bad-index`)**: 在 `test_pointer.py` 中，代码 `d = {L.key: "value"}` 创建了一个字典，其键的类型是 `SemanticPointer`。然而，`assert d["key"] == "value"` 试图使用一个 `str` 类型的 `"key"` 来索引它，这在类型上是不匹配的。正确的测试方法是使用 `SemanticPointer` 对象 `L.key` 本身来索引，这在下一行 `assert d[L.key] == "value"` 已经做到了。因此，错误的这一行应该被删除。
-   **第二和第三个错误 (`not-iterable`)**: 在 `test_parser_advanced.py` 中，`arg_meta.annotation` 的类型是 `Optional[str]`，这意味着它可能是 `str` 或 `None`。`assert "..." in arg_meta.annotation` 操作在 `arg_meta.annotation` 为 `None` 时会失败。为了修复这个问题，我需要在执行 `in` 检查之前，先断言 `arg_meta.annotation` 不为 `None`。

我将生成一个计划来执行这些修复。

## [WIP] fix: 修复 pyrefly 报告的类型错误

### 用户需求
用户要求修复 `pyrefly check` 命令报告的三个类型错误，包括一个 `bad-index` 错误和两个 `not-iterable` 错误。

### 评论
这些是由静态类型检查器发现的有效问题。修复它们可以提高代码的健壮性和正确性，并确保测试的准确性。

-   `test_pointer.py` 中的错误是一个逻辑错误，测试用例试图用错误的类型访问字典键。
-   `test_parser_advanced.py` 中的错误是典型的 `Optional` 类型处理不当，在使用前未进行 `None` 检查。

### 目标
1.  修正 `packages/stitcher-needle/tests/test_pointer.py` 中的字典索引错误。
2.  在 `packages/stitcher-scanner/tests/test_parser_advanced.py` 中为 `Optional[str]` 类型的变量添加 `None` 检查，以确保类型安全。

### 基本原理
-   对于 `bad-index` 错误，我们将删除使用字符串字面量对 `dict[SemanticPointer, str]` 进行索引的无效断言行。正确的测试（使用 `SemanticPointer` 对象作为键）已经存在，因此删除多余且错误的行即可。
-   对于 `not-iterable` 错误，我们将在执行 `in` 操作之前插入 `assert xxx is not None`。这向类型检查器保证了在该代码路径下，变量是一个 `str`，从而允许字符串操作。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/type-errors #task/action/bug-fix #task/state/begin

---
### Script

#### Acts 1: 修正 `test_pointer.py` 中的测试逻辑

我们将移除 `test_hashability` 测试函数中错误的断言行。

~~~~~act
patch_file
packages/stitcher-needle/tests/test_pointer.py
~~~~~
~~~~~python.old
def test_hashability():
    # Pointers should be usable as dictionary keys
    d = {L.key: "value"}
    assert d["key"] == "value"
    assert d[L.key] == "value"
~~~~~
~~~~~python.new
def test_hashability():
    # Pointers should be usable as dictionary keys
    d = {L.key: "value"}
    assert d[L.key] == "value"
~~~~~

#### Acts 2: 在 `test_parser_advanced.py` 中添加 None 检查

在对 `arg_meta.annotation` 进行 `in` 操作前，我们先断言它不为 `None`。

~~~~~act
patch_file
packages/stitcher-scanner/tests/test_parser_advanced.py
~~~~~
~~~~~python.old
    arg_meta = func.args[1]
    # LibCST might strip whitespace differently, but usually it preserves structure
    # We check if key parts are present
    assert "Union" in arg_meta.annotation
    assert "Dict[str, Any]" in arg_meta.annotation
~~~~~
~~~~~python.new
    arg_meta = func.args[1]
    # LibCST might strip whitespace differently, but usually it preserves structure
    # We check if key parts are present
    assert arg_meta.annotation is not None
    assert "Union" in arg_meta.annotation
    assert "Dict[str, Any]" in arg_meta.annotation
~~~~~
### 下一步建议
我已经生成了修复错误的计划。在执行此计划后，建议你再次运行 `pyrefly check` 以确认所有已报告的错误都已解决。
