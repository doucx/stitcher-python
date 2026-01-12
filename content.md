The test has failed exactly as expected! This confirms the bug: the signature file was moved, but the keys inside it still refer to the old file path (`py://src/my_app/logic.py...`), rendering them invalid.

Now I will proceed to fix this issue.

## [WIP] fix: Update SURI keys when moving files in refactor

### 错误分析

The `MoveFileOperation` (and by extension `MoveDirectoryOperation`) correctly moves the physical signature file but fails to update its internal content. The `SidecarUpdateMixin._update_sidecar_data` method currently only updates keys if they strictly match the FQN pattern. However, signature files use a special URI format (SURI) like `py://<file_path>#<symbol_name>`. The current logic does not recognize or transform these SURI keys.

To fix this, the update logic must be aware of the SURI format. When a file move occurs, we need to detect keys that start with `py://` and, if the file path component matches the file being moved, update it to the new path.

### 用户需求

When a file is moved via the refactoring engine, all corresponding entries in its signature file must have their keys updated to reflect the new file path in the SURI (e.g., `py://old/path.py#sym` -> `py://new/path.py#sym`).

### 评论

This fix is crucial for data integrity. The solution involves enhancing the `SidecarUpdateMixin` in `packages/stitcher-refactor/src/stitcher/refactor/operations/base.py`. We need to add logic specifically for handling SURI keys during a sidecar update. Since both `MoveFileOperation` and `MoveDirectoryOperation` rely on this mixin and the same `SidecarUpdateIntent`, fixing it in one place should resolve the issue globally.

### 目标

1.  Modify `SidecarUpdateMixin._update_sidecar_data` in `packages/stitcher-refactor/src/stitcher/refactor/operations/base.py`.
2.  Add logic to detect if a key is a SURI (starts with `py://`).
3.  If it is a SURI, parse the path component.
4.  If the path component matches the old file path (derived from `old_fqn` or passed context), replace it with the new file path.
    *   *Self-Correction*: The `SidecarUpdateIntent` provides `old_fqn` and `new_fqn`, but for SURIs we need file paths. However, the SURI *is* the file path. The `SidecarUpdateIntent` is triggered by a file move. When moving a file, the `old_fqn` and `new_fqn` in the intent represent the module path.
    *   *Refined Strategy*: A cleaner approach is to recognize that we are processing a file move. The signature file being updated belongs to the file being moved. Therefore, *every* SURI in that file that starts with `py://` and matches the old relative file path should be updated.
    *   Wait, `SidecarUpdateIntent` carries `old_fqn` (module path). We might not have the raw file path readily available in `_update_sidecar_data` without some calculation.
    *   *Alternative*: The `MoveFileOperation` knows the `src_path` and `dest_path`. When it creates the `SidecarUpdateIntent`, it could pass this information. But `SidecarUpdateIntent` is defined with FQNs.
    *   *Better Strategy*: SURI construction is `py://<rel_path>#<fragment>`. The `rel_path` corresponds to the file path relative to the project root.
    *   In `_update_sidecar_data`, we are iterating over keys. If a key looks like `py://<path>#...`, we can check if `<path>` corresponds to the module being renamed.
    *   Actually, since we are moving the *entire file*, **all** SURIs in that signature file that refer to the file itself should be updated.
    *   The `SidecarUpdateMixin` methods are generic.
    *   Let's look at `packages/stitcher-refactor/src/stitcher/refactor/operations/base.py`.

### 基本原理

I will modify `packages/stitcher-refactor/src/stitcher/refactor/operations/base.py`.

