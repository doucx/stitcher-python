## [WIP] fix(app): Prevent generation of root-level __init__.pyi

### 错误分析
集成测试失败，提示实际生成了 4 个文件，而预期是 3 个。
多出来的文件是位于项目根目录的 `__init__.pyi`。
这是因为在 `_process_plugins` 方法中，构建中间目录的循环 `range(len(module_path_parts) + 1)` 从 0 开始迭代。
当 `i=0` 时，`parts[:0]` 为空列表，导致 `Path(*[], "__init__.py")` 解析为根目录下的 `__init__.py`。
在大多数情况下，我们不应该将项目根目录本身标记为一个 Python 包。

### 用户需求
修复 `_process_plugins` 逻辑，使其只为插件路径中的子目录创建 `__init__.pyi`，而跳过根目录。

### 评论
这是一个经典的 Off-by-one 错误。

### 目标
1.  修改 `stitcher.app.core` 中的 `_process_plugins` 方法，将循环范围修改为从 1 开始。

### 基本原理
当 `parts=["A", "B", "func"]` 时，我们需要 `A/__init__.py` 和 `A/B/__init__.py`。
`module_path_parts` 为 `["A", "B"]`。
我们需要切片 `[:1]` 和 `[:2]`。
因此循环应为 `range(1, len(module_path_parts) + 1)`。

### 标签
#intent/fix #flow/ready #priority/high #comp/application #scope/core #ai/refine #task/domain/plugins #task/object/orchestration-layer #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复循环范围

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
                func_path = Path(*module_path_parts, f"{func_file_name}.py")
                
                # Ensure all intermediate __init__.py modules exist
                for i in range(len(module_path_parts) + 1):
                    init_path = Path(*parts[:i], "__init__.py")
                    if not virtual_modules[init_path].file_path:
                         virtual_modules[init_path].file_path = init_path.as_posix()
~~~~~
~~~~~python.new
                func_path = Path(*module_path_parts, f"{func_file_name}.py")
                
                # Ensure all intermediate __init__.py modules exist
                # Start from 1 to avoid creating __init__.py at the root level (parts[:0])
                for i in range(1, len(module_path_parts) + 1):
                    init_path = Path(*parts[:i], "__init__.py")
                    if not virtual_modules[init_path].file_path:
                         virtual_modules[init_path].file_path = init_path.as_posix()
~~~~~
