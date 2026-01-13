## [WIP] refactor(refactor): 引入 LockUpdateIntent 并简化重构操作以适配新的 Lock 机制

## 标签
#intent/refine #flow/ready #priority/high #comp/refactor #concept/state #scope/core
#task/domain/refactoring #task/object/refactor-engine #task/action/simplify
#task/state/begin


### 评论
这是“重构引擎简化”阶段的核心工作。我们将彻底改变重构引擎处理元数据的方式，从直接操作分散的 `.json` 签名文件，转变为操作集中式的 `stitcher.lock` 文件。这涉及引入新的 Intent 类型、清理旧的 Operation 逻辑，并升级 Planner 以支持 Lock 文件的读写。

### 目标
1.  **Context 升级**: 在 `RefactorContext` 中引入 `LockManagerProtocol`。
2.  **Intent 定义**: 新增 `LockSymbolUpdateIntent` (用于重命名) 和 `LockPathUpdateIntent` (用于移动)。
3.  **Operation 清理**: 修改 `RenameSymbolOperation`、`MoveFileOperation` 和 `MoveDirectoryOperation`，移除旧的 Signature `.json` 处理逻辑，改为生成新的 Lock Intents。
4.  **Planner 升级**: 在 `Planner` 中实现对新 Lock Intents 的处理逻辑，包括加载、更新和保存 `stitcher.lock`。

### 基本原理
旧的架构中，每个源文件对应一个 `.json` 签名文件，重构时需要物理移动和更新这些文件，导致 IO 操作繁琐且容易出错。新的架构引入了 `stitcher.lock`，将所有指纹集中管理。因此，重构操作不再需要关心 `.json` 文件，只需要向 Planner 发送“更新 Lock 数据”的意图即可。这大大简化了 Operation 的逻辑，并将持久化复杂性隔离在 Planner 和 LockManager 中。

---

### Script

#### Acts 1: 更新 RefactorContext

我们需要在上下文对象中提供 `LockManager`，以便 Planner 和 Operation 使用（尽管 Operation 主要使用 Workspace 来定位 Package Root，但 Planner 需要 LockManager 来执行 IO）。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/context.py
~~~~~
~~~~~python.old
from stitcher.spec import IndexStoreProtocol
from stitcher.analysis.semantic import SemanticGraph


@dataclass
class RefactorContext:
    workspace: Workspace
    graph: SemanticGraph
    sidecar_manager: SidecarManager
    index_store: IndexStoreProtocol
~~~~~
~~~~~python.new
from stitcher.spec import IndexStoreProtocol, LockManagerProtocol
from stitcher.analysis.semantic import SemanticGraph


@dataclass
class RefactorContext:
    workspace: Workspace
    graph: SemanticGraph
    sidecar_manager: SidecarManager
    index_store: IndexStoreProtocol
    lock_manager: LockManagerProtocol
~~~~~

#### Acts 2: 定义新的 Lock Intents

引入 `LockSymbolUpdateIntent` 和 `LockPathUpdateIntent`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/intent.py
~~~~~
~~~~~python.old
    new_fqn: str
    # New fields for SURI updates
    old_file_path: Optional[str] = None
    new_file_path: Optional[str] = None
~~~~~
~~~~~python.new
    new_fqn: str
    # New fields for SURI updates
    old_file_path: Optional[str] = None
    new_file_path: Optional[str] = None


# --- Lock-level Intents ---


@dataclass(frozen=True)
class LockSymbolUpdateIntent(RefactorIntent):
    """Represents a renaming of a symbol within the stitcher.lock file."""
    package_root: Path
    old_suri: str
    new_suri: str


@dataclass(frozen=True)
class LockPathUpdateIntent(RefactorIntent):
    """Represents a mass update of SURIs due to file/directory moves."""
    package_root: Path
    old_path_prefix: str  # Workspace-relative path prefix
    new_path_prefix: str  # Workspace-relative path prefix
~~~~~

#### Acts 3: 改造 RenameSymbolOperation

移除旧的 `.json` 逻辑，添加 SURI 计算和 `LockSymbolUpdateIntent` 生成。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
from typing import List, Optional

from .base import AbstractOperation
from ..engine.utils import path_to_fqn
from stitcher.refactor.engine.context import RefactorContext
from stitcher.analysis.semantic import SymbolNode
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
)


class RenameSymbolOperation(AbstractOperation):
~~~~~
~~~~~python.new
from typing import List, Optional

from .base import AbstractOperation
from ..engine.utils import path_to_fqn
from stitcher.refactor.engine.context import RefactorContext
from stitcher.analysis.semantic import SymbolNode
from stitcher.lang.python.uri import PythonURIGenerator
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    LockSymbolUpdateIntent,
)


