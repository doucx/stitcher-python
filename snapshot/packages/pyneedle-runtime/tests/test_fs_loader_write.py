import json
from pathlib import Path
from stitcher.test_utils import WorkspaceFactory

from needle.pointer import L
from needle.loaders.fs_loader import FileSystemLoader


def test_fs_loader_locate_returns_correct_path(tmp_path: Path):
    # Arrange
    project_root = WorkspaceFactory(tmp_path).build()
    loader = FileSystemLoader(roots=[project_root])

    # Act
    path = loader.locate(L.cli.ui.welcome, "en")

    # Assert
    expected = (
        project_root / ".stitcher" / "needle" / "en" / "cli" / "ui.json"
    )
    assert path == expected


def test_fs_loader_put_creates_files_and_writes_data(tmp_path: Path):
    # Arrange
    project_root = WorkspaceFactory(tmp_path).build()
    loader = FileSystemLoader(roots=[project_root])

    # Act
    success1 = loader.put(L.app.db.connect_error, "Connection failed.", "en")
    success2 = loader.put(L.app.db.timeout, "Timeout reached.", "en")

    # Assert
    assert success1
    assert success2

    target_file = (
        project_root / ".stitcher" / "needle" / "en" / "app" / "db.json"
    )
    init_file = (
        project_root / ".stitcher" / "needle" / "en" / "app" / "__init__.json"
    )

    assert target_file.exists()
    assert init_file.exists()

    with target_file.open("r") as f:
        data = json.load(f)

    assert data["app.db.connect_error"] == "Connection failed."
    assert data["app.db.timeout"] == "Timeout reached."


def test_fs_loader_put_updates_existing_file(tmp_path: Path):
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = factory.with_source(
        ".stitcher/needle/en/app/db.json",
        '{"app.db.existing": "Original"}',
    ).build()

    loader = FileSystemLoader(roots=[project_root])

    # Act
    success = loader.put(L.app.db.new, "New value", "en")

    # Assert
    assert success
    target_file = (
        project_root / ".stitcher" / "needle" / "en" / "app" / "db.json"
    )
    with target_file.open("r") as f:
        data = json.load(f)

    assert data["app.db.existing"] == "Original"
    assert data["app.db.new"] == "New value"