from pathlib import Path
import yaml
import json

from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager
from stitcher.refactor.operations.move_file import MoveFileOperation


def test_move_file_end_to_end(tmp_path):
    # 1. Arrange: Create a virtual project
    # Project structure:
    # mypkg/
    #   old_mod.py  (defines MyClass)
    #   main.py     (uses MyClass)
    #   old_mod.stitcher.yaml
    # .stitcher/signatures/mypkg/old_mod.json

    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()

    # Source files
    src_path = pkg_dir / "old_mod.py"
    src_path.write_text("class MyClass:\n    pass\n", encoding="utf-8")

    main_path = pkg_dir / "main.py"
    main_path.write_text(
        "from mypkg.old_mod import MyClass\n\ninstance = MyClass()", encoding="utf-8"
    )

    # Sidecar files
    doc_path = pkg_dir / "old_mod.stitcher.yaml"
    doc_path.write_text(
        yaml.dump({"mypkg.old_mod.MyClass": "This is a class."}), encoding="utf-8"
    )

    sig_dir = tmp_path / ".stitcher" / "signatures" / "mypkg"
    sig_dir.mkdir(parents=True)
    sig_path = sig_dir / "old_mod.json"
    sig_path.write_text(
        json.dumps({"mypkg.old_mod.MyClass": {"hash": "abc"}}), encoding="utf-8"
    )

    # 2. Act: Perform the move operation
    graph = SemanticGraph(root_path=tmp_path)
    graph.load("mypkg")
    ctx = RefactorContext(graph=graph)

    dest_path = pkg_dir / "new_mod.py"
    op = MoveFileOperation(src_path=src_path, dest_path=dest_path)
    file_ops = op.analyze(ctx)

    tm = TransactionManager(tmp_path)
    for fop in file_ops:
        # The transaction manager requires relative paths for operations
        # but the analyzer might produce ops with different kinds of paths.
        # This test logic handles that by just executing what analyze returns.
        # Let's commit them one by one. This is a simplification.
        # A real TM would take a list. Our TM can add ops sequentially.
        if fop.__class__.__name__ == "WriteFileOp":
            tm.add_write(fop.path, fop.content)
        elif fop.__class__.__name__ == "MoveFileOp":
            tm.add_move(fop.path, fop.dest)

    tm.commit()

    # 3. Assert: Verify the final state of the filesystem and contents
    # New paths
    new_doc_path = pkg_dir / "new_mod.stitcher.yaml"
    new_sig_path = sig_dir / "new_mod.json"

    # 3.1 Verify file moves
    assert not src_path.exists()
    assert dest_path.exists()
    assert not doc_path.exists()
    assert new_doc_path.exists()
    assert not sig_path.exists()
    assert new_sig_path.exists()

    # 3.2 Verify code content updates
    assert dest_path.read_text(encoding="utf-8") == "class MyClass:\n    pass\n"
    assert (
        main_path.read_text(encoding="utf-8")
        == "from mypkg.new_mod import MyClass\n\ninstance = MyClass()"
    )

    # 3.3 Verify sidecar content updates (key renaming)
    new_doc_data = yaml.safe_load(new_doc_path.read_text("utf-8"))
    assert "mypkg.new_mod.MyClass" in new_doc_data
    assert "mypkg.old_mod.MyClass" not in new_doc_data

    new_sig_data = json.loads(new_sig_path.read_text("utf-8"))
    assert "mypkg.new_mod.MyClass" in new_sig_data
    assert "mypkg.old_mod.MyClass" not in new_sig_data
    assert new_sig_data["mypkg.new_mod.MyClass"]["hash"] == "abc"