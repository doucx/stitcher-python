You've found an excellent bug. My apologies, that's a clear mistake in the API design.

The error `TypeError: MoveFileOperation.__init__() got an unexpected keyword argument 'src'` indicates a mismatch between how the migration script is *calling* the `Move` operation and how the `MoveFileOperation` class is *defined*.

The script uses `Move(src=..., dest=...)`, which is clean and intuitive. However, the class constructor was implemented to expect `src_path` and `dest_path`. I will fix the class to match the intuitive API, which is the correct long-term solution.

## [WIP] fix(refactor): Align Move operation API with keyword arguments

### 错误分析

用户在运行迁移脚本时遇到了 `TypeError`。

1.  **根本原因**: `MoveFileOperation` 和 `MoveDirectoryOperation` 类的 `__init__` 方法的参数名与迁移脚本中推荐的调用方式不一致。
2.  **具体问题**:
    *   迁移脚本 API 设计为使用简洁的关键字 `src` 和 `dest` (e.g., `Move(src=..., dest=...)`)。
    *   `MoveFileOperation` 的构造函数却期望 `src_path` 和 `dest_path`。
    *   `MoveDirectoryOperation` 的构造函数期望 `src_dir` 和 `dest_dir`。
    *   这导致 Python 无法将调用端的关键字参数 `src` 映射到定义端的 `src_path`，从而抛出 `TypeError`。

### 用户需求

修复 `Move` 和 `MoveDir` 操作，使其能够接受 `src` 和 `dest` 关键字参数，从而使迁移脚本能够按预期工作。

### 评论

这是一个典型的 API 不一致性 bug。修复这个问题对于提供一个干净、可预测的开发者体验至关重要。将内部实现（`src_path`）与公共 API（`src`）对齐，是正确的做法。

### 目标

1.  修改 `MoveFileOperation` 的 `__init__` 方法，使其接受 `src` 和 `dest` 参数，并更新整个类以使用 `self.src` 和 `self.dest`。
2.  修改 `MoveDirectoryOperation` 的 `__init__` 方法，使其接受 `src`和 `dest` 参数，并更新整个类以使用 `self.src` 和 `self.dest`。

### 基本原理

我们将直接重构这两个操作类的构造函数和内部属性。通过将参数名统一为 `src` 和 `dest`，我们使得这些类的公共 API 与迁移脚本的调用方式完全匹配，从而从根本上解决 `TypeError`。这个改动不会影响它们的功能，但会显著提升 API 的一致性和易用性。

### 标签

#intent/fix #flow/ready #priority/high #comp/refactor #scope/api #scope/dx #ai/instruct #task/domain/tooling #task/object/refactor-engine #task/action/dogfooding #task/state/continue

---

### Script

#### Acts 1: 统一 `MoveFileOperation` 的 API

我们将修改 `move_file.py` 以使用 `src` 和 `dest`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
class MoveFileOperation(AbstractOperation):
    def __init__(self, src_path: Path, dest_path: Path):
        self.src_path = src_path
        self.dest_path = dest_path

    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
