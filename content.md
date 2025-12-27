## [WIP] test: 更新测试以适配多目标配置架构

### 用户需求
用户要求更新测试用例，以反映刚刚对 `stitcher-config` 和 `stitcher-application` 进行的多目标（Multi-Target）架构更改。

### 评论
代码变更已经破坏了旧的测试契约（例如 `load_config_from_path` 的返回值类型）。必须修复现有测试，并增加新的测试用例来覆盖多目标解析和执行的核心逻辑，以确保新功能的正确性和稳定性。

### 目标
1.  修复 `stitcher-config` 的测试：更新 `test_loader.py` 以处理 `load_config_from_path` 返回列表的变化，并添加针对 `[tool.stitcher.targets]` 解析的新测试。
2.  增强 `stitcher-application` 的测试：在 `test_end_to_end.py` 中添加一个集成测试，验证 `StitcherApp` 能正确处理并生成多个目标的存根。

### 基本原理
`load_config_from_path` 现在返回 `(List[StitcherConfig], str)`。旧测试期望返回单个对象，因此会失败。我们需要通过取列表的第一个元素来修复旧测试（模拟默认行为）。对于新功能，我们需要显式构建包含 `targets` 的 `pyproject.toml` 并验证解析器和执行器是否按预期迭代处理。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/config #scope/core #ai/instruct #task/domain/testing #task/object/test-suite #task/action/update #task/state/continue

---
### Script

#### Acts 1: 更新 `stitcher-config` 测试

我们将修复 `test_loader.py` 中的现有测试，并添加一个新的测试用例来验证多目标配置的解析。

~~~~~act
write_file
packages/stitcher-config/tests/test_loader.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from textwrap import dedent

from stitcher.config import load_config_from_path


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    # Main project config (Legacy Single Target Mode)
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
        [tool.stitcher]
        scan_paths = ["src/app"]
    """)
    )

    # A plugin package
    plugin_dir = tmp_path / "packages" / "my-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "pyproject.toml").write_text(
        dedent("""
        [project.entry-points."stitcher.plugins"]
        "my_plugin.api" = "my_pkg.api:create_api"
        "my_plugin.utils" = "my_pkg.utils:helpers"
    """)
    )

    # Another package without plugins
    other_dir = tmp_path / "packages" / "other-lib"
    other_dir.mkdir(parents=True)
    (other_dir / "pyproject.toml").write_text("[project]\nname='other'")

    return tmp_path


def test_load_config_discovers_plugins_legacy_mode(workspace: Path):
    # Act
    configs, project_name = load_config_from_path(workspace)

    # Assert
    assert len(configs) == 1
    config = configs[0]
    
    assert config.name == "default"
    assert config.scan_paths == ["src/app"]
    assert "my_plugin.api" in config.plugins
    assert config.plugins["my_plugin.api"] == "my_pkg.api:create_api"
    assert config.plugins["my_plugin.utils"] == "my_pkg.utils:helpers"
    assert len(config.plugins) == 2


def test_load_config_multi_target_mode(tmp_path: Path):
    # Arrange
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
        [project]
        name = "multi-target-proj"

        [tool.stitcher.targets.core]
        scan_paths = ["src/core"]
        stub_package = "packages/core-stubs"

        [tool.stitcher.targets.plugin]
        scan_paths = ["src/plugin"]
        stub_package = "packages/plugin-stubs"
    """)
    )

    # Act
    configs, project_name = load_config_from_path(tmp_path)

    # Assert
    assert project_name == "multi-target-proj"
    assert len(configs) == 2

    # Configs order depends on dictionary iteration order (insertion order in modern Python),
    # but let's look them up by name to be safe.
    config_map = {c.name: c for c in configs}

    assert "core" in config_map
    assert config_map["core"].scan_paths == ["src/core"]
    assert config_map["core"].stub_package == "packages/core-stubs"

    assert "plugin" in config_map
    assert config_map["plugin"].scan_paths == ["src/plugin"]
    assert config_map["plugin"].stub_package == "packages/plugin-stubs"
~~~~~

#### Acts 2: 更新 `stitcher-application` 集成测试

我们将向 `test_end_to_end.py` 添加一个新的测试用例，模拟一个具有多个生成目标的 Monorepo 环境，并验证 `StitcherApp` 是否为每个目标正确生成了文件。

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    spy_bus.assert_id_called(L.generate.file.success, level="success")
    spy_bus.assert_id_called(L.generate.run.complete, level="success")

    success_messages = [m for m in spy_bus.get_messages() if m["level"] == "success"]
    # 2 files generated (main.py, helpers.py), 1 run complete message
    assert len(success_messages) == 3


def test_app_generates_stubs_for_plugins_and_sources(tmp_path, monkeypatch):
~~~~~
~~~~~python
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    spy_bus.assert_id_called(L.generate.file.success, level="success")
    spy_bus.assert_id_called(L.generate.run.complete, level="success")

    success_messages = [m for m in spy_bus.get_messages() if m["level"] == "success"]
    # 2 files generated (main.py, helpers.py), 1 run complete message
    assert len(success_messages) == 3


def test_app_run_multi_target(tmp_path, monkeypatch):
    """
    Verifies that StitcherApp correctly handles multiple targets defined in pyproject.toml.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    
    # Manually injecting multi-target config into pyproject.toml via raw content
    # because WorkspaceFactory.with_config currently assumes simple [tool.stitcher] structure.
    # We'll just overwrite pyproject.toml at the end or use with_source for it.
    
    project_root = (
        factory
        .with_source("src/pkg_a/main.py", "def func_a(): ...")
        .with_source("src/pkg_b/main.py", "def func_b(): ...")
        .build()
    )

    # Overwrite pyproject.toml with multi-target config
    (project_root / "pyproject.toml").write_text(
        """
[project]
name = "monorepo"

[tool.stitcher.targets.pkg_a]
scan_paths = ["src/pkg_a"]
stub_path = "typings/pkg_a"

[tool.stitcher.targets.pkg_b]
scan_paths = ["src/pkg_b"]
stub_path = "typings/pkg_b"
        """,
        encoding="utf-8"
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    # 3. Assert
    # Check physical files
    assert (project_root / "typings/pkg_a/main.pyi").exists()
    assert (project_root / "typings/pkg_b/main.pyi").exists()

    # Check bus messages
    # We expect "Processing target: ..." messages
    messages = spy_bus.get_messages()
    processing_msgs = [m for m in messages if m["id"] == str(L.generate.target.processing)]
    assert len(processing_msgs) == 2
    
    target_names = {m["params"]["name"] for m in processing_msgs}
    assert target_names == {"pkg_a", "pkg_b"}

    spy_bus.assert_id_called(L.generate.run.complete, level="success")


def test_app_generates_stubs_for_plugins_and_sources(tmp_path, monkeypatch):
~~~~~
