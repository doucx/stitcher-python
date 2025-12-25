好的，现在进入 **GREEN** 阶段。我们将分两步完成任务：
1.  **实现 Config Loader**: 让 `stitcher-config` 能够找到并解析 `pyproject.toml`。
2.  **实现 App Orchestration**: 让 `StitcherApp` 使用配置来发现文件并调用 `run_generate`。

## [WIP] feat(app,config): 实现基于配置的项目扫描 (Green Phase)

### 用户需求
实现 `stitcher-config` 和 `stitcher-application` 的逻辑，以通过 `test_app_run_from_config` 测试。这要求应用能够：
1.  自动在项目根目录找到 `pyproject.toml`。
2.  解析 `[tool.stitcher]` 表。
3.  根据 `scan_paths` 递归地查找所有 `.py` 文件。
4.  为找到的文件生成 `.pyi` 存根。

### 评论
**Config Loader**: `load_config_from_path` 的逻辑需要向上遍历目录树，直到找到 `pyproject.toml`。我们将使用 `pathlib` 来实现这一点。Python 3.11+ 内置了 `tomllib`，为了向后兼容，我们将为旧版本添加 `tomli` 依赖。

**App Logic**: `run_from_config` 将成为 `StitcherApp` 的主要入口点。它会首先调用 `load_config_from_path`，然后使用 `Path.glob` 来实现文件发现。最后，它会把发现的文件列表委托给已经测试过的 `run_generate` 方法，这体现了良好的职责分离。

### 目标
1.  在 `stitcher-config` 中实现 `load_config_from_path` 的完整逻辑。
2.  在 `StitcherApp` 中实现 `run_from_config` 的完整逻辑。
3.  确保所有测试通过。

### 基本原理
通过将配置解析和应用逻辑分离，我们构建了一个灵活的系统。`StitcherApp` 依赖于 `StitcherConfig` 数据类，而不是直接依赖于 TOML 文件本身，这使得未来的测试和扩展（例如，从其他来源加载配置）变得更加容易。

### 标签
#intent/build #flow/ready #priority/high
#comp/app #comp/config #scope/core #ai/instruct
#task/domain/implementation #task/object/orchestrator-logic #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 实现 Config Loader
我们将用完整的实现替换 `loader.py` 中的占位符。

~~~~~act
write_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Any, Dict

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


@dataclass
class StitcherConfig:
    scan_paths: List[str] = field(default_factory=list)


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

#### Acts 2: 实现 App 的文件发现与生成逻辑
现在我们来填充 `StitcherApp.run_from_config`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_from_config(self) -> List[Path]:
        """
        Loads config, discovers files, and generates stubs.
        """
        # TODO: Implement config loading and file discovery
        return []
~~~~~
~~~~~python.new
    def run_from_config(self) -> List[Path]:
        """
        Loads config, discovers files, and generates stubs.
        """
        config = load_config_from_path(self.root_path)
        
        if not config.scan_paths:
            # Handle case where config is empty or not found.
            # We could default to scanning the root path, or do nothing.
            # Let's do nothing for now, to be explicit.
            return []
            
        files_to_scan = []
        for scan_path_str in config.scan_paths:
            scan_path = self.root_path / scan_path_str
            if scan_path.is_dir():
                # Recursively find all .py files in the directory
                files_to_scan.extend(scan_path.rglob("*.py"))
            elif scan_path.is_file():
                # If it's a single file, add it
                files_to_scan.append(scan_path)
        
        # Deduplicate in case of overlapping paths
        unique_files = sorted(list(set(files_to_scan)))
        
        # Delegate the actual generation to the already tested method
        return self.run_generate(files=unique_files)
~~~~~

### 下一步建议
运行 `pytest`。所有测试现在都应该通过了。

我们已经完成了从 **任务 1.1** 到 **任务 1.3** MVP 版本的核心实现。我们现在拥有一个可以根据 `pyproject.toml` 配置，扫描项目并生成 `.pyi` 文件的功能完备的应用层。

接下来的步骤是：
1.  **实现 `stitcher-cli`**: 将 `StitcherApp` 连接到 `typer` 命令，使其成为一个真正可用的命令行工具。
2.  **插件发现**: 开始实现 **任务 1.4**，这是解决 IDE 体验问题的核心。这会涉及到对 `stitcher-config` 的扩展，以解析 `entry-points`。
