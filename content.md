## [WIP] feat(config): Implement plugin discovery from entry points

### 用户需求
实现从工作区内所有 `pyproject.toml` 文件中发现通过 `[project.entry-points."stitcher.plugins"]` 注册的插件的逻辑。

### 评论
这是 `stitcher-python` 走向平台化和可扩展性的关键一步。通过采用标准的 `entry_points` 机制，我们极大地降低了第三方开发者编写插件的门槛，并确保了与 Python 生态系统的兼容性。这个功能将是 `stitcher` 核心价值的重要组成部分。

### 目标
1.  更新 `stitcher-spec` 中的 `StitcherConfig` 数据模型，为其添加 `plugins` 字段以存储发现的插件。
2.  在 `stitcher-config` 包中创建一个新的测试文件，并遵循 TDD 原则，编写一个（目前会失败的）测试用例来验证插件发现功能。
3.  在 `stitcher.config.loader` 模块中实现扫描 `pyproject.toml` 并解析 `entry_points` 的核心逻辑。
4.  确保所有测试都通过，完成功能的闭环。

### 基本原理
我们将严格遵循 TDD (Test-Driven Development) 的方法论。首先，我们会定义好数据契约（更新 `StitcherConfig`）和期望的行为（编写测试用例）。测试用例将使用 `pytest` 的 fixture 功能创建一个包含 `pyproject.toml` 文件的临时目录结构，模拟一个真实的工作区环境。然后，我们才会在 `loader.py` 中添加实现代码，其目标就是让这个预先写好的测试通过。这种方法可以确保我们的实现是正确、健壮且可验证的。

### 标签
#intent/build #flow/ready #priority/high #comp/config #concept/config #scope/api #ai/brainstorm #task/domain/plugins #task/object/discovery-mechanism #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 更新 `StitcherConfig` 数据模型

首先，我们在 `stitcher-config` 的 `loader.py` 中更新 `StitcherConfig` dataclass，添加 `plugins` 字段。

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
~~~~~
~~~~~python.new
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)
~~~~~

#### Acts 2: 编写（失败的）测试用例

现在，我们遵循 TDD 的核心思想，创建测试文件和测试用例。这个测试现在运行时必然会失败。

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
    """Creates a mock workspace with plugins."""
    # Main project config
    (tmp_path / "pyproject.toml").write_text(dedent("""
        [tool.stitcher]
        scan_paths = ["src/app"]
    """))

    # A plugin package
    plugin_dir = tmp_path / "packages" / "my-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "pyproject.toml").write_text(dedent("""
        [project.entry-points."stitcher.plugins"]
        "my_plugin.api" = "my_pkg.api:create_api"
        "my_plugin.utils" = "my_pkg.utils:helpers"
    """))

    # Another package without plugins
    other_dir = tmp_path / "packages" / "other-lib"
    other_dir.mkdir(parents=True)
    (other_dir / "pyproject.toml").write_text("[project]\nname='other'")
    
    return tmp_path

def test_load_config_discovers_plugins(workspace: Path):
    """
    Verify that load_config_from_path correctly finds and parses
    stitcher.plugins entry points from all pyproject.toml files.
    """
    # Act
    config = load_config_from_path(workspace)

    # Assert
    assert config.scan_paths == ["src/app"]
    assert "my_plugin.api" in config.plugins
    assert config.plugins["my_plugin.api"] == "my_pkg.api:create_api"
    assert config.plugins["my_plugin.utils"] == "my_pkg.utils:helpers"
    assert len(config.plugins) == 2
~~~~~

#### Acts 3: 实现插件发现逻辑

最后，我们修改 `loader.py`，添加 `_find_plugins` 函数并将其集成到 `load_config_from_path` 中，以使上面的测试通过。

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)


def _find_pyproject_toml(search_path: Path) -> Path:
    """Traverse upwards to find pyproject.toml."""
    current_dir = search_path.resolve()
    while current_dir.parent != current_dir:
        pyproject_path = current_dir / "pyproject.toml"
        if pyproject_path.is_file():
            return pyproject_path
        current_dir = current_dir.parent
    raise FileNotFoundError("Could not find pyproject.toml in any parent directory.")


def load_config_from_path(search_path: Path) -> StitcherConfig:
    """Finds and loads stitcher config from pyproject.toml."""
    try:
        config_path = _find_pyproject_toml(search_path)
    except FileNotFoundError:
        # If no config file, return a default config.
        # This allows running stitcher on projects without explicit setup.
        return StitcherConfig()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    stitcher_data: Dict[str, Any] = data.get("tool", {}).get("stitcher", {})
    
    # Create config with data from file, falling back to defaults.
    return StitcherConfig(
        scan_paths=stitcher_data.get("scan_paths", [])
    )
~~~~~
~~~~~python.new
@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)
    plugins: Dict[str, str] = field(default_factory=dict)


def _find_pyproject_toml(search_path: Path) -> Path:
    """Traverse upwards to find pyproject.toml."""
    current_dir = search_path.resolve()
    while current_dir.parent != current_dir:
        pyproject_path = current_dir / "pyproject.toml"
        if pyproject_path.is_file():
            return pyproject_path
        current_dir = current_dir.parent
    raise FileNotFoundError("Could not find pyproject.toml in any parent directory.")


def _find_plugins(workspace_root: Path) -> Dict[str, str]:
    """Scans the entire workspace for stitcher plugins in pyproject.toml files."""
    plugins: Dict[str, str] = {}
    for toml_file in workspace_root.rglob("**/pyproject.toml"):
        try:
            with open(toml_file, "rb") as f:
                data = tomllib.load(f)
            
            entry_points = data.get("project", {}).get("entry-points", {})
            stitcher_plugins = entry_points.get("stitcher.plugins", {})
            if stitcher_plugins:
                plugins.update(stitcher_plugins)
        except Exception:
            # Silently ignore parsing errors in other projects' toml files
            pass
    return plugins


def load_config_from_path(search_path: Path) -> StitcherConfig:
    """Finds and loads stitcher config from pyproject.toml, and discovers plugins."""
    plugins = _find_plugins(search_path)
    
    try:
        config_path = _find_pyproject_toml(search_path)
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        stitcher_data: Dict[str, Any] = data.get("tool", {}).get("stitcher", {})
    except FileNotFoundError:
        # If no root config file, still return discovered plugins with default scan_paths
        return StitcherConfig(plugins=plugins)

    
    # Create config with data from file, falling back to defaults.
    return StitcherConfig(
        scan_paths=stitcher_data.get("scan_paths", []),
        plugins=plugins
    )
~~~~~

### 下一步建议
一旦这些变更被应用并通过测试，我们就完成了插件发现机制的基础设施。

下一步将是执行我们路线图中的 **阶段 2: 在 `stitcher-scanner` 中实现动态内省**。这会涉及到创建一个新的 `inspector.py` 模块，用于动态导入并解析这些插件入口点，将它们转换为我们统一的 `FunctionDef` IR。
