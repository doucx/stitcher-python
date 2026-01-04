from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation


def test_rename_symbol_end_to_end(tmp_path):
    # 1. Setup: Create a virtual project
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    
    # File with the definition
    core_path = pkg_dir / "core.py"
    core_path.write_text(
        "class OldHelper:\n    pass\n\ndef old_func():\n    pass",
        encoding="utf-8"
    )
    
    # File with usages
    app_path = pkg_dir / "app.py"
    app_path.write_text(
        "from .core import OldHelper, old_func\n\n"
        "h = OldHelper()\n"
        "old_func()",
        encoding="utf-8"
    )

    # 2. Analysis Phase
    graph = SemanticGraph(root_path=tmp_path)
    graph.load("mypkg")
    ctx = RefactorContext(graph=graph)

    # 3. Planning Phase
    op = RenameSymbolOperation(
        old_fqn="mypkg.core.OldHelper", 
        new_fqn="mypkg.core.NewHelper"
    )
    file_ops = op.analyze(ctx)

    # 4. Execution Phase
    tm = TransactionManager(tmp_path)
    for op in file_ops:
        # In a real app, we might add ops one by one. Here we add all.
        # This assumes analyze() returns WriteFileOp with correct content.
        tm.add_write(op.path, op.content)
    
    tm.commit()

    # 5. Verification Phase
    # Check the file where the definition was
    modified_core_code = core_path.read_text(encoding="utf-8")
    expected_core_code = "class NewHelper:\n    pass\n\ndef old_func():\n    pass"
    assert modified_core_code == expected_core_code

    # Check the file where it was used
    modified_app_code = app_path.read_text(encoding="utf-8")
    expected_app_code = ("from .core import NewHelper, old_func\n\n"
                         "h = NewHelper()\n"
                         "old_func()")
    assert modified_app_code == expected_app_code