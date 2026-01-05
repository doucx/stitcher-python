您提供的测试失败信息非常清晰，直接指出了 `Workspace` 类在处理“扁平布局”（flat layout）时的逻辑缺陷。我的实现过于草率了。

感谢您提供如此精确的反馈。这是修正该问题的计划。

## [WIP] fix: 修复 Workspace 在扁平布局下的包发现逻辑

### 错误分析

测试 `test_workspace_flat_layout` 的失败暴露了 `_find_src_dir` 辅助方法中的一个核心逻辑错误。

1.  **当前行为**: 当处理扁平布局时（即源代码包直接位于 `pyproject.toml` 所在的目录），`_find_src_dir` 会错误地返回**第一个找到的包目录本身**（例如，`.../pkg_b/pkgb_lib`）作为“源目录”。
2.  **错误后果**: 随后，`_get_top_level_import_names` 方法被调用，并试图在 `.../pkg_b/pkgb_lib` 这个目录*内部*寻找顶级的可导入包。由于该目录内部只有 `__init__.py` 而没有其他包目录，它什么也找不到，返回一个空列表。
3.  **最终结果**: `import_to_source_dirs` 字典没有被填充，导致测试断言 `set() == {PosixPath(...)}` 失败。

### 目标

修正 `Workspace._find_src_dir` 方法，使其在处理扁平布局时，返回**包含包的目录**（例如 `.../pkg_b`），而不是包目录本身。

### 基本原理

正确的逻辑应该是：`_find_src_dir` 的职责是且仅是定位**包含顶级可导入包的目录**。

*   对于 `src` 布局，这个目录是 `.../pkg_a/src`。
*   对于扁平布局，这个目录应该是 `.../pkg_b`。

通过修改 `_find_src_dir` 的回退逻辑，使其在确认当前目录（`pkg_root`）下至少存在一个 Python 包后，直接返回 `pkg_root` 本身，我们就能统一这两种情况的行为。这样，`_get_top_level_import_names` 就能在正确的容器目录中查找，并成功发现如 `pkgb_lib` 这样的顶级包。

### 标签

#intent/fix #flow/ready #priority/critical #comp/refactor #concept/config #scope/core #ai/instruct #task/domain/refactor-engine #task/object/workspace-discovery #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正 `_find_src_dir` 的扁平布局逻辑

我们将修改 `workspace.py` 中 `_find_src_dir` 方法的回退逻辑，以确保它为扁平布局返回正确的源文件根目录。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
~~~~~
~~~~~python.old
        # Fallback for flat layouts: find the first dir containing __init__.py
        for item in pkg_root.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                return item

        return None
~~~~~
~~~~~python.new
        # Fallback for flat layouts: check if pkg_root itself contains packages.
        is_flat_layout = any(
            item.is_dir() and (item / "__init__.py").exists()
            for item in pkg_root.iterdir()
        )
        if is_flat_layout:
            return pkg_root

        return None
~~~~~

### 下一步建议

这个修复应该能让所有单元测试通过。一旦确认，我们将继续执行路线图的**任务 1.2**：实现 `SidecarManager` 类。
