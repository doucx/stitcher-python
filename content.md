# [WIP] test: 更新集成测试以匹配绝对导入行为

### 用户需求
修复因最近的“相对导入转绝对导入”变更导致的 `test_move_file_e2e.py` 测试失败。

### 评论
我们最近修改了 `SymbolRenamerTransformer`，使其在处理带有 `module` 部分的 `ImportFrom` 语句时，强制使用绝对导入。这是为了解决跨目录移动时的路径计算问题。
这个变更导致了 `test_move_file_e2e.py` 失败，因为它断言重构后的代码保留了相对导入格式 `from .new import A`，而实际结果现在是 `from mypkg.new import A`。
我们需要更新测试断言以接受这种更稳健的绝对导入风格。

### 目标
修改 `packages/stitcher-refactor/tests/integration/test_move_file_e2e.py`，更新对 `app.py` 内容的断言。

### 基本原理
将断言从检查相对路径更改为检查绝对路径。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/refactor #scope/core #ai/instruct #task/domain/refactoring #task/object/test-suite #task/action/update-assertion #task/state/continue

---

### Script

#### Acts 1: 更新 test_move_file_e2e.py

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python.old
    # Content updated?
    new_app = app_py.read_text("utf-8")
    assert "import mypkg.new" in new_app
    assert "from mypkg.new import A" in new_app
    assert "from . import new" in new_app
    assert "from .new import A as AliasA" in new_app

    # Sidecar Keys
~~~~~
~~~~~python.new
    # Content updated?
    new_app = app_py.read_text("utf-8")
    assert "import mypkg.new" in new_app
    assert "from mypkg.new import A" in new_app
    assert "from . import new" in new_app
    # Note: Stitcher now converts relative imports with a module part to absolute imports for robustness
    assert "from mypkg.new import A as AliasA" in new_app

    # Sidecar Keys
~~~~~

### 下一步建议
运行所有相关测试：
`uv run pytest packages/stitcher-refactor/tests/integration/test_bug_relative_import_refactor.py packages/stitcher-refactor/tests/integration/test_move_file_e2e.py`
