好的，我们现在开始执行**任务 2.4**，这是第二阶段的收官之作。我们将把新的 `SidecarManager` 全面应用到所有的重构操作类中，彻底根除硬编码的路径逻辑。

## [WIP] refactor: 重构 Operation 类以使用 SidecarManager

### 用户需求

根据重构路线图，实施第二阶段的任务 2.4：
逐一重构 `RenameSymbolOperation`、`MoveFileOperation` 和 `MoveDirectoryOperation` 这三个类。将它们内部所有手动计算 Sidecar 文件（`.stitcher.yaml` 和签名 `.json`）路径的逻辑，全部替换为对 `ctx.sidecar_manager` 相应方法的调用。

### 评论

这是我们前期所有基础工作的最终回报。通过这次重构，`*Operation` 类将变得更加简洁、健壮，并且完全与其操作的 Sidecar 文件的存储位置解耦。它们不再关心“路径是如何构建的”，只关心“通过 Manager 获取路径”。这使得我们的重构引擎核心逻辑（Operations）与存储策略（SidecarManager）实现了完美的关注点分离，极大地提升了整个系统的可维护性和可扩展性。

### 目标

1.  **重构 `RenameSymbolOperation`**: 修改 `analyze` 方法，使用 `sidecar_manager` 定位文档和签名文件。
2.  **重构 `MoveFileOperation`**: 修改 `analyze` 方法，使用 `sidecar_manager` 定位源和目标的 Sidecar 文件，用于内容更新和物理移动规划。
3.  **重构 `MoveDirectoryOperation`**: 修改 `analyze` 方法，使用 `sidecar_manager` 来识别一个 Python 源文件关联的所有 Sidecar 文件，以确保它们在目录移动过程中被正确处理且仅处理一次。

### 基本原理

我们将遵循我们已建立的依赖注入模式。每个 `Operation` 类的 `analyze` 方法都会接收一个功能完备的 `RefactorContext` 实例。我们将系统地查找所有 `.with_suffix(".stitcher.yaml")` 或手动拼接 `.stitcher/signatures` 路径的硬编码片段，并将它们替换为对 `ctx.sidecar_manager.get_doc_path(...)` 和 `ctx.sidecar_manager.get_signature_path(...)` 的调用。因为 `SidecarManager` 返回的是绝对路径，所以我们将相应地调整代码，确保在需要时能正确计算出相对于项目根目录的路径，以用于 `FileOp` 的创建。

### 标签

#intent/refine #flow/ready #priority/high #comp/refactor #concept/dependency-injection #scope/core #ai/instruct #task/domain/refactor-engine #task/object/operations #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重构 `RenameSymbolOperation`

我们首先更新 `RenameSymbolOperation`，用 `SidecarManager` 替换其 Sidecar 路径发现逻辑。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
                # --- 2. Handle Sidecar Renaming ---
                doc_updater = DocUpdater()
                sig_updater = SigUpdater()

                # Doc file
                doc_path = file_path.with_suffix(".stitcher.yaml")
                if doc_path.exists():
                    doc_data = doc_updater.load(doc_path)
                    new_doc_data = doc_updater.rename_key(
                        doc_data, self.old_fqn, self.new_fqn
                    )
                    if new_doc_data != doc_data:
                        ops.append(
                            WriteFileOp(
                                path=doc_path.relative_to(ctx.graph.root_path),
                                content=doc_updater.dump(new_doc_data),
                            )
                        )

                # Signature file
                sig_path = (
                    ctx.graph.root_path
                    / ".stitcher/signatures"
                    / relative_path.with_suffix(".json")
                )
                if sig_path.exists():
                    sig_data = sig_updater.load(sig_path)
                    new_sig_data = sig_updater.rename_key(
                        sig_data, self.old_fqn, self.new_fqn
                    )
                    if new_sig_data != sig_data:
                        ops.append(
                            WriteFileOp(
                                path=sig_path.relative_to(ctx.graph.root_path),
                                content=sig_updater.dump(new_sig_data),
                            )
                        )
