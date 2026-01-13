好的，我来修复由上次大规模重构引发的类型错误和导入错误。这些错误是意料之中的，因为我们拆除了一个核心组件 (`SidecarUpdateMixin`)，现在需要调整其周边的代码以适应新的、由 Planner 驱动的架构。

## [WIP] fix: Resolve type errors and imports after Mixin removal

### 错误分析

1.  **`ImportError`**: `SidecarUpdateMixin` 已被删除，但 `move_file.py` 和 `move_directory.py` 仍在尝试导入和继承它。
2.  **Pyright: Unbound Variable**: `sidecar.py` 中的 `update_keys` 方法，`parser` 变量的作用域让类型检查器感到困惑。
3.  **Pyright: `None` is not iterable**: `planner.py` 在未检查 `find_symbol_by_fqn` 返回 `None` 的情况下就尝试对其结果进行元组解包。
4.  **逻辑缺失**: `MoveFileOperation` 和 `MoveDirectoryOperation` 依赖 `_path_to_fqn` 来生成 `RenameIntent`，这个辅助函数随着 Mixin 的删除而消失了。
5.  **核心数据流中断**: `Planner` 在处理 SURI 重命名时，无法从 `UsageLocation` 对象中获取原始的 SURI key，因为它只携带了 FQN。

### 评论

这些错误是架构演进过程中的正常现象。修复它们不仅仅是修正语法，更是将新架构的思想（职责分离、索引驱动）贯彻到每一个组件中的过程。通过这次修复，我们将完成从旧模型到新模型的过渡。

### 目标

1.  创建一个新的 `operations/utils.py` 文件，用于存放 `path_to_fqn` 这样的共享辅助函数。
2.  修正 `move_file.py` 和 `move_directory.py`，移除对已删除 Mixin 的引用，并改用新的工具函数。
3.  增强核心数据模型 `UsageLocation`，使其能同时携带符号的 FQN 和 ID (SURI)。
4.  更新 `SemanticGraph.find_usages` 以填充这个增强后的数据模型。
5.  重构 `Planner` 以使用增强后的 `UsageLocation` 来正确处理 SURI 重命名，并修复类型错误。
6.  重构 `SidecarUpdater` 以消除类型检查器的警告。

### 基本原理

我们将把 `path_to_fqn` 逻辑提取到一个公共位置。然后，我们将打通从 `IndexStore` -> `SemanticGraph` -> `Planner` 的数据流，确保 `UsageLocation` 携带足够的信息（FQN 和 SURI），让 `Planner` 能够确定性地生成所有文件（代码和 Sidecar）的更新操作，而无需任何猜测。

### 标签

#intent/fix #flow/ready #priority/critical #comp/refactor #concept/engine #scope/core #ai/instruct #task/domain/refactoring #task/object/type-errors #task/action/fix #task.state/continue

---

### Script

#### Acts 1: 创建共享工具并修复 Operation 类

首先，我们创建 `utils.py` 并修复 `ImportError`。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/utils.py
~~~~~
~~~~~python
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
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
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
~~~~~python.new
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    ScaffoldIntent,
)


class MoveFileOperation(AbstractOperation):
    def __init__(self, src_path: Path, dest_path: Path):
        self.src_path = src_path
        self.dest_path = dest_path

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # Resolve paths against the project root
        src_path = ctx.workspace.root_path.joinpath(self.src_path)
        dest_path = ctx.workspace.root_path.joinpath(self.dest_path)

        old_module_fqn = path_to_fqn(src_path, ctx.graph.search_paths)
        new_module_fqn = path_to_fqn(dest_path, ctx.graph.search_paths)

        # 1. Declare symbol rename intents if the module's FQN changes.
        if (
            old_module_fqn is not None
            and new_module_fqn is not None
            and old_module_fqn != new_module_fqn
        ):
            intents.append(RenameIntent(old_module_fqn, new_module_fqn))
            members = ctx.graph.iter_members(old_module_fqn)
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn) :]
                    target_new_fqn = new_module_fqn + suffix
                    intents.append(RenameIntent(member.fqn, target_new_fqn))

        # 2. Declare physical file move intents for main file and sidecars
        intents.append(MoveFileIntent(src_path, dest_path))
        for get_sidecar_path in [
            ctx.sidecar_manager.get_doc_path,
            ctx.sidecar_manager.get_signature_path,
        ]:
            sidecar_src = get_sidecar_path(src_path)
            if sidecar_src.exists():
                sidecar_dest = get_sidecar_path(dest_path)
                intents.append(MoveFileIntent(sidecar_src, sidecar_dest))

        # 3. Declare scaffolding intents for __init__.py files
        intents.extend(self._scaffold_init_intents(dest_path, ctx))
        return intents

    def _scaffold_init_intents(
        self, file_path: Path, ctx: RefactorContext
    ) -> List[ScaffoldIntent]:
        intents: List[ScaffoldIntent] = []
        parent = file_path.parent
        search_paths = ctx.graph.search_paths
        active_root = next(
            (
                sp
                for sp in sorted(
                    search_paths, key=lambda p: len(p.parts), reverse=True
                )
                if parent.is_relative_to(sp)
            ),
            None,
        )

        if not active_root:
            return []

        while parent != active_root and not (parent / "__init__.py").exists():
            intents.append(ScaffoldIntent(path=parent / "__init__.py", content=""))
            parent = parent.parent
        return intents
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
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
~~~~~python.new
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    DeleteDirectoryIntent,
    ScaffoldIntent,
)


