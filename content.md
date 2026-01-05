生成 Quipu 计划以修复 `stitcher-refactor` 中的逻辑错误和测试失败。

简要回答：
Plan 包含对 `RenameNamespaceOperation` 逻辑错误的修复，对 `MoveDirectoryOperation` 遗漏 Sidecar 移动的修复，以及更新单元测试以匹配最新的 `UsageLocation` 数据结构。

## [WIP] fix: 修复重构引擎中的目录移动逻辑与测试数据结构

### 错误分析

1.  **`RenameNamespaceOperation` NameError**:
    *   在 `analyze` 方法中，代码试图在列表推导式中使用未定义的变量 `u` 来查询 registry，且忽略了循环变量 `usages_by_file` 中的 value。
    *   **修复**: 正确解包 `usages_by_file.items()`，并使用当前文件聚合的 `file_usages` 列表来构建 `locations` 映射。

2.  **`MoveDirectoryOperation` 遗漏 Sidecar 移动**:
    *   集成测试失败表明签名文件未被移动。检查代码发现，`MoveDirectoryOperation` 虽然更新了 Sidecar 的内容（FQN 重命名），但没有生成对应的 `MoveFileOp` 来物理移动这些 Sidecar 文件。
    *   **修复**: 在处理 `.py` 文件时，显式检查并添加 Sidecar 文件的移动操作。

3.  **单元测试 TypeError**:
    *   `UsageLocation` dataclass 新增了 `ref_type` 和 `target_node_fqn` 字段，但单元测试中的构造函数调用未更新。
    *   **修复**: 更新 `test_rename_operation.py` 和 `test_rename_transformer.py`，填充缺失的参数。

### 用户需求
修复当前的测试套件失败，确保重构引擎在移动目录时能正确处理 Sidecar 文件，并修复命名空间重命名逻辑中的 Bug。

### 评论
这些修复对于 `stitcher-refactor` 的稳定性至关重要，特别是目录移动操作涉及多文件、多 Sidecar 的协调，必须保证原子性和完整性。

### 目标
1.  修复 `RenameNamespaceOperation.analyze` 中的逻辑错误。
2.  确保 `MoveDirectoryOperation` 会移动关联的 yaml 和 json Sidecar 文件。
3.  修复所有因 `UsageLocation` 签名变更导致的单元测试失败。

### 基本原理
*   **命名空间重命名**: 我们需要准确地将 usage 映射传递给 transformer，以便它知道哪些节点需要修改。
*   **目录移动**: Sidecar 文件紧随源文件。如果源文件移动了，Sidecar 必须随之移动，否则会变成“孤儿”或丢失基线数据。
*   **测试一致性**: 测试数据必须反映真实代码的数据结构。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #concept/refactor #scope/core #ai/instruct #task/domain/refactoring #task/object/engine #task/action/fix-bugs #task/state/continue

---

### Script

#### Acts 1: 修复 `RenameNamespaceOperation` 中的变量引用错误

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_namespace.py
~~~~~
~~~~~python.old
        for file_path, _ in usages_by_file.items():
            try:
                original_source = file_path.read_text(encoding="utf-8")
                module = cst.parse_module(original_source)

                # We need to provide QualifiedName metadata for the transformer
                # It relies on the UsageLocations we stored earlier.
                locations = {
                    (u.lineno, u.col_offset): u for u in ctx.graph.registry._index.get(u.target_node_fqn, [])
                }

                class UsageBasedQualifiedNameProvider(cst.metadata.BaseMetadataProvider):
~~~~~
~~~~~python.new
        for file_path, file_usages in usages_by_file.items():
            try:
                original_source = file_path.read_text(encoding="utf-8")
                module = cst.parse_module(original_source)

                # We need to provide QualifiedName metadata for the transformer
                # It relies on the UsageLocations we stored earlier.
                locations = {
                    (u.lineno, u.col_offset): u for u in file_usages
                }

                class UsageBasedQualifiedNameProvider(cst.metadata.BaseMetadataProvider):
~~~~~

#### Acts 2: 修复 `MoveDirectoryOperation` 以移动 Sidecar 文件

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
            # If it's a Python file, update its associated sidecars
            if src_item.suffix == ".py":
                # Doc sidecar
                doc_path = ctx.sidecar_manager.get_doc_path(src_item)
                if doc_path.exists():
                    doc_data = doc_updater.load(doc_path)
                    updated_data = {
                        key.replace(old_prefix, new_prefix, 1): value
                        for key, value in doc_data.items()
                    }
                    if updated_data != doc_data:
                        # Write updated content before moving
                        all_ops.append(
                            WriteFileOp(
                                path=doc_path.relative_to(root),
                                content=doc_updater.dump(updated_data),
                            )
                        )

                # Signature sidecar
                sig_path = ctx.sidecar_manager.get_signature_path(src_item)
                if sig_path.exists():
                    sig_data = sig_updater.load(sig_path)
                    updated_data = {
                        key.replace(old_prefix, new_prefix, 1): value
                        for key, value in sig_data.items()
                    }
                    if updated_data != sig_data:
                        all_ops.append(
                            WriteFileOp(
                                path=sig_path.relative_to(root),
                                content=sig_updater.dump(updated_data),
                            )
                        )
