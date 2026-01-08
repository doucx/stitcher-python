from pathlib import Path
from stitcher.common.services import AssetPathResolver


class SidecarManager:
    def __init__(self, root_path: Path):
        self.resolver = AssetPathResolver(root_path)

    def get_doc_path(self, source_file_path: Path) -> Path:
        return self.resolver.get_doc_path(source_file_path)

    def get_signature_path(self, source_file_path: Path) -> Path:
        return self.resolver.get_signature_path(source_file_path)