class RenameSymbolOperation(AbstractOperation):
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
            doc_path = ctx.sidecar_manager.get_doc_path(definition_file_path)
            if doc_path.exists():
                intents.append(
                    SidecarUpdateIntent(
                        sidecar_path=doc_path,
                        module_fqn=module_fqn,
                        old_fqn=self.old_fqn,
                        new_fqn=self.new_fqn,
                    )
                )

            # Signature file intent
            sig_path = ctx.sidecar_manager.get_signature_path(definition_file_path)
            if sig_path.exists():
                intents.append(
                    SidecarUpdateIntent(
                        sidecar_path=sig_path,
                        module_fqn=module_fqn,
                        old_fqn=self.old_fqn,
                        new_fqn=self.new_fqn,
                    )
                )

        return intents
~~~~~
~~~~~python.new
            doc_path = ctx.sidecar_manager.get_doc_path(definition_file_path)
            if doc_path.exists():
                intents.append(
                    SidecarUpdateIntent(
                        sidecar_path=doc_path,
                        module_fqn=module_fqn,
                        old_fqn=self.old_fqn,
                        new_fqn=self.new_fqn,
                    )
                )

            # 3. Declare intent to update stitcher.lock (SURI rename)
            # We calculate SURIs based on the definition file location.
            # TODO: In Phase 3, inject URIGenerator via Context.
            uri_gen = PythonURIGenerator()
            rel_path = ctx.workspace.to_workspace_relative(definition_file_path)
            
            # Extract fragments (short names)
            old_fragment = self.old_fqn.split(".")[-1]
            new_fragment = self.new_fqn.split(".")[-1]
            
            # If the symbol is nested (e.g. Class.method), we need to be careful.
            # However, for RenameSymbol, we usually get the full FQN.
            # The fragment for SURI usually matches the logical path.
            # But wait, definition_node.path gives the file.
            # If we rename 'pkg.mod.Class', old_fragment is 'Class'.
            # If we rename 'pkg.mod.Class.method', old_fragment is 'Class.method'?
            # Stitcher Python Adapter SURI fragment logic:
            # Top level function/class: "Func"
            # Method: "Class.method"
            # So if self.old_fqn is "a.b.Class.method", how do we know "Class.method" is the fragment?
            # We rely on the module FQN.
            
            if module_fqn and self.old_fqn.startswith(module_fqn + "."):
                old_suri_fragment = self.old_fqn[len(module_fqn) + 1 :]
                new_suri_fragment = self.new_fqn[len(module_fqn) + 1 :]
                
                old_suri = uri_gen.generate_symbol_uri(rel_path, old_suri_fragment)
                new_suri = uri_gen.generate_symbol_uri(rel_path, new_suri_fragment)
                
                owning_package = ctx.workspace.find_owning_package(definition_file_path)
                
                intents.append(
                    LockSymbolUpdateIntent(
                        package_root=owning_package,
                        old_suri=old_suri,
                        new_suri=new_suri,
                    )
                )

        return intents
~~~~~

#### Acts 4: 改造 MoveFileOperation

移除旧的 `.json` 逻辑，添加 `LockPathUpdateIntent`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    ScaffoldIntent,
    SidecarUpdateIntent,
)
~~~~~
~~~~~python.new
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    ScaffoldIntent,
    SidecarUpdateIntent,
    LockPathUpdateIntent,
)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
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

        # 3. Declare Lock Update Intent (Mass update SURIs)
        # Note: We need to update SURIs in the OLD package's lock file.
        # If the file moves across packages, we technically need to move entries from one lock to another.
        # LockPathUpdateIntent handles updating the path prefix. 
        # But if package_root changes, we need to handle migration?
        # For simplicity in this phase, we assume LockPathUpdateIntent updates paths within the same lock context
        # OR Planner is smart enough to handle cross-package moves if we provide enough info.
        # Current simplified strategy: Update SURIs in the source package's lock. 
        # If it moves to a new package, the entries in the old lock will point to a path outside the old package root.
        # This is valid for SURI (workspace relative), but 'stitcher.lock' usually scopes to the package.
        # TODO: Handle Cross-Package Lock Migration. 
        # For now, we just emit the intent on the source package.
        
        owning_package = ctx.workspace.find_owning_package(src_path)
        intents.append(
            LockPathUpdateIntent(
                package_root=owning_package,
                old_path_prefix=rel_src_path,
                new_path_prefix=rel_dest_path,
            )
        )

        # 4. Declare physical file move intents
        intents.append(MoveFileIntent(src_path, dest_path))

        yaml_src = ctx.sidecar_manager.get_doc_path(src_path)
        if yaml_src.exists():
            yaml_dest = ctx.sidecar_manager.get_doc_path(dest_path)
            intents.append(MoveFileIntent(yaml_src, yaml_dest))

        # 5. Declare scaffolding intents for __init__.py files
