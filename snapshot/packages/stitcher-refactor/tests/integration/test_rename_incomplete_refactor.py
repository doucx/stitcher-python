from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_rename_operation_fails_to_rename_symbol_definition(tmp_path):
    """
    This test reproduces a critical bug where RenameSymbolOperation renames
    all usages of a symbol but fails to rename the class definition itself.
    """
    # 1. ARRANGE: Create a project with a definition and a usage.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldName: pass")
        .with_source("mypkg/app.py", "from mypkg.core import OldName\n\ninstance = OldName()")
    ).build()

    definition_file = project_root / "mypkg/core.py"
    usage_file = project_root / "mypkg/app.py"

    # 2. ACT: Run the refactoring operation.
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    op = RenameSymbolOperation("mypkg.core.OldName", "mypkg.core.NewName")
    file_ops = op.analyze(ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT: Verify the incomplete refactoring.
    # Assert that the usage file was correctly updated.
    updated_usage_code = usage_file.read_text()
    assert "from mypkg.core import NewName" in updated_usage_code
    assert "instance = NewName()" in updated_usage_code

    # Assert that the definition file was NOT updated (THIS IS THE BUG).
    definition_code = definition_file.read_text()
    assert "class OldName: pass" in definition_code
    assert "class NewName: pass" not in definition_code, \
        "The bug appears to be fixed. This test should now fail and be updated."