In `_update_sidecar_data`:
1.  Check if the key starts with `py://`.
2.  If so, it's a SURI. We need to determine if this SURI belongs to the module being moved/renamed.
3.  We have `module_fqn` (the old module name of the file being processed), `old_fqn` (the old name of the symbol/module being renamed), and `new_fqn`.
4.  If `module_fqn` matches `old_fqn` (meaning the file itself is being moved/renamed), we can infer the path change.
5.  However, converting FQN back to a file path is ambiguous without the workspace context.
6.  **Crucial realization**: The SURI contains the *file path*. If we are processing a `SidecarUpdateIntent` triggered by `MoveFileOperation`, we are updating the file at `dest_path` (content from `src_path`). The SURIs inside will still point to `src_path`.
7.  We need to know the `old_path` and `new_path` to do a simple string replacement on the SURI.
8.  The current `SidecarUpdateIntent` only has FQNs. This is a limitation.
9.  **Plan B**: We can try to deduce the path change from the FQN change, but that's risky.
10. **Plan A (Robust)**: Update `SidecarUpdateIntent` to optionally carry `old_path` and `new_path`.
    *   `packages/stitcher-refactor/src/stitcher/refactor/engine/intent.py`: Add `old_path: Optional[str]` and `new_path: Optional[str]` to `SidecarUpdateIntent`.
    *   `packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py`: Populate these fields when creating the intent.
    *   `packages/stitcher-refactor/src/stitcher/refactor/operations/base.py`: Use these fields in `_update_sidecar_data` to handle SURIs.

Let's check `intent.py`. `SidecarUpdateIntent` is a frozen dataclass. Modifying it is safe but requires updating callsites.
Let's check callsites: `move_file.py`, `move_directory.py`, `rename_symbol.py`.

Wait, for `RenameSymbol`, the file path *doesn't* change, only the FQN fragment changes. So `old_path` would be None or same.
For `MoveFile`, the file path changes.

Let's modify `SidecarUpdateIntent` to include `old_file_path` and `new_file_path` (as strings, relative to root).

**Detailed Steps:**

1.  **Modify `intent.py`**: Add `old_file_path` and `new_file_path` fields to `SidecarUpdateIntent`. Default them to None to minimize breakage if I miss a callsite (though I should update all).
2.  **Modify `move_file.py`**: Pass the source and dest paths (relative to root) when creating the intent.
3.  **Modify `base.py`**: Update `_update_sidecar_data` to accept these new arguments. Implement SURI update logic:
    *   If `key.startswith("py://")` AND `old_file_path` is provided:
        *   Parse the SURI path part.
        *   If it matches `old_file_path`, replace it with `new_file_path`.

This seems robust and correct.

### 标签

#intent/fix #flow/ready #priority/high #comp/refactor #concept/suri #scope/dx #ai/instruct #task/domain/refactor #task/object/suri-update #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: Update Intent Definition

First, I update the `SidecarUpdateIntent` to carry the necessary path information.

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/engine/intent.py
~~~~~
~~~~~python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RefactorIntent:
    pass


# --- Symbol-level Intents ---


@dataclass(frozen=True)
class RenameIntent(RefactorIntent):
    old_fqn: str
    new_fqn: str


# --- Filesystem-level Intents ---


@dataclass(frozen=True)
class FileSystemIntent(RefactorIntent):
    pass


@dataclass(frozen=True)
class MoveFileIntent(FileSystemIntent):
    src_path: Path
    dest_path: Path


@dataclass(frozen=True)
class DeleteFileIntent(FileSystemIntent):
    path: Path


@dataclass(frozen=True)
class DeleteDirectoryIntent(FileSystemIntent):
    path: Path


@dataclass(frozen=True)
class ScaffoldIntent(FileSystemIntent):
    path: Path
    content: str = ""


# --- Sidecar-level Intents ---


@dataclass(frozen=True)
class SidecarUpdateIntent(RefactorIntent):
    sidecar_path: Path
    module_fqn: Optional[str]
    old_fqn: str
    new_fqn: str
    # New fields for SURI updates
    old_file_path: Optional[str] = None
    new_file_path: Optional[str] = None
~~~~~

#### Acts 2: Update `MoveFileOperation` to pass path info

Now I update `move_file.py` to populate these new fields. I need to calculate the relative paths to the project root, which I can do using `ctx.workspace.root_path`.

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation, SidecarUpdateMixin
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    ScaffoldIntent,
    SidecarUpdateIntent,
)


