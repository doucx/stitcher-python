import pytest
from pathlib import Path
from .workspace import WorkspaceFactory
from .bus import SpyBus


@pytest.fixture
def workspace_factory(tmp_path: Path) -> WorkspaceFactory:
    """Provides a factory to create isolated test workspaces."""
    return WorkspaceFactory(tmp_path)


@pytest.fixture
def spy_bus() -> SpyBus:
    """Provides a SpyBus instance to intercept and inspect bus messages."""
    return SpyBus()