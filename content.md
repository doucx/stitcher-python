Excellent. The tests have immediately caught a critical flaw in our implementation. This is exactly why we write tests first.

The error message `libcst._nodes.base.CSTValidationError: Invalid string prefix` is extremely revealing. Let's break down what's happening.

1.  **`format_docstring` 的输出**:
    *   我们的新代理函数 `format_docstring` 表现得**完全正确**。它接收纯文本和缩进，然后输出一个**完整的、可直接放入 `.py` 文件的 Python 字符串字面量**。例如，它输出的正是 `'        """\n        Line 1.\n        Line 2.\n        """'`。这是一个**代码片段 (Code Snippet)**。

2.  **`cst.SimpleString` 的输入**:
    *   LibCST 的 `cst.SimpleString(value=...)` 构造函数期望 `value` 参数是字符串的**内容**，而不是完整的字面量表示。它会自己负责添加外部的引号。
    *   例如，要创建一个代表代码 `"""Hello"""` 的节点，你应该调用 `cst.SimpleString(value='"""Hello"""')`。

3.  **根本冲突 (The Core Conflict)**:
    *   在重构后的 `InjectorTransformer` 中，我们错误地将 `format_docstring` 生成的**完整代码片段**传递给了 `cst.SimpleString` 的 `value` 参数。
    *   我们实际上执行了这样的操作：`cst.SimpleString(value='"""indented content"""')`。
    *   LibCST 接收到这个值后，尝试将它作为**内容**来处理，并试图用另一层引号把它包起来，这导致了混乱。它看到我们值中的 `"""`，无法理解，最终在验证字符串“前缀”时失败，因为整个结构对它来说都是无效的。

**简而言之，我们进行了“双重包装”。我们把一个已经格式化好的盒子，又试图塞进另一个盒子里。**

我们不能修改 `format_docstring`，因为它的行为是我们想要的：生成一个完美的、最终的代码片段。

我们需要修改的是 `InjectorTransformer` **使用**这个片段的方式。我们不应该手动**构建**一个 `SimpleString` 节点，而应该让 LibCST **解析**我们已经拥有的完美代码片段。

正确的工具是 `cst.parse_statement`。

这个函数可以接收一个字符串形式的、有效的单行 Python 语句，并将其转换为一个正确的 LibCST 节点。我们的 `format_docstring` 生成的带缩进的 `"""..."""` 正是一个有效的表达式语句。

**新的工作流程将是：**
1.  `InjectorTransformer` 调用 `format_docstring` 获取格式化好的字符串字面量。
2.  `InjectorTransformer` 调用 `cst.parse_statement()`，将这个字符串字面量传递给它。
3.  LibCST 将其正确地解析为一个 `cst.SimpleStatementLine` 节点，其内部包含了我们想要的 `cst.Expr` 和 `cst.SimpleString`。
4.  我们将这个新解析出的节点注入到 AST 中。

这完美地维护了我们的抽象：`format_docstring` 负责生成代码，`InjectorTransformer` 负责将其集成到 AST 中，职责清晰。

我将生成一个计划来修复 `InjectorTransformer` 中的这个逻辑错误。

## [WIP] fix(scanner): 修正 InjectorTransformer 中的 CST 节点创建逻辑

### 错误分析
`InjectorTransformer` 在重构后，错误地将一个完整的、预格式化的文档字符串字面量（一个代码片段）传递给了 `cst.SimpleString` 构造函数，该构造函数期望的是字符串的原始内容。这导致了 `CSTValidationError`，因为 LibCST 无法处理这种“双重包装”。

### 用户需求
修复 `stitcher-scanner` 中的 `InjectorTransformer`，使其不再手动构建 `cst.SimpleString` 节点，而是使用 `cst.parse_statement` 来正确地将由 `format_docstring` 生成的代码片段解析为有效的 LibCST 节点。

### 评论
这是一个典型的由于抽象层次不匹配导致的 bug。修复它的过程将使我们的代码更加健壮。通过从“构建节点”转向“解析代码片段”，我们让 `InjectorTransformer` 的实现变得更加声明式和清晰。它不再需要关心 `format_docstring` 输出的具体内部结构，只需相信它是一个有效的 Python 语句即可。

### 目标
1.  修改 `packages/stitcher-scanner/src/stitcher/scanner/transformer.py` 文件。
2.  在 `InjectorTransformer` 中，将对 `cst.SimpleString(...)` 的调用替换为对 `cst.parse_statement(...)` 的调用。
3.  确保 `import cst` 存在于文件顶部。

### 基本原理
我们将利用 LibCST 的解析能力来代替手动节点构建。`cst.parse_statement` 是处理这种情况的理想工具，因为它能将一个格式正确的单行代码字符串转换为相应的 AST 节点树。这将直接解决验证错误，并使 `InjectorTransformer` 的实现与我们的“格式化代理”的输出意图完全对齐。

### 标签
#intent/fix #flow/ready #priority/critical
#comp/scanner #scope/core
#ai/instruct
#task/domain/testing #task/object/injector-transformer #task/action/bug-fix
#task/state/continue

---
### Script

#### Acts 1: 修复 `InjectorTransformer` 的节点创建逻辑

我们将修改 `InjectorTransformer`，使用 `cst.parse_statement` 来正确处理格式化后的文档字符串。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/transformer.py
~~~~~
~~~~~python.old
    ) -> HasBody:
        current_indent = self.indent_str * level
        # format_docstring expects the indentation of the """ quotes themselves.
        formatted_string = format_docstring(doc_content, current_indent)
        new_doc_node = cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.SimpleString(value=formatted_string))]
        )

        body = updated_node.body
        if isinstance(body, cst.SimpleStatementSuite):
~~~~~
~~~~~python.new
    ) -> HasBody:
        current_indent = self.indent_str * level
        # format_docstring returns a complete, indented string literal statement.
        formatted_string = format_docstring(doc_content, current_indent)

        # We parse this valid python snippet into a statement node directly.
        # This avoids abstraction leaks and validation errors.
        new_doc_node = cst.parse_statement(formatted_string)

        body = updated_node.body
        if isinstance(body, cst.SimpleStatementSuite):
~~~~~

#### Acts 2: 修复 `leave_Module` 中的相同逻辑

模块级别的 docstring 注入也存在同样的问题，需要一并修复。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/transformer.py
~~~~~
~~~~~python.old
    ) -> cst.Module:
        if "__doc__" in self.docs:
            formatted_string = format_docstring(self.docs["__doc__"], indent_str="")
            new_doc_node = cst.SimpleStatementLine(
                body=[cst.Expr(value=cst.SimpleString(value=formatted_string))]
            )
            new_body = []
            if updated_node.body:
                first = updated_node.body[0]
~~~~~
~~~~~python.new
    ) -> cst.Module:
        if "__doc__" in self.docs:
            formatted_string = format_docstring(self.docs["__doc__"], indent_str="")
            new_doc_node = cst.parse_statement(formatted_string)
            new_body = []

            if updated_node.body:
                first = updated_node.body[0]
~~~~~
### 下一步建议
我们已经定位并修复了 `InjectorTransformer` 中的核心逻辑错误。执行此计划后，请再次运行 `stitcher-scanner` 的测试套件。

我们期望之前所有失败的 6 个测试现在都应该**成功通过**。

测试通过后，我们的重构就基本完成了。最后一步将是为您之前提到的 `InjectorTransformer` 添加一个专门的“黄金测试”，以永久锁定 `eject` 命令的正确格式化行为，防止未来出现回归。
