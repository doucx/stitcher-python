from typing import List, Optional
from pathlib import Path

from stitcher.lang.python.analysis.utils import path_to_logical_fqn


def path_to_fqn(path: Path, search_paths: List[Path]) -> Optional[str]:
    base_path = None
    # Find the longest matching search path as the base
    for sp in sorted(search_paths, key=lambda p: len(p.parts), reverse=True):
        try:
            if path.is_relative_to(sp):
                base_path = sp
                break
        except AttributeError:  # Python < 3.9
            try:
                path.relative_to(sp)
                base_path = sp
                break
            except ValueError:
                continue

    if base_path is None:
        return None

    rel_path = path.relative_to(base_path)
    return path_to_logical_fqn(rel_path.as_posix())