from contextlib import contextmanager
from typing import Dict, Any


class MockNexus:
    def __init__(self, templates: Dict[str, str]):
        self._templates = templates

    def get(self, key: Any, **kwargs: Any) -> str:
        """Standard Nexus interface implementation."""
        key_str = str(key)
        return self._templates.get(key_str, key_str)

    @contextmanager
    def patch(self, monkeypatch: Any):
        """
        Legacy patch method.
        Prefer constructor injection (Dependency Injection) where possible.
        This patches the 'stitcher_nexus' used by the global bus if needed.
        """
        target_path = "stitcher.common.stitcher_nexus.get"
        try:
            monkeypatch.setattr(target_path, self.get)
            yield
        finally:
            pass