非常抱歉，在之前的执行块中我遗漏了 `patch_file` 指令所需的 `old` 和 `new` 内容块，导致执行失败。

我现在将重新生成完整的、符合规范的计划，并补全所有缺失的对比块，以确保阶段 3 的顺利实施。

## [WIP] feat: 补全结构化文档渲染管线实施计划

### 用户需求
完成“结构化文档支持”路线图的阶段 3，实现代码类型信息与 YAML 描述内容的动态合并渲染。

### 评论
由于之前的操作指令不完整，导致协议层和逻辑层的修改未能成功落地。本次计划将严格遵循 `patch_file` 策略，精确修改相关文件，打通从 `DocstringIR` 到最终风格化字符串的链路。

### 目标
1.  **协议对齐**: 更新 `DocstringRendererProtocol` 以支持上下文感知。
2.  **数据下钻**: 在 `DocumentManager` 中实现 `DocstringIR` 向 IR 树的深度注入。
3.  **生成器改造**: 使 `StubGenerator` 具备调用渲染器处理 `DocstringIR` 的能力。
4.  **智能渲染**: 实现 `Google` 和 `NumPy` 风格下，类型（来自代码）与描述（来自 YAML）的自动缝合。

### 标签
#intent/build #flow/ready #priority/high #comp/spec #comp/application #comp/adapter #concept/docstring #scope/core #task/domain/docstring #task/object/rendering-pipeline #task/action/integration #task/state/continue

---

### Script

#### Acts 1: 更新协议 (spec)
修改协议定义，使 `render` 方法能够接收上下文对象。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python.old
class DocstringRendererProtocol(Protocol):
    def render(self, docstring_ir: DocstringIR) -> str: ...
~~~~~
~~~~~python.new
class DocstringRendererProtocol(Protocol):
    def render(
        self,
        docstring_ir: DocstringIR,
        context: Optional[Union[FunctionDef, ClassDef, ModuleDef]] = None,
    ) -> str: ...
~~~~~

#### Acts 2: 注入 IR 到 Module 树 (application)
修改 `DocumentManager`，确保在加载文档时，不仅更新摘要字符串，还将整个 `DocstringIR` 注入到对应的定义对象中。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def _apply_to_function(
        self, func: FunctionDef, docs: Dict[str, DocstringIR], prefix: str = ""
    ):
        full_name = f"{prefix}{func.name}"
        if full_name in docs:
            # Injecting back to code: we only care about the summary (content)
            func.docstring = docs[full_name].summary

    def _apply_to_class(
        self, cls: ClassDef, docs: Dict[str, DocstringIR], prefix: str = ""
    ):
        full_name = f"{prefix}{cls.name}"
        if full_name in docs:
            cls.docstring = docs[full_name].summary
        for method in cls.methods:
            self._apply_to_function(method, docs, prefix=f"{full_name}.")
        for attr in cls.attributes:
            attr_key = f"{full_name}.{attr.name}"
            if attr_key in docs:
                attr.docstring = docs[attr_key].summary

    def apply_docs_to_module(self, module: ModuleDef) -> None:
        docs = self.load_docs_for_module(module)
        if not docs:
            return
        if "__doc__" in docs:
            module.docstring = docs["__doc__"].summary
        for func in module.functions:
            self._apply_to_function(func, docs)
        for cls in module.classes:
            self._apply_to_class(cls, docs)
        for attr in module.attributes:
            if attr.name in docs:
                attr.docstring = docs[attr.name].summary
