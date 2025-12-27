from contextlib import contextmanager
from typing import Dict, Any


class MockNeedle:
    def __init__(self, templates: Dict[str, str]):
        self._templates = templates

    def _mock_get(self, key: Any, **kwargs: Any) -> str:
        key_str = str(key)
        return self._templates.get(key_str, key_str)

    @contextmanager
    def patch(self, monkeypatch: Any):
        # The target path must be where `nexus` is used by the code under test.
        # The MessageBus now imports `stitcher_nexus` from `stitcher.common` and aliases it.
        # So we patch the original location.
        target_path = "stitcher.common.stitcher_nexus.get"
        try:
            monkeypatch.setattr(target_path, self._mock_get)
            yield
        finally:
            # monkeypatch handles teardown automatically, but this ensures clarity.
            pass
