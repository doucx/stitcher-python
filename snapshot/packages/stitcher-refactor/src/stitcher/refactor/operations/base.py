from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from stitcher.lang.python.analysis.utils import path_to_logical_fqn
from stitcher.lang.python.uri import SURIGenerator
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.intent import RefactorIntent


class SidecarUpdateMixin:
    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
        base_path = None
        for sp in sorted(search_paths, key=lambda p: len(p.parts), reverse=True):
            try:
                # Use is_relative_to for modern Python
                if path.is_relative_to(sp):
                    base_path = sp
                    break
            except (ValueError, AttributeError):
                # Fallback for older Python or different path types
                if str(path).startswith(str(sp)):
                    base_path = sp
                    break
                continue

        if base_path is None:
            return None

        rel_path = path.relative_to(base_path)
        return path_to_logical_fqn(rel_path.as_posix())

    def _calculate_fragments(
        self, module_fqn: Optional[str], old_fqn: str, new_fqn: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Derives symbol fragments by stripping the module FQN prefix.
        This correctly handles nested fragments like 'Class.method'.
        """
        old_fragment = old_fqn
        if module_fqn and old_fqn.startswith(module_fqn + "."):
            old_fragment = old_fqn.split(module_fqn + ".", 1)[1]

        new_fragment = new_fqn
        new_module_prefix = ".".join(new_fqn.split(".")[:-1])
        if module_fqn and new_module_prefix == module_fqn:
            if new_fqn.startswith(module_fqn + "."):
                new_fragment = new_fqn.split(module_fqn + ".", 1)[1]
        
        # If it's a move, the new_fqn will have a different module prefix.
        # The fragment itself might be the same.
        # e.g., old_fqn=a.b.C, new_fqn=x.y.C. The fragment is 'C'.
        if old_fqn.split(".")[-1] == new_fqn.split(".")[-1]:
             if module_fqn and old_fqn.startswith(module_fqn + "."):
                  old_fragment = old_fqn.split(module_fqn + ".", 1)[1]
             
             new_mod_fqn = self._get_module_fqn_from_symbol_fqn(new_fqn)
             if new_mod_fqn and new_fqn.startswith(new_mod_fqn + "."):
                 new_fragment = new_fqn.split(new_mod_fqn + ".", 1)[1]

        return old_fragment, new_fragment
    
    def _get_module_fqn_from_symbol_fqn(self, fqn: str) -> Optional[str]:
        if "." not in fqn:
            return None # Top-level module/file
        return fqn.rsplit(".", 1)[0]


    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        sidecar_path: Path,
        module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
        old_file_path: Optional[str] = None,
        new_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatcher for sidecar updates based on file type.
        """
        old_fragment, new_fragment = self._calculate_fragments(
            module_fqn, old_fqn, new_fqn
        )

        if sidecar_path.suffix == ".json":
            return self._update_json_data(
                data, old_file_path, new_file_path, old_fragment, new_fragment
            )
        elif sidecar_path.suffix in (".yaml", ".yml"):
            return self._update_yaml_data(data, old_fragment, new_fragment)

        return data

    def _update_json_data(
        self,
        data: Dict[str, Any],
        old_file_path: Optional[str],
        new_file_path: Optional[str],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
        """
        Updates Signature JSON data where keys are SURIs (py://path#fragment).
        """
        new_data = {}
        modified = False

        for key, value in data.items():
            if not key.startswith("py://"):
                new_data[key] = value
                continue

            try:
                path, fragment = SURIGenerator.parse(key)
            except ValueError:
                new_data[key] = value
                continue

            path_changed = False
            fragment_changed = False

            if old_file_path and new_file_path and path == old_file_path:
                path = new_file_path
                path_changed = True

            if old_fragment and new_fragment and fragment:
                if fragment == old_fragment:
                    fragment = new_fragment
                    fragment_changed = True
                elif fragment.startswith(old_fragment + "."):
                    suffix = fragment[len(old_fragment) :]
                    fragment = new_fragment + suffix
                    fragment_changed = True

            if path_changed or fragment_changed:
                new_key = (
                    SURIGenerator.for_symbol(path, fragment)
                    if fragment
                    else SURIGenerator.for_file(path)
                )
                new_data[new_key] = value
                modified = True
            else:
                new_data[key] = value

        return new_data if modified else data

    def _update_yaml_data(
        self,
        data: Dict[str, Any],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
        """
        Updates Doc YAML data where keys are Fragments (Short Names).
        """
        if not old_fragment or not new_fragment or old_fragment == new_fragment:
            return data

        new_data = {}
        modified = False

        for key, value in data.items():
            if key == old_fragment:
                new_data[new_fragment] = value
                modified = True
            elif key.startswith(old_fragment + "."):
                suffix = key[len(old_fragment) :]
                new_key = new_fragment + suffix
                new_data[new_key] = value
                modified = True
            else:
                new_data[key] = value

        return new_data if modified else data


class AbstractOperation(ABC):
    @abstractmethod
    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        pass