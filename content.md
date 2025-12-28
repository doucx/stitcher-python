简要回答
我们已准备好实施 Needle Runtime v2 架构重构。

这将涉及引入正交化的三层加载模型（原语、组合、策略），通过新的 `BaseLoader` 基类统一回退策略，并更新所有现有加载器（`MemoryLoader`, `OverlayNexus`, `FileSystemLoader`）以遵循新的协议。这将彻底解决优先级倒置问题。

## [WIP] refactor(runtime): 实施 Needle Runtime v2 正交化加载器架构

### 目标
1.  **定义新协议**: 更新 `ResourceLoaderProtocol` 以包含 `fetch` (原语) 和 `get` (策略) 方法。
2.  **提取策略层**: 创建 `BaseLoader` 基类，集中处理语言回退和身份回退逻辑。
3.  **正交化实现**:
    *   重构 `MemoryLoader` 和 `FileSystemLoader` 以实现原语层接口 `fetch`。
    *   重构 `OverlayNexus` 专注于组合层逻辑（垂直回退）。
4.  **验证**: 确保新架构通过所有核心测试，并正确处理优先级。

### 基本原理
当前的 `Nexus` 承担了过多的职责（聚合、缓存、回退策略），导致了严重的优先级倒置问题（系统级默认语言可能覆盖项目级特定语言）。通过采用“正交化三层模型”，我们将 I/O、组合和策略彻底解耦，使得系统行为可预测、可扩展且更健壮。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #concept/executor #scope/core #ai/instruct
#task/domain/runtime #task/object/loader-architecture #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 更新核心协议 (Spec)

首先，我们更新规范以反映新的三层架构。`ResourceLoaderProtocol` 将成为所有加载器的核心契约。

~~~~~act
patch_file
packages/pyneedle-spec/src/needle/spec/protocols.py
~~~~~
~~~~~python.old
class ResourceLoaderProtocol(Protocol):
    def load(self, domain: str) -> Dict[str, Any]: ...


class WritableResourceLoaderProtocol(ResourceLoaderProtocol, Protocol):
~~~~~
~~~~~python.new
class ResourceLoaderProtocol(Protocol):
    def fetch(
        self, pointer: str, domain: str, ignore_cache: bool = False
    ) -> str | None: ...

    def get(
        self,
        pointer: Union[str, "SemanticPointerProtocol"],
        domain: str | None = None,
    ) -> str: ...

    def load(self, domain: str, ignore_cache: bool = False) -> Dict[str, Any]: ...


class WritableResourceLoaderProtocol(ResourceLoaderProtocol, Protocol):
~~~~~

~~~~~act
patch_file
packages/pyneedle-spec/src/needle/spec/protocols.py
~~~~~
~~~~~python.old
class NexusProtocol(ResourceLoaderProtocol, Protocol):
    def get(
        self, pointer: Union[str, SemanticPointerProtocol], domain: str | None = None
    ) -> str: ...

    def reload(self, domain: str | None = None) -> None: ...
~~~~~
~~~~~python.new
class NexusProtocol(ResourceLoaderProtocol, Protocol):
    def reload(self, domain: str | None = None) -> None: ...
~~~~~

#### Acts 2: 创建策略层基类 (BaseLoader)

我们在 `pyneedle-nexus` 中引入 `BaseLoader`。它实现了**策略层**的核心逻辑：语言回退和身份回退。所有加载器都将继承它。

~~~~~act
write_file
packages/pyneedle-nexus/src/needle/nexus/base.py
~~~~~
~~~~~python
import os
from typing import Optional, Union, Dict, Any, TYPE_CHECKING
from needle.spec import ResourceLoaderProtocol, SemanticPointerProtocol

if TYPE_CHECKING:
    pass


class BaseLoader(ResourceLoaderProtocol):
    """
    [Policy Layer]
    Implements the standard policy for language and identity fallback.
    All specific loaders should inherit from this class and implement the
    Primitive Layer `fetch` method.
    """

    def __init__(self, default_domain: str = "en"):
        self.default_domain = default_domain

    def fetch(
        self, pointer: str, domain: str, ignore_cache: bool = False
    ) -> Optional[str]:
        """
        [Primitive Layer]
        Must be implemented by subclasses.
        Performs an atomic lookup in the specified domain without any fallback.
        """
        raise NotImplementedError

    def load(self, domain: str, ignore_cache: bool = False) -> Dict[str, Any]:
        """
        [Utility]
        Must be implemented by subclasses.
        Returns the full view of resources for a domain.
        """
        raise NotImplementedError

    def _resolve_domain(self, explicit_domain: Optional[str] = None) -> str:
        if explicit_domain:
            return explicit_domain

        # Priority 1: NEEDLE_LANG
        needle_domain = os.getenv("NEEDLE_LANG")
        if needle_domain:
            return needle_domain

        # Priority 2: STITCHER_LANG (legacy compatibility)
        stitcher_domain = os.getenv("STITCHER_LANG")
        if stitcher_domain:
            return stitcher_domain

        # Priority 3: System LANG
        system_domain = os.getenv("LANG")
        if system_domain:
            return system_domain.split("_")[0].split(".")[0].lower()

        return self.default_domain

    def get(
        self,
        pointer: Union[str, SemanticPointerProtocol],
        domain: Optional[str] = None,
    ) -> str:
        """
        [Policy Layer Implementation]
        Orchestrates the fallback logic:
        1. Target Domain -> 2. Default Domain -> 3. Identity
        """
        key = str(pointer)
        target_domain = self._resolve_domain(domain)

        # 1. Try target domain
        value = self.fetch(key, target_domain)
        if value is not None:
            return value

        # 2. Try default domain (if different)
        if target_domain != self.default_domain:
            value = self.fetch(key, self.default_domain)
            if value is not None:
                return value

        # 3. Fallback to Identity
        return key
