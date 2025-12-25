from pathlib import Path
from typing import List

from stitcher.scanner import parse_source_code
from stitcher.io import StubGenerator


from stitcher.common import bus
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
        config = load_config_from_path(self.root_path)
        
        if not config.scan_paths:
            bus.warning("error.config.not_found")
            return []
            
        files_to_scan = []
        for scan_path_str in config.scan_paths:
            scan_path = self.root_path / scan_path_str
            if scan_path.is_dir():
                files_to_scan.extend(scan_path.rglob("*.py"))
            elif scan_path.is_file():
                files_to_scan.append(scan_path)
        
        unique_files = sorted(list(set(files_to_scan)))
        
        generated_files = self.run_generate(files=unique_files)
        
        if generated_files:
            bus.success("generate.run.complete", count=len(generated_files))

        return generated_files

    def run_generate(self, files: List[Path]) -> List[Path]:
        """
        Scans the given files and generates .pyi stubs for them.
        Returns the list of generated .pyi file paths.
        """
        generated_files: List[Path] = []
        
        for source_file in files:
            try:
                content = source_file.read_text(encoding="utf-8")
                module_def = parse_source_code(content, file_path=str(source_file))
                pyi_content = self.generator.generate(module_def)
                
                output_path = source_file.with_suffix(".pyi")
                output_path.write_text(pyi_content, encoding="utf-8")
                
                bus.success("generate.file.success", path=output_path.relative_to(self.root_path))
                generated_files.append(output_path)
            except Exception as e:
                bus.error("error.generic", error=e)

        return generated_files