~~~~~
~~~~~python.new
    def _apply_to_function(
        self, func: FunctionDef, docs: Dict[str, DocstringIR], prefix: str = ""
    ):
        full_name = f"{prefix}{func.name}"
        if full_name in docs:
            # Injecting back to code: we only care about the summary (content)
            func.docstring = docs[full_name].summary
            func.docstring_ir = docs[full_name]

    def _apply_to_class(
        self, cls: ClassDef, docs: Dict[str, DocstringIR], prefix: str = ""
    ):
        full_name = f"{prefix}{cls.name}"
        if full_name in docs:
            cls.docstring = docs[full_name].summary
            cls.docstring_ir = docs[full_name]
        for method in cls.methods:
            self._apply_to_function(method, docs, prefix=f"{full_name}.")
        for attr in cls.attributes:
            attr_key = f"{full_name}.{attr.name}"
            if attr_key in docs:
                attr.docstring = docs[attr_key].summary

    def apply_docs_to_module(self, module: ModuleDef) -> None:
        docs = self.load_docs_for_module(module)
        if not docs:
            return
        if "__doc__" in docs:
            module.docstring = docs["__doc__"].summary
            module.docstring_ir = docs["__doc__"]
        for func in module.functions:
            self._apply_to_function(func, docs)
        for cls in module.classes:
            self._apply_to_class(cls, docs)
        for attr in module.attributes:
            if attr.name in docs:
                attr.docstring = docs[attr.name].summary
~~~~~

#### Acts 3: 改造内部生成器以支持渲染 (adapter)
修改 Python 的 `.pyi` 生成器，使其优先尝试使用渲染器。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/stub_generator.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
)
from stitcher.common import format_docstring


class StubGenerator:
    def __init__(self, indent_spaces: int = 4):
        self._indent_str = " " * indent_spaces

    def generate(self, module: ModuleDef) -> str:
        lines = []

        # 1. Module Docstring
        if module.docstring:
            # format_docstring returns the literal without starting indent, so we prepend it.
            # For module level (level 0), indent is empty string, but consistent logic applies.
            formatted = format_docstring(module.docstring, self._indent(0))
            lines.append(f"{self._indent(0)}{formatted}")
            lines.append("")  # Empty line after docstring
~~~~~
~~~~~python.new
from typing import Optional
from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
    DocstringRendererProtocol,
)
from stitcher.common import format_docstring


class StubGenerator:
    def __init__(self, indent_spaces: int = 4):
        self._indent_str = " " * indent_spaces
        self._renderer: Optional[DocstringRendererProtocol] = None

    def set_renderer(self, renderer: DocstringRendererProtocol) -> None:
        self._renderer = renderer

    def generate(self, module: ModuleDef) -> str:
        lines = []

        # 1. Module Docstring
        doc_content = None
        if module.docstring_ir and self._renderer:
            doc_content = self._renderer.render(module.docstring_ir, context=module)
        elif module.docstring:
            doc_content = module.docstring

        if doc_content:
            formatted = format_docstring(doc_content, self._indent(0))
            lines.append(f"{self._indent(0)}{formatted}")
            lines.append("")  # Empty line after docstring
~~~~~

继续修改函数和类的生成逻辑：

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/stub_generator.py
~~~~~
~~~~~python.old
        # Body
        if func.docstring:
            lines.append(def_line)
            formatted = format_docstring(func.docstring, self._indent(level + 1))
            lines.append(f"{self._indent(level + 1)}{formatted}")
            lines.append(f"{self._indent(level + 1)}...")
        else:
~~~~~
~~~~~python.new
        # Body
        doc_content = None
        if func.docstring_ir and self._renderer:
            doc_content = self._renderer.render(func.docstring_ir, context=func)
        elif func.docstring:
            doc_content = func.docstring

        if doc_content:
            lines.append(def_line)
            formatted = format_docstring(doc_content, self._indent(level + 1))
            lines.append(f"{self._indent(level + 1)}{formatted}")
            lines.append(f"{self._indent(level + 1)}...")
        else:
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/stub_generator.py
~~~~~
~~~~~python.old
        # Body
        has_content = False

        # Docstring
        if cls.docstring:
            formatted = format_docstring(cls.docstring, self._indent(level + 1))
            lines.append(f"{self._indent(level + 1)}{formatted}")
            has_content = True
