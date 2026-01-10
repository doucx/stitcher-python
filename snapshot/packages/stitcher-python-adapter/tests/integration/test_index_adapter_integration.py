from textwrap import dedent
from stitcher.index.scanner import WorkspaceScanner
from stitcher.adapter.python import PythonAdapter
from stitcher.test_utils.workspace import WorkspaceFactory


def test_alias_and_reference_resolution_end_to_end(tmp_path, store):
    """
    End-to-end test for the entire alias and reference pipeline.
    Verifies:
    1. Alias symbols (`import`) are created correctly in the importing module.
    2. Reference records (`usage`) correctly point to the original definition's SURI.
    """
    # 1. Arrange: Create a workspace with a package structure
    wf = WorkspaceFactory(tmp_path)
    wf.with_source("src/my_pkg/__init__.py", "")
    wf.with_source(
        "src/my_pkg/utils.py",
        dedent(
            """
            class HelperClass:
                pass

            def helper_func():
                pass
            """
        ),
    )
    wf.with_source(
        "src/my_pkg/main.py",
        dedent(
            """
            import my_pkg.utils
            from my_pkg.utils import helper_func
            from my_pkg.utils import HelperClass as HC

            def main_flow():
                my_pkg.utils.helper_func()
                helper_func()
                instance = HC()
            """
        ),
    )
    root_path = wf.build()

    # 2. Act: Run the scanner
    scanner = WorkspaceScanner(root_path, store)
    adapter = PythonAdapter(root_path)
    scanner.register_adapter(".py", adapter)
    scanner.scan()

    # 3. Assert
    # --- Get file records from DB ---
    main_file = store.get_file_by_path("src/my_pkg/main.py")
    utils_file = store.get_file_by_path("src/my_pkg/utils.py")
    assert main_file is not None
    assert utils_file is not None

    main_symbols = {s.name: s for s in store.get_symbols_by_file(main_file.id)}
    main_refs = store.get_references_by_file(main_file.id)

    # --- Expected SURIs for definitions in utils.py ---
    utils_helper_class_suri = "py://src/my_pkg/utils.py#HelperClass"
    utils_helper_func_suri = "py://src/my_pkg/utils.py#helper_func"

    # --- Assertion Set 1: Alias symbols in main.py are correct ---
    assert "my_pkg" in main_symbols
    assert main_symbols["my_pkg"].kind == "alias"
    assert main_symbols["my_pkg"].alias_target_id == "py://src/my_pkg.py"

    assert "helper_func" in main_symbols
    assert main_symbols["helper_func"].kind == "alias"
    assert main_symbols["helper_func"].alias_target_id == utils_helper_func_suri

    assert "HC" in main_symbols
    assert main_symbols["HC"].kind == "alias"
    assert main_symbols["HC"].alias_target_id == utils_helper_class_suri

    # --- Assertion Set 2: Reference records in main.py are correct ---
    ref_targets = {ref.target_id for ref in main_refs}

    # All three usages should resolve directly to the definition SURIs
    assert utils_helper_func_suri in ref_targets
    assert utils_helper_class_suri in ref_targets

    # Check reference counts for more precision
    func_ref_count = sum(1 for r in main_refs if r.target_id == utils_helper_func_suri)
    class_ref_count = sum(
        1 for r in main_refs if r.target_id == utils_helper_class_suri
    )

    # We expect 2 usages of the function and 1 of the class
    assert func_ref_count >= 2  # my_pkg.utils.helper_func() and helper_func()
    assert class_ref_count >= 1  # HC()