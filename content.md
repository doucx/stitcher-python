好的，测试已经就位并捕获了预期的失败。现在，我们将实施“正规军”的修复方案。

## [WIP] fix(refactor): 实现基于 Python 标识符规范的健壮包发现过滤

### 错误分析
当前的 `Workspace` 包发现逻辑过于宽松，它将任何不以 `__` 开头和结尾的目录都视为潜在的包。这导致了诸如 `stitcher_python.egg-info`、`.git`、`invalid-pkg` 等非 Python 包目录被错误地包含进来，并传递给下游的 Griffe 分析器，最终导致 `ImportError` 崩溃。

正确的做法是，一个目录或模块文件名要想成为一个可导入的 Python 实体，其名称必须是一个**有效的 Python 标识符**。

### 用户需求
用户要求实现一个健壮的、非捷径的解决方案，以精确地过滤掉所有无效的包和模块目录，只保留那些符合 Python 语言规范的可导入实体。

### 评论
这是一个至关重要的修复，它将 `stitcher-refactor` 的行为与 Python 的导入系统对齐。通过使用 Python 内置的 `str.isidentifier()` 方法，我们采用了最标准、最pythonic 的方式来验证包名，确保了工具的健壮性和准确性，杜绝了因项目根目录下的非代码文件夹而导致的意外崩溃。

### 目标
1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/workspace.py` 中的 `_get_top_level_importables` 方法。
2.  对所有发现的目录名和模块名（`.py` 文件的词干）应用 `str.isidentifier()` 检查。
3.  只将那些通过了标识符检查的名称添加到最终的可导入包列表中。

### 基本原理
我们将利用 `str.isidentifier()` 这个内置方法。它能完美地处理所有边缘情况：
-   拒绝包含 `.` 或 `-` 的名称。
-   拒绝以数字开头的名称。
-   自动处理 Python 关键字。
-   允许标准的 `[a-zA-Z0-9_]` 字符组合。

这将一次性、优雅地解决所有在 `test_workspace_filtering.py` 中定义的过滤问题。

### 标签
#intent/fix #flow/ready #priority/critical #comp/refactor #scope/core #ai/instruct #task/domain/core-abstractions #task/object/workspace-filtering #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 实施基于 `isidentifier` 的过滤逻辑

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
~~~~~
~~~~~python.old
    def _get_top_level_importables(self, src_path: Path) -> List[str]:
        names: Set[str] = set()
        for item in src_path.iterdir():
            # A top-level package is a directory. Griffe will handle namespace packages.
            # Exclude dunder directories like __pycache__
            if item.is_dir() and not (item.name.startswith("__") and item.name.endswith("__")):
                names.add(item.name)
            # A top-level module is a .py file (but not __init__.py itself)
            elif (
                item.is_file() and item.name.endswith(".py") and item.stem != "__init__"
            ):
                names.add(item.stem)
        return list(names)
~~~~~
~~~~~python.new
    def _get_top_level_importables(self, src_path: Path) -> List[str]:
        names: Set[str] = set()
        if not src_path.is_dir():
            return []

        for item in src_path.iterdir():
            # A potential top-level package is a directory whose name is a valid identifier.
            if item.is_dir() and item.name.isidentifier():
                names.add(item.name)
            # A potential top-level module is a .py file whose stem is a valid identifier.
            elif (
                item.is_file() and item.name.endswith(".py") and item.stem.isidentifier()
            ):
                names.add(item.stem)
        return list(names)
~~~~~

### 下一步建议
1.  **验证修复**：首先，请重新运行我们刚刚创建的过滤测试，以确认修复已生效且所有断言都通过。
    ```bash
    pytest packages/stitcher-refactor/tests/unit/refactor/test_workspace_filtering.py
    ```

2.  **执行重构**：测试通过后，我们就可以满怀信心地重新运行最初的重构命令了。它现在应该能够正确地发现所有合法的包，并成功完成重命名。
    ```bash
    stitcher refactor apply 001_rename_message_bus.py --yes
    ```
