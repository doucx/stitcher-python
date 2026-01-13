from collections import defaultdict
from pathlib import Path
from typing import List, Dict, DefaultDict, TYPE_CHECKING
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
    LockSymbolUpdateIntent,
    LockPathUpdateIntent,
)
from stitcher.refactor.engine.renamer import GlobalBatchRenamer
from stitcher.lang.sidecar import (
    SidecarTransformer,
    SidecarTransformContext,
    SidecarAdapter,
)
from stitcher.lang.python.uri import PythonURIGenerator
from .utils import path_to_fqn


class Planner:
    def plan(self, spec: "MigrationSpec", ctx: RefactorContext) -> List[FileOp]:
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

        # Build a map of module renames from move intents. This is the source of truth
        # for determining the new module FQN context.
        module_rename_map: Dict[str, str] = {}
        for intent in all_intents:
            if isinstance(intent, MoveFileIntent):
                old_mod_fqn = path_to_fqn(intent.src_path, ctx.graph.search_paths)
                new_mod_fqn = path_to_fqn(intent.dest_path, ctx.graph.search_paths)
                if old_mod_fqn and new_mod_fqn:
                    module_rename_map[old_mod_fqn] = new_mod_fqn

        # Aggregate and process sidecar updates
        sidecar_updates: DefaultDict[Path, List[SidecarUpdateIntent]] = defaultdict(
            list
        )
        for intent in all_intents:
            if isinstance(intent, SidecarUpdateIntent):
                sidecar_updates[intent.sidecar_path].append(intent)

        sidecar_adapter = SidecarAdapter(ctx.workspace.root_path)
        sidecar_transformer = SidecarTransformer()
        for path, intents in sidecar_updates.items():
            # Load the sidecar file only once
            is_yaml = path.suffix in [".yaml", ".yml"]
            data = (
                sidecar_adapter.load_raw_data(path)
                if is_yaml
                else json.loads(path.read_text("utf-8"))
            )

            # Apply all intents for this file
            for intent in intents:
                old_module_fqn = intent.module_fqn
                if old_module_fqn is not None:
                    new_module_fqn = module_rename_map.get(old_module_fqn, old_module_fqn)
                else:
                    new_module_fqn = None

                transform_ctx = SidecarTransformContext(
                    old_module_fqn=old_module_fqn,
                    new_module_fqn=new_module_fqn,
                    old_fqn=intent.old_fqn,
                    new_fqn=intent.new_fqn,
                    old_file_path=intent.old_file_path,
                    new_file_path=intent.new_file_path,
                )
                data = sidecar_transformer.transform(path, data, transform_ctx)

            # Dump the final state
            content = (
                sidecar_adapter.dump_raw_data_to_string(data)
                if is_yaml
                else json.dumps(data, indent=2, sort_keys=True)
            )
            all_ops.append(WriteFileOp(path.relative_to(ctx.graph.root_path), content))

        # --- Process Lock Update Intents ---
        # Group updates by package root (stitcher.lock location)
        lock_updates: DefaultDict[Path, List[RefactorIntent]] = defaultdict(list)
        for intent in all_intents:
            if isinstance(intent, (LockSymbolUpdateIntent, LockPathUpdateIntent)):
                lock_updates[intent.package_root].append(intent)

        for pkg_root, intents in lock_updates.items():
            # Load existing lock data
            # Dict[suri, Fingerprint]
            lock_data = ctx.lock_manager.load(pkg_root)
            modified = False

            # We need to process path updates (Mass moves) first, then symbol updates
            # Sort intents: LockPathUpdateIntent first
            intents.sort(key=lambda x: 0 if isinstance(x, LockPathUpdateIntent) else 1)
            
            # Since we are iterating over the dict we are modifying, we collect updates first
            # Or use a new dict. Rebuilding is safer.
            # But wait, we have mixed intents.
            # Let's do in-place updates carefully or build a transition map.
            
            # Strategy: Apply intents sequentially to the in-memory state
            current_data = lock_data.copy()

            for intent in intents:
                next_data = {}
                
                if isinstance(intent, LockPathUpdateIntent):
                    # Mass update based on path prefix
                    # SURI format: py://<path>#<fragment>
                    prefix = f"py://{intent.old_path_prefix}"
                    new_prefix_str = f"py://{intent.new_path_prefix}"
                    
                    for suri, fp in current_data.items():
                        # We match exact file path OR directory prefix
                        # Exact file match: py://path/to/file.py#...
                        # Dir match: py://path/to/dir/...
                        
                        path, fragment = PythonURIGenerator.parse(suri)
                        
                        # Check if 'path' matches 'intent.old_path_prefix'
                        # Logic: 
                        # 1. path == old_prefix (File move)
                        # 2. path.startswith(old_prefix + "/") (Directory move)
                        
                        is_match = False
                        new_path = path
                        
                        if path == intent.old_path_prefix:
                            is_match = True
                            new_path = intent.new_path_prefix
                        elif path.startswith(intent.old_path_prefix + "/"):
                            is_match = True
                            suffix = path[len(intent.old_path_prefix):]
                            new_path = intent.new_path_prefix + suffix
                            
                        if is_match:
                            modified = True
                            # Reconstruct SURI
                            # TODO: Phase 3 inject generator
                            uri_gen = PythonURIGenerator()
                            new_suri = uri_gen.generate_symbol_uri(new_path, fragment) if fragment else uri_gen.generate_file_uri(new_path)
                            next_data[new_suri] = fp
                        else:
                            # Keep as is
                            next_data[suri] = fp
                            
                    current_data = next_data

                elif isinstance(intent, LockSymbolUpdateIntent):
                    # Single symbol rename
                    # Note: old_suri might have been changed by a previous LockPathUpdateIntent!
                    # This logic is complex if we mix moves and renames in one transaction.
                    # But typically Refactor operations are atomic or sequential.
                    # If we move file AND rename symbol in one go, we need to trace the identity.
                    # Current implementation assumes old_suri in intent is valid for the current state.
                    # But if we moved the file first, the SURI in 'current_data' has already changed.
                    # The intent.old_suri was calculated based on the INITIAL state.
                    
                    # This implies we need to transform the intent's old_suri if it was affected by previous moves?
                    # Or rely on the fact that RenameSymbolOperation calculates SURI based on definition node location?
                    # If we move the file, the definition node location (path) changes.
                    # Planner executes:
                    # 1. Renamer (modifies source code)
                    # 2. Sidecar Transformer (modifies sidecars)
                    # 3. Lock Updates
                    
                    # If we have MoveFile(A->B) AND Rename(A.C->A.D), 
                    # intents are generated from INITIAL state.
                    # MoveFile generates LockPathUpdate(A->B).
                    # Rename generates LockSymbolUpdate(A.C -> A.D) (Note: path is A).
                    
                    # If we apply PathUpdate first: A.C becomes B.C in `current_data`.
                    # Then we try to apply SymbolUpdate(A.C->A.D).
                    # A.C is no longer in `current_data`!
                    
                    # Solution: We need to check if intent.old_suri exists.
                    # If not, check if it was moved? That's hard.
                    
                    # BETTER APPROACH:
                    # RenameSymbolOperation updates the FRAGMENT.
                    # MoveFileOperation updates the PATH.
                    # SURIs are independent? No, SURI = Path + Fragment.
                    
                    # If we can't robustly compose them, we might assume user does one type of refactor at a time,
                    # OR we implement a robust SURI tracking mechanism.
                    # For now, let's implement basic handling and assume sequential consistency or disjoint operations.
                    
                    # For Rename, we just look for key.
                    if intent.old_suri in current_data:
                        fp = current_data.pop(intent.old_suri)
                        current_data[intent.new_suri] = fp
                        modified = True
                    # Fallback: maybe it was moved? 
                    # We skip complex resolution for MVP.

            if modified:
                content = ctx.lock_manager.serialize(current_data)
                rel_lock_path = (pkg_root / "stitcher.lock").relative_to(ctx.graph.root_path)
                all_ops.append(WriteFileOp(rel_lock_path, content))

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
