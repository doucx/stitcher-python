Excellent. You've provided the exact context needed. The `rg` output confirms which files depend on `SidecarUpdateMixin`, and the content of `test_sidecar_update_mixin.py` gives me the perfect blueprint for creating an equivalent test for our new `SidecarTransformer`.

This is the final step to complete the decoupling. I will now generate the plan to refactor the `Operation` classes, transform the test file, and then remove the obsolete mixin.

## [WIP] refactor: Finalize Sidecar logic decoupling by removing SidecarUpdateMixin

### 用户需求

用户要求完成 Sidecar 转换逻辑的解耦，彻底移除 `SidecarUpdateMixin`。这包括：
1.  修改所有依赖该 Mixin 的 `Operation` 子类，使其使用新的 `engine.utils.path_to_fqn` 辅助函数。
2.  将 `test_sidecar_update_mixin.py` 的测试逻辑迁移并适配到 `stitcher-lang-sidecar` 包中，以直接测试 `SidecarTransformer`。
3.  物理删除 `SidecarUpdateMixin` 的定义及其旧的测试文件。

### 评论

这是本次架构重构的点睛之笔。通过移除 Mixin，我们用显式的策略组合（`Planner` 调用 `SidecarTransformer`）彻底取代了隐式的继承耦合。这使得 `stitcher-refactor` 包的职责更加纯粹，只关注操作的“规划”，而将“特定格式的转换”完全委托出去。同时，将单元测试与其所测试的逻辑（`SidecarTransformer`）放在同一个包内，也极大地提升了代码库的内聚性和可维护性。

### 目标

1.  重构 `MoveFileOperation`, `MoveDirectoryOperation`, 和 `RenameSymbolOperation`，移除对 `SidecarUpdateMixin` 的继承，并改用从 `engine.utils` 导入的 `path_to_fqn` 函数。
2.  在 `stitcher-lang-sidecar` 包中创建一个新的测试文件 `tests/unit/test_transform.py`。
3.  将 `test_sidecar_update_mixin.py` 中的所有测试用例迁移到新的测试文件中，并修改它们以调用 `SidecarTransformer.transform()` 方法，验证其行为与原 Mixin 完全一致。
4.  从 `stitcher-refactor/src/stitcher/refactor/operations/base.py` 中删除 `SidecarUpdateMixin` 类的定义。
5.  删除原始的测试文件 `packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py`。

### 基本原理

我们将分三步完成此次清理。首先，对三个 `Operation` 子类进行 `patch` 操作，将它们的依赖从 Mixin 切换到新的 `utils` 模块。其次，我们将在 `stitcher-lang-sidecar` 中创建一个新的单元测试，并将旧测试的核心逻辑（输入数据和断言）原封不动地迁移过来，只修改调用方式，从 `mixin._update_sidecar_data()` 变为 `transformer.transform()`。这确保了我们逻辑迁移的正确性，并且没有丢失测试覆盖。最后，在所有依赖都解除后，我们就可以安全地删除 Mixin 的定义和其旧的测试文件，完成整个重构闭环。

### 标签
#intent/refine #flow/ready #priority/high #comp/refactor #comp/lang-sidecar #comp/tests #concept/decoupling #scope/core #ai/instruct #task/domain/refactor #task/object/sidecar-logic #task/action/decoupling #task/state/end

---

### Script

#### Acts 1: Refactor Operation Classes to Remove Mixin Dependency

我们将逐一修改 `Operation` 子类，移除对 `SidecarUpdateMixin` 的继承，并更新其内部实现以使用新的工具函数。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python
from typing import List, Optional

from .base import AbstractOperation, SidecarUpdateMixin
from stitcher.refactor.engine.context import RefactorContext
from stitcher.analysis.semantic import SymbolNode
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
)