~~~~~
~~~~~python.new
            # If it's a Python file, update its associated sidecars
            if src_item.suffix == ".py":
                # Doc sidecar
                doc_path = ctx.sidecar_manager.get_doc_path(src_item)
                if doc_path.exists():
                    # 1. Update Content if needed
                    doc_data = doc_updater.load(doc_path)
                    updated_data = {
                        key.replace(old_prefix, new_prefix, 1): value
                        for key, value in doc_data.items()
                    }
                    if updated_data != doc_data:
                        # Write updated content before moving
                        all_ops.append(
                            WriteFileOp(
                                path=doc_path.relative_to(root),
                                content=doc_updater.dump(updated_data),
                            )
                        )
                    # 2. Move File
                    dest_doc_path = ctx.sidecar_manager.get_doc_path(dest_item)
                    all_ops.append(
                        MoveFileOp(
                            doc_path.relative_to(root), dest_doc_path.relative_to(root)
                        )
                    )

                # Signature sidecar
                sig_path = ctx.sidecar_manager.get_signature_path(src_item)
                if sig_path.exists():
                    # 1. Update Content if needed
                    sig_data = sig_updater.load(sig_path)
                    updated_data = {
                        key.replace(old_prefix, new_prefix, 1): value
                        for key, value in sig_data.items()
                    }
                    if updated_data != sig_data:
                        all_ops.append(
                            WriteFileOp(
                                path=sig_path.relative_to(root),
                                content=sig_updater.dump(updated_data),
                            )
                        )
                    # 2. Move File
                    dest_sig_path = ctx.sidecar_manager.get_signature_path(dest_item)
                    all_ops.append(
                        MoveFileOp(
                            sig_path.relative_to(root), dest_sig_path.relative_to(root)
                        )
                    )
~~~~~

#### Acts 3: 修复单元测试 `test_rename_operation.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
    locations = [
        # Locations in a.py
        UsageLocation(file_a_path, 1, 23, 1, 32),  # from mypkg.core import OldHelper
        UsageLocation(file_a_path, 3, 6, 3, 15),  # obj = OldHelper()
        # Locations in b.py
        UsageLocation(file_b_path, 2, 27, 2, 36),  # from mypkg.core import OldHelper
        UsageLocation(file_b_path, 3, 11, 3, 20),  # return OldHelper
    ]
~~~~~
~~~~~python.new
    from stitcher.refactor.engine.graph import ReferenceType

    locations = [
        # Locations in a.py
        UsageLocation(
            file_a_path,
            1,
            23,
            1,
            32,
            ReferenceType.IMPORT_PATH,
            "mypkg.core.OldHelper",
        ),  # from mypkg.core import OldHelper
        UsageLocation(
            file_a_path, 3, 6, 3, 15, ReferenceType.SYMBOL, "mypkg.core.OldHelper"
        ),  # obj = OldHelper()
        # Locations in b.py
        UsageLocation(
            file_b_path,
            2,
            27,
            2,
            36,
            ReferenceType.IMPORT_PATH,
            "mypkg.core.OldHelper",
        ),  # from mypkg.core import OldHelper
        UsageLocation(
            file_b_path,
            3,
            11,
            3,
            20,
            ReferenceType.SYMBOL,
            "mypkg.core.OldHelper",
        ),  # return OldHelper
    ]
~~~~~

#### Acts 4: 修复单元测试 `test_rename_transformer.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_transformer.py
~~~~~
~~~~~python.old
    locations = [
        UsageLocation(Path(""), lineno=3, col_offset=4, end_lineno=3, end_col_offset=7),
        UsageLocation(
            Path(""), lineno=4, col_offset=11, end_lineno=4, end_col_offset=14
        ),
    ]
~~~~~
~~~~~python.new
    from stitcher.refactor.engine.graph import ReferenceType

    locations = [
        UsageLocation(
            Path(""),
            lineno=3,
            col_offset=4,
            end_lineno=3,
            end_col_offset=7,
            ref_type=ReferenceType.SYMBOL,
            target_node_fqn="foo",
        ),
        UsageLocation(
            Path(""),
            lineno=4,
            col_offset=11,
            end_lineno=4,
            end_col_offset=14,
            ref_type=ReferenceType.SYMBOL,
            target_node_fqn="foo",
        ),
    ]
~~~~~

### 下一步建议
执行测试以验证修复是否成功。如果通过，我们可以继续进行下一阶段的任务（例如实战演练 Dogfooding）。
