这是 `libcst` 的一个关键验证机制导致的错误，也揭示了我们在设计 `format_docstring` 时的一个细微但致命的误解。

1.  **LibCST 的 `SimpleString` 规则**: `cst.SimpleString(value=...)` 接受的 `value` 必须是一个**合法的 Python 字符串字面量**。这意味着它必须以引号开头（如 `"""`）。它**不能**以空白（缩进）开头。LibCST 期望缩进由包含该字符串的语句节点（如 `SimpleStatementLine`）来管理。
2.  **`format_docstring` 的当前实现**: 我们的函数目前返回的是 `    """doc"""`（包含起始缩进）。这对 `StubGenerator`（纯文本拼接）是方便的，但对 `InjectorTransformer`（AST 构建）是**非法**的。

我们需要调整 `format_docstring` 的语义：
*   **它应该返回**: 文档字符串的**字面量内容**，其中包含**内部行**的正确缩进（因为这是字面量的一部分）。
*   **它不应该返回**: **第一行**的起始缩进（因为这是代码结构的一部分，由调用者控制）。

**修正后的行为示例**:
输入: `content="a\nb"`, `indent="    "`
输出: `"""\na\n    b\n    """` (注意第一行 `"""` 前无空格)

这样：
1.  **对于 `InjectorTransformer`**: 直接将此输出传给 `SimpleString(value=...)` 是合法的。LibCST 会在打印 AST 时自动为第一行添加缩进。
2.  **对于 `StubGenerator`**: 我们需要在拼接时手动加上起始缩进：`lines.append(f"{indent}{formatted_doc}")`。

这在逻辑上更正确：`format_docstring` 负责生成一个符合格式的字符串对象，而“把它放在哪一行、缩进多少”是使用者的责任。

我将生成一个计划，修改 `formatting.py` 并同步更新 `StubGenerator`。

## [WIP] fix(common): 调整 format_docstring 以兼容 LibCST 节点规范

### 用户需求
修复 `stitcher-scanner` 测试中出现的 `CSTValidationError: Invalid string prefix` 错误。

### 评论
这个修复不仅仅是为了消除错误，它纠正了我们对“格式化代理”职责的定义。代理应该产生合法的 Python 对象表示（字符串字面量），而不是特定于上下文的代码片段（带缩进的行）。这种职责分离使得我们的代理能同时完美服务于文本生成器（StubGenerator）和 AST 构建器（LibCST）。

### 目标
1.  修改 `packages/stitcher-common/src/stitcher/common/formatting.py` 中的 `format_docstring` 函数，使其返回的字符串**不再包含起始缩进**。
2.  修改 `packages/stitcher-io/src/stitcher/io/stub_generator.py`，在调用 `format_docstring` 的所有地方，手动在其返回结果前添加缩进。

### 基本原理
LibCST 的 `SimpleString` 节点值不能包含前导空白。通过移除 `format_docstring` 返回值的前导空白，我们满足了 LibCST 的要求。同时，对于基于文本的 `StubGenerator`，我们只需在拼接时显式补上这个缩进即可保持原有行为不变。

### 标签
#intent/fix #flow/ready #priority/high
#comp/common #comp/io #scope/dx
#ai/instruct
#task/domain/testing #task/object/formatter #task/action/bug-fix
#task/state/continue

---
### Script

#### Acts 1: 修正 `formatting.py` 去除起始缩进

我们将修改 `format_docstring`，只负责内部行的缩进和引号包裹，不再添加第一行的缩进。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/formatting.py
~~~~~
~~~~~python.old
    if len(lines) == 1:
        # Single line: keep it compact and escape internal quotes
        processed_doc = content.replace('"""', '\\"\\"\\"')
        return f'{indent_str}"""{processed_doc}"""'

    # Multi-line: adopt the ruff/black style for readability
    # Re-indent all lines to match the current level.
    indented_body = "\n".join(f"{indent_str}{line}" for line in lines)
    return f'{indent_str}"""\n{indented_body}\n{indent_str}"""'
~~~~~
~~~~~python.new
    if len(lines) == 1:
        # Single line: keep it compact and escape internal quotes
        processed_doc = content.replace('"""', '\\"\\"\\"')
        return f'"""{processed_doc}"""'

    # Multi-line: adopt the ruff/black style for readability
    # Re-indent all lines to match the current level.
    # Note: The start quotes do NOT have indentation here, as that is handled
    # by the caller (StubGenerator) or the AST wrapper (LibCST).
    # However, internal lines MUST have the indentation.
    indented_body = "\n".join(f"{indent_str}{line}" for line in lines)
    return f'"""\n{indented_body}\n{indent_str}"""'
~~~~~

#### Acts 2: 更新 `StubGenerator` 以手动添加起始缩进

由于 `format_docstring` 不再返回起始缩进，我们需要在 `stub_generator.py` 中手动拼接它。

~~~~~act
patch_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python.old
        # 1. Module Docstring
        if module.docstring:
            lines.append(format_docstring(module.docstring, self._indent(0)))
            lines.append("")  # Empty line after docstring
~~~~~
~~~~~python.new
        # 1. Module Docstring
        if module.docstring:
            # format_docstring returns the literal without starting indent, so we prepend it.
            # For module level (level 0), indent is empty string, but consistent logic applies.
            formatted = format_docstring(module.docstring, self._indent(0))
            lines.append(f"{self._indent(0)}{formatted}")
            lines.append("")  # Empty line after docstring
~~~~~

~~~~~act
patch_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python.old
        # Body
        if func.docstring:
            lines.append(def_line)
            lines.append(format_docstring(func.docstring, self._indent(level + 1)))
            lines.append(f"{self._indent(level + 1)}...")
~~~~~
~~~~~python.new
        # Body
        if func.docstring:
            lines.append(def_line)
            formatted = format_docstring(func.docstring, self._indent(level + 1))
            lines.append(f"{self._indent(level + 1)}{formatted}")
            lines.append(f"{self._indent(level + 1)}...")
~~~~~

~~~~~act
patch_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python.old
        # Docstring
        if cls.docstring:
            lines.append(format_docstring(cls.docstring, self._indent(level + 1)))
            has_content = True
~~~~~
~~~~~python.new
        # Docstring
        if cls.docstring:
            formatted = format_docstring(cls.docstring, self._indent(level + 1))
            lines.append(f"{self._indent(level + 1)}{formatted}")
            has_content = True
~~~~~
### 下一步建议
我们已经修正了 `formatting.py` 和 `StubGenerator`。现在：
1.  `format_docstring` 返回合法的、无起始缩进的字符串字面量。
2.  `StubGenerator` 手动处理起始缩进，因此其输出保持不变（仍符合 ruff 风格）。
3.  `InjectorTransformer`（未修改）直接使用 `format_docstring` 的返回值，现在这应该能通过 LibCST 的验证了。

请重新运行测试。现在所有的测试，包括 `stitcher-io` 的生成测试和 `stitcher-scanner` 的注入测试，都应该能通过。这将标志着我们彻底解决了文档字符串格式不一致和 DRY 违规的问题。
