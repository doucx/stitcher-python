from unittest.mock import MagicMock
from stitcher.test_utils import WorkspaceFactory, create_test_app


def test_check_hits_index_cache_on_second_run(tmp_path, monkeypatch):
    """
    Verifies that a second 'check' run without file changes hits the index cache
    and avoids re-parsing YAML files.
    """
    # 1. Arrange: A standard workspace
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(): pass")
        .with_docs("src/main.stitcher.yaml", {"func": "doc"})
        .build()
    )
    app = create_test_app(project_root)

    # 2. Act (First Run): Populate the index
    # We don't need to check the result, just warm up the index.
    app.run_check()

    # 3. Arrange (Spying): Patch the expensive IO/parsing method
    # This method is downstream of the indexer and should only be called on a cache miss.
    from stitcher.lang.sidecar.adapter import SidecarAdapter

    mock_load_irs = MagicMock(wraps=SidecarAdapter.load_doc_irs)
    monkeypatch.setattr(
        "stitcher.lang.sidecar.adapter.SidecarAdapter.load_doc_irs", mock_load_irs
    )

    # 4. Act (Second Run): This run should hit the cache
    app.run_check()

    # 5. Assert (Cache Hit): The expensive method was NOT called
    mock_load_irs.assert_not_called()

    # 6. Act (Third Run - Cache Miss): Modify a file to invalidate the cache
    (project_root / "src/main.stitcher.yaml").write_text(
        'func: "updated doc"', encoding="utf-8"
    )
    app.run_check()

    # 7. Assert (Cache Miss): The expensive method was called this time
    mock_load_irs.assert_called_once()