~~~~~

~~~~~act
patch_file
packages/pyneedle-nexus/src/needle/nexus/__init__.py
~~~~~
~~~~~python.old
from .nexus import OverlayNexus
from .loaders import MemoryLoader

__all__ = ["OverlayNexus", "MemoryLoader"]
~~~~~
~~~~~python.new
from .base import BaseLoader
from .nexus import OverlayNexus
from .loaders import MemoryLoader

__all__ = ["BaseLoader", "OverlayNexus", "MemoryLoader"]
~~~~~

#### Acts 3: 重构加载器 (MemoryLoader & OverlayNexus)

现在我们重构具体的加载器以继承 `BaseLoader` 并实现 `fetch`。

`MemoryLoader` 变得更简单，专注于内存查找。
`OverlayNexus` 专注于**组合层**（垂直回退），将策略逻辑委托给基类。

~~~~~act
patch_file
packages/pyneedle-nexus/src/needle/nexus/loaders.py
~~~~~
~~~~~python.old
from typing import Dict, Any
from needle.spec import ResourceLoaderProtocol


class MemoryLoader(ResourceLoaderProtocol):
    def __init__(self, data: Dict[str, Dict[str, Any]]):
        self._data = data

    def load(self, domain: str) -> Dict[str, Any]:
        # Return a copy to simulate I/O snapshotting and prevent
        # ChainMap from reflecting dynamic changes in source data immediately.
        return self._data.get(domain, {}).copy()
~~~~~
~~~~~python.new
from typing import Dict, Any, Optional
from .base import BaseLoader


class MemoryLoader(BaseLoader):
    def __init__(self, data: Dict[str, Dict[str, Any]], default_domain: str = "en"):
        super().__init__(default_domain)
        self._data = data

    def fetch(
        self, pointer: str, domain: str, ignore_cache: bool = False
    ) -> Optional[str]:
        # Atomic lookup in memory
        domain_data = self._data.get(domain)
        if domain_data:
            val = domain_data.get(pointer)
            if val is not None:
                return str(val)
        return None

    def load(self, domain: str, ignore_cache: bool = False) -> Dict[str, Any]:
        # Return a copy to simulate I/O snapshotting
        return self._data.get(domain, {}).copy()
~~~~~

~~~~~act
write_file
packages/pyneedle-nexus/src/needle/nexus/nexus.py
~~~~~
~~~~~python
from collections import ChainMap
from typing import List, Dict, Optional, Union, Any
from needle.spec import NexusProtocol, ResourceLoaderProtocol, SemanticPointerProtocol, WritableResourceLoaderProtocol
from .base import BaseLoader
from pathlib import Path


