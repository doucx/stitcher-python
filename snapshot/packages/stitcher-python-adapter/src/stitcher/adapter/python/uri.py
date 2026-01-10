from pathlib import Path
from typing import Optional


class SURIGenerator:
    """Generates Stitcher Uniform Resource Identifiers (SURI) for Python entities."""

    @staticmethod
    def for_file(rel_path: str) -> str:
        """
        Generate SURI for a file.
        Format: py://<rel_path>
        Example: py://src/main.py
        """
        # Ensure forward slashes for cross-platform consistency
        normalized_path = Path(rel_path).as_posix()
        return f"py://{normalized_path}"

    @staticmethod
    def for_symbol(rel_path: str, fragment: str) -> str:
        """
        Generate SURI for a symbol within a file.
        Format: py://<rel_path>#<fragment>
        Example: py://src/main.py#MyClass.method
        """
        normalized_path = Path(rel_path).as_posix()
        return f"py://{normalized_path}#{fragment}"

    @staticmethod
    def parse(suri: str) -> tuple[str, Optional[str]]:
        """
        Parse a SURI into (rel_path, fragment).
        """
        if not suri.startswith("py://"):
            raise ValueError(f"Invalid Python SURI: {suri}")

        content = suri[5:]  # Strip 'py://'
        if "#" in content:
            path, fragment = content.split("#", 1)
            return path, fragment
        return content, None