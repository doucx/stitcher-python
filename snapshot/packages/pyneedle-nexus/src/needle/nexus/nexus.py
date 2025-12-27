import os
from collections import ChainMap
from typing import List, Dict, Optional, Union, Any, cast
from pathlib import Path
from needle.spec import (
    NexusProtocol,
    ResourceLoaderProtocol,
    WritableResourceLoaderProtocol,
    SemanticPointerProtocol,
)


class OverlayNexus(NexusProtocol):
    def __init__(
        self, loaders: List[ResourceLoaderProtocol], default_domain: str = "en"
    ):
        self.loaders = loaders
        self.default_domain = default_domain
        self._views: Dict[str, ChainMap[str, Any]] = {}

    def _get_or_create_view(self, domain: str) -> ChainMap[str, Any]:
        if domain not in self._views:
            maps = [loader.load(domain) for loader in self.loaders]
            self._views[domain] = ChainMap(*maps)
        return self._views[domain]

    def _resolve_domain(self, explicit_domain: Optional[str] = None) -> str:
        if explicit_domain:
            return explicit_domain

        # Priority is given to language-specific env vars for backward compatibility
        # and common use case.
        # Priority 1: NEEDLE_LANG (new standard)
        needle_lang = os.getenv("NEEDLE_LANG")
        if needle_lang:
            return needle_lang

        # Priority 2: STITCHER_LANG (legacy compatibility)
        stitcher_lang = os.getenv("STITCHER_LANG")
        if stitcher_lang:
            return stitcher_lang

        system_lang = os.getenv("LANG")
        if system_lang:
            return system_lang.split("_")[0].split(".")[0].lower()

        return self.default_domain

    def get(
        self,
        pointer: Union[str, SemanticPointerProtocol],
        domain: Optional[str] = None,
    ) -> str:
        key = str(pointer)
        target_domain = self._resolve_domain(domain)

        # 1. Try target domain
        target_view = self._get_or_create_view(target_domain)
        value = target_view.get(key)
        if value is not None:
            return str(value)

        # 2. Try default domain (if different)
        if target_domain != self.default_domain:
            default_view = self._get_or_create_view(self.default_domain)
            value = default_view.get(key)
            if value is not None:
                return str(value)

        # 3. Fallback to Identity
        return key

    def reload(self, domain: Optional[str] = None) -> None:
        if domain:
            self._views.pop(domain, None)
        else:
            self._views.clear()

    def _find_writable_loader(self) -> Optional[WritableResourceLoaderProtocol]:
        for loader in self.loaders:
            if isinstance(loader, WritableResourceLoaderProtocol):
                # The cast is safe because of the isinstance check.
                return cast(WritableResourceLoaderProtocol, loader)
        return None

    def put(
        self, pointer: SemanticPointerProtocol, value: Any, domain: str
    ) -> bool:
        writable_loader = self._find_writable_loader()
        if writable_loader:
            return writable_loader.put(pointer, value, domain)
        return False

    def locate(
        self, pointer: SemanticPointerProtocol, domain: str
    ) -> Union[Path, None]:
        writable_loader = self._find_writable_loader()
        if writable_loader:
            return writable_loader.locate(pointer, domain)
        return None

    # Implement the load method to make Nexus itself a loader
    def load(self, domain: str) -> Dict[str, Any]:
        """Loads all resources for a domain, returning a flat dictionary."""
        # This makes a Nexus composable inside another Nexus.
        view = self._get_or_create_view(domain)
        # ChainMap.maps is a list of dicts. We merge them from lowest to highest priority.
        merged: Dict[str, Any] = {}
        for m in reversed(view.maps):
            merged.update(m)
        return merged