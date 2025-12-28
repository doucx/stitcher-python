好的，我注意到了这两个测试失败。你的判断是正确的，这些测试确实与 `FileSystemLoader` 的最新实现（特别是基于文件路径合成 FQN 的逻辑）脱节了。同时，这也暴露了 `put` 方法中一个关于键处理的逻辑缺陷。

这是一个典型的“代码演进后，测试未同步”的问题。我们将一次性修复它们。

1.  **`test_nexus_with_fs_loader_handles_overrides` 失败原因**:
    *   **现状**: 测试用例在一个名为 `main.json` 的文件中，使用了 `cli.default` 这样的**完整 FQN** 作为键。
    *   **问题**: 当前的 `FileSystemLoader` 实现遵循 SST 规范，它会从文件路径中推断出 FQN 的第一部分。例如，它期望 `cli.json` 文件包含 `default` 键，然后将它们组合成 `cli.default`。测试中的数据结构不再有效，导致加载器无法找到预期的键。

2.  **`test_fs_loader_put_writes_to_correct_location` 失败原因**:
    *   **现状**: `FileSystemLoader.put` 方法在更新数据时，直接使用了完整的 FQN（例如 `app.title`）作为字典的键写入 `file_data`。
    *   **问题**: 当 `handler.save` 被调用时，`JsonHandler` 的 `_inflate_dict` 方法会将这个带点的键错误地展开成一个嵌套对象（例如，`{"app": {"title": ...}}`）。当这个文件被重新加载时，`FileSystemLoader` 会再次加上文件名前缀 `app`，最终导致 FQN 变成了错误的 `app.app.title`。正确的行为应该是 `put` 方法将**相对键**（`title`）写入 `file_data`。

我将执行一个计划来修正这两个问题：

1.  **更新测试数据**: 我会修改 `test_assembly.py` 中的 `multi_root_workspace` fixture，使其创建的文件结构和内容与 SST 规范保持一致。
2.  **修复 `put` 方法**: 我会修改 `FileSystemLoader.put` 的实现，确保它在写入文件时使用相对键，而不是完整的 FQN。

这将使测试恢复正常，并增强 `FileSystemLoader` 的健壮性。

我将生成一个计划来实现这个修复。

## [WIP] fix: 修复过时的 FileSystemLoader 测试并修正 put 方法

### 错误分析
`pyneedle-runtime` 包中的两个测试用例 `test_nexus_with_fs_loader_handles_overrides` 和 `test_fs_loader_put_writes_to_correct_location` 失败。

1.  **测试数据过时**: 第一个测试用例使用的数据结构（在 `main.json` 和 `overrides.json` 中使用完整 FQN）与 `FileSystemLoader` 当前基于 SST（从文件路径合成 FQN 前缀）的实现不匹配。
2.  **`put` 方法缺陷**: 第二个测试用例暴露了 `FileSystemLoader.put` 方法的一个 bug。它错误地将完整的 FQN（如 `app.title`）作为键写入文件，而不是使用相对键（`title`），这导致在重新加载时 FQN 被错误地构造为 `app.app.title`。

### 用户需求
修复这两个失败的测试，确保 Needle 的文件系统加载器行为正确且测试覆盖有效。

### 评论
这是一个重要的修复，它使核心的 `FileSystemLoader` 的行为（特别是写入操作）与其设计规范（SST）保持一致，并更新了关键的集成测试以防止未来的回归。

### 目标
1.  修改 `packages/pyneedle-runtime/tests/test_assembly.py`，更新 `multi_root_workspace` fixture 以使用符合 SST 规范的文件名和键。
2.  修改 `packages/pyneedle-runtime/src/needle/loaders/fs_loader.py` 中的 `put` 方法，使其在写入数据时使用相对键。

### 基本原理
通过将测试用例与 `FileSystemLoader` 的既定规范对齐，并修复 `put` 方法中 FQN 到相对键的转换逻辑，我们可以确保 `load` 和 `put` 操作的对称性和正确性。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/fs-loader #task/action/bug-fix #task.state/continue

---

### Script

#### Acts 1: 更新过时的测试用例

我们将 `main.json` 和 `overrides.json` 重命名为 `cli.json`，并移除键中的 `cli.` 前缀，使其符合 SST 规范。

~~~~~act
patch_file
packages/pyneedle-runtime/tests/test_assembly.py
~~~~~
~~~~~python.old
    # 1. Define package assets (low priority)
    pkg_root = tmp_path / "pkg_assets"
    factory.with_source(
        f"{pkg_root.name}/needle/en/main.json",
        """
        {
            "cli.default": "I am a default",
            "cli.override_me": "Default Value"
        }
        """,
    )

    # 2. Define user project assets (high priority)
    project_root = tmp_path / "my_project"
    factory.with_source(
        f"{project_root.name}/pyproject.toml", "[project]\nname='my-project'"
    ).with_source(
        f"{project_root.name}/.stitcher/needle/en/overrides.json",
        """
        {
            "cli.override_me": "User Override!",
            "cli.user_only": "I am from the user"
        }
        """,
    )
~~~~~
~~~~~python.new
    # 1. Define package assets (low priority)
    pkg_root = tmp_path / "pkg_assets"
    factory.with_source(
        f"{pkg_root.name}/needle/en/cli.json",
        """
        {
            "default": "I am a default",
            "override_me": "Default Value"
        }
        """,
    )

    # 2. Define user project assets (high priority)
    project_root = tmp_path / "my_project"
    factory.with_source(
        f"{project_root.name}/pyproject.toml", "[project]\nname='my-project'"
    ).with_source(
        f"{project_root.name}/.stitcher/needle/en/cli.json",
        """
        {
            "override_me": "User Override!",
            "user_only": "I am from the user"
        }
        """,
    )
~~~~~

#### Acts 2: 修复 FileSystemLoader.put 方法

我们将修改 `put` 方法，确保在更新 `file_data` 字典时使用相对键。

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~
~~~~~python.old
        # 3. Update the file's data
        file_data[key] = str_value

        # 4. Save back to the specific file
~~~~~
~~~~~python.new
        # 3. Update the file's data
        parts = key.split(".", 1)
        # The key inside the file is relative to the filename (which is parts[0])
        relative_key = parts[1] if len(parts) > 1 else key
        file_data[relative_key] = str_value

        # 4. Save back to the specific file
~~~~~