class MoveDirectoryOperation(AbstractOperation):
    def __init__(self, src_dir: Path, dest_dir: Path):
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []
        src_dir = ctx.workspace.root_path.joinpath(self.src_dir)
        dest_dir = ctx.workspace.root_path.joinpath(self.dest_dir)

        # 1. Declare namespace rename intent
        old_prefix = path_to_fqn(src_dir, ctx.graph.search_paths)
        new_prefix = path_to_fqn(dest_dir, ctx.graph.search_paths)
        if old_prefix and new_prefix and old_prefix != new_prefix:
            intents.append(RenameIntent(old_prefix, new_prefix))
            for member in ctx.graph.iter_members(old_prefix):
                if member.fqn.startswith(old_prefix + "."):
                    suffix = member.fqn[len(old_prefix) :]
                    new_fqn = new_prefix + suffix
                    intents.append(RenameIntent(member.fqn, new_fqn))

        # 2. Declare physical file moves for all files within the directory
        if src_dir.is_dir():
            for src_item in src_dir.rglob("*"):
                if not src_item.is_file():
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
        active_root = next(
            (
                sp
                for sp in sorted(
                    search_paths, key=lambda p: len(p.parts), reverse=True
                )
                if directory_path.is_relative_to(sp)
            ),
            None,
        )

        if not active_root:
            return []

        current = directory_path
        while current != active_root and not (current / "__init__.py").exists():
            intents.append(ScaffoldIntent(path=current / "__init__.py", content=""))
            current = current.parent
        return intents
~~~~~

#### Acts 2: 增强核心数据模型和查询逻辑

现在我们打通数据流，让 SURI ID 能流向 Planner。

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/models.py
~~~~~
~~~~~python.old
@dataclass
class UsageLocation:
    file_path: Path
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    ref_type: ReferenceType
    target_node_fqn: str

    @property
~~~~~
~~~~~python.new
@dataclass
class UsageLocation:
    file_path: Path
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    ref_type: ReferenceType
    target_node_fqn: Optional[str]
    target_node_id: Optional[str] = None

    @property
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/semantic/graph.py
~~~~~
~~~~~python.old
            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=ref.lineno,
                    col_offset=ref.col_offset,
                    end_lineno=ref.end_lineno,
                    end_col_offset=ref.end_col_offset,
                    ref_type=ref_type,
                    target_node_fqn=ref.target_fqn or target_fqn, # Fallback if target_fqn is NULL (SURI refs)
                )
            )

        # 2. Find the definition itself and treat it as a usage site
        definition_result = self.index_store.find_symbol_by_fqn(target_fqn)
~~~~~
~~~~~python.new
            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=ref.lineno,
                    col_offset=ref.col_offset,
                    end_lineno=ref.end_lineno,
                    end_col_offset=ref.end_col_offset,
                    ref_type=ref_type,
                    target_node_fqn=ref.target_fqn,
                    target_node_id=ref.target_id,
                )
            )

        # 2. Find the definition itself and treat it as a usage site
        definition_result = self.index_store.find_symbol_by_fqn(target_fqn)
~~~~~

#### Acts 3: 修复并增强 Planner 和 SidecarUpdater

最后，我们让 Planner 和 Updater 使用新的数据模型，并修复类型错误。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/sidecar.py
~~~~~
~~~~~python.old
from typing import Dict, Any, List, Tuple
from ruamel.yaml import YAML
import json
from io import StringIO


