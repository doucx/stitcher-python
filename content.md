## [WIP] fix(core): 修复 Sidecar 发现机制与目录移动逻辑

### 错误分析

1.  **签名文件未被更新**: 多数集成测试失败的原因是 `.json` 签名文件的内容（键名）未被重命名。这是因为 `Workspace.discover_files` 包含一个硬编码的过滤器 `if not p.startswith(".stitcher/")`，这直接导致位于 `.stitcher/signatures/` 下的所有签名文件被排除在索引之外。索引器“看不见”这些文件，自然无法为它们生成重命名计划。
2.  **签名文件未被移动**: `MoveDirectoryOperation` 仅遍历并移动了源目录下的物理文件。由于签名文件存储在源码树之外的 `.stitcher/signatures` 目录中，它们被遗留在了旧位置。
3.  **调试测试用例失败**: `test_debug_rename_failure.py` 在 `.stitcher.yaml` 中使用了 `"MessageBus"` 这样的短名，而 `RenameSymbolOperation` 依据 FQN (`stitcher.common.messaging.bus.MessageBus`) 进行匹配。由于 `SidecarAdapter` 目前不执行自动名称解析，这种不匹配导致重命名被跳过。

### 用户需求

修复上述三个问题，使重构引擎能够正确地：
1.  **发现**并索引 `.stitcher/signatures` 下的签名文件。
2.  在移动目录时，**同步移动**关联的外部 Sidecar 文件。
3.  通过修正测试数据，**验证** Sidecar 内容的重命名逻辑。

### 评论

这是一个非常关键的修复。它不仅解决了一大批集成测试失败的问题，更重要的是它填补了系统在处理“影子文件”（Shadow Files/Sidecars）时的架构漏洞。特别是 `Workspace` 的发现逻辑修正，对于确保系统的完整性至关重要。

### 目标

1.  修改 `Workspace.discover_files`，允许 `.stitcher/signatures` 目录被发现，但继续排除 `.stitcher/index` 等缓存目录。
2.  增强 `MoveDirectoryOperation`，使其在处理每个源文件时，利用 `SidecarManager` 检查并生成对应 Sidecar 的移动意图。
3.  修正 `test_debug_rename_failure.py`，使用标准的 FQN 作为 Sidecar 键名。

### 基本原理

1.  **白名单机制**: 我们不能简单地移除 `.stitcher/` 的过滤器，因为 `.stitcher/index` (SQLite DB) 不应被作为文本文件索引。我们需要一个精细的过滤逻辑：排除 `.stitcher` 但特例放行 `.stitcher/signatures`。
2.  **操作原子性**: 目录移动操作在逻辑上等同于“批量文件移动”。因此，它必须继承“移动文件”的所有语义，包括对关联 Sidecar 的处理。最简单的实现方式是在遍历源文件时，复用 `SidecarManager` 的路径解析逻辑。
3.  **测试一致性**: 既然系统设计为“Sidecar 使用 FQN”，测试数据就必须遵循这一契约，除非我们计划在 Adapter 层引入复杂的符号解析（目前不在范围内）。

### 标签

#intent/fix #flow/ready #priority/critical
#comp/runtime #comp/refactor #comp/tests
#concept/file-discovery #concept/sidecar #concept/refactoring
#task/domain/refactoring #task/object/sidecar-handling #task/action/fix-discovery-and-move

---

### Script

#### Acts 1: 修正 Workspace 的文件发现逻辑

修改 `workspace.py`，将针对 `.stitcher/` 的全局屏蔽改为精细化过滤。我们将允许 `.stitcher/signatures` 通过，同时继续拦截其他 `.stitcher` 子目录。

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/workspace.py
~~~~~
~~~~~python.old
        # Global Filter: Exclude .stitcher directory
        final_paths = {
            p for p in paths if not p.startswith(".stitcher/") and p != ".stitcher"
        }
        return final_paths