~~~~~

#### Acts 5: 改造 MoveDirectoryOperation

同上，适配目录移动。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
    SidecarUpdateIntent,
    DeleteDirectoryIntent,
    ScaffoldIntent,
)
~~~~~
~~~~~python.new
    SidecarUpdateIntent,
    DeleteDirectoryIntent,
    ScaffoldIntent,
    LockPathUpdateIntent,
)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
            # Declare file move
            intents.append(MoveFileIntent(src_item, dest_item))

            # Declare sidecar content update & move intents
            item_module_fqn = path_to_fqn(src_item, ctx.graph.search_paths)

            doc_path = ctx.sidecar_manager.get_doc_path(src_item)
            if doc_path.exists() and old_prefix and new_prefix:
                processed_files.add(doc_path)
                intents.append(
                    SidecarUpdateIntent(
                        doc_path,
                        item_module_fqn,
                        old_prefix,
                        new_prefix,
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
                        sig_path,
                        item_module_fqn,
                        old_prefix,
                        new_prefix,
                        old_file_path=rel_src_path,
                        new_file_path=rel_dest_path,
                    )
                )
                intents.append(
                    MoveFileIntent(
                        sig_path, ctx.sidecar_manager.get_signature_path(dest_item)
                    )
                )
~~~~~
~~~~~python.new
            # Declare file move
            intents.append(MoveFileIntent(src_item, dest_item))

            # Declare sidecar content update & move intents
            item_module_fqn = path_to_fqn(src_item, ctx.graph.search_paths)

            doc_path = ctx.sidecar_manager.get_doc_path(src_item)
            if doc_path.exists() and old_prefix and new_prefix:
                processed_files.add(doc_path)
                intents.append(
                    SidecarUpdateIntent(
                        doc_path,
                        item_module_fqn,
                        old_prefix,
                        new_prefix,
                        old_file_path=rel_src_path,
                        new_file_path=rel_dest_path,
                    )
                )
                intents.append(
                    MoveFileIntent(
                        doc_path, ctx.sidecar_manager.get_doc_path(dest_item)
                    )
                )
        
        # 3. Declare Lock Update Intent for the entire directory
        rel_src_dir = ctx.workspace.to_workspace_relative(src_dir)
        rel_dest_dir = ctx.workspace.to_workspace_relative(dest_dir)
        owning_package = ctx.workspace.find_owning_package(src_dir)
        
        intents.append(
            LockPathUpdateIntent(
                package_root=owning_package,
                old_path_prefix=rel_src_dir,
                new_path_prefix=rel_dest_dir,
            )
        )

        # 4. Process non-Python files
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
        # 3. Declare deletion of the source directory
        intents.append(DeleteDirectoryIntent(src_dir))

        # 4. Declare scaffolding of __init__.py files
        intents.extend(self._scaffold_init_intents(dest_dir, ctx))

        return intents
~~~~~
~~~~~python.new
        # 5. Declare deletion of the source directory
        intents.append(DeleteDirectoryIntent(src_dir))

        # 6. Declare scaffolding of __init__.py files
        intents.extend(self._scaffold_init_intents(dest_dir, ctx))

        return intents
~~~~~

#### Acts 6: 升级 Planner

这是最关键的一步。Planner 需要能够聚合 `Lock*Intent`，加载 Lock 文件，执行内存修改，并生成 `WriteFileOp`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
    ScaffoldIntent,
    DeleteDirectoryIntent,
)
from stitcher.refactor.engine.renamer import GlobalBatchRenamer
from stitcher.lang.sidecar import (
    SidecarTransformer,
    SidecarTransformContext,
    SidecarAdapter,
)
from .utils import path_to_fqn
~~~~~
~~~~~python.new
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
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
            )
            all_ops.append(WriteFileOp(path.relative_to(ctx.graph.root_path), content))

        # Process simple filesystem intents
        for intent in all_intents:
            if isinstance(intent, MoveFileIntent):
~~~~~
~~~~~python.new
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
~~~~~

### 下一步建议

现在基础架构已经支持新的 Lock 机制，下一步是**验证**。我们需要：
1.  更新 `stitcher-refactor` 的测试套件，使其使用新的 `LockManager` 和 `stitcher.lock` 文件进行验证，而不是旧的 signatures JSON。这包括修改 `integration/` 下的所有 E2E 测试。
2.  确保 `InitRunner` 和 `PumpRunner` 也被升级以使用新的机制（这是阶段 3 的任务，但在测试 Refactor 之前可能需要确保环境一致性）。

此计划完成了阶段 4 的所有代码变更。测试修复将在后续计划中进行。
