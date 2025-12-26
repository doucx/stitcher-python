import os
from pathlib import Path
from typing import Dict, Optional, Union

from .loader import Loader
from .pointer import SemanticPointer


class Needle:
    """
    The runtime kernel for semantic addressing.
    """

    def __init__(self, root_path: Optional[Path] = None, default_lang: str = "en"):
        # We now support multiple roots. The project root is just the primary one.
        project_root = root_path or self._find_project_root()
        self.roots: list[Path] = [project_root] if project_root else []

        self.default_lang = default_lang
        self._registry: Dict[str, Dict[str, str]] = {}  # lang -> {fqn: value}
        self._loader = Loader()
        self._loaded_langs: set = set()

    def add_root(self, path: Path):
        """Registers an additional root directory to search for needle assets."""
        if path not in self.roots:
            # We append to let existing (Project) roots take precedence during merge
            self.roots.append(path)
            # Clear cache to force reload on next access
            self._loaded_langs.clear()
            self._registry.clear()

    def _find_project_root(self, start_dir: Optional[Path] = None) -> Path:
        """
        Finds the project root by searching upwards for common markers.
        Search priority: pyproject.toml -> .git
        """
        current_dir = (start_dir or Path.cwd()).resolve()
        while current_dir.parent != current_dir:  # Stop at filesystem root
            # Priority 1: pyproject.toml (strongest Python project signal)
            if (current_dir / "pyproject.toml").is_file():
                return current_dir
            # Priority 2: .git directory (strong version control signal)
            if (current_dir / ".git").is_dir():
                return current_dir
            current_dir = current_dir.parent
        # Fallback to the starting directory if no markers are found
        return start_dir or Path.cwd()

    def _ensure_lang_loaded(self, lang: str):
        if lang in self._loaded_langs:
            return

        merged_data: Dict[str, str] = {}

        # Iterate over all roots in reverse order.
        # Primary root (e.g. Project Root) should be roots[0] and should overwrite
        # Secondary roots (e.g. System Assets).
        for root in reversed(self.roots):
            # Try strict SST (.stitcher/needle)
            hidden_needle = root / ".stitcher" / "needle" / lang
            if hidden_needle.exists():
                merged_data.update(self._loader.load_directory(hidden_needle))

            # Try unhidden needle (needle/) for package assets
            visible_needle = root / "needle" / lang
            if visible_needle.exists():
                merged_data.update(self._loader.load_directory(visible_needle))

        self._registry[lang] = merged_data
        self._loaded_langs.add(lang)

    def get(
        self, pointer: Union[SemanticPointer, str], lang: Optional[str] = None
    ) -> str:
        """
        Resolves a semantic pointer to a string value with graceful fallback.

        Lookup Order:
        1. Target Language
        2. Default Language (en)
        3. Identity (the key itself)
        """
        key = str(pointer)
        target_lang = lang or os.getenv("STITCHER_LANG", self.default_lang)

        # 1. Try target language
        self._ensure_lang_loaded(target_lang)
        val = self._registry.get(target_lang, {}).get(key)
        if val is not None:
            return val

        # 2. Try default language (if different)
        if target_lang != self.default_lang:
            self._ensure_lang_loaded(self.default_lang)
            val = self._registry.get(self.default_lang, {}).get(key)
            if val is not None:
                return val

        # 3. Fallback to Identity
        return key


# Global Runtime Instance
needle = Needle()