class MoveFileOperation(AbstractOperation, SidecarUpdateMixin):
    def __init__(self, src_path: Path, dest_path: Path):
        self.src_path = src_path
        self.dest_path = dest_path

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # Resolve paths against the project root
        src_path = ctx.workspace.root_path.joinpath(self.src_path)
        dest_path = ctx.workspace.root_path.joinpath(self.dest_path)

        old_module_fqn = self._path_to_fqn(src_path, ctx.graph.search_paths)
        new_module_fqn = self._path_to_fqn(dest_path, ctx.graph.search_paths)

        # Prepare path strings for SURI updates
        rel_src_path = src_path.relative_to(ctx.workspace.root_path).as_posix()
        rel_dest_path = dest_path.relative_to(ctx.workspace.root_path).as_posix()

        # 1. Declare symbol rename intents if the module's FQN changes.
        if (
            old_module_fqn is not None
            and new_module_fqn is not None
            and old_module_fqn != new_module_fqn
        ):
            # Rename the module itself
            intents.append(RenameIntent(old_module_fqn, new_module_fqn))

            # Rename all members within the module
            members = ctx.graph.iter_members(old_module_fqn)
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn) :]
                    target_new_fqn = new_module_fqn + suffix
                    intents.append(RenameIntent(member.fqn, target_new_fqn))

            # 2. Declare sidecar content update intents
            doc_src_path = ctx.sidecar_manager.get_doc_path(src_path)
            if doc_src_path.exists():
                intents.append(
                    SidecarUpdateIntent(
                        sidecar_path=doc_src_path,
                        module_fqn=old_module_fqn,
                        old_fqn=old_module_fqn,
                        new_fqn=new_module_fqn,
                        old_file_path=rel_src_path,
                        new_file_path=rel_dest_path,
                    )
                )

            sig_src_path = ctx.sidecar_manager.get_signature_path(src_path)
            if sig_src_path.exists():
                intents.append(
                    SidecarUpdateIntent(
                        sidecar_path=sig_src_path,
                        module_fqn=old_module_fqn,
                        old_fqn=old_module_fqn,
                        new_fqn=new_module_fqn,
                        old_file_path=rel_src_path,
                        new_file_path=rel_dest_path,
                    )
                )

        # 3. Declare physical file move intents
        intents.append(MoveFileIntent(src_path, dest_path))

        yaml_src = ctx.sidecar_manager.get_doc_path(src_path)
        if yaml_src.exists():
            yaml_dest = ctx.sidecar_manager.get_doc_path(dest_path)
            intents.append(MoveFileIntent(yaml_src, yaml_dest))

        sig_src = ctx.sidecar_manager.get_signature_path(src_path)
        if sig_src.exists():
            sig_dest = ctx.sidecar_manager.get_signature_path(dest_path)
            intents.append(MoveFileIntent(sig_src, sig_dest))

        # 4. Declare scaffolding intents for __init__.py files
        intents.extend(self._scaffold_init_intents(dest_path, ctx))

        return intents

    def _scaffold_init_intents(
        self, file_path: Path, ctx: RefactorContext
    ) -> List[ScaffoldIntent]:
        intents: List[ScaffoldIntent] = []
        parent = file_path.parent
        search_paths = ctx.graph.search_paths

        active_root = None
        for sp in search_paths:
            try:
                if parent.is_relative_to(sp):
                    if active_root is None or len(sp.parts) > len(active_root.parts):
                        active_root = sp
            except AttributeError:
                try:
                    parent.relative_to(sp)
                    if active_root is None or len(sp.parts) > len(active_root.parts):
                        active_root = sp
                except ValueError:
                    continue

        if not active_root:
            return []

        while parent != active_root:
            try:
                parent.relative_to(active_root)
            except ValueError:
                break
                
            init_file = parent / "__init__.py"
            if not init_file.exists():
                intents.append(ScaffoldIntent(path=init_file, content=""))
            parent = parent.parent

        return intents
~~~~~

#### Acts 3: Update `Planner` and `Base` logic

