from unittest.mock import MagicMock
import pytest
from stitcher.index.scanner import WorkspaceScanner, LanguageAdapterProtocol
from stitcher.index.types import SymbolRecord, ReferenceRecord


@pytest.fixture
def mock_adapter():
    mock = MagicMock(spec=LanguageAdapterProtocol)
    mock.parse.return_value = (
        [SymbolRecord(id="s1", name="s1", kind="k", location_start=0, location_end=1)],
        [ReferenceRecord(target_id="t1", kind="k", location_start=0, location_end=1)],
    )
    return mock


@pytest.fixture
def scanner(tmp_path, store, mock_adapter):
    # Setup a git repo for reliable file discovery
    (tmp_path / ".git").mkdir()
    return WorkspaceScanner(tmp_path, store, mock_adapter)


def test_initial_scan(scanner, tmp_path, mock_adapter, store):
    """All files are new and should be parsed."""
    (tmp_path / "main.py").write_text("...")
    (tmp_path / "lib.py").write_text("...")

    scanner.scan()

    assert mock_adapter.parse.call_count == 2
    assert store.get_file_by_path("main.py") is not None
    assert store.get_file_by_path("lib.py") is not None
    file_rec = store.get_file_by_path("main.py")
    assert len(store.get_symbols_by_file(file_rec.id)) == 1


def test_no_change_scan(scanner, tmp_path, mock_adapter):
    """On a second scan with no changes, nothing should be parsed."""
    (tmp_path / "main.py").write_text("...")
    scanner.scan()  # First scan

    mock_adapter.reset_mock()
    scanner.scan()  # Second scan

    mock_adapter.parse.assert_not_called()


def test_content_change_scan(scanner, tmp_path, mock_adapter):
    """Only the file with content change should be parsed."""
    (tmp_path / "main.py").write_text("a")
    (tmp_path / "lib.py").write_text("b")
    scanner.scan()

    mock_adapter.reset_mock()
    (tmp_path / "main.py").write_text("c")  # Change content

    scanner.scan()

    mock_adapter.parse.assert_called_once()
    call_args = mock_adapter.parse.call_args[0]
    assert call_args[0].name == "main.py"


def test_metadata_change_no_reparse(scanner, tmp_path, mock_adapter):
    """A file with only mtime change but same hash should not be re-parsed."""
    file = tmp_path / "main.py"
    file.write_text("a")
    scanner.scan()

    mock_adapter.reset_mock()
    # Simulate just touching the file
    file.touch()

    scanner.scan()
    mock_adapter.parse.assert_not_called()


def test_deleted_file_is_pruned(scanner, tmp_path, mock_adapter, store):
    """A deleted file should be removed from the index."""
    (tmp_path / "main.py").write_text("a")
    (tmp_path / "lib.py").write_text("b")
    scanner.scan()

    assert store.get_file_by_path("lib.py") is not None

    (tmp_path / "lib.py").unlink()
    scanner.scan()

    assert store.get_file_by_path("lib.py") is None
    assert store.get_file_by_path("main.py") is not None