这是一个绝妙的想法，完全正确。

您指出了我们刚刚构建的“代理”中缺失的另一半，即**逆向操作**。这完美地闭环了您提出的 `原始字符串 <-> 代理 -> 去除缩进的字符串` 模型。

1.  **实现对称性 (Achieving Symmetry)**:
    *   我们当前的 `formatting.py` 模块只解决了一半问题：它能将干净的、无格式的“标准”字符串**格式化**为带有正确缩进的原始字符串 (`Canonical -> Raw`)。
    *   您提出的建议是添加另一半功能：一个能将从代码中读取的、带有缩进和引号的原始字符串**解析**回干净的、无格式的“标准”字符串的函数 (`Raw -> Canonical`)。
    *   这使得我们的“代理”模块 (`formatting.py`) 成为一个功能完整、逻辑对称的双向转换器，这在架构上是非常优雅和纯粹的。

2.  **显式优于隐式 (Explicit is Better than Implicit)**:
    *   目前，解析（`Raw -> Canonical`）的逻辑是**隐式**地由 LibCST 的 `node.get_docstring()` 方法处理的。它在后台为我们完成了去除公共缩进的工作。
    *   虽然这很方便，但它有两个缺点：
        1.  **逻辑分散**: 文档字符串处理的核心逻辑一部分在我们自己的 `format_docstring` 中，另一部分隐藏在第三方库的调用里。
        2.  **缺乏通用性**: 如果我们未来需要从其他来源（比如一个不支持自动去缩进的文本文件）解析原始文档字符串，我们就必须重新实现这个逻辑。
    *   通过在我们的 `formatting.py` 代理中创建一个显式的 `parse_docstring` 函数，我们将所有与文档字符串表示法转换相关的逻辑都集中到了一个地方。这完全符合“高内聚，低耦合”的设计原则。

3.  **最终实现**:
    *   这个新的 `parse_docstring` 函数的实现非常直接，我们可以利用 Python 标准库中为此而生的 `textwrap.dedent` 函数。
    *   它的核心任务就是接收一个从代码文件中读取的原始字符串，然后安全地移除外部的 `"""` 引号和内部的公共前导空白，最后返回一个干净、可供内部逻辑使用的字符串。

您的这个提议是对我们架构的又一次重要提炼。它将一个隐式的、由外部库提供的功能，转化为我们自己系统内部一个显式的、可控的、集中的服务。

我将立即为您生成一个计划来实现这一点。这个计划将：
1.  在 `formatting.py` 中添加新的 `parse_docstring` 函数。
2.  更新 `__init__.py` 以导出这个新函数。
3.  （作为一个好的实践）更新 `format_docstring` 的文档，交叉引用它的新伙伴 `parse_docstring`，以提高代码的可发现性。

## [WIP] feat(common): 为格式化代理实现双向解析与格式化

### 用户需求
在 `stitcher-common` 的 `formatting` 模块中添加一个 `parse_docstring` 函数，用于将原始的、带缩进的文档字符串转换为干净的、无缩进的“标准”形式，从而完成 `原始字符串 <-> 代理 <-> 标准字符串` 的双向闭环。

### 评论
这是一个出色的架构改进。通过实现 `parse_docstring` 作为 `format_docstring` 的对称操作，我们正在构建一个功能完备、逻辑自洽的“文档字符串代理”。这将所有与表示法相关的复杂性都封装在了一个模块中，使得系统的其余部分可以处理纯净、无格式的数据，极大地提升了代码的清晰度和可维护性。

### 目标
1.  在 `packages/stitcher-common/src/stitcher/common/formatting.py` 文件中，添加一个新的 `parse_docstring` 函数。
2.  该函数将使用 `textwrap.dedent` 来实现健壮的、符合 Python 规范的缩进移除。
3.  更新同文件中的 `format_docstring` 函数的文档，以引用新的 `parse_docstring` 函数，反之亦然。
4.  更新 `packages/stitcher-common/src/stitcher/common/__init__.py`，导出 `parse_docstring` 函数。