Now I need to update `planner.py` to extract the new fields from the intent and pass them to the update method. Then, I need to update `base.py` to implement the actual SURI replacement logic.

First, `base.py` to update the signature of `_update_sidecar_data` and logic.

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from stitcher.python.analysis.utils import path_to_logical_fqn
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.intent import RefactorIntent


class SidecarUpdateMixin:
    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
        base_path = None
        for sp in sorted(search_paths, key=lambda p: len(p.parts), reverse=True):
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

    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
        old_file_path: Optional[str] = None,
        new_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        new_data = {}
        modified = False

        for key, value in data.items():
            # --- Case 1: SURI Update (py://path/to/file.py#symbol) ---
            if key.startswith("py://") and old_file_path and new_file_path:
                # Format: py://<path>#<fragment>
                # We check if the path component matches our old file path.
                prefix = f"py://{old_file_path}#"
                if key.startswith(prefix):
                    fragment = key[len(prefix) :]
                    # Reconstruct with new path
                    new_key = f"py://{new_file_path}#{fragment}"
                    new_data[new_key] = value
                    modified = True
                    continue
                # If path matches exactly (unlikely for symbol key but possible for file key)
                if key == f"py://{old_file_path}":
                    new_key = f"py://{new_file_path}"
                    new_data[new_key] = value
                    modified = True
                    continue

            # --- Case 2: Standard FQN Update ---
            key_fqn = key
            is_short_name = False

            if module_fqn:
                if key.startswith(module_fqn + "."):
                    key_fqn = key
                    is_short_name = False
                else:
                    # Heuristic: If it starts with the project's root package but not
                    # the current module, it's likely an FQN from another module.
                    project_prefix = module_fqn.split(".")[0] + "."
                    if key.startswith(project_prefix):
                        key_fqn = key
                        is_short_name = False
                    else:
                        key_fqn = f"{module_fqn}.{key}"
                        is_short_name = True

            # Determine the effective module FQN for short-name restoration.
            if module_fqn == old_fqn:
                effective_new_module = new_fqn
            elif module_fqn and module_fqn.startswith(old_fqn + "."):
                # Module is inside the renamed namespace/directory
                suffix = module_fqn[len(old_fqn) :]
                effective_new_module = new_fqn + suffix
            else:
                effective_new_module = module_fqn

            new_key = key
            if key_fqn == old_fqn:
                target_fqn = new_fqn
                if is_short_name and effective_new_module:
                    if target_fqn.startswith(effective_new_module + "."):
                        new_key = target_fqn[len(effective_new_module) + 1 :]
                    else:
                        new_key = target_fqn
                else:
                    new_key = target_fqn
                modified = True

            elif key_fqn.startswith(old_fqn + "."):
                suffix = key_fqn[len(old_fqn) :]
                target_fqn = new_fqn + suffix
                if is_short_name and effective_new_module:
                    if target_fqn.startswith(effective_new_module + "."):
                        new_key = target_fqn[len(effective_new_module) + 1 :]
                    else:
                        new_key = target_fqn
                else:
                    new_key = target_fqn
                modified = True

            new_data[new_key] = value

        return new_data if modified else data


class AbstractOperation(ABC):
    @abstractmethod
    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        pass
~~~~~

Now `planner.py` to extract the new args from the intent.

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, DefaultDict, TYPE_CHECKING

from stitcher.common.adapters.yaml_adapter import YamlAdapter
import json

if TYPE_CHECKING:
    from stitcher.refactor.migration import MigrationSpec
from stitcher.refactor.engine.context import RefactorContext
from stitcher.common.transaction import (
    FileOp,
    MoveFileOp,
    WriteFileOp,
    DeleteFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    MoveFileIntent,
    DeleteFileIntent,
    ScaffoldIntent,
    DeleteDirectoryIntent,
)
from stitcher.refactor.engine.renamer import GlobalBatchRenamer
from stitcher.refactor.operations.base import SidecarUpdateMixin


