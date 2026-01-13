根据全量测试的反馈，由于我们加强了 `stitcher-workspace` 的发现逻辑（禁止静默回退），现有的集成测试环境因为缺失 `.git` 目录或 `[tool.uv.workspace]` 标记而无法被识别为合法的工作区。

我们将通过为测试用的 `WorkspaceFactory` 增加 `.init_git()` 调用来修复这些测试，确保它们符合“确定性工作区”的要求。

## [WIP] fix(tests): 修复集成测试以符合确定性工作区发现规则

### 错误分析
在之前的重构中，我们强化了 `find_workspace_root` 的逻辑：如果没有找到 `.git` 或特定的 `pyproject.toml` 配置，系统将抛出错误。
目前的集成测试中，`WorkspaceFactory` 创建的临时目录是一个平铺的文件夹，缺乏这些标识符，导致 CLI 在尝试定位工作区根目录时失败。

### 目标
1.  在所有失败的集成测试中，为 `WorkspaceFactory` 链增加 `.init_git()` 调用。
2.  确保 `stitcher-cli` 的集成测试能够在模拟的 Git 仓库中运行。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #comp/workspace #scope/core #ai/refine #task/domain/testing #task/object/integration-tests #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修复 `test_coverage_command.py`

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_coverage_command.py
~~~~~
~~~~~python.old
    # 1. Setup a workspace with diverse documentation coverage
    ws_root = (
        WorkspaceFactory(tmp_path)
        .with_config({"scan_paths": ["src"]})
~~~~~
~~~~~python.new
    # 1. Setup a workspace with diverse documentation coverage
    ws_root = (
        WorkspaceFactory(tmp_path)
        .init_git()
        .with_config({"scan_paths": ["src"]})
~~~~~

#### Acts 2: 修复 `test_fidelity_principles.py`

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_fidelity_principles.py
~~~~~
~~~~~python.old
    comments are preserved, and new keys are appended.
    """
    # 1. ARRANGE
    # Create a workspace with an existing, custom-formatted .stitcher.yaml
    # and a new function in the source code to be pumped.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
~~~~~
~~~~~python.new
    comments are preserved, and new keys are appended.
    """
    # 1. ARRANGE
    # Create a workspace with an existing, custom-formatted .stitcher.yaml
    # and a new function in the source code to be pumped.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
~~~~~
~~~~~python.old
    # 1. ARRANGE
    # Create a workspace, run `init`, and then `strip` to get a truly
    # clean state (docs only in YAML).
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
~~~~~
~~~~~python.new
    # 1. ARRANGE
    # Create a workspace, run `init`, and then `strip` to get a truly
    # clean state (docs only in YAML).
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
~~~~~

#### Acts 3: 修复 `test_pump_strip_interaction.py`

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py
~~~~~
~~~~~python.old
def test_pump_prompts_for_strip_when_redundant(tmp_path, monkeypatch):
    """
    Verifies that when 'pump' extracts docstrings (making source docs redundant),
    it prompts the user to strip them, and performs the strip if confirmed.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    # Create a file with a docstring that will be extracted
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
~~~~~
~~~~~python.new
def test_pump_prompts_for_strip_when_redundant(tmp_path, monkeypatch):
    """
    Verifies that when 'pump' extracts docstrings (making source docs redundant),
    it prompts the user to strip them, and performs the strip if confirmed.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    # Create a file with a docstring that will be extracted
    project_root = (
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
~~~~~
~~~~~python.old
def test_pump_with_strip_flag_executes_strip(tmp_path, monkeypatch):
    """
    Verifies that 'pump --strip' directly triggers a strip operation and
    emits the correct completion signal. This test bypasses interactive prompts.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
~~~~~
~~~~~python.new
def test_pump_with_strip_flag_executes_strip(tmp_path, monkeypatch):
    """
    Verifies that 'pump --strip' directly triggers a strip operation and
    emits the correct completion signal. This test bypasses interactive prompts.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
~~~~~

#### Acts 4: 修复 `test_refactor_command.py`

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python.old
def test_refactor_apply_e2e(tmp_path, monkeypatch):
    # 1. Arrange: Create a project and a migration script
    factory = WorkspaceFactory(tmp_path)
    # Project with a symbol to be renamed
    (
        factory.with_project_name("mypkg")
~~~~~
~~~~~python.new
def test_refactor_apply_e2e(tmp_path, monkeypatch):
    # 1. Arrange: Create a project and a migration script
    factory = WorkspaceFactory(tmp_path)
    # Project with a symbol to be renamed
    (
        factory.init_git()
        .with_project_name("mypkg")
~~~~~
~~~~~python.old
def test_refactor_apply_dry_run(tmp_path, monkeypatch):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    (
        factory.with_project_name("mypkg")
~~~~~
~~~~~python.new
def test_refactor_apply_dry_run(tmp_path, monkeypatch):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    (
        factory.init_git()
        .with_project_name("mypkg")
~~~~~

### 下一步建议
1.  **验证集成测试**: 重新运行 `packages/stitcher-cli` 下的集成测试，确保“无法定位工作区”的错误消失。
2.  **检查测试独立性**: 确保 `init_git()` 在 `tmp_path` 下创建的 `.git` 不会干扰父目录（即项目本身）的 Git 状态。`WorkspaceFactory` 默认应该处理好了这一点。