class RenameSymbolOperation(AbstractOperation, SidecarUpdateMixin):
    def __init__(self, old_fqn: str, new_fqn: str):
        self.old_fqn = old_fqn
        self.new_fqn = new_fqn

    def _find_definition_node(self, ctx: RefactorContext) -> Optional[SymbolNode]:
        return ctx.graph.find_symbol(self.old_fqn)

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # 1. Declare the core intent: rename the symbol everywhere.
        # The Planner will be responsible for finding usages and transforming code.
        intents.append(RenameIntent(old_fqn=self.old_fqn, new_fqn=self.new_fqn))

        # 2. Declare intents to update sidecar files.
        # If the symbol definition is found, try to update sidecars.
        # If not found, skip sidecar updates but proceed with code rename.
        definition_node = self._find_definition_node(ctx)
        if definition_node and definition_node.path:
            definition_file_path = definition_node.path
            module_fqn = self._path_to_fqn(definition_file_path, ctx.graph.search_paths)

            # Doc file intent
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
~~~~~python
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
    def __init__(self, old_fqn: str, new_fqn: str):
        self.old_fqn = old_fqn
        self.new_fqn = new_fqn

    def _find_definition_node(self, ctx: RefactorContext) -> Optional[SymbolNode]:
        return ctx.graph.find_symbol(self.old_fqn)

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # 1. Declare the core intent: rename the symbol everywhere.
        # The Planner will be responsible for finding usages and transforming code.
        intents.append(RenameIntent(old_fqn=self.old_fqn, new_fqn=self.new_fqn))

        # 2. Declare intents to update sidecar files.
        # If the symbol definition is found, try to update sidecars.
        # If not found, skip sidecar updates but proceed with code rename.
        definition_node = self._find_definition_node(ctx)
        if definition_node and definition_node.path:
            definition_file_path = definition_node.path
            module_fqn = path_to_fqn(definition_file_path, ctx.graph.search_paths)

            # Doc file intent
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
~~~~~act
patch_file
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
~~~~~
~~~~~python
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    ScaffoldIntent,
    SidecarUpdateIntent,
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
~~~~~
~~~~~act
patch_file
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
~~~~~
~~~~~python
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    SidecarUpdateIntent,
    DeleteDirectoryIntent,
    ScaffoldIntent,
)


class MoveDirectoryOperation(AbstractOperation):
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
        old_prefix = path_to_fqn(src_dir, ctx.graph.search_paths)
        new_prefix = path_to_fqn(dest_dir, ctx.graph.search_paths)
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
            item_module_fqn = path_to_fqn(src_item, ctx.graph.search_paths)

            doc_path = ctx.sidecar_manager.get_doc_path(src_item)
            if doc_path.exists() and old_prefix and new_prefix:
~~~~~

#### Acts 2: Re-home and Adapt the Test File

我们现在将旧 Mixin 的测试文件移动到 `stitcher-lang-sidecar` 包中，并将其重命名。然后，我们用 `write_file` 彻底重写其内容，使其直接测试 `SidecarTransformer`，确保功能等价。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-lang-sidecar/tests/unit
~~~~~

~~~~~act
write_file
packages/stitcher-lang-sidecar/tests/unit/test_transform.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from stitcher.lang.sidecar import SidecarTransformer, SidecarTransformContext


@pytest.fixture
def transformer():
    return SidecarTransformer()