~~~~~
~~~~~python.new
class MoveFileOperation(AbstractOperation):
    def __init__(self, src: Path, dest: Path):
        self.src = src
        self.dest = dest

    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        rename_ops: List[FileOp] = []
        move_ops: List[FileOp] = []
        content_update_ops: List[FileOp] = []

        old_module_fqn = self._path_to_fqn(self.src_path, ctx.graph.search_paths)
        new_module_fqn = self._path_to_fqn(self.dest_path, ctx.graph.search_paths)

        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # 1. Update external references to the moved symbols
            # Rename the module itself (handles "import old_mod")
            rename_mod_op = RenameSymbolOperation(old_module_fqn, new_module_fqn)
            rename_ops.extend(rename_mod_op.analyze(ctx))

            # Rename all members (handles "from old_mod import X")
            members = ctx.graph.iter_members(old_module_fqn)
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn) :]
                    target_new_fqn = new_module_fqn + suffix
                    sub_op = RenameSymbolOperation(member.fqn, target_new_fqn)
                    rename_ops.extend(sub_op.analyze(ctx))

            # 2. Update the content of the sidecar files associated with the moved module
            # YAML sidecar
            yaml_src_path = self.src_path.with_suffix(".stitcher.yaml")
            if yaml_src_path.exists():
                doc_updater = DocUpdater()
                doc_data = doc_updater.load(yaml_src_path)
                updated_data = {
                    key.replace(old_module_fqn, new_module_fqn, 1)
                    if key.startswith(old_module_fqn)
                    else key: value
                    for key, value in doc_data.items()
                }
                if updated_data != doc_data:
                    content_update_ops.append(
                        WriteFileOp(
                            path=yaml_src_path.relative_to(ctx.graph.root_path),
                            content=doc_updater.dump(updated_data),
                        )
                    )
            # Signature sidecar
            rel_src_base = self.src_path.relative_to(ctx.graph.root_path)
            sig_src_path = (
                ctx.graph.root_path
                / ".stitcher/signatures"
                / rel_src_base.with_suffix(".json")
            )
            if sig_src_path.exists():
                sig_updater = SigUpdater()
                sig_data = sig_updater.load(sig_src_path)
                updated_data = {
                    key.replace(old_module_fqn, new_module_fqn, 1)
                    if key.startswith(old_module_fqn)
                    else key: value
                    for key, value in sig_data.items()
                }
                if updated_data != sig_data:
                    content_update_ops.append(
                        WriteFileOp(
                            path=sig_src_path.relative_to(ctx.graph.root_path),
                            content=sig_updater.dump(updated_data),
                        )
                    )

        # 3. Plan the physical moves
        rel_src = self.src_path.relative_to(ctx.graph.root_path)
        rel_dest = self.dest_path.relative_to(ctx.graph.root_path)
        move_ops.append(MoveFileOp(rel_src, rel_dest))

        # Sidecar moves
        yaml_src = self.src_path.with_suffix(".stitcher.yaml")
        if yaml_src.exists():
            rel_yaml_src = yaml_src.relative_to(ctx.graph.root_path)
            rel_yaml_dest = self.dest_path.with_suffix(".stitcher.yaml").relative_to(
                ctx.graph.root_path
            )
            move_ops.append(MoveFileOp(rel_yaml_src, rel_yaml_dest))

        sig_root = ctx.graph.root_path / ".stitcher/signatures"
        sig_src = sig_root / rel_src.with_suffix(".json")
        if sig_src.exists():
            rel_sig_src = sig_src.relative_to(ctx.graph.root_path)
            rel_sig_dest = sig_root / rel_dest.with_suffix(".json")
            rel_sig_dest = rel_sig_dest.relative_to(ctx.graph.root_path)
            move_ops.append(MoveFileOp(rel_sig_src, rel_sig_dest))

        # Return combined ops: content updates first, then moves
        return content_update_ops + rename_ops + move_ops
~~~~~
~~~~~python.new
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        rename_ops: List[FileOp] = []
        move_ops: List[FileOp] = []
        content_update_ops: List[FileOp] = []

        old_module_fqn = self._path_to_fqn(self.src, ctx.graph.search_paths)
        new_module_fqn = self._path_to_fqn(self.dest, ctx.graph.search_paths)

        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # 1. Update external references to the moved symbols
            # Rename the module itself (handles "import old_mod")
            rename_mod_op = RenameSymbolOperation(old_module_fqn, new_module_fqn)
            rename_ops.extend(rename_mod_op.analyze(ctx))

            # Rename all members (handles "from old_mod import X")
            members = ctx.graph.iter_members(old_module_fqn)
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn) :]
                    target_new_fqn = new_module_fqn + suffix
                    sub_op = RenameSymbolOperation(member.fqn, target_new_fqn)
                    rename_ops.extend(sub_op.analyze(ctx))

            # 2. Update the content of the sidecar files associated with the moved module
            # YAML sidecar
            yaml_src_path = self.src.with_suffix(".stitcher.yaml")
            if yaml_src_path.exists():
                doc_updater = DocUpdater()
                doc_data = doc_updater.load(yaml_src_path)
                updated_data = {
                    key.replace(old_module_fqn, new_module_fqn, 1)
                    if key.startswith(old_module_fqn)
                    else key: value
                    for key, value in doc_data.items()
                }
                if updated_data != doc_data:
                    content_update_ops.append(
                        WriteFileOp(
                            path=yaml_src_path.relative_to(ctx.graph.root_path),
                            content=doc_updater.dump(updated_data),
                        )
                    )
            # Signature sidecar
            rel_src_base = self.src.relative_to(ctx.graph.root_path)
            sig_src_path = (
                ctx.graph.root_path
                / ".stitcher/signatures"
                / rel_src_base.with_suffix(".json")
            )
            if sig_src_path.exists():
                sig_updater = SigUpdater()
                sig_data = sig_updater.load(sig_src_path)
                updated_data = {
                    key.replace(old_module_fqn, new_module_fqn, 1)
                    if key.startswith(old_module_fqn)
                    else key: value
                    for key, value in sig_data.items()
                }
                if updated_data != sig_data:
                    content_update_ops.append(
                        WriteFileOp(
                            path=sig_src_path.relative_to(ctx.graph.root_path),
                            content=sig_updater.dump(updated_data),
                        )
                    )

        # 3. Plan the physical moves
        rel_src = self.src.relative_to(ctx.graph.root_path)
        rel_dest = self.dest.relative_to(ctx.graph.root_path)
        move_ops.append(MoveFileOp(rel_src, rel_dest))

        # Sidecar moves
        yaml_src = self.src.with_suffix(".stitcher.yaml")
        if yaml_src.exists():
            rel_yaml_src = yaml_src.relative_to(ctx.graph.root_path)
            rel_yaml_dest = self.dest.with_suffix(".stitcher.yaml").relative_to(
                ctx.graph.root_path
            )
            move_ops.append(MoveFileOp(rel_yaml_src, rel_yaml_dest))

        sig_root = ctx.graph.root_path / ".stitcher/signatures"
        sig_src = sig_root / rel_src.with_suffix(".json")
        if sig_src.exists():
            rel_sig_src = sig_src.relative_to(ctx.graph.root_path)
            rel_sig_dest = sig_root / rel_dest.with_suffix(".json")
            rel_sig_dest = rel_sig_dest.relative_to(ctx.graph.root_path)
            move_ops.append(MoveFileOp(rel_sig_src, rel_sig_dest))

        # Return combined ops: content updates first, then moves
        return content_update_ops + rename_ops + move_ops