~~~~~
~~~~~python.new
        # Body
        has_content = False

        # Docstring
        doc_content = None
        if cls.docstring_ir and self._renderer:
            doc_content = self._renderer.render(cls.docstring_ir, context=cls)
        elif cls.docstring:
            doc_content = cls.docstring

        if doc_content:
            formatted = format_docstring(doc_content, self._indent(level + 1))
            lines.append(f"{self._indent(level + 1)}{formatted}")
            has_content = True
~~~~~

#### Acts 4: 暴露渲染器设置接口 (adapter)
在适配器外层暴露 `set_renderer` 方法。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/generator.py
~~~~~
~~~~~python.old
from stitcher.spec import ModuleDef
from .internal.stub_generator import StubGenerator


class PythonStubGenerator:
    def __init__(self):
        self._delegate = StubGenerator()

    def generate(self, module: ModuleDef) -> str:
        return self._delegate.generate(module)
~~~~~
~~~~~python.new
from stitcher.spec import ModuleDef, DocstringRendererProtocol
from .internal.stub_generator import StubGenerator


class PythonStubGenerator:
    def __init__(self):
        self._delegate = StubGenerator()

    def set_renderer(self, renderer: DocstringRendererProtocol) -> None:
        self._delegate.set_renderer(renderer)

    def generate(self, module: ModuleDef) -> str:
        return self._delegate.generate(module)
~~~~~

#### Acts 5: 装配渲染器 (application)
在 `StitcherApp` 中，根据配置获取渲染器并注入到生成器中。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        # Configure Docstring Strategy
        parser, _ = get_docstring_codec(config.docstring_style)
        serializer = get_docstring_serializer(config.docstring_style)
        self.doc_manager.set_strategy(parser, serializer)

        # Handle Plugins
~~~~~
~~~~~python.new
        # Configure Docstring Strategy
        parser, renderer = get_docstring_codec(config.docstring_style)
        serializer = get_docstring_serializer(config.docstring_style)
        self.doc_manager.set_strategy(parser, serializer)

        # Inject renderer into stub generator
        if hasattr(self.generate_runner.generator, "set_renderer"):
            self.generate_runner.generator.set_renderer(renderer)

        # Handle Plugins
~~~~~

#### Acts 6: 实现完整的结构化渲染逻辑 (adapter)
覆盖之前的占位文件，实现具有“合并类型”能力的 `Google` 和 `NumPy` 渲染器。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/renderers.py
~~~~~
~~~~~python
from typing import Optional, Union, List, cast
from stitcher.spec import (
    DocstringIR,
    DocstringSection,
    DocstringItem,
    DocstringRendererProtocol,
    FunctionDef,
    ClassDef,
    ModuleDef,
    SectionKind,
)


