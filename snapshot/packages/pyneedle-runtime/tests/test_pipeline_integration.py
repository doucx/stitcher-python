from pathlib import Path
from needle.pointer import L
from needle.operators import FileSystemOperator, OverlayOperator


def test_fs_pipeline_overrides(tmp_path: Path):
    """
    Simulate the full Stitcher pipeline:
    Project Root (.stitcher/needle/en) -> Overrides -> Common Assets (needle/en)
    """

    # 1. Setup "Common Assets" (Low Priority)
    common_root = tmp_path / "common" / "needle" / "en"
    common_root.mkdir(parents=True)
    (common_root / "cli.json").write_text('{"help": "Default Help"}', encoding="utf-8")
    (common_root / "error.json").write_text('{"404": "Not Found"}', encoding="utf-8")

    # 2. Setup "User Project" (High Priority)
    project_root = tmp_path / "project" / ".stitcher" / "needle" / "en"
    project_root.mkdir(parents=True)
    (project_root / "cli.json").write_text('{"help": "Custom Help"}', encoding="utf-8")

    # 3. Build Operators
    common_op = FileSystemOperator(common_root)
    project_op = FileSystemOperator(project_root)

    # 4. Compose Pipeline (Project > Common)
    pipeline = OverlayOperator([project_op, common_op])

    # Act & Assert

    # A. Override: Project value wins
    assert pipeline(L.cli.help) == "Custom Help"

    # B. Fallback: Project doesn't have error.json, falls back to common
    assert pipeline(L.error["404"]) == "Not Found"

    # C. Missing
    assert pipeline(L.cli.unknown) is None


def test_fs_pipeline_nested_keys(tmp_path: Path):
    """
    Verify nested key access works through the pipeline.
    """
    root = tmp_path / "assets"
    root.mkdir()
    (root / "check.json").write_text(
        '{"messages": {"success": "OK", "fail": "NO"}}', encoding="utf-8"
    )

    op = FileSystemOperator(root)

    # Flattening happens inside FileSystemOperator -> JsonHandler
    # check.json -> messages -> success
    assert op(L.check.messages.success) == "OK"
