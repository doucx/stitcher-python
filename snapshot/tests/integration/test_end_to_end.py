import pytest
from pathlib import Path
from textwrap import dedent

# This module doesn't exist yet, driving its creation
from stitcher.app import StitcherApp

def test_app_scan_and_generate_single_file(tmp_path):
    # 1. Arrange: Create a source python file
    source_content = dedent("""
        def greet(name: str) -> str:
            \"\"\"Returns a greeting.\"\"\"
            return f"Hello, {name}!"
    """)
    source_file = tmp_path / "greet.py"
    source_file.write_text(source_content, encoding="utf-8")
    
    # 2. Act: Initialize App and run generation
    app = StitcherApp(root_path=tmp_path)
    # We expect this method to scan the file and generate a .pyi next to it
    generated_files = app.run_generate(files=[source_file])
    
    # 3. Assert: Verify the .pyi file exists and has correct content
    expected_pyi_path = tmp_path / "greet.pyi"
    
    assert expected_pyi_path.exists()
    assert expected_pyi_path in generated_files
    
    pyi_content = expected_pyi_path.read_text(encoding="utf-8")
    
    # Verify core components are present
    assert "def greet(name: str) -> str:" in pyi_content
    assert '"""Returns a greeting."""' in pyi_content
    assert "..." in pyi_content