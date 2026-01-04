好的，非常感谢指出这个错误。我的疏忽，单元测试中的 mock 断言没有正确匹配 `pathlib.Path` 对象的类型。

这是一个典型的 `str` 与 `Path` 对象在测试中不匹配的问题。`TransactionManager` 的实现是正确的，它始终使用 `Path` 对象，但测试断言错误地使用了字符串。

我将生成一个计划来修正这个单元测试。

## [WIP] fix: 修正 TransactionManager 单元测试中的 mock 断言

### 错误分析
测试 `test_transaction_commit` 在 `packages/stitcher-refactor/tests/unit/test_transaction.py` 中失败。

**根本原因**: `mock_fs.move.assert_called_once_with` 的断言是错误的。`TransactionManager.commit` 方法在调用 `fs.move` 时，第二个参数（目标路径）是一个 `pathlib.Path` 对象 (`root / "dest.py"`)。然而，测试代码错误地断言它应该是一个字符串 (`"root/dest.py"`)。这导致了 `AssertionError`。

### 用户需求
修复因 `pathlib.Path` 对象与字符串不匹配而失败的单元测试。

### 评论
这是一个很好的例子，说明了测试代码与实现代码保持同步的重要性。修复此问题将确保我们的单元测试能够准确地验证 `TransactionManager` 的行为意图，即它正确地构造了路径对象并传递给文件系统适配器。

### 目标
1.  修改 `packages/stitcher-refactor/tests/unit/test_transaction.py` 文件。
2.  在 `test_transaction_commit` 函数中，将 `mock_fs.move.assert_called_once_with` 的第二个参数从字符串 `"root/dest.py"` 更改为 `Path` 对象 `root / "dest.py"`。

### 基本原理
为了让测试通过并正确反映被测代码的行为，mock 断言的参数必须在类型和值上都与实际调用完全匹配。`TransactionManager` 内部使用 `pathlib` 进行路径拼接，因此生成的是 `Path` 对象，断言也必须使用 `Path` 对象。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #task/domain/refactor #task/object/transaction-manager #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正 mock 断言
我们将修正 `test_transaction.py` 中错误的断言。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_transaction.py
~~~~~
~~~~~python.old
    # 2. Verify Move
    mock_fs.move.assert_called_once_with(root / "src.py", "root/dest.py")

    # 3. Verify Queue Cleared
~~~~~
~~~~~python.new
    # 2. Verify Move
    mock_fs.move.assert_called_once_with(root / "src.py", root / "dest.py")

    # 3. Verify Queue Cleared
~~~~~

### 下一步建议
测试修复后，`TransactionManager` 的基础设施就稳固了。我们可以继续推进路线图，开始实现 `SemanticGraph` 原型，为符号重命名操作做准备。
