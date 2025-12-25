from pathlib import Path
from typing import List

class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path

    def run_generate(self, files: List[Path]) -> List[Path]:
        """
        Scans the given files and generates .pyi stubs for them.
        Returns the list of generated .pyi file paths.
        """
        # TODO: Implement orchestration logic
        return []