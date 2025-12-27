好的，我们正式进入 Phase 3。在这个阶段，我们将构建 `Needle` 生态的“大脑”——`OverlayNexus`。这是一个纯粹的、与 I/O 解耦的运行时引擎，它通过逻辑层叠（Logical Overlay）的方式，优雅地解决了数据来源和优先级的问题。

## [WIP] feat: 创建 pyneedle-nexus 并实现 Overlay 引擎

### 用户需求
创建 `pyneedle-nexus` 包，实现一个基于 `collections.ChainMap` 的 `OverlayNexus` 运行时。它必须：
1.  依赖于 `pyneedle-spec` 中定义的协议。
2.  管理一个有序的 `ResourceLoaderProtocol` 列表，列表顺序代表优先级。
3.  按需加载并缓存每个语言的资源视图，避免不必要的 I/O。
4.  包含一个 `MemoryLoader` 用于测试和动态数据注入。

### 评论
这是 `Needle` 架构从一个简单的“物理合并”模型向一个高度可追溯、可测试的“逻辑层叠”模型的关键转变。`OverlayNexus` 的设计将使我们能够清晰地看到数据是如何被覆盖的（例如，用户配置 > 项目默认 > 库内置），并且通过注入 `MemoryLoader`，我们可以对业务逻辑进行完全隔离的、闪电般快速的单元测试。

### 目标
1.  创建 `packages/pyneedle-nexus` 的包结构和 `pyproject.toml`。
2.  实现 `MemoryLoader`，一个用于测试的、基于内存的加载器。
3.  实现 `OverlayNexus`，核心的运行时引擎，使用 `ChainMap` 管理加载器。
4.  确保 `OverlayNexus` 完全遵循 `NexusProtocol` 契约。

### 基本原理
*   **`collections.ChainMap`**: 这是实现逻辑层叠的理想工具。它将多个字典链接成一个单一的可更新视图。当查找一个键时，`ChainMap` 会按顺序搜索每个字典，直到找到为止。这完美地映射了我们的优先级需求，且无需进行昂贵的物理字典合并。
*   **协议驱动**: `OverlayNexus` 只与 `ResourceLoaderProtocol` 交互，它不关心数据是来自文件、内存还是网络。这种设计使得整个系统极具扩展性。
*   **懒加载与缓存**: 只有在首次请求某种语言时，`Nexus` 才会触发所有加载器加载该语言的资源并构建 `ChainMap` 视图。该视图随后被缓存，后续对该语言的 `get` 调用将直接命中缓存，性能极高。

### 标签
#intent/build #flow/ready #priority/high
#comp/runtime #concept/state #scope/core
#task/domain/runtime #task/object/pyneedle-nexus #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 初始化包结构和配置
创建目录和 `pyproject.toml`，并声明对 `pyneedle-spec` 的依赖。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/pyneedle-nexus/src/needle/nexus
~~~~~

~~~~~act
write_file
packages/pyneedle-nexus/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyneedle-nexus"
version = "0.1.0"
description = "Layered overlay runtime (Nexus) for the PyNeedle ecosystem."
requires-python = ">=3.10"
dependencies = [
    "pyneedle-spec",
]

[tool.hatch.build.targets.wheel]
packages = ["src/needle"]

[tool.uv.sources]
pyneedle-spec = { workspace = true }
~~~~~

#### Acts 2: 实现 MemoryLoader
这是一个用于测试和动态注入数据的简单加载器。

~~~~~act
write_file
packages/pyneedle-nexus/src/needle/nexus/loaders.py
~~~~~
~~~~~python
from typing import Dict, Any
from needle.spec import ResourceLoaderProtocol


class MemoryLoader(ResourceLoaderProtocol):
    """
    A resource loader that sources data from an in-memory dictionary.

    Ideal for testing, dynamic configuration, or runtime overrides.
    """

    def __init__(self, data: Dict[str, Dict[str, Any]]):
        """
        Initializes the loader with data.

        Args:
            data: A dictionary where keys are language codes and values are
                  dictionaries of FQN -> value.
                  e.g., {"en": {"app.title": "My App"}}
        """
        self._data = data

    def load(self, lang: str) -> Dict[str, Any]:
        """
        Loads resources for a specific language from memory.
        """
        return self._data.get(lang, {})