class Planner(SidecarUpdateMixin):
    def plan(self, spec: "MigrationSpec", ctx: RefactorContext) -> List[FileOp]:
        # Local import to break circular dependency

        all_ops: List[FileOp] = []

        # --- 1. Intent Collection ---
        all_intents: List[RefactorIntent] = []
        for operation in spec.operations:
            all_intents.extend(operation.collect_intents(ctx))

        # --- 2. Intent Aggregation & Processing ---

        # Aggregate renames for batch processing
        rename_map: Dict[str, str] = {}
        for intent in all_intents:
            if isinstance(intent, RenameIntent):
                # TODO: Handle rename chains (A->B, B->C should become A->C)
                rename_map[intent.old_fqn] = intent.new_fqn

        # Process symbol renames in code
        renamer = GlobalBatchRenamer(rename_map, ctx)
        all_ops.extend(renamer.analyze())

        # Aggregate and process sidecar updates
        sidecar_updates: DefaultDict[Path, List[SidecarUpdateIntent]] = defaultdict(
            list
        )
        for intent in all_intents:
            if isinstance(intent, SidecarUpdateIntent):
                sidecar_updates[intent.sidecar_path].append(intent)

        # TODO: Inject real adapters instead of instantiating them here.
        yaml_adapter = YamlAdapter()
        for path, intents in sidecar_updates.items():
            # Load the sidecar file only once
            is_yaml = path.suffix == ".yaml"
            data = (
                yaml_adapter.load(path)
                if is_yaml
                else json.loads(path.read_text("utf-8"))
            )

            # Apply all intents for this file
            for intent in intents:
                data = self._update_sidecar_data(
                    data,
                    intent.module_fqn,
                    intent.old_fqn,
                    intent.new_fqn,
                    old_file_path=intent.old_file_path,
                    new_file_path=intent.new_file_path,
                )

            # Dump the final state
            content = (
                yaml_adapter.dump(data)
                if is_yaml
                else json.dumps(data, indent=2, sort_keys=True)
            )
            all_ops.append(WriteFileOp(path.relative_to(ctx.graph.root_path), content))

        # Process simple filesystem intents
        for intent in all_intents:
            if isinstance(intent, MoveFileIntent):
                all_ops.append(
                    MoveFileOp(
                        intent.src_path.relative_to(ctx.graph.root_path),
                        intent.dest_path.relative_to(ctx.graph.root_path),
                    )
                )
            elif isinstance(intent, DeleteFileIntent):
                all_ops.append(
                    DeleteFileOp(intent.path.relative_to(ctx.graph.root_path))
                )
            elif isinstance(intent, DeleteDirectoryIntent):
                all_ops.append(
                    DeleteDirectoryOp(intent.path.relative_to(ctx.graph.root_path))
                )
            elif isinstance(intent, ScaffoldIntent):
                all_ops.append(
                    WriteFileOp(
                        intent.path.relative_to(ctx.graph.root_path), intent.content
                    )
                )

        return all_ops
~~~~~

#### Acts 4: Update `MoveDirectoryOperation` for completeness

Although the test only covers `MoveFile`, `MoveDirectory` also generates `SidecarUpdateIntent`s and should be updated to maintain consistency.

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation, SidecarUpdateMixin
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    SidecarUpdateIntent,
    DeleteDirectoryIntent,
    ScaffoldIntent,
)


