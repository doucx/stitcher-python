from pathlib import Path
from typing import List

from stitcher.scanner import parse_source_code
from stitcher.io import StubGenerator


from stitcher.config import load_config_from_path

class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # The app 'has a' generator, it uses it as a tool.
        self.generator = StubGenerator()

    def run_from_config(self) -> List[Path]:
        """
        Loads config, discovers files, and generates stubs.
        """
        # TODO: Implement config loading and file discovery
        return []

    def run_generate(self, files: List[Path]) -> List[Path]:
        """
        Scans the given files and generates .pyi stubs for them.
        Returns the list of generated .pyi file paths.
        """
        generated_files: List[Path] = []
        
        for source_file in files:
            # 1. Read the source content
            content = source_file.read_text(encoding="utf-8")
            
            # 2. Scan the content to get the IR
            # Pass the file path for better error messages in the future
            module_def = parse_source_code(content, file_path=str(source_file))
            
            # 3. Generate the .pyi string from the IR
            pyi_content = self.generator.generate(module_def)
            
            # 4. Determine output path and write the file
            output_path = source_file.with_suffix(".pyi")
            output_path.write_text(pyi_content, encoding="utf-8")
            
            generated_files.append(output_path)
            
        return generated_files