class SidecarUpdater:
    def update_keys(
        self, content: str, rename_map: Dict[str, str], is_yaml: bool
    ) -> str:
        """
        Loads a sidecar file (YAML or JSON), renames top-level keys
        according to the rename_map, and returns the updated content.
        """
        if is_yaml:
            parser = YAML()
            data = parser.load(content)
        else:
            data = json.loads(content)

        if not isinstance(data, dict):
            return content

        new_data = {}
        for key, value in data.items():
            new_key = rename_map.get(key, key)
            new_data[new_key] = value

        if is_yaml:
            string_stream = StringIO()
            parser.dump(new_data, string_stream)
            return string_stream.getvalue()
        else:
            return json.dumps(new_data, indent=2, sort_keys=True)
~~~~~
~~~~~python.new
from typing import Dict, Any
from ruamel.yaml import YAML
import json
from io import StringIO


class SidecarUpdater:
    def update_keys(
        self, content: str, rename_map: Dict[str, str], is_yaml: bool
    ) -> str:
        """
        Loads a sidecar file (YAML or JSON), renames top-level keys
        according to the rename_map, and returns the updated content.
        """
        if is_yaml:
            return self._update_yaml_keys(content, rename_map)
        else:
            return self._update_json_keys(content, rename_map)

    def _update_yaml_keys(self, content: str, rename_map: Dict[str, str]) -> str:
        parser = YAML()
        data = parser.load(content)
        if not isinstance(data, dict):
            return content

        new_data = {rename_map.get(k, k): v for k, v in data.items()}

        string_stream = StringIO()
        parser.dump(new_data, string_stream)
        return string_stream.getvalue()

    def _update_json_keys(self, content: str, rename_map: Dict[str, str]) -> str:
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return content
        except json.JSONDecodeError:
            return content

        new_data = {rename_map.get(k, k): v for k, v in data.items()}
        return json.dumps(new_data, indent=2, sort_keys=True)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
            elif file_path.suffix == ".json":
                # For JSON, the key is the SURI. We need to construct the SURI rename map.
                suri_rename_map = {}
                for loc in locations:
                    old_fqn = loc.target_node_fqn
                    if old_fqn in rename_map:
                        new_fqn = rename_map[old_fqn]
                        # This is a simplification. It doesn't handle module moves well.
                        # It assumes the file path part of the SURI remains the same.
                        symbol_record, _ = ctx.index_store.find_symbol_by_fqn(old_fqn)
                        if symbol_record:
                           old_suri = symbol_record.id
                           new_suri = old_suri.replace(old_fqn, new_fqn) # this is very wrong
                           # a suri is path#fragment, fqn is pkg.mod.Class
                           # Correct way: find symbol, get path and old fragment.
                           # Construct new SURI with same path and new fragment.
                           # Let's assume for now renames are within the same module.
                           old_frag = old_fqn.split(".")[-1]
                           new_frag = new_fqn.split(".")[-1]
                           if symbol_record and symbol_record.id:
                               suri_rename_map[symbol_record.id] = symbol_record.id.replace(old_frag, new_frag)

                if suri_rename_map:
                    new_content = self._sidecar_updater.update_keys(
                        content, suri_rename_map, is_yaml=False
                    )
~~~~~
~~~~~python.new
            elif file_path.suffix == ".json":
                # For JSON, the key is the SURI. We construct the SURI rename map.
                suri_rename_map = {}
                for loc in locations:
                    if not (loc.target_node_id and loc.target_node_fqn):
                        continue

                    old_suri = loc.target_node_id
                    old_fqn = loc.target_node_fqn

                    if old_fqn in rename_map:
                        new_fqn = rename_map[old_fqn]

                        # Reconstruct SURI. This logic assumes a symbol rename, not a file move.
                        # File moves are handled by MoveFileOperation generating cascading renames.
                        try:
                            path, old_fragment = SURIGenerator.parse(old_suri)
                            _, new_fragment_base = SURIGenerator.parse(
                                f"py://dummy#{new_fqn.replace('.', '#')}"
                            )
                            new_suri = SURIGenerator.for_symbol(path, new_fragment_base)
                            suri_rename_map[old_suri] = new_suri
                        except (ValueError, AttributeError):
                            continue # Ignore malformed SURIs or FQNs

                if suri_rename_map:
                    new_content = self._sidecar_updater.update_keys(
                        content, suri_rename_map, is_yaml=False
                    )
~~~~~

### 下一步建议

我们已经完成了对重构引擎核心逻辑的置换手术。现在系统在理论上是完备和一致的。

下一步是**运行完整的测试套件**，特别是 `stitcher-refactor` 包下的集成测试。这将暴露我们在重构过程中可能遗漏的边界情况或逻辑错误。修复所有测试失败将是我们的首要任务，以确保新系统的行为与旧系统一致（在正确性方面），并能处理我们新支持的场景。
