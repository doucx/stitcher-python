## [WIP] test: 添加 PEP 420 隐式命名空间包发现的回归测试

### 用户需求
用户要求创建一个新的单元测试，以防止之前修复的 PEP 420 隐式命名空间包发现问题发生回归。该测试应验证 `Workspace` 类能够正确识别没有 `__init__.py` 文件的命名空间包。

### 评论
这个回归测试至关重要。它确保了对 `_get_top_level_importables` 方法的修改是持久的，并且未来对 `Workspace` 逻辑的任何改动都不会无意中破坏 PEP 420 命名空间包的发现能力。这提升了 `stitcher-refactor` 对现代 Python 项目结构的支持健壮性。

### 目标
1.  在 `packages/stitcher-refactor/tests/unit/refactor/` 目录下创建一个新的测试文件 `test_pep420_discovery.py`。
2.  在测试中，使用 `WorkspaceFactory` 模拟一个典型的 PEP 420 命名空间包结构：
    *   一个项目根目录。
    *   一个 `src/` 目录。
    *   在该 `src/` 目录下创建一个命名空间包（例如 `my_namespace`），其中不包含 `__init__.py` 文件。
    *   在该命名空间包内创建一个实际的子包（例如 `my_package`）。
3.  实例化 `Workspace` 并断言 `my_namespace` 能够被正确地识别为一个可导入的包，并且其源目录被正确地映射。

### 基本原理
该测试将直接验证 `Workspace._get_top_level_importables` 方法在遇到没有 `__init__.py` 文件的目录时，仍能正确将其识别为命名空间包的一部分并添加到导入路径中。这将有效地阻止相关回归。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/workspace #task/action/reproduction #task/state/begin

---

### Script

#### Acts 1: 创建 PEP 420 命名空间包的回归测试

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/refactor/test_pep420_discovery.py
~~~~~
~~~~~python
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
from pathlib import Path


def test_workspace_discovers_pep420_namespace_packages(tmp_path: Path):
    """
    Verifies that the Workspace correctly identifies and maps source directories
    for PEP 420 implicit namespace packages (i.e., directories without an __init__.py).
    """
    # 1. Arrange: Create a project with a PEP 420 namespace package
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory
        .with_pyproject("my-project")
        .with_source("my-project/src/my_namespace/my_package/__init__.py", "VERSION = '1.0'")
        .with_source("my-project/src/my_namespace/my_package/module.py", "def func(): pass")
        .build()
    )

    # The actual source directory containing 'my_namespace'
    namespace_parent_src = project_root / "my-project" / "src"

    # 2. Act
    workspace = Workspace(root_path=project_root)
    
    # 3. Assert
    # The 'my_namespace' should be discovered as a top-level importable.
    assert "my_namespace" in workspace.import_to_source_dirs, \
        f"'my_namespace' was not discovered. Found: {list(workspace.import_to_source_dirs.keys())}"

    # The source directory for 'my_namespace' should be its parent 'src' directory.
    assert namespace_parent_src in workspace.import_to_source_dirs["my_namespace"], \
        f"Expected '{namespace_parent_src}' in source dirs for 'my_namespace', but got: {workspace.import_to_source_dirs['my_namespace']}"

    # Also verify that the overall search paths include this source directory.
    assert namespace_parent_src in workspace.get_search_paths(), \
        f"Expected '{namespace_parent_src}' in search paths, but got: {workspace.get_search_paths()}"

~~~~~

### 下一步建议
请运行这个新创建的测试：

```bash
pytest packages/stitcher-refactor/tests/unit/refactor/test_pep420_discovery.py
```

如果测试通过，则证明修复是有效的，并且我们有了一个防止回归的保障。之后，我们可以继续执行最初的重构计划。