class OverlayNexus(BaseLoader, NexusProtocol):
    """
    [Composition Layer]
    Implements vertical fallback by iterating through a stack of loaders.
    Inherits policy logic (get) from BaseLoader.
    """

    def __init__(
        self, loaders: List[ResourceLoaderProtocol], default_domain: str = "en"
    ):
        super().__init__(default_domain)
        self.loaders = loaders
        self._views: Dict[str, ChainMap[str, Any]] = {}

    def fetch(
        self, pointer: str, domain: str, ignore_cache: bool = False
    ) -> Optional[str]:
        """
        [Composition Layer Implementation]
        Vertical Fallback: Ask each loader in order. First one to return non-None wins.
        """
        # Optimization: If we have a cached view, check it first
        # But for 'fetch' semantic (atomic lookup), maybe we should iterate loaders?
        # To be strictly correct with "Composition Layer", we should delegate to loaders.
        # However, OverlayNexus typically caches views for performance using ChainMap.
        
        # Let's use the view cache for performance, as it represents the composed state.
        if not ignore_cache:
            view = self._get_or_create_view(domain)
            val = view.get(pointer)
            if val is not None:
                return str(val)
            return None
            
        # If ignore_cache, we must query loaders directly (bypassing ChainMap cache)
        for loader in self.loaders:
            val = loader.fetch(pointer, domain, ignore_cache=True)
            if val is not None:
                return val
        return None

    def load(self, domain: str, ignore_cache: bool = False) -> Dict[str, Any]:
        if ignore_cache:
             self.reload(domain)
        return self._get_or_create_view(domain)

    def _get_or_create_view(self, domain: str) -> ChainMap[str, Any]:
        if domain not in self._views:
            # Trigger load() on all loaders for the requested domain.
            # The order of `self.loaders` is preserved (Priority: First > Last)
            # Note: We call load() on children, not fetch(), to build the view.
            maps = [loader.load(domain) for loader in self.loaders]
            self._views[domain] = ChainMap(*maps)
        return self._views[domain]

    def reload(self, domain: Optional[str] = None) -> None:
        if domain:
            self._views.pop(domain, None)
        else:
            self._views.clear()

    # --- Write Support ---

    def _get_writable_loader(self) -> Optional[WritableResourceLoaderProtocol]:
        for loader in self.loaders:
            if isinstance(loader, WritableResourceLoaderProtocol):
                return loader
        return None

    def put(
        self,
        pointer: Union[str, SemanticPointerProtocol],
        value: Any,
        domain: Optional[str] = None,
    ) -> bool:
        target_domain = self._resolve_domain(domain)
        loader = self._get_writable_loader()
        if not loader:
            return False

        success = loader.put(pointer, value, target_domain)
        if success:
            self.reload(target_domain)
        return success

    def locate(
        self,
        pointer: Union[str, SemanticPointerProtocol],
        domain: Optional[str] = None,
    ) -> Optional[Path]:
        target_domain = self._resolve_domain(domain)
        loader = self._get_writable_loader()
        if not loader:
            return None
        return loader.locate(pointer, target_domain)
~~~~~

#### Acts 4: 适配 FileSystemLoader

最后，我们更新 `FileSystemLoader` 以继承 `BaseLoader` 并实现 `fetch`。
**注意**: 为了此次架构重构的原子性，这里的 `fetch` 实现暂时基于已有的全量 `load` 逻辑。真正的基于 SST v2 的物理探测优化将在后续计划中实现。

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~
~~~~~python.old
from .protocols import FileHandlerProtocol
from .json_handler import JsonHandler


from needle.spec import WritableResourceLoaderProtocol

# ... imports ...


class FileSystemLoader(WritableResourceLoaderProtocol):
    def __init__(
        self,
        roots: Optional[List[Path]] = None,
        handlers: Optional[List[FileHandlerProtocol]] = None,
    ):
        self.handlers = handlers or [JsonHandler()]
        self.roots = roots or [self._find_project_root()]
~~~~~
~~~~~python.new
from .protocols import FileHandlerProtocol
from .json_handler import JsonHandler


from needle.spec import WritableResourceLoaderProtocol
from needle.nexus import BaseLoader

# ... imports ...


class FileSystemLoader(BaseLoader, WritableResourceLoaderProtocol):
    def __init__(
        self,
        roots: Optional[List[Path]] = None,
        handlers: Optional[List[FileHandlerProtocol]] = None,
        default_domain: str = "en",
    ):
        super().__init__(default_domain)
        self.handlers = handlers or [JsonHandler()]
        self.roots = roots or [self._find_project_root()]
~~~~~

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~
~~~~~python.old
    def add_root(self, path: Path):
        if path not in self.roots:
            self.roots.insert(0, path)

    def load(self, domain: str) -> Dict[str, Any]:
        merged_registry: Dict[str, str] = {}

        for root in self.roots:
~~~~~
~~~~~python.new
    def add_root(self, path: Path):
        if path not in self.roots:
            self.roots.insert(0, path)

    def fetch(
        self, pointer: str, domain: str, ignore_cache: bool = False
    ) -> Optional[str]:
        # TODO: Implement optimized physical probing based on SST v2 relative keys.
        # For now, we rely on the full load() method to maintain backward compatibility
        # and correctness during the architectural migration.
        registry = self.load(domain, ignore_cache)
        val = registry.get(pointer)
        return str(val) if val is not None else None

    def load(self, domain: str, ignore_cache: bool = False) -> Dict[str, Any]:
        merged_registry: Dict[str, str] = {}

        for root in self.roots:
~~~~~

### 下一步建议
我们已经完成了架构的正交化重构。目前的系统已经运行在三层模型上，但 `FileSystemLoader` 的性能仍有优化空间。

接下来的计划应专注于 **SST v2** 的物理层实现：
1.  在 `FileSystemLoader.fetch` 中实现基于 SST v2 规则的物理文件探测。
2.  实现“相对键”到“FQN”的动态合成，从而真正实现按需加载。