class TestJsonSuriUpdates:
    def test_updates_suri_on_symbol_rename(self, transformer):
        old_suri = "py://src/app.py#OldClass"
        new_suri = "py://src/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        context = SidecarTransformContext(
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        updated = transformer.transform(Path("src/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_nested_symbol_rename(self, transformer):
        old_suri = "py://src/app.py#MyClass.old_method"
        new_suri = "py://src/app.py#MyClass.new_method"
        data = {old_suri: {"hash": "1"}}
        context = SidecarTransformContext(
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        updated = transformer.transform(Path("src/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_parent_rename(self, transformer):
        old_suri = "py://src/app.py#OldClass.method"
        new_suri = "py://src/app.py#NewClass.method"
        data = {old_suri: {"hash": "1"}}
        context = SidecarTransformContext(
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        updated = transformer.transform(Path("src/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_file_move(self, transformer):
        old_suri = "py://src/old_path/app.py#MyClass"
        new_suri = "py://src/new_path/app.py#MyClass"
        data = {old_suri: {"hash": "1"}}
        context = SidecarTransformContext(
            old_module_fqn="old_path.app",
            new_module_fqn="new_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        updated = transformer.transform(Path("src/old_path/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_combined_move_and_rename(self, transformer):
        old_suri = "py://src/old_path/app.py#OldClass"
        new_suri = "py://src/new_path/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        context = SidecarTransformContext(
            old_module_fqn="old_path.app",
            new_module_fqn="new_path.app",
            old_fqn="old_path.app.OldClass",
            new_fqn="new_path.app.NewClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        updated = transformer.transform(Path("src/old_path/app.json"), data, context)
        assert updated == {new_suri: {"hash": "1"}}


class TestYamlFragmentUpdates:
    def test_updates_fragment_on_symbol_rename(self, transformer):
        data = {"OldClass": "doc", "Other": "doc"}
        context = SidecarTransformContext(
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        updated = transformer.transform(Path("app.stitcher.yaml"), data, context)
        assert updated == {"NewClass": "doc", "Other": "doc"}

    def test_updates_fragment_on_nested_symbol_rename(self, transformer):
        data = {"MyClass.old_method": "doc"}
        context = SidecarTransformContext(
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        updated = transformer.transform(Path("app.stitcher.yaml"), data, context)
        assert updated == {"MyClass.new_method": "doc"}

    def test_updates_fragment_on_parent_rename(self, transformer):
        data = {"OldClass.method": "doc"}
        context = SidecarTransformContext(
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        updated = transformer.transform(Path("app.stitcher.yaml"), data, context)
        assert updated == {"NewClass.method": "doc"}

    def test_does_not_update_fragment_on_pure_file_move(self, transformer):
        data = {"MyClass": "doc"}
        original_data = data.copy()
        context = SidecarTransformContext(
            old_module_fqn="old_path.app",
            new_module_fqn="new_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass",
            old_file_path="old_path/app.py",
            new_file_path="new_path/app.py",
        )
        updated = transformer.transform(
            Path("old_path/app.stitcher.yaml"), data, context
        )
        assert updated == original_data
~~~~~

#### Acts 3: Final Cleanup

现在所有依赖都已移除，我们可以安全地删除 `SidecarUpdateMixin` 的定义及其旧的测试文件。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python
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
                if path.is_relative_to(sp):
                    base_path = sp
                    break
            except (ValueError, AttributeError):
                if str(path).startswith(str(sp)):
                    base_path = sp
                    break
                continue

        if base_path is None:
            return None

        rel_path = path.relative_to(base_path)
        return path_to_logical_fqn(rel_path.as_posix())

    def _calculate_fragments(
        self,
        old_module_fqn: Optional[str],
        new_module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        # --- Calculate Old Fragment ---
        old_fragment = old_fqn
        # The module_fqn is the context of the sidecar file, which relates to the OLD state.
        if old_module_fqn and old_fqn.startswith(old_module_fqn + "."):
            old_fragment = old_fqn.split(old_module_fqn + ".", 1)[1]
        elif old_module_fqn and old_fqn == old_module_fqn:
            old_fragment = None  # Represents the module itself

        # --- Calculate New Fragment ---
        new_fragment = new_fqn
        # The new fragment must be relative to the NEW module FQN, which is passed in.
        if new_module_fqn and new_fqn.startswith(new_module_fqn + "."):
            new_fragment = new_fqn.split(new_module_fqn + ".", 1)[1]

        # Handle renaming of a module itself
        if old_fqn == old_module_fqn:
            new_fragment = None

        return old_fragment, new_fragment

    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        sidecar_path: Path,
        old_module_fqn: Optional[str],
        new_module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
        old_file_path: Optional[str] = None,
        new_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        old_fragment, new_fragment = self._calculate_fragments(
            old_module_fqn, new_module_fqn, old_fqn, new_fqn
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
~~~~~
~~~~~python
from abc import ABC, abstractmethod
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.intent import RefactorIntent


class AbstractOperation(ABC):
    @abstractmethod
    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        pass
~~~~~
~~~~~act
delete_file
packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py
~~~~~

### 下一步建议

我们已经成功地完成了将 Sidecar 转换逻辑从 `stitcher-refactor` 中解耦的整个过程。`Planner` 和 `Operation` 类的职责现在更加清晰，`SidecarTransformer` 作为一个独立的、可测试的策略组件存在。

- **运行完整测试套件**：执行 `pytest`，确保我们所有的修改没有引入任何回归问题，特别是要验证新创建的 `test_transform.py` 能够成功运行。
- **审视 `Operation` 类**：现在 `Operation` 类的主要职责是收集 `Intent`。可以审视一下是否有进一步简化的空间，或者是否可以为更复杂的重构场景（如提取方法）创建新的 `Operation` 子类。
- **依赖注入**：`Planner` 目前仍然在内部实例化 `YamlAdapter` 和 `SidecarTransformer`。在未来的迭代中，可以考虑通过依赖注入的方式将这些服务传入，以进一步增强可测试性和灵活性。