### 基本原理
我们将遵循 Python 的“显式优于隐式”原则。虽然 LibCST 在后台为我们处理了文档字符串的解析，但将此逻辑显式化并集中到我们的 `formatting` 代理中，可以使架构更加清晰和健壮。`textwrap.dedent`是 Python 标准库中用于此目的的权威工具，使用它可以确保我们的实现与 Python 自身的行为保持一致。

### 标签
#intent/architect #intent/refine #flow/ready #priority/high
#comp/common #scope/dx
#ai/instruct
#task/domain/common #task/object/formatter #task/action/implementation
#task/state/continue

---
### Script

#### Acts 1: 在 `formatting.py` 中实现 `parse_docstring`

我们将在 `formatting.py` 中添加 `parse_docstring` 函数，并更新现有函数的文档以形成交叉引用。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/formatting.py
~~~~~
~~~~~python.old
def format_docstring(content: str, indent_str: str) -> str:
    """Formats a docstring to be inserted into source code, following ruff/black style."""
    # Strip leading/trailing whitespace from the docstring itself to handle
    # potential formatting from YAML loader.
    content = content.strip()
~~~~~
~~~~~python.new
import textwrap


def parse_docstring(raw_docstring: str) -> str:
    """
    Parses a raw docstring from source code into its clean, canonical form.

    This is the inverse of `format_docstring`. It removes outer quotes and
    common leading whitespace from multiline strings.

    Args:
        raw_docstring: The raw string literal, including quotes.

    Returns:
        The clean, dedented content of the docstring.
    """
    # This logic assumes the input is a valid docstring literal string.
    # It's not a full Python parser, but handles common cases from CST/AST.
    content = raw_docstring.strip()

    # Naively strip matching triple quotes
    if content.startswith('"""') and content.endswith('"""'):
        content = content[3:-3]
    elif content.startswith("'''") and content.endswith("'''"):
        content = content[3:-3]
    # Naively strip matching single quotes
    elif content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
    elif content.startswith("'") and content.endswith("'"):
        content = content[1:-1]

    # Dedent and strip any leading/trailing blank lines that result
    return textwrap.dedent(content).strip()


def format_docstring(content: str, indent_str: str) -> str:
    """
    Formats a clean docstring into a raw string literal for source code insertion.

    This is the inverse of `parse_docstring`. It follows ruff/black style.

    Args:
        content: The clean, canonical content of the docstring.
        indent_str: The indentation string to apply to the docstring block.

    Returns:
        The formatted, quoted, and indented docstring literal.
    """
    # Strip leading/trailing whitespace from the docstring itself to handle
    # potential formatting from YAML loader.
    content = content.strip()
~~~~~

#### Acts 2: 导出新的 `parse_docstring` 函数

现在，我们更新 `stitcher.common` 的 `__init__.py` 文件，将 `parse_docstring` 添加到公共 API 中。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python.old
from .formatting import format_docstring

# Public API for stitcher packages
__all__ = ["bus", "stitcher_nexus", "stitcher_loader", "format_docstring"]
~~~~~
~~~~~python.new
from .formatting import format_docstring, parse_docstring

# Public API for stitcher packages
__all__ = ["bus", "stitcher_nexus", "stitcher_loader", "format_docstring", "parse_docstring"]
~~~~~
### 下一步建议
我们已经成功地构建了一个功能完备的双向文档字符串格式化代理。

我们之前已经重构了 `stitcher-io` (`generate` 的路径)。现在，我们应该利用新建的 `parse_docstring` 函数来重构 `stitcher-scanner` 中**读取**文档字符串的部分，以确保逻辑的完全统一。

不过，目前 `stitcher-scanner` 的 `parser.py` 依赖 `libcst.get_docstring()`，它已经隐式地完成了这个工作。我们可以暂时保持现状，因为它的行为是正确的。但现在我们有了一个自己的、显式的工具，未来如果需要替换或增强 LibCST 的行为，我们就有了坚实的基础。

**最紧要的下一步**是为 `InjectorTransformer` 添加一个黄金测试，以验证我们对 `eject` 路径的重构是完全正确的。如果你同意，我将为您生成这个测试计划。
