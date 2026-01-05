import yaml
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    WriteFileOp,
)
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_repro_sidecar_keys_should_remain_short_names_after_move(tmp_path):
    """
    Reproduction test for the bug where moving a file causes Sidecar keys
    to be expanded to FQNs instead of remaining as Short Names.
    
    Scenario:
      Move 'mypkg/core.py' -> 'mypkg/moved.py'.
      The sidecar 'mypkg/core.stitcher.yaml' has keys like "MyClass".
      
    Expected:
      The new sidecar 'mypkg/moved.stitcher.yaml' should have keys "MyClass",
      NOT "mypkg.moved.MyClass".
    """
    # 1. ARRANGE
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class MyClass:\n    def __init__(self): pass")
        .with_docs(
            "mypkg/core.stitcher.yaml",
            {
                "MyClass": "Class doc",
                "MyClass.__init__": "Init doc"
            },
        )
        .build()
    )

    src_path = project_root / "mypkg/core.py"
    dest_path = project_root / "mypkg/moved.py"

    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveFileOperation(src_path, dest_path)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    new_yaml_path = dest_path.with_suffix(".stitcher.yaml")
    assert new_yaml_path.exists()
    
    data = yaml.safe_load(new_yaml_path.read_text())
    
    # Debug output to help verify the failure/success
    print(f"\n[DEBUG] Keys in new sidecar: {list(data.keys())}")
    
    # We explicitly assert that the SHORT names are present.
    # If the bug exists, these assertions will fail because the keys will be FQNs.
    
    assert "MyClass" in data, (
        f"Short name 'MyClass' missing. Found keys: {list(data.keys())}"
    )
    assert "MyClass.__init__" in data, (
        f"Short name 'MyClass.__init__' missing. Found keys: {list(data.keys())}"
    )
    
    # Verify content wasn't lost
    assert data["MyClass"] == "Class doc"
    assert data["MyClass.__init__"] == "Init doc"