~~~~~
~~~~~python.new
                # --- 2. Handle Sidecar Renaming ---
                doc_updater = DocUpdater()
                sig_updater = SigUpdater()

                # Doc file
                doc_path = ctx.sidecar_manager.get_doc_path(file_path)
                if doc_path.exists():
                    doc_data = doc_updater.load(doc_path)
                    new_doc_data = doc_updater.rename_key(
                        doc_data, self.old_fqn, self.new_fqn
                    )
                    if new_doc_data != doc_data:
                        ops.append(
                            WriteFileOp(
                                path=doc_path.relative_to(ctx.graph.root_path),
                                content=doc_updater.dump(new_doc_data),
                            )
                        )

                # Signature file
                sig_path = ctx.sidecar_manager.get_signature_path(file_path)
                if sig_path.exists():
                    sig_data = sig_updater.load(sig_path)
                    new_sig_data = sig_updater.rename_key(
                        sig_data, self.old_fqn, self.new_fqn
                    )
                    if new_sig_data != sig_data:
                        ops.append(
                            WriteFileOp(
                                path=sig_path.relative_to(ctx.graph.root_path),
                                content=sig_updater.dump(new_sig_data),
                            )
                        )
~~~~~

#### Acts 2: 重构 `MoveFileOperation`

接着，我们对 `MoveFileOperation` 进行更广泛的重构，包括其内容更新和物理移动规划两个部分。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
            # 2. Update the content of the sidecar files associated with the moved module
            # YAML sidecar
            yaml_src_path = ctx.sidecar_manager.get_doc_path(self.src_path)
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
            sig_src_path = ctx.sidecar_manager.get_signature_path(self.src_path)
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
        root = ctx.graph.root_path
        rel_src = self.src_path.relative_to(root)
        rel_dest = self.dest_path.relative_to(root)
        move_ops.append(MoveFileOp(rel_src, rel_dest))

        # Sidecar moves
        yaml_src = ctx.sidecar_manager.get_doc_path(self.src_path)
        if yaml_src.exists():
            yaml_dest = ctx.sidecar_manager.get_doc_path(self.dest_path)
            move_ops.append(
                MoveFileOp(yaml_src.relative_to(root), yaml_dest.relative_to(root))
            )

        sig_src = ctx.sidecar_manager.get_signature_path(self.src_path)
        if sig_src.exists():
            sig_dest = ctx.sidecar_manager.get_signature_path(self.dest_path)
            move_ops.append(
                MoveFileOp(sig_src.relative_to(root), sig_dest.relative_to(root))
            )
~~~~~

#### Acts 3: 重构 `MoveDirectoryOperation`

最后，我们清理 `MoveDirectoryOperation` 中的 Sidecar 路径计算逻辑。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
            # Mark the source file and its potential sidecars as handled
            handled_paths.add(src_file)
            handled_paths.add(src_file.with_suffix(".stitcher.yaml"))
            sig_rel_path = src_file.relative_to(ctx.graph.root_path).with_suffix(
                ".json"
            )
            sig_abs_path = ctx.graph.root_path / ".stitcher/signatures" / sig_rel_path
            handled_paths.add(sig_abs_path)
~~~~~
~~~~~python.new
            # Mark the source file and its potential sidecars as handled
            handled_paths.add(src_file)
            doc_path = ctx.sidecar_manager.get_doc_path(src_file)
            handled_paths.add(doc_path)
            sig_path = ctx.sidecar_manager.get_signature_path(src_file)
            handled_paths.add(sig_path)
~~~~~

### 下一步建议

我们已经成功完成了重构路线图的**第二阶段**。`stitcher-refactor` 引擎现在拥有了一个健壮、解耦且可维护的核心架构。

下一步，我们将进入至关重要的**第三阶段：验证与清理**。我建议立即开始执行 **任务 3.1: 编写新的端到端集成测试**。我们将创建一个专门的测试，模拟一个复杂的 monorepo 场景（类似于 `Cascade` 项目），并执行一次跨包的目录移动操作，以端到端地验证我们所有重构工作的正确性和健壮性。如果你同意，我将开始设计并生成该测试计划。
