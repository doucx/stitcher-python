import pytest
from needle.pointer import L

from stitcher.test_utils import WorkspaceFactory, SpyBus, create_test_app


def test_check_does_not_report_imports_as_missing_docs(
    workspace_factory: WorkspaceFactory, spy_bus: SpyBus, monkeypatch
):
    """
    Verifies that 'stitcher check' does not incorrectly flag imported symbols
    as missing documentation. It should only flag symbols defined within the
    scanned module.
    """
    # 1. Setup: Create a project with a file that has imports and defined symbols
    ws = (
        workspace_factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/my_pkg/core.py",
            """
import os
import logging
from pathlib import Path
from typing import Optional, List

# This function is defined locally and should be reported as missing docs.
def my_public_function():
    pass

# This class is defined locally and should also be reported.
class MyPublicClass:
    pass
            """,
        )
        .build()
    )

    # 2. Execution: Run the check command
    app = create_test_app(ws)
    with spy_bus.patch(monkeypatch):
        # We expect this to fail because docs are missing, which is what we're testing.
        success = app.run_check()
        assert not success

    # 3. Assertion: Verify the output from the bus
    messages = spy_bus.get_messages()

    # Filter for only the 'missing documentation' warnings
    missing_doc_warnings = [
        msg for msg in messages if msg["id"] == str(L.check.issue.missing)
    ]

    assert len(missing_doc_warnings) == 2, "Should only find 2 missing doc warnings"

    # Extract the 'key' (the FQN) from the warning parameters
    reported_keys = {msg["params"]["key"] for msg in missing_doc_warnings}

    # Assert that our defined symbols ARE reported
    assert "my_public_function" in reported_keys
    assert "MyPublicClass" in reported_keys

    # Assert that imported symbols are NOT reported
    imported_symbols = {"os", "logging", "Path", "Optional", "List"}
    for symbol in imported_symbols:
        assert (
            symbol not in reported_keys
        ), f"Imported symbol '{symbol}' was incorrectly reported as missing docs"