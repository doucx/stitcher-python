你分析得完全正确。在上一步中，我修正了测试夹具 `mock_context` 的返回类型注解，但忘记了更新使用该夹具的测试函数中的参数类型注解。这导致 `pyright` 仍然将 `mock_context` 变量视为真实的 `RefactorContext` 实例，而不是 `Mock` 对象，因此无法识别 `side_effect` 和 `return_value` 属性。

我将生成一个计划来修正这两个测试函数中的类型提示。

## [WIP] fix: 修正测试函数中 mock 参数的类型提示

### 错误分析

`pyright` 报告的两个 `AttributeAccessIssue` 错误均源于测试函数 `test_planner_merges_rename_operations_for_same_file` 和 `test_planner_handles_move_and_rename_on_same_file` 中，其参数 `mock_context` 被错误地注解为 `RefactorContext`。

尽管 `mock_context` 夹具实际返回的是一个 `unittest.mock.Mock` 对象，但 `pyright` 优先采信了函数签名中的类型提示。因此，它认为 `mock_context.graph.find_usages` 是一个普通的方法（`MethodType`），该类型上不存在 `side_effect` 或 `return_value` 属性，从而引发了类型错误。

### 用户需求

修复 `pyright` 报告的 `AttributeAccessIssue` 错误。

### 评论

这是一个常见的类型提示错误，特别是在使用 `pytest` 夹具和 `mock` 对象时。保持夹具的返回类型和测试函数参数的类型注解一致，对于静态分析工具的正确性至关重要。这次修复将使代码的类型信息恢复一致。

### 目标

1.  修改 `test_planner_merges_rename_operations_for_same_file` 函数，将其 `mock_context` 参数的类型提示从 `RefactorContext` 更改为 `Mock`。
2.  修改 `test_planner_handles_move_and_rename_on_same_file` 函数，将其 `mock_context` 参数的类型提示从 `RefactorContext` 更改为 `Mock`。

### 基本原理

通过将测试函数参数的类型提示从 `RefactorContext` 修正为 `Mock`，我们可以向 `pyright` 明确传达该变量的真实类型。这样，类型检查器就能正确地推断出 `mock_context` 的所有属性（如 `graph`）也都是 `Mock` 对象，进而识别出 `side_effect` 和 `return_value` 是合法的属性，从而消除错误。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/static-analysis #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正测试函数中的类型提示

我们将对 `test_planner_merging.py` 文件执行两次 `patch_file` 操作，分别更新两个测试函数中 `mock_context` 参数的类型注解。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/engine/test_planner_merging.py
~~~~~
~~~~~python.old
def test_planner_merges_rename_operations_for_same_file(mock_context: RefactorContext):
~~~~~
~~~~~python.new
def test_planner_merges_rename_operations_for_same_file(mock_context: Mock):
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/engine/test_planner_merging.py
~~~~~
~~~~~python.old
def test_planner_handles_move_and_rename_on_same_file(mock_context: RefactorContext):
~~~~~
~~~~~python.new
def test_planner_handles_move_and_rename_on_same_file(mock_context: Mock):
~~~~~

### 下一步建议

应用此修复后，`pyright` 应该不再报告任何错误。建议重新运行静态分析以确认。之后，我们可以将所有累积的修复作为一个完整的单元进行提交。
