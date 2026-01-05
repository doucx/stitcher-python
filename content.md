## [WIP] test: 添加测试用例以复现重构时的包发现问题

### 用户需求
用户报告了一个严重的 Bug：在 Monorepo 环境下运行 `stitcher refactor` 时，工具似乎未能发现所有相关的包，导致重构操作遗漏了关键的符号引用。特别是核心的 `stitcher` 命名空间包没有出现在加载列表中。用户要求创建一个测试文件来复现并捕获这个错误，且明确禁止在此时修复代码。

### 评论
该问题可能源于 `Workspace` 类在扫描和构建包映射时的逻辑缺陷，特别是在处理复杂的 Monorepo 结构（包含根目录 `pyproject.toml` 和子目录 `packages/*`）以及命名空间包（如 `src/stitcher`）时的边缘情况。

### 目标
1.  在 `packages/stitcher-refactor/tests/unit/refactor/` 目录下创建一个新的测试文件 `test_workspace_discovery_bug.py`。
2.  在测试中，使用 `WorkspaceFactory` 精确模拟用户的目录结构，包括：
    *   根目录下的 `pyproject.toml` 和迁移脚本。
    *   `packages/` 目录下的多个子包（`stitcher-cli`, `stitcher-common`）。
    *   使用 `src/stitcher` 这种标准的命名空间包结构。
3.  断言 `Workspace` 能够正确地将 `stitcher` 识别为一个顶层包，并包含来自所有子包的源目录。

### 基本原理
通过构建一个最小化的、但结构上等同于用户环境的复现案例，我们可以确定问题是否出在 `Workspace._discover_packages` 的发现逻辑上。如果测试失败（即 `stitcher` 未被发现或路径不全），则证实了 Bug 的位置。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/workspace-discovery #task/action/reproduction #task/state/begin

---

### Script

#### Acts 1: 创建复现测试文件

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/refactor/test_workspace_discovery_bug.py
~~~~~
~~~~~python
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_workspace_discovery_with_root_config_and_namespace_packages(tmp_path):
    """
    Reproduction test for a bug where 'stitcher' namespace package is not discovered
    when running in a monorepo structure with a root pyproject.toml and a migration script.
    """
    # 1. Arrange: Simulate the user's environment structure
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory
        # Root level configuration and script
        .with_pyproject(".")
        .with_source("001_rename_message_bus.py", "pass")
        
        # Package 1: stitcher-common (contributes to stitcher namespace)
        .with_pyproject("packages/stitcher-common")
        .with_source(
            "packages/stitcher-common/src/stitcher/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)"
        )
        .with_source("packages/stitcher-common/src/stitcher/common/__init__.py", "")
        
        # Package 2: stitcher-cli (contributes to stitcher namespace)
        .with_pyproject("packages/stitcher-cli")
        .with_source(
            "packages/stitcher-cli/src/stitcher/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)"
        )
        .with_source("packages/stitcher-cli/src/stitcher/cli/__init__.py", "")
        
        # Another package: needle (should be discovered)
        .with_pyproject("packages/pyneedle")
        .with_source("packages/pyneedle/src/needle/__init__.py", "")
        
        .build()
    )

    # 2. Act
    workspace = Workspace(root_path=project_root)
    discovered_packages = list(workspace.import_to_source_dirs.keys())
    
    # Debug output for analysis
    print(f"Discovered packages: {discovered_packages}")

    # 3. Assert
    # The migration script might be discovered as a module (e.g. '001_rename_message_bus')
    # But crucially, 'stitcher' MUST be present.
    assert "stitcher" in workspace.import_to_source_dirs, \
        f"'stitcher' package was not discovered. Found: {discovered_packages}"

    # Verify that 'stitcher' maps to multiple source directories (from common and cli)
    stitcher_sources = workspace.import_to_source_dirs["stitcher"]
    assert len(stitcher_sources) >= 2, \
        f"Expected at least 2 source dirs for 'stitcher', found {len(stitcher_sources)}: {stitcher_sources}"
~~~~~

### 下一步建议
请运行这个新创建的测试：

```bash
pytest packages/stitcher-refactor/tests/unit/refactor/test_workspace_discovery_bug.py
```

根据测试结果（是通过还是失败），我们将决定下一步是修复 `Workspace` 类，还是继续排查其他组件（如 Griffe 加载器）。
