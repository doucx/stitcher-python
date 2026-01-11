import pytest
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .workspace import WorkspaceFactory
    from .bus import SpyBus


@pytest.fixture
def workspace_factory(tmp_path: Path) -> "WorkspaceFactory":
    """Provides a factory to create isolated test workspaces."""
    # Lazy import to prevent 'stitcher' from being imported during pytest collection,
    # which causes coverage warnings (module imported but not measured).
    from .workspace import WorkspaceFactory
    return WorkspaceFactory(tmp_path)


@pytest.fixture
def spy_bus() -> "SpyBus":
    """Provides a SpyBus instance to intercept and inspect bus messages."""
    # Lazy import to prevent premature loading of stitcher.common
    from .bus import SpyBus
    return SpyBus()