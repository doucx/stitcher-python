import pytest
from pathlib import Path
from needle.pointer import L
from needle.operators import DictOperator, FileSystemOperator


def test_dict_operator_retrieves_values():
    data = {"app.title": "My App", "simple_key": "Value"}
    op = DictOperator(data)

    assert op("app.title") == "My App"
    assert op(L.app.title) == "My App"
    assert op("simple_key") == "Value"
    assert op("missing") is None


def test_fs_operator_lazy_loading(tmp_path: Path):
    # Arrange
    root = tmp_path / "assets"
    root.mkdir()
    
    # Create app.json
    (root / "app.json").write_text('{"title": "My App", "ver": {"major": 1}}', encoding="utf-8")
    
    op = FileSystemOperator(root)

    # Act & Assert
    
    # 1. Simple fetch
    # This should trigger load of app.json
    assert op(L.app.title) == "My App"

    # 2. Nested key fetch (JsonHandler flattens nested dicts)
    # "ver": {"major": 1} -> "ver.major": "1"
    assert op(L.app.ver.major) == "1"

    # 3. Missing file
    assert op(L.auth.login) is None
    
    # 4. Missing key in existing file
    assert op(L.app.description) is None


def test_fs_operator_caching(tmp_path: Path):
    root = tmp_path / "assets"
    root.mkdir()
    f = root / "data.json"
    f.write_text('{"key": "v1"}', encoding="utf-8")

    op = FileSystemOperator(root)
    
    # First access loads v1
    assert op(L.data.key) == "v1"

    # Externally change file
    f.write_text('{"key": "v2"}', encoding="utf-8")

    # Second access should still return cached v1
    assert op(L.data.key) == "v1"