class BaseStructuredRenderer(DocstringRendererProtocol):
    def render(
        self,
        docstring_ir: DocstringIR,
        context: Optional[Union[FunctionDef, ClassDef, ModuleDef]] = None,
    ) -> str:
        blocks = []

        if docstring_ir.summary:
            blocks.append(docstring_ir.summary)

        if docstring_ir.extended:
            blocks.append(docstring_ir.extended)

        for section in docstring_ir.sections:
            rendered_section = self._render_section(section, context)
            if rendered_section:
                blocks.append(rendered_section)

        return "\n\n".join(blocks)

    def _render_section(
        self,
        section: DocstringSection,
        context: Optional[Union[FunctionDef, ClassDef, ModuleDef]],
    ) -> str:
        raise NotImplementedError

    def _get_default_title(self, kind: str) -> str:
        return ""

    def _merge_params_with_context(
        self, items: List[DocstringItem], context: Optional[Union[FunctionDef, ClassDef, ModuleDef]]
    ) -> List[DocstringItem]:
        if not isinstance(context, FunctionDef):
            return items

        item_map = {item.name: item for item in items if item.name}
        merged_items = []

        for arg in context.args:
            display_name = arg.name
            if arg.kind == "VAR_POSITIONAL":
                display_name = f"*{arg.name}"
            elif arg.kind == "VAR_KEYWORD":
                display_name = f"**{arg.name}"

            existing_item = item_map.get(display_name)
            if not existing_item and arg.name:
                existing_item = item_map.get(arg.name)

            description = existing_item.description if existing_item else ""

            merged_items.append(
                DocstringItem(
                    name=display_name,
                    annotation=arg.annotation,
                    description=description,
                    default=arg.default,
                )
            )
        return merged_items
    
    def _merge_returns_with_context(
        self, items: List[DocstringItem], context: Optional[Union[FunctionDef, ClassDef, ModuleDef]]
    ) -> List[DocstringItem]:
        if not isinstance(context, FunctionDef) or not context.return_annotation:
            return items
        
        new_items = []
        if items:
            for item in items:
                new_items.append(DocstringItem(
                    name=item.name,
                    annotation=context.return_annotation,
                    description=item.description
                ))
        return new_items if new_items else items


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

    def _render_section(
        self,
        section: DocstringSection,
        context: Optional[Union[FunctionDef, ClassDef, ModuleDef]],
    ) -> str:
        lines = []
        title = section.title or self._get_default_title(section.kind)

        content = section.content
        if isinstance(content, list):
            if section.kind == SectionKind.PARAMETERS:
                content = self._merge_params_with_context(cast(List[DocstringItem], content), context)
            elif section.kind == SectionKind.RETURNS:
                content = self._merge_returns_with_context(cast(List[DocstringItem], content), context)

        if title:
            lines.append(f"{title}:")

        if section.kind == SectionKind.TEXT or section.kind == SectionKind.ADMONITION:
            if isinstance(content, str):
                for line in content.splitlines():
                    lines.append(f"    {line}")
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, DocstringItem): continue
                prefix = ""
                if item.name:
                    prefix = f"{item.name}"
                    if item.annotation: prefix += f" ({item.annotation})"
                elif item.annotation:
                    prefix = f"{item.annotation}"

                if prefix:
                    lines.append(f"    {prefix}: {item.description}" if item.description else f"    {prefix}")
                elif item.description:
                    lines.append(f"    {item.description}")

        return "\n".join(lines)


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

    def _render_section(
        self,
        section: DocstringSection,
        context: Optional[Union[FunctionDef, ClassDef, ModuleDef]],
    ) -> str:
        lines = []
        title = section.title or self._get_default_title(section.kind)

        content = section.content
        if isinstance(content, list):
            if section.kind == SectionKind.PARAMETERS:
                content = self._merge_params_with_context(cast(List[DocstringItem], content), context)
            elif section.kind == SectionKind.RETURNS:
                content = self._merge_returns_with_context(cast(List[DocstringItem], content), context)

        if title:
            lines.append(title)
            lines.append("-" * len(title))

        if section.kind == SectionKind.TEXT or section.kind == SectionKind.ADMONITION:
            if isinstance(content, str):
                for line in content.splitlines(): lines.append(line)
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, DocstringItem): continue
                header = ""
                if item.name:
                    header = item.name
                    if item.annotation: header += f" : {item.annotation}"
                elif item.annotation:
                    header = item.annotation
                if header: lines.append(header)
                if item.description:
                    for line in item.description.splitlines(): lines.append(f"    {line}")

        return "\n".join(lines)
~~~~~

### 下一步建议
我们已经完成了阶段 3 的所有代码修改。接下来建议：
1.  **手动测试**: 在一个测试项目中配置 `docstring_style = "google"`，并运行 `stitcher generate`，验证生成的 `.pyi` 文件是否包含了正确的参数类型。
2.  **编写单元测试**: 针对 `renderers.py` 中的合并逻辑编写专门的测试用例。
3.  **准备阶段 4**: 进入最后的验证与交付阶段。
