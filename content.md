简要回答

好的，我明白了。错误的根本原因是 `griffe` 在解析标准的 Google/Numpy 风格 section（如 `Args` 或 `Parameters`）时，并不会将标题文本存储在 `title` 字段中（它为 `None`），而是通过 `kind` 字段来标识语义。

为了修复这个问题并支持风格转换（例如 Parse Google -> Render Numpy），我们需要采取以下架构决策：
1.  **Parser**: 对于标准 Section，保持 `title` 为 `None`。
2.  **Renderer**: 负责根据 Section 的 `kind` 和目标风格，生成默认的标准标题。
3.  **Test**: 更新测试以符合上述行为。

## [WIP] fix: 完善结构化文档的标题处理逻辑

### 用户需求

修复 `test_parsers.py` 中的断言错误，并完善渲染器以处理 `title` 为 `None` 的情况。

### 评论

这是一个非常好的发现，它促使我们明确了 IR 中 `title` 字段的语义：它应该只用于存储**非标准**或**自定义**的标题。标准标题应由 Renderer 根据语义（`kind`）动态生成。这不仅修复了测试，还增强了系统进行文档风格转换的能力。

### 目标

1.  修改 `packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/renderers.py`，为渲染器添加默认标题映射逻辑。
2.  修改 `packages/stitcher-python-adapter/tests/docstring/test_parsers.py`，更新断言，不再期待 Parser 返回标准标题文本。
3.  修改 `packages/stitcher-python-adapter/tests/docstring/test_renderers.py`，增加测试用例以验证无标题 Section 的渲染。

### 基本原理

通过将“标准标题生成”的责任移交给 Renderer，我们确保了 IR 的纯洁性（只包含语义），并解耦了源文档风格与目标文档风格。

### 标签

#intent/fix #flow/ready #priority/high #comp/adapter #concept/renderer #task/domain/docstring #task/object/renderer #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 增强渲染器逻辑

我们将修改 `BaseStructuredRenderer` 及其子类，引入 `_get_default_title` 方法。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/renderers.py
~~~~~
~~~~~python.old
class BaseStructuredRenderer(DocstringRendererProtocol):
    def render(self, docstring_ir: DocstringIR) -> str:
        blocks = []

        if docstring_ir.summary:
            blocks.append(docstring_ir.summary)

        if docstring_ir.extended:
            blocks.append(docstring_ir.extended)

        for section in docstring_ir.sections:
            rendered_section = self._render_section(section)
            if rendered_section:
                blocks.append(rendered_section)

        # Join blocks with an empty line between them
        return "\n\n".join(blocks)

    def _render_section(self, section: DocstringSection) -> str:
        raise NotImplementedError


class GoogleDocstringRenderer(BaseStructuredRenderer):
    def _render_section(self, section: DocstringSection) -> str:
        lines = []
        if section.title:
            lines.append(f"{section.title}:")
        
        if section.kind == "text" or section.kind == "admonition":
             # Text content: Indent body
~~~~~
~~~~~python.new
class BaseStructuredRenderer(DocstringRendererProtocol):
    def render(self, docstring_ir: DocstringIR) -> str:
        blocks = []

        if docstring_ir.summary:
            blocks.append(docstring_ir.summary)

        if docstring_ir.extended:
            blocks.append(docstring_ir.extended)

        for section in docstring_ir.sections:
            rendered_section = self._render_section(section)
            if rendered_section:
                blocks.append(rendered_section)

        # Join blocks with an empty line between them
        return "\n\n".join(blocks)

    def _render_section(self, section: DocstringSection) -> str:
        raise NotImplementedError
    
    def _get_default_title(self, kind: str) -> str:
        return ""


class GoogleDocstringRenderer(BaseStructuredRenderer):
    def _get_default_title(self, kind: str) -> str:
        mapping = {
            "parameters": "Args",
            "returns": "Returns",
            "raises": "Raises",
            "yields": "Yields",
            "attributes": "Attributes",
        }
        return mapping.get(kind, "")

    def _render_section(self, section: DocstringSection) -> str:
        lines = []
        title = section.title or self._get_default_title(section.kind)
        
        if title:
            lines.append(f"{title}:")
        
        if section.kind == "text" or section.kind == "admonition":
             # Text content: Indent body
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/renderers.py
~~~~~
~~~~~python.old
class NumpyDocstringRenderer(BaseStructuredRenderer):
    def _render_section(self, section: DocstringSection) -> str:
        lines = []
        
        # NumPy Style:
        # Title
        # -----
        if section.title:
            lines.append(section.title)
            lines.append("-" * len(section.title))

        if section.kind == "text" or section.kind == "admonition":
