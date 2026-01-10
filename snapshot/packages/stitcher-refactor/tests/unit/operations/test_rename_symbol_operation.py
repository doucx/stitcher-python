import pytest
from pathlib import Path
from unittest.mock import MagicMock

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.workspace import Workspace


def test_collect_intents_raises_error_if_symbol_not_found():
    """
    Verifies that a ValueError is raised if the target symbol for renaming
    cannot be found in the semantic graph. This prevents silent failures.
    """
    # 1. Arrange
    # Create a real, but empty, workspace and semantic graph.
    workspace = Workspace(root_path=Path("/tmp"))
    graph = SemanticGraph(workspace=workspace)
    # The graph is empty, so it won't find the symbol.

    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=MagicMock()
    )
    op = RenameSymbolOperation(
        old_fqn="non.existent.symbol", new_fqn="new.existent.symbol"
    )

    # 2. Act & Assert
    # We expect a ValueError because the symbol doesn't exist in the empty graph.
    with pytest.raises(
        ValueError, match="Could not find definition for symbol: non.existent.symbol"
    ):
        op.collect_intents(ctx)