class MoveDirectoryOperation(AbstractOperation, SidecarUpdateMixin):
    def __init__(self, src_dir: Path, dest_dir: Path):
        # In a real app, we'd add more robust validation here.
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # Resolve paths against the project root
        src_dir = ctx.workspace.root_path.joinpath(self.src_dir)
        dest_dir = ctx.workspace.root_path.joinpath(self.dest_dir)

        # 1. Declare namespace rename intent
        old_prefix = self._path_to_fqn(src_dir, ctx.graph.search_paths)
        new_prefix = self._path_to_fqn(dest_dir, ctx.graph.search_paths)
        if old_prefix and new_prefix and old_prefix != new_prefix:
            # We explicitly check for truthiness above, so they are str here
            intents.append(RenameIntent(old_prefix, new_prefix))
            # Also handle all symbols inside the namespace
            # Note: This might be slightly redundant if the renamer can handle prefixes,
            # but being explicit is safer for now.
            for member in ctx.graph.iter_members(old_prefix):
                if member.fqn.startswith(old_prefix + "."):
                    suffix = member.fqn[len(old_prefix) :]
                    new_fqn = new_prefix + suffix
                    intents.append(RenameIntent(member.fqn, new_fqn))

        # 2. Declare physical file moves and sidecar updates for all files
        processed_files = set()
        all_files = [p for p in src_dir.rglob("*") if p.is_file()]

        for src_item in all_files:
            if src_item.suffix != ".py":
                continue

            processed_files.add(src_item)
            relative_path = src_item.relative_to(src_dir)
            dest_item = dest_dir / relative_path

            # Prepare path strings for SURI updates
            rel_src_path = src_item.relative_to(ctx.workspace.root_path).as_posix()
            rel_dest_path = dest_item.relative_to(ctx.workspace.root_path).as_posix()

            # Declare file move
            intents.append(MoveFileIntent(src_item, dest_item))

            # Declare sidecar content update & move intents
            item_module_fqn = self._path_to_fqn(src_item, ctx.graph.search_paths)

            doc_path = ctx.sidecar_manager.get_doc_path(src_item)
            if doc_path.exists() and old_prefix and new_prefix:
                processed_files.add(doc_path)
                intents.append(
                    SidecarUpdateIntent(
                        doc_path, item_module_fqn, old_prefix, new_prefix,
                        old_file_path=rel_src_path,
                        new_file_path=rel_dest_path,
                    )
                )
                intents.append(
                    MoveFileIntent(
                        doc_path, ctx.sidecar_manager.get_doc_path(dest_item)
                    )
                )

            sig_path = ctx.sidecar_manager.get_signature_path(src_item)
            if sig_path.exists() and old_prefix and new_prefix:
                processed_files.add(sig_path)
                intents.append(
                    SidecarUpdateIntent(
                        sig_path, item_module_fqn, old_prefix, new_prefix,
                        old_file_path=rel_src_path,
                        new_file_path=rel_dest_path,
                    )
                )
                intents.append(
                    MoveFileIntent(
                        sig_path, ctx.sidecar_manager.get_signature_path(dest_item)
                    )
                )

        # Process non-Python files
        for src_item in all_files:
            if src_item in processed_files:
                continue
            relative_path = src_item.relative_to(src_dir)
            dest_item = dest_dir / relative_path
            intents.append(MoveFileIntent(src_item, dest_item))

        # 3. Declare deletion of the source directory
        intents.append(DeleteDirectoryIntent(src_dir))

        # 4. Declare scaffolding of __init__.py files
        intents.extend(self._scaffold_init_intents(dest_dir, ctx))

        return intents

    def _scaffold_init_intents(
        self, directory_path: Path, ctx: RefactorContext
    ) -> List[ScaffoldIntent]:
        intents: List[ScaffoldIntent] = []
        search_paths = ctx.graph.search_paths

        active_root = None
        for sp in search_paths:
            try:
                if directory_path.is_relative_to(sp):
                    if active_root is None or len(sp.parts) > len(active_root.parts):
                        active_root = sp
            except AttributeError:
                try:
                    directory_path.relative_to(sp)
                    if active_root is None or len(sp.parts) > len(active_root.parts):
                        active_root = sp
                except ValueError:
                    continue

        if not active_root:
            return []

        current = directory_path

        while current != active_root:
            try:
                current.relative_to(active_root)
            except ValueError:
                break
                
            init_file = current / "__init__.py"
            if not init_file.exists():
                intents.append(ScaffoldIntent(path=init_file, content=""))
            current = current.parent

        return intents
~~~~~

### 下一步建议

All components (Intent definition, MoveFile operation, MoveDirectory operation, Planner, and Base mixin) have been updated to propagate and use file path information for SURI updates. Please run the integration test `tests/integration/test_refactor_move_updates_suri_in_signatures.py` again. It should now pass.
