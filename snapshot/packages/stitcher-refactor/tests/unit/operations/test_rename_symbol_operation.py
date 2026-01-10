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
    # Mock a workspace and an empty semantic graph
    mock_workspace = MagicMock(spec=Workspace)
    mock_graph = MagicMock(spec=SemanticGraph)
    mock_graph.iter_members.return_value = []  # Simulate symbol not found
    mock_graph._modules = {}  # Mock the internal structure it iterates

    # This is the key part of the mock that will trigger the error
    def find_def_node_side_effect(ctx):
        # Simulate the original logic raising an error
        raise ValueError("Symbol 'non.existent.symbol' not found")

    # In the fixed version, we will mock graph.find_symbol, but for now,
    # we target the problematic internal method.
    # To test the existing code, we need to mock the iteration to be empty.
    op = RenameSymbolOperation(
        old_fqn="non.existent.symbol", new_fqn="new.existent.symbol"
    )
    # Patch the problematic method directly to check if its exception is silenced
    op._find_definition_node = MagicMock(side_effect=find_def_node_side_effect)

    mock_ctx = MagicMock(spec=RefactorContext)
    mock_ctx.graph = mock_graph

    # 2. Act & Assert
    # We expect a ValueError because the symbol doesn't exist.
    # If this test fails, it's because the `except ValueError: pass` is silencing it.
    with pytest.raises(
        ValueError, match="Could not find definition for symbol: non.existent.symbol"
    ):
        op.collect_intents(mock_ctx)

    # To make the test pass after we fix the silent pass, we need to adjust
    # how we're mocking. For now, let's create a more realistic test.
    # Let's write the test for the *fixed* code.

    # Re-arranging for the post-fix scenario
    real_workspace = Workspace(root_path=Path("/tmp"))
    real_graph = SemanticGraph(workspace=real_workspace)
    # The graph is empty, so it won't find the symbol.

    ctx = RefactorContext(
        workspace=real_workspace, graph=real_graph, sidecar_manager=MagicMock()
    )
    op_final = RenameSymbolOperation(
        old_fqn="non.existent.symbol", new_fqn="new.existent.symbol"
    )

    with pytest.raises(
        ValueError, match="Could not find definition for symbol: non.existent.symbol"
    ):
        op_final.collect_intents(ctx)