~~~~~
~~~~~python.new
class NumpyDocstringRenderer(BaseStructuredRenderer):
    def _get_default_title(self, kind: str) -> str:
        mapping = {
            "parameters": "Parameters",
            "returns": "Returns",
            "raises": "Raises",
            "yields": "Yields",
            "attributes": "Attributes",
        }
        return mapping.get(kind, "")

    def _render_section(self, section: DocstringSection) -> str:
        lines = []
        title = section.title or self._get_default_title(section.kind)
        
        # NumPy Style:
        # Title
        # -----
        if title:
            lines.append(title)
            lines.append("-" * len(title))

        if section.kind == "text" or section.kind == "admonition":
~~~~~

#### Acts 2: 修正 Parser 测试

我们将更新 `test_parsers.py`，断言 `title` 为 `None`，并验证 `kind` 是否正确。

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/docstring/test_parsers.py
~~~~~
~~~~~python.old
        args_section = next(s for s in ir.sections if s.kind == "parameters")
        assert args_section.title == "Args"
        assert len(args_section.content) == 2
        assert args_section.content[0].name == "x"
~~~~~
~~~~~python.new
        args_section = next(s for s in ir.sections if s.kind == "parameters")
        # Griffe parses standard headers into kind, leaving title as None
        assert args_section.title is None
        assert len(args_section.content) == 2
        assert args_section.content[0].name == "x"
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/docstring/test_parsers.py
~~~~~
~~~~~python.old
        assert ir.summary == "Summary line."
        
        args_section = next(s for s in ir.sections if s.kind == "parameters")
        assert args_section.title == "Parameters"
        assert args_section.content[0].name == "x"
        assert args_section.content[0].annotation == "int"
~~~~~
~~~~~python.new
        assert ir.summary == "Summary line."
        
        args_section = next(s for s in ir.sections if s.kind == "parameters")
        # Griffe parses standard headers into kind, leaving title as None
        assert args_section.title is None
        assert args_section.content[0].name == "x"
        assert args_section.content[0].annotation == "int"
~~~~~

#### Acts 3: 增强 Renderer 测试

我们将更新 `test_renderers.py`，增加一个测试用例，明确验证当 `title` 为 `None` 时，渲染器是否能正确输出默认标题。

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/docstring/test_renderers.py
~~~~~
~~~~~python.old
class TestGoogleDocstringRenderer:
    def test_render_google(self, sample_ir):
        renderer = GoogleDocstringRenderer()
        output = renderer.render(sample_ir)
        
        expected = """Summary line.

Extended description.

Args:
    x (int): The x value.
    y: The y value.

Returns:
    bool: True if success."""
        
        assert output.strip() == expected.strip()


class TestNumpyDocstringRenderer:
    def test_render_numpy(self, sample_ir):
        # Adjust titles for Numpy conventions
        sample_ir.sections[0].title = "Parameters" 
        sample_ir.sections[1].title = "Returns" 

        renderer = NumpyDocstringRenderer()
        output = renderer.render(sample_ir)
        
        expected = """Summary line.

Extended description.

Parameters
----------
x : int
    The x value.
y
    The y value.

Returns
-------
bool
    True if success."""
        
        assert output.strip() == expected.strip()
~~~~~
~~~~~python.new
class TestGoogleDocstringRenderer:
    def test_render_google(self, sample_ir):
        # Ensure we test the default title generation logic by unsetting titles
        for section in sample_ir.sections:
            section.title = None

        renderer = GoogleDocstringRenderer()
        output = renderer.render(sample_ir)
        
        expected = """Summary line.

Extended description.

Args:
    x (int): The x value.
    y: The y value.

Returns:
    bool: True if success."""
        
        assert output.strip() == expected.strip()


class TestNumpyDocstringRenderer:
    def test_render_numpy(self, sample_ir):
        # Ensure we test the default title generation logic by unsetting titles
        for section in sample_ir.sections:
            section.title = None

        renderer = NumpyDocstringRenderer()
        output = renderer.render(sample_ir)
        
        expected = """Summary line.

Extended description.

Parameters
----------
x : int
    The x value.
y
    The y value.

Returns
-------
bool
    True if success."""
        
        assert output.strip() == expected.strip()
~~~~~

### 下一步建议

测试通过后，我们将完成“阶段 1”。届时我们可以推进到 **阶段 2: 存储层升级**，将这些 IR 结构化地存储到 YAML 中。