~~~~~

#### Acts 2: 统一 `MoveDirectoryOperation` 的 API

同样，我们修改 `move_directory.py`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
class MoveDirectoryOperation(AbstractOperation):
    def __init__(self, src_dir: Path, dest_dir: Path):
        if not src_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {src_dir}")
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        all_ops: List[FileOp] = []
        handled_paths: Set[Path] = set()

        # Phase 1: Smart-process all Python files and their sidecars
        for src_file in self.src_dir.rglob("*.py"):
            relative_path = src_file.relative_to(self.src_dir)
            dest_file = self.dest_dir / relative_path

            # Delegate to the smart MoveFileOperation
            file_mover = MoveFileOperation(src_file, dest_file)
            file_specific_ops = file_mover.analyze(ctx)
            all_ops.extend(file_specific_ops)

            # Mark the source file and its potential sidecars as handled
            handled_paths.add(src_file)
            handled_paths.add(src_file.with_suffix(".stitcher.yaml"))
            sig_rel_path = src_file.relative_to(ctx.graph.root_path).with_suffix(
                ".json"
            )
            sig_abs_path = ctx.graph.root_path / ".stitcher/signatures" / sig_rel_path
            handled_paths.add(sig_abs_path)

        # Phase 2: Process all remaining items (non-Python files)
        for src_item in self.src_dir.rglob("*"):
            if src_item in handled_paths or not src_item.is_file():
                continue

            # This item is a non-Python, non-sidecar file. Do a simple move.
            relative_path = src_item.relative_to(self.src_dir)
            dest_item = self.dest_dir / relative_path

            rel_src_item = src_item.relative_to(ctx.graph.root_path)
            rel_dest_item = dest_item.relative_to(ctx.graph.root_path)

            all_ops.append(MoveFileOp(rel_src_item, rel_dest_item))
            handled_paths.add(src_item)

        # Phase 3: Schedule the now-empty source directory for deletion
        all_ops.append(DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path)))

        return all_ops
~~~~~
~~~~~python.new
class MoveDirectoryOperation(AbstractOperation):
    def __init__(self, src: Path, dest: Path):
        if not src.is_dir():
            raise ValueError(f"Source path is not a directory: {src}")
        self.src = src
        self.dest = dest

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        all_ops: List[FileOp] = []
        handled_paths: Set[Path] = set()

        # Phase 1: Smart-process all Python files and their sidecars
        for src_file in self.src.rglob("*.py"):
            relative_path = src_file.relative_to(self.src)
            dest_file = self.dest / relative_path

            # Delegate to the smart MoveFileOperation
            file_mover = MoveFileOperation(src_file, dest_file)
            file_specific_ops = file_mover.analyze(ctx)
            all_ops.extend(file_specific_ops)

            # Mark the source file and its potential sidecars as handled
            handled_paths.add(src_file)
            handled_paths.add(src_file.with_suffix(".stitcher.yaml"))
            sig_rel_path = src_file.relative_to(ctx.graph.root_path).with_suffix(
                ".json"
            )
            sig_abs_path = ctx.graph.root_path / ".stitcher/signatures" / sig_rel_path
            handled_paths.add(sig_abs_path)

        # Phase 2: Process all remaining items (non-Python files)
        for src_item in self.src.rglob("*"):
            if src_item in handled_paths or not src_item.is_file():
                continue

            # This item is a non-Python, non-sidecar file. Do a simple move.
            relative_path = src_item.relative_to(self.src)
            dest_item = self.dest / relative_path

            rel_src_item = src_item.relative_to(ctx.graph.root_path)
            rel_dest_item = dest_item.relative_to(ctx.graph.root_path)

            all_ops.append(MoveFileOp(rel_src_item, rel_dest_item))
            handled_paths.add(src_item)

        # Phase 3: Schedule the now-empty source directory for deletion
        all_ops.append(DeleteDirectoryOp(self.src.relative_to(ctx.graph.root_path)))

        return all_ops
~~~~~

### 下一步建议

API 已修复并保持了一致性。你现在可以**无需修改**，直接重新运行之前的迁移脚本：

```bash
stitcher refactor apply migrations/001_refactor_cli_l_pointers.py
```

这次它应该可以成功执行了。
