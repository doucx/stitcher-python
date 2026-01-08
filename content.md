[简要回答]
我们将通过引入 `DocstringSerializerProtocol` 及其具体实现（Google/NumPy），将 YAML 存储结构升级为 Style-Aware 模式，实现“所见即所得”的文档编辑体验。

## [WIP] feat: 实施存储层升级 (Phase 2) - 基础设施与序列化器

### 用户需求
用户希望 `stitcher` 的 YAML 存储文件能够根据配置的文档风格（Google/NumPy），呈现出符合该风格直觉的结构（如使用 `Parameters` 而非通用的 `Args`），从而提供更好的编辑体验（DX），而不是强制使用一套统一的机器 Schema。

### 评论
这是一个关键的架构调整。原计划的“统一 Schema”虽然对机器友好，但牺牲了可读性和直觉性。通过引入策略模式的 Serializer，我们可以在保持内部 IR 统一的同时，让存储层展现出多态性，真正做到以开发者为中心。

### 目标
1.  在 `stitcher-spec` 中定义 `SectionKind` 枚举和 `DocstringSerializerProtocol` 协议。
2.  在 `stitcher-python-adapter` 中实现 `Raw`, `Google`, `Numpy` 三种 Serializer。
3.  在 Serializer 中实现类型信息的字符串编码策略（`(type) description`），以在保持 YAML 简洁的同时支持类型信息的持久化。

### 基本原理
我们将采用 **Strategy Pattern**。`DocumentManager` 不再硬编码序列化逻辑，而是通过 `DocstringSerializerProtocol` 委托给具体的实现。
-   **Style-Aware**: `GoogleSerializer` 会将 Parameters 映射为 `Args`，`NumpySerializer` 映射为 `Parameters`。
-   **Lossless**: 通过在 Value 字符串中编码类型（`(Type) Description`），我们解决了 YAML 简洁性与信息完整性的冲突。
-   **Plugin-Ready**: 所有 Serializer 都将无条件透传 `Addon.*` 字段，确保插件数据的持久化。

### 标签
#intent/architect #intent/build #flow/ready #priority/high
#comp/spec #comp/adapter #concept/docstring #concept/storage
#task/domain/storage #task/object/docstring-serializer #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 更新 Spec (SectionKind & Protocols)

首先，我们在 Spec 中定义必要的枚举和协议，为序列化器提供契约。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/docstring.py
~~~~~
~~~~~python.old
@dataclass
class DocstringSection:
    """Represents a section of a docstring, like 'Args' or 'Returns'."""

    kind: str  # e.g., "params", "returns", "raises", "text"
    title: Optional[str] = None  # The rendered title, e.g., "Parameters"
    content: Union[str, List["DocstringItem"]] = ""
~~~~~
~~~~~python.new
class SectionKind(str, Enum):
    TEXT = "text"
    PARAMETERS = "parameters"
    RETURNS = "returns"
    RAISES = "raises"
    YIELDS = "yields"
    ATTRIBUTES = "attributes"
    EXAMPLES = "examples"
    NOTES = "notes"
    WARNING = "warning"
    SEE_ALSO = "see_also"
    ADMONITION = "admonition"


@dataclass
class DocstringSection:
    """Represents a section of a docstring, like 'Args' or 'Returns'."""

    kind: str  # Should use SectionKind values
    title: Optional[str] = None  # The rendered title, e.g., "Parameters"
    content: Union[str, List["DocstringItem"]] = ""
~~~~~

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
    def render(self, docstring_ir: DocstringIR) -> str: ...


