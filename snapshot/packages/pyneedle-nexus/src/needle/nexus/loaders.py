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
