好的，我们来完成这次重构，将 `stitcher-scanner` 与我们新的格式化代理同步。

我将生成一个计划，用 `write_file` 来重写 `transformer.py`。这次重构将：
1.  **导入新的代理函数**: `from stitcher.common import format_docstring`。
2.  **移除冗余代码**: 删除 `InjectorTransformer` 内部复杂且重复的缩进和格式化逻辑。
3.  **简化实现**: 让 `InjectorTransformer` 直接调用 `format_docstring` 来生成完美的、格式一致的文档字符串节点。

这将是我们解决 DRY 违规问题的最后一步，也是确保 `eject` 和 `generate` 命令输出完全一致的关键。

## [WIP] refactor(scanner): 重构 InjectorTransformer 以使用统一代理

### 用户需求
修改 `stitcher-scanner` 包中的 `InjectorTransformer`，让它调用位于 `stitcher-common` 中的新 `format_docstring` 函数，从而与 `StubGenerator` 的输出格式保持完全一致。

### 评论
这次重构是实现架构一致性的收官之作。通过让 `InjectorTransformer` 依赖于我们创建的单一格式化代理，我们彻底消除了代码库中的重复逻辑。从现在开始，任何对文档字符串格式的调整都只需要在一个地方进行，`generate` 和 `eject` 命令的行为将得到根本性的统一。这是对项目长期健康和可维护性的一项重要投资。

### 目标
1.  使用 `write_file` 重写 `packages/stitcher-scanner/src/stitcher/scanner/transformer.py` 文件。
2.  在文件顶部添加 `from stitcher.common import format_docstring`。
3.  大幅简化 `InjectorTransformer` 类，移除其内部的 `_create_docstring_node` 方法和 `_inject_into_body` 方法中的手动格式化代码。
4.  确保 `InjectorTransformer` 现在使用 `format_docstring` 来生成最终的文档字符串表示，然后再将其转换为 LibCST 节点。

### 基本原理
`InjectorTransformer` 当前的实现包含了一套复杂、脆弱且与 `StubGenerator` 不一致的字符串处理逻辑。这违反了 DRY 原则，是产生 bug 的温床。

我们将用一个更清晰、更简单的方法替换它。`InjectorTransformer` 的职责将被简化为：
1.  确定注入文档字符串的**位置**（类、函数或模块体）。
2.  计算该位置所需的**缩进级别**。
3.  调用 `stitcher.common.format_docstring`，将纯文本内容和计算出的缩进级别作为参数，获取一个**预先格式化好的、完整的文档字符串字面量**。
4.  将这个完美的字符串字面量包装成一个 LibCST 节点并注入 AST。

这种方法将格式化的复杂性完全委托给了我们可信的中央代理，使 `InjectorTransformer` 的代码更易于理解和维护。

### 标签
#intent/refine #flow/ready #priority/high
#comp/scanner #comp/common #scope/dx
#ai/instruct
#task/domain/testing #task/object/injector-transformer #task/action/refactor
#task/state/continue

---
### Script

#### Acts 1: 重写 `transformer.py` 以使用格式化代理

我们将用一个精简后的版本替换整个 `transformer.py` 文件。新版本将移除所有本地的格式化逻辑，并转而调用 `stitcher.common.format_docstring`。

~~~~~act
write_file
packages/stitcher-scanner/src/stitcher/scanner/transformer.py
~~~~~
~~~~~python
import libcst as cst
from typing import Dict, List, Optional, Union
from stitcher.common import format_docstring

# Type alias for nodes that have a body attribute
HasBody = Union[cst.Module, cst.ClassDef, cst.FunctionDef]


class StripperTransformer(cst.CSTTransformer):
    def _is_docstring(self, node: cst.BaseSmallStatement) -> bool:
        if isinstance(node, cst.Expr) and isinstance(node.value, cst.SimpleString):
            return True
        return False

    def _process_body(
        self, body: Union[cst.BaseSuite, cst.SimpleStatementSuite]
    ) -> Union[cst.BaseSuite, cst.SimpleStatementSuite]:
        if isinstance(body, cst.SimpleStatementSuite):
            # One-liner: def foo(): "doc" -> def foo(): pass
            # SimpleStatementSuite contains a list of small statements
            new_body = []
            for stmt in body.body:
                if not self._is_docstring(stmt):
                    new_body.append(stmt)

            if not new_body:
                # If became empty, convert to a single 'pass'
                return cst.SimpleStatementSuite(body=[cst.Pass()])
            return body.with_changes(body=new_body)

        elif isinstance(body, cst.IndentedBlock):
            new_body = []
            if body.body:
                first_stmt = body.body[0]
                # In an IndentedBlock, the statements are typically SimpleStatementLine
                # which contain small statements.
                # We check if the FIRST line is a docstring expression.
                if isinstance(first_stmt, cst.SimpleStatementLine):
                    if len(first_stmt.body) == 1 and self._is_docstring(
                        first_stmt.body[0]
                    ):
                        # Skip this line (it's the docstring)
                        new_body.extend(body.body[1:])
                    else:
                        new_body.extend(body.body)
                else:
                    new_body.extend(body.body)

            if not new_body:
                # If empty, add pass
                # We need to ensure we have a valid indentation block structure
                return body.with_changes(
                    body=[cst.SimpleStatementLine(body=[cst.Pass()])]
                )

            return body.with_changes(body=new_body)

        return body

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        # Module body is just a sequence of statements, not wrapped in IndentedBlock
        new_body = []
        if updated_node.body:
            first_stmt = updated_node.body[0]
            if isinstance(first_stmt, cst.SimpleStatementLine):
                if len(first_stmt.body) == 1 and self._is_docstring(first_stmt.body[0]):
                    new_body.extend(updated_node.body[1:])
                else:
                    new_body.extend(updated_node.body)
            else:
                new_body.extend(updated_node.body)

        return updated_node.with_changes(body=new_body)

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        return updated_node.with_changes(body=self._process_body(updated_node.body))

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        return updated_node.with_changes(body=self._process_body(updated_node.body))


class InjectorTransformer(cst.CSTTransformer):
    def __init__(self, docs: Dict[str, str]):
        self.docs = docs
        self.scope_stack: List[str] = []
        self.indent_str: str = " " * 4  # Default indent

    def _get_current_fqn(self, name: str) -> str:
        if not self.scope_stack:
            return name
        return f"{'.'.join(self.scope_stack)}.{name}"

    def _is_docstring(self, node: cst.BaseSmallStatement) -> bool:
        return isinstance(node, cst.Expr) and isinstance(node.value, cst.SimpleString)

    def _inject_into_body(
        self,
        node: HasBody,
        updated_node: HasBody,
        doc_content: str,
        level: int,
    ) -> HasBody:
        current_indent = self.indent_str * level
        # format_docstring expects the indentation of the """ quotes themselves.
        formatted_string = format_docstring(doc_content, current_indent)
        new_doc_node = cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.SimpleString(value=formatted_string))]
        )

        body = updated_node.body
        if isinstance(body, cst.SimpleStatementSuite):
            # Convert "def f(): stmt" to:
            # def f():
            #     """doc"""
            #     stmt
            new_stmts = [new_doc_node]
            for stmt in body.body:
                if isinstance(stmt, cst.Pass):
                    continue
                new_stmts.append(cst.SimpleStatementLine(body=[stmt]))
            return updated_node.with_changes(body=cst.IndentedBlock(body=new_stmts))

        elif isinstance(body, cst.IndentedBlock):
            new_body_stmts = []
            if body.body:
                first = body.body[0]
                if (
                    isinstance(first, cst.SimpleStatementLine)
                    and len(first.body) == 1
                    and self._is_docstring(first.body[0])
                ):
                    # Replace existing docstring
                    new_body_stmts.append(new_doc_node)
                    new_body_stmts.extend(body.body[1:])
                else:
                    new_body_stmts.append(new_doc_node)
                    new_body_stmts.extend(body.body)
            else:
                new_body_stmts.append(new_doc_node)
            return updated_node.with_changes(body=body.with_changes(body=new_body_stmts))

        return updated_node

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        self.scope_stack.append(node.name.value)
        return True

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        fqn = ".".join(self.scope_stack)
        if fqn in self.docs:
            updated_node = self._inject_into_body(
                original_node, updated_node, self.docs[fqn], level=len(self.scope_stack)
            )
        self.scope_stack.pop()
        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self.scope_stack.append(node.name.value)
        return True

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        fqn = ".".join(self.scope_stack)
        if fqn in self.docs:
            updated_node = self._inject_into_body(
                original_node, updated_node, self.docs[fqn], level=len(self.scope_stack)
            )
        self.scope_stack.pop()
        return updated_node

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        if "__doc__" in self.docs:
            formatted_string = format_docstring(self.docs["__doc__"], indent_str="")
            new_doc_node = cst.SimpleStatementLine(
                body=[cst.Expr(value=cst.SimpleString(value=formatted_string))]
            )
            new_body = []
            if updated_node.body:
                first = updated_node.body[0]
                if (
                    isinstance(first, cst.SimpleStatementLine)
                    and len(first.body) == 1
                    and self._is_docstring(first.body[0])
                ):
                    new_body.append(new_doc_node)
                    new_body.extend(updated_node.body[1:])
                else:
                    new_body.append(new_doc_node)
                    new_body.extend(updated_node.body)
            else:
                new_body.append(new_doc_node)
            return updated_node.with_changes(body=new_body)
        return updated_node


def strip_docstrings(source_code: str) -> str:
    module = cst.parse_module(source_code)
    transformer = StripperTransformer()
    modified = module.visit(transformer)
    return modified.code


def inject_docstrings(source_code: str, docs: Dict[str, str]) -> str:
    module = cst.parse_module(source_code)
    transformer = InjectorTransformer(docs)
    modified = module.visit(transformer)
    return modified.code
~~~~~
### 下一步建议
我们已经成功完成了对 `InjectorTransformer` 的重构。现在，`stitcher-io` 和 `stitcher-scanner` 都依赖于同一个 docstring 格式化代理，从根本上解决了行为不一致的问题。

为了验证我们的工作并确保万无一失，下一步是：
1.  **为 `InjectorTransformer` 添加测试**：在 `packages/stitcher-scanner/tests/` 目录下创建一个新的测试文件，例如 `test_transformer_eject.py`。
2.  **编写黄金测试**：在这个文件中，编写一个测试用例，它调用 `inject_docstrings` 函数，并断言其输出与我们期望的、符合 `ruff` 风格的“黄金标准”字符串完全一致。这个测试将直接验证我们的重构是否成功。

如果你同意，我将为您生成创建此测试的计划。