class DocstringSerializerProtocol(Protocol):
    def to_yaml(self, ir: DocstringIR) -> Dict[str, Any]: ...

    def from_yaml(self, data: Union[str, Dict[str, Any]]) -> DocstringIR: ...
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
from .docstring import DocstringIR, DocstringSection, DocstringItem
from .models import (
    Argument,
~~~~~
~~~~~python.new
from .docstring import DocstringIR, DocstringSection, DocstringItem, SectionKind
from .models import (
    Argument,
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
    StubGeneratorProtocol,
    DocstringParserProtocol,
    DocstringRendererProtocol,
)

__all__ = [
    "DocstringIR",
    "DocstringSection",
    "DocstringItem",
    "LanguageParserProtocol",
    "LanguageTransformerProtocol",
    "FingerprintStrategyProtocol",
    "StubGeneratorProtocol",
    "DocstringParserProtocol",
    "DocstringRendererProtocol",
    "Fingerprint",
~~~~~
~~~~~python.new
    StubGeneratorProtocol,
    DocstringParserProtocol,
    DocstringRendererProtocol,
    DocstringSerializerProtocol,
)

__all__ = [
    "DocstringIR",
    "DocstringSection",
    "DocstringItem",
    "SectionKind",
    "LanguageParserProtocol",
    "LanguageTransformerProtocol",
    "FingerprintStrategyProtocol",
    "StubGeneratorProtocol",
    "DocstringParserProtocol",
    "DocstringRendererProtocol",
    "DocstringSerializerProtocol",
    "Fingerprint",
~~~~~

#### Acts 2: 实现 Serializers

现在我们在 Adapter 层实现具体的序列化逻辑。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/serializers.py
~~~~~
~~~~~python
import re
from typing import Dict, Any, Union, List, Optional
from stitcher.spec import (
    DocstringIR,
    DocstringSection,
    DocstringItem,
    DocstringSerializerProtocol,
    SectionKind,
)


class BaseSerializer(DocstringSerializerProtocol):
    """
    Base serializer that handles Addon preservation and common utilities.
    """

    def _extract_addons(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in data.items() if k.startswith("Addon.")}

    def _encode_item_value(self, item: DocstringItem) -> str:
        """
        Encodes DocstringItem into a string format: "(type) description".
        """
        desc = item.description or ""
        if item.annotation:
            return f"({item.annotation}) {desc}"
        return desc

    def _decode_item_value(self, value: str) -> dict:
        """
        Decodes string format "(type) description" into parts.
        """
        # Simple regex to catch (type) at the start
        match = re.match(r"^\((.+?)\)\s*(.*)", value, re.DOTALL)
        if match:
            return {"annotation": match.group(1), "description": match.group(2)}
        return {"annotation": None, "description": value}

    def to_yaml(self, ir: DocstringIR) -> Dict[str, Any]:
        raise NotImplementedError

    def from_yaml(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        raise NotImplementedError


class RawSerializer(BaseSerializer):
    """
    Legacy serializer.
    Format:
        "summary string"
    OR
        {"Raw": "summary string", "Addon...": ...}
    """

    def to_yaml(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]:
        summary = ir.summary or ""
        if ir.addons:
            data = {"Raw": summary}
            data.update(ir.addons)
            return data
        return summary

    def from_yaml(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        if isinstance(data, str):
            return DocstringIR(summary=data)
        
        ir = DocstringIR()
        if isinstance(data, dict):
            ir.summary = data.get("Raw", "")
            ir.addons = self._extract_addons(data)
        return ir


class StructuredSerializer(BaseSerializer):
    """
    Base class for Google/NumPy serializers.
    """
    
    # Maps SectionKind -> YAML Key (e.g. PARAMETERS -> Args)
    KIND_TO_KEY: Dict[str, str] = {}
    # Maps YAML Key -> SectionKind (e.g. Args -> PARAMETERS)
    KEY_TO_KIND: Dict[str, str] = {}

    def __init__(self):
        # Build reverse mapping automatically
        self.KEY_TO_KIND = {v: k for k, v in self.KIND_TO_KEY.items()}

    def to_yaml(self, ir: DocstringIR) -> Dict[str, Any]:
        data = {}
        
        if ir.summary:
            data["Summary"] = ir.summary
        
        if ir.extended:
            data["Extended"] = ir.extended

        for section in ir.sections:
            key = self.KIND_TO_KEY.get(section.kind)
            if not key:
                # Fallback for unknown sections: use title or capitalized kind
                key = section.title or section.kind.capitalize()
            
            if isinstance(section.content, str):
                data[key] = section.content
            elif isinstance(section.content, list):
                # Dict[name, encoded_value]
                section_data = {}
                for item in section.content:
                    # If item has no name (e.g. Returns/Raises), we need a strategy.
                    # For Returns/Raises, Google/NumPy style often puts type as name or key.
                    # We use item.annotation as key if name is missing?
                    # Or just a list? YAML dicts are better.
                    
                    k = item.name
                    if not k:
                         # Fallback for return/raises where name might be empty but annotation exists
                         k = item.annotation or "return" # Fallback key
                         
                    section_data[k] = self._encode_item_value(item)
                
                data[key] = section_data

        if ir.addons:
            data.update(ir.addons)
            
        return data

    def from_yaml(self, data: Union[str, Dict[str, Any]]) -> DocstringIR:
        # Graceful fallback if data is just a string (User switched from Raw to Structured)
        if isinstance(data, str):
             return DocstringIR(summary=data)

        ir = DocstringIR()
        ir.addons = self._extract_addons(data)
        
        ir.summary = data.get("Summary")
        ir.extended = data.get("Extended")
        
        for key, value in data.items():
            if key in ["Summary", "Extended"] or key.startswith("Addon."):
                continue
            
            kind = self.KEY_TO_KIND.get(key, SectionKind.TEXT) # Default to text if unknown key
            
            # Heuristic: If it's a dict, parse as items. If string, parse as text content.
            if isinstance(value, dict):
                items = []
                for name, content in value.items():
                    decoded = self._decode_item_value(str(content))
                    
                    # Reconstruction logic
                    item = DocstringItem(description=decoded["description"])
                    
                    if kind in [SectionKind.RETURNS, SectionKind.YIELDS, SectionKind.RAISES]:
                         # For these, the 'key' in YAML usually represents the Type/Exception
                         # We stored it as 'name' in section_data above for persistence
                         # But semantically it maps to annotation for Returns/Raises
                         item.annotation = name
                         # item.name remains None
                    else:
                         item.name = name
                         if decoded["annotation"]:
                             item.annotation = decoded["annotation"]
                    
                    items.append(item)
                
                ir.sections.append(DocstringSection(kind=kind, content=items))
            
            elif isinstance(value, str):
                ir.sections.append(DocstringSection(kind=kind, content=value))

        return ir


class GoogleSerializer(StructuredSerializer):
    KIND_TO_KEY = {
        SectionKind.PARAMETERS: "Args",
        SectionKind.RETURNS: "Returns",
        SectionKind.RAISES: "Raises",
        SectionKind.YIELDS: "Yields",
        SectionKind.ATTRIBUTES: "Attributes",
        SectionKind.EXAMPLES: "Examples",
        SectionKind.NOTES: "Notes",
        SectionKind.WARNING: "Warning",
    }


class NumpySerializer(StructuredSerializer):
    KIND_TO_KEY = {
        SectionKind.PARAMETERS: "Parameters",
        SectionKind.RETURNS: "Returns",
        SectionKind.RAISES: "Raises",
        SectionKind.YIELDS: "Yields",
        SectionKind.ATTRIBUTES: "Attributes",
        SectionKind.EXAMPLES: "Examples",
        SectionKind.NOTES: "Notes",
        SectionKind.WARNING: "Warning",
        SectionKind.SEE_ALSO: "See Also",
    }
~~~~~

#### Acts 3: 注册 Serializers

更新 Factory，使其能返回 Serializer。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/factory.py
~~~~~
~~~~~python.old
from .parsers import RawDocstringParser, GriffeDocstringParser
from .renderers import GoogleDocstringRenderer, NumpyDocstringRenderer


class RawDocstringRenderer(DocstringRendererProtocol):
~~~~~
~~~~~python.new
from .parsers import RawDocstringParser, GriffeDocstringParser
from .renderers import GoogleDocstringRenderer, NumpyDocstringRenderer
from .serializers import (
    RawSerializer,
    GoogleSerializer,
    NumpySerializer,
)
from stitcher.spec import DocstringSerializerProtocol


class RawDocstringRenderer(DocstringRendererProtocol):
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/factory.py
~~~~~
~~~~~python.old
    
    # Default to raw
    return RawDocstringParser(), RawDocstringRenderer()
~~~~~
~~~~~python.new
    
    # Default to raw
    return RawDocstringParser(), RawDocstringRenderer()


def get_docstring_serializer(style: str) -> DocstringSerializerProtocol:
    """
    Factory to get the serializer for a specific docstring style.
    """
    if style == "google":
        return GoogleSerializer()
    elif style == "numpy":
        return NumpySerializer()

    # Default to raw
    return RawSerializer()
~~~~~

#### Acts 4: 导出 Symbols

最后，更新 `__init__.py` 导出新组件。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/__init__.py
~~~~~
~~~~~python.old
from .parsers import RawDocstringParser, GriffeDocstringParser
from .renderers import GoogleDocstringRenderer, NumpyDocstringRenderer
from .factory import get_docstring_codec

__all__ = [
    "RawDocstringParser",
    "GriffeDocstringParser",
    "GoogleDocstringRenderer",
    "NumpyDocstringRenderer",
    "get_docstring_codec",
]
~~~~~
~~~~~python.new
from .parsers import RawDocstringParser, GriffeDocstringParser
from .renderers import GoogleDocstringRenderer, NumpyDocstringRenderer
from .serializers import RawSerializer, GoogleSerializer, NumpySerializer
from .factory import get_docstring_codec, get_docstring_serializer

__all__ = [
    "RawDocstringParser",
    "GriffeDocstringParser",
    "GoogleDocstringRenderer",
    "NumpyDocstringRenderer",
    "RawSerializer",
    "GoogleSerializer",
    "NumpySerializer",
    "get_docstring_codec",
    "get_docstring_serializer",
]
~~~~~

### 下一步建议

基础设施现已就绪。下一步是 **Plan 2: 应用层集成**，我们需要在 `stitcher-application` 中重构 `DocumentManager`，使其根据配置调用这些 Serializer，并进行端到端的验证。这将正式启用 Style-Aware 的存储能力。