~~~~~

#### Acts 3: 实现 OverlayNexus 引擎
这是 `Needle` 的核心运行时逻辑。

~~~~~act
write_file
packages/pyneedle-nexus/src/needle/nexus/nexus.py
~~~~~
~~~~~python
import os
from collections import ChainMap
from typing import List, Dict, Optional, Union, Any
from needle.spec import NexusProtocol, ResourceLoaderProtocol, SemanticPointerProtocol


class OverlayNexus(NexusProtocol):
    """
    Standard implementation of the Nexus protocol using a logical overlay strategy.

    It manages an ordered list of resource loaders and uses `collections.ChainMap`
    to create prioritized, logical views of resources without performing
    a physical merge.
    """

    def __init__(self, loaders: List[ResourceLoaderProtocol], default_lang: str = "en"):
        """
        Initializes the Nexus with a list of loaders.

        Args:
            loaders: A list of resource loaders. The order determines priority;
                     loaders at the beginning of the list override those at the end.
            default_lang: The fallback language to use if the target language is not found.
        """
        self.loaders = loaders
        self.default_lang = default_lang
        self._views: Dict[str, ChainMap[str, Any]] = {}

    def _get_or_create_view(self, lang: str) -> ChainMap[str, Any]:
        """
        Lazily loads and caches the ChainMap view for a given language.
        """
        if lang not in self._views:
            # Trigger load() on all loaders for the requested language.
            # The list comprehension creates a list of dictionaries.
            # The order of `self.loaders` is preserved, which is crucial for ChainMap.
            maps = [loader.load(lang) for loader in self.loaders]
            self._views[lang] = ChainMap(*maps)
        return self._views[lang]

    def _resolve_lang(self, explicit_lang: Optional[str] = None) -> str:
        """
        Determines the current language based on a standard hierarchy.
        """
        if explicit_lang:
            return explicit_lang

        stitcher_lang = os.getenv("STITCHER_LANG") or os.getenv("NEEDLE_LANG")
        if stitcher_lang:
            return stitcher_lang

        system_lang = os.getenv("LANG")
        if system_lang:
            return system_lang.split("_")[0].split(".")[0].lower()

        return self.default_lang

    def get(
        self, pointer: Union[str, SemanticPointerProtocol], lang: Optional[str] = None
    ) -> str:
        """
        Resolves a semantic pointer to a string value with graceful fallback.
        """
        key = str(pointer)
        target_lang = self._resolve_lang(lang)

        # 1. Try target language
        target_view = self._get_or_create_view(target_lang)
        value = target_view.get(key)
        if value is not None:
            return str(value)

        # 2. Try default language (if different)
        if target_lang != self.default_lang:
            default_view = self._get_or_create_view(self.default_lang)
            value = default_view.get(key)
            if value is not None:
                return str(value)

        # 3. Fallback to Identity
        return key

    def reload(self, lang: Optional[str] = None) -> None:
        """
        Clears internal caches to force a reload on the next `get` call.
        """
        if lang:
            self._views.pop(lang, None)
        else:
            self._views.clear()
~~~~~

#### Acts 4: 导出公共 API
创建 `__init__.py` 并导出关键类。

~~~~~act
write_file
packages/pyneedle-nexus/src/needle/nexus/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .nexus import OverlayNexus
from .loaders import MemoryLoader

__all__ = ["OverlayNexus", "MemoryLoader"]
~~~~~

### 下一步建议
我们已经构建了 `Needle` 生态的纯逻辑核心。它现在拥有了处理指针代数的能力 (`pyneedle-pointer`) 和一个可测试的、分层的运行时引擎 (`pyneedle-nexus`)。

最后一步是 **Phase 4: 电池组装 (pyneedle)**。在这个阶段，我们将创建一个顶层 `pyneedle` 包，它会：
1.  把所有这些组件组装在一起。
2.  实现 `FileSystemLoader`，让 `Nexus` 能够从磁盘读取真实的文件。
3.  提供一个开箱即用的全局 `needle` 实例，供最终用户方便地导入和使用。