~~~~~
~~~~~python.new
        # Global Filter: Exclude .stitcher directory, BUT allow signatures
        final_paths = set()
        for p in paths:
            if p == ".stitcher":
                continue
            if p.startswith(".stitcher/"):
                # Only allow signatures, skip index, cache, etc.
                if not p.startswith(".stitcher/signatures/"):
                    continue
            final_paths.add(p)
        return final_paths
~~~~~

#### Acts 2: 增强 MoveDirectoryOperation 以处理 Sidecar

修改 `MoveDirectoryOperation`，在遍历源目录文件生成 `MoveFileIntent` 的同时，检查并生成对应的 Sidecar 移动意图。这复用了 `MoveFileOperation` 中的部分逻辑思想，但适配了批量处理的上下文。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
                dest_item = dest_dir / relative_path
                intents.append(MoveFileIntent(src_item, dest_item))

        # 3. Declare deletion of the source directory
~~~~~
~~~~~python.new
                dest_item = dest_dir / relative_path
                intents.append(MoveFileIntent(src_item, dest_item))

                # Also move associated sidecars (docs and signatures)
                # These are usually outside the src_dir (e.g. signatures), so they won't be caught by rglob.
                for get_sidecar_path in [
                    ctx.sidecar_manager.get_doc_path,
                    ctx.sidecar_manager.get_signature_path,
                ]:
                    try:
                        sidecar_src = get_sidecar_path(src_item)
                        if sidecar_src.exists():
                            sidecar_dest = get_sidecar_path(dest_item)
                            intents.append(MoveFileIntent(sidecar_src, sidecar_dest))
                    except ValueError:
                        # Ignore paths that can't be mapped (e.g. outside root)
                        pass

        # 3. Declare deletion of the source directory
~~~~~

#### Acts 3: 修正测试用例数据

修改 `test_debug_rename_failure.py`，将 YAML 中的键名从短名 `MessageBus` 更新为 FQN `stitcher.common.messaging.bus.MessageBus`，以符合 `SidecarAdapter` 的索引预期。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
~~~~~
~~~~~python.old
        .with_docs(
            "packages/stitcher-common/src/stitcher/common/messaging/bus.stitcher.yaml",
            {
                "MessageBus": "Docs for MessageBus.",
                "MessageBus.info": "Docs for info method.",
            },
        )
~~~~~
~~~~~python.new
        .with_docs(
            "packages/stitcher-common/src/stitcher/common/messaging/bus.stitcher.yaml",
            {
                "stitcher.common.messaging.bus.MessageBus": "Docs for MessageBus.",
                "stitcher.common.messaging.bus.MessageBus.info": "Docs for info method.",
            },
        )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
~~~~~
~~~~~python.old
    # Assert YAML sidecar content
    updated_yaml_data = yaml.safe_load(bus_yaml_path.read_text())
    assert "FeedbackBus" in updated_yaml_data, "BUG: YAML doc key was not renamed."
    assert "MessageBus" not in updated_yaml_data
    assert "FeedbackBus.info" in updated_yaml_data, (
        "BUG: YAML doc method key was not renamed."
    )
~~~~~
~~~~~python.new
    # Assert YAML sidecar content
    updated_yaml_data = yaml.safe_load(bus_yaml_path.read_text())
    assert new_fqn in updated_yaml_data, "BUG: YAML doc key was not renamed."
    assert old_fqn not in updated_yaml_data
    assert f"{new_fqn}.info" in updated_yaml_data, (
        "BUG: YAML doc method key was not renamed."
    )
~~~~~

### 下一步建议

执行此计划后，所有的集成测试（包括重命名和移动操作）应该都能通过。接下来，我们应该：
1.  运行所有测试以确认修复有效。
2.  考虑为 `SidecarAdapter` 添加更智能的解析逻辑，使其能够处理短名（可选，视未来需求而定）。
3.  检查 `DeleteDirectoryOperation` 是否也存在类似的遗漏 Sidecar 的问题（虽然删除源码通常不强制要求删除历史签名，但保持清洁是好的）。
