from pathlib import Path

from stitcher.adapter.python import PythonAdapter
from stitcher.test_utils import WorkspaceFactory


def test_reference_extraction_with_aliases(tmp_path: Path):
    """
    Verify that reference extraction correctly identifies usages and
    links them to the SURI of the alias in __init__.py, not the
    original definition.
    """
    # Arrange: Create a project with a nested module and an alias
    wf = WorkspaceFactory(tmp_path)
    wf.with_source(
        "pkg/core.py",
        """
    class App:
        '''The main application class.'''
        pass
    """,
    )
    wf.with_source(
        "pkg/__init__.py",
        """
    from .core import App
    """,
    )
    wf.with_source(
        "main.py",
        """
    from pkg import App

    # This is a usage of the App alias
    instance = App()
    """,
    )
    wf.build()

    adapter = PythonAdapter(root_path=tmp_path)

    # Act: Parse the file that uses the alias
    main_py_path = tmp_path / "main.py"
    main_content = main_py_path.read_text()
    _, references = adapter.parse(main_py_path, main_content)

    # Assert
    assert (
        len(references) >= 2
    ), "Should find at least references for the import and the instantiation"

    # The key assertion: the target SURI must point to the alias in __init__.py
    expected_target_suri = "py://pkg/__init__.py#App"

    # Find the reference for the `App()` instantiation on line 5
    app_usage_ref = None
    for ref in references:
        if ref.target_id == expected_target_suri and ref.location_start == 5:
            app_usage_ref = ref
            break

    assert (
        app_usage_ref is not None
    ), f"Did not find reference to '{expected_target_suri}' on line 5"
    assert app_usage_ref.kind == "symbol"

    # Find the reference for the `from pkg import App` statement on line 2
    import_usage_ref = None
    for ref in references:
        if ref.target_id == expected_target_suri and ref.location_start == 2:
            import_usage_ref = ref
            break

    assert (
        import_usage_ref is not None
    ), f"Did not find import reference to '{expected_target_suri}' on line 2"
    assert import_usage_ref.kind == "symbol"