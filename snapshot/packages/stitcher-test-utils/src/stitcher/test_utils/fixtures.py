import pytest
from pathlib import Path

@pytest.fixture
def workspace_factory(tmp_path: Path):
    """Provides a factory to create isolated test workspaces."""
    from .workspace import WorkspaceFactory
    return WorkspaceFactory(tmp_path)


@pytest.fixture
def spy_bus():
    """Provides a SpyBus instance to intercept and inspect bus messages."""
    from .bus import SpyBus
    return SpyBus()