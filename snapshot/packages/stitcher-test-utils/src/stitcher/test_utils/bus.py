from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union

# No top-level imports of stitcher packages to avoid coverage warnings
from needle.pointer import SemanticPointer

class SpyRenderer:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def render(self, message: str, level: str) -> None:
        # The spy logic mostly acts on record(), but satisfy interface
        pass

    def record(self, level: str, msg_id: SemanticPointer, params: Dict[str, Any]):
        self.messages.append({"level": level, "id": str(msg_id), "params": params})


class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()

    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus"):
        # Lazy import inside the context manager
        import stitcher.common
        
        # The singleton instance we need to mutate
        real_bus = stitcher.common.bus

        # Define the interceptor hook
        def intercept_render(
            level: str, msg_id: Union[str, SemanticPointer], **kwargs: Any
        ) -> None:
            if isinstance(msg_id, SemanticPointer):
                self._spy_renderer.record(level, msg_id, kwargs)

        # Apply In-Place Patches
        monkeypatch.setattr(real_bus, "_render", intercept_render)
        monkeypatch.setattr(real_bus, "_renderer", self._spy_renderer)

        yield self

    def get_messages(self) -> List[Dict[str, Any]]:
        return self._spy_renderer.messages

    def assert_id_called(self, msg_id: SemanticPointer, level: Optional[str] = None):
        key = str(msg_id)
        found = False
        captured = self.get_messages()

        for msg in captured:
            if msg["id"] == key and (level is None or msg["level"] == level):
                found = True
                break

        if not found:
            ids_seen = [m["id"] for m in captured]
            raise AssertionError(
                f"Message with ID '{key}' was not sent.\nCaptured IDs: {ids_seen}"
            )