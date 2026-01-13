from pathlib import Path
from typing import Union

from stitcher.common.services import AssetPathResolver
from stitcher.lang.sidecar.signature_manager import SignatureManager
from stitcher.workspace import Workspace


class SidecarManager:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.resolver = AssetPathResolver(workspace.root_path)
        self.signature_manager = SignatureManager(workspace)

    def get_doc_path(self, source_file_path: Union[str, Path]) -> Path:
        """
        Returns the path to the document sidecar (.stitcher.yaml) for a given source file.
        Delegates to AssetPathResolver as doc files are still per-source-file.
        """
        return self.resolver.get_doc_path(source_file_path)

    def get_signature_path(self, source_file_path: Union[str, Path]) -> Path:
        """
        Returns the path to the signature lock file (stitcher.lock) containing the given source file.
        Delegates to SignatureManager to handle package root resolution.
        """
        # SignatureManager expects a string path relative to workspace root or absolute?
        # Looking at SignatureManager implementation:
        # abs_file_path = (self.workspace.root_path / file_path).resolve()
        # If file_path is absolute, pathlib joins ignores the left side.
        # So passing absolute path works.
        
        return self.signature_manager.get_signature_path(str(source_file_path))