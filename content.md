简要回答：
很好的建议。将测试项目结构作为外部 fixtures（固定装置）是一种标准的、更清晰的测试方法。我们将创建一个 `tests/fixtures/` 目录来存放这个模拟项目，然后在测试运行时将其复制到 `tmp_path` 中。

**RED 阶段**：我们将编写一个新的集成测试，它会：
1.  创建一个包含 `pyproject.toml` 和多个源文件的模拟项目结构。
2.  调用一个尚未实现的新方法 `StitcherApp.run_from_config()`。
3.  断言 `StitcherApp` 能够根据配置 (`scan_paths`) 找到并处理正确的文件，忽略其他文件。

## [WIP] test(e2e): 添加基于配置的项目扫描集成测试 (Red Phase)

### 用户需求
为 `StitcherApp` 添加一个集成测试，该测试验证其根据 `pyproject.toml` 中的配置 (`[tool.stitcher]`) 扫描项目并生成 `.pyi` 文件的能力。测试数据（模拟项目）应作为外部文件存在，以保持测试代码的整洁。

### 评论
我们将在 `tests/fixtures/sample_project/` 目录下创建这个模拟项目。测试函数会使用 `shutil.copytree` 将其完整复制到 `pytest` 提供的临时目录 `tmp_path` 中。

这个测试驱动了 `stitcher-config` 包的第一个真实需求：我们需要一个 `load_config` 函数。同时，它也驱动了 `StitcherApp` 的演进，使其从处理显式文件列表，升级到能根据配置自主发现工作。

### 目标
1.  创建 `tests/fixtures/sample_project` 目录结构和文件。
2.  在 `test_end_to_end.py` 中添加新的测试 `test_app_run_from_config`。
3.  创建 `stitcher-config` 包的占位符实现。
4.  在 `StitcherApp` 中添加 `run_from_config` 占位符方法。
5.  运行 `pytest` 并预期新测试失败。

### 基本原理
通过模拟一个真实的项目结构，我们可以非常精确地测试配置加载、路径解析和文件过滤等关键功能，确保 `Stitcher` 在真实世界场景中的行为符合预期。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/tests #comp/app #comp/config #scope/core #ai/instruct
#task/domain/testing #task/object/e2e-tests #task/action/create-case
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 创建测试用的 Fixture 项目结构
首先创建目录。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p tests/fixtures/sample_project/src/app/utils
mkdir -p tests/fixtures/sample_project/tests
~~~~~

#### Acts 2: 填充 Fixture 项目文件
现在，我们为这个模拟项目添加 `pyproject.toml` 配置文件和几个 Python 文件。

~~~~~act
write_file
tests/fixtures/sample_project/pyproject.toml
~~~~~
~~~~~toml
[tool.stitcher]
scan_paths = ["src/app"]
~~~~~

~~~~~act
write_file
tests/fixtures/sample_project/src/app/main.py
~~~~~
~~~~~python
def start():
    """Starts the application."""
    pass
~~~~~

~~~~~act
write_file
tests/fixtures/sample_project/src/app/utils/helpers.py
~~~~~
~~~~~python
def assist():
    """Provides assistance."""
    pass
~~~~~

~~~~~act
write_file
tests/fixtures/sample_project/tests/test_helpers.py
~~~~~
~~~~~python
# This file should NOT be scanned and have a .pyi generated for it.
from app.utils.helpers import assist

def test_assist():
    pass
~~~~~

#### Acts 3: 创建 Config Loader 占位符
为了让测试能够导入，我们需要 `stitcher-config` 中的骨架。

~~~~~act
write_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class StitcherConfig:
    scan_paths: List[str] = dataclasses.field(default_factory=list)

def load_config_from_path(search_path: Path) -> StitcherConfig:
    """Finds and loads stitcher config from pyproject.toml."""
    # TODO: Implement file finding and toml parsing
    return StitcherConfig()
~~~~~

~~~~~act
write_file
packages/stitcher-config/src/stitcher/config/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .loader import StitcherConfig, load_config_from_path

__all__ = ["StitcherConfig", "load_config_from_path"]
~~~~~

#### Acts 4: 编写新的集成测试 (RED)
我们将这个新测试添加到 `test_end_to_end.py` 中。

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
import pytest
from pathlib import Path
from textwrap import dedent

# This module doesn't exist yet, driving its creation
from stitcher.app import StitcherApp
~~~~~
~~~~~python.new
import pytest
import shutil
from pathlib import Path
from textwrap import dedent

# This module doesn't exist yet, driving its creation
from stitcher.app import StitcherApp
~~~~~

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
    # Verify core components are present
    assert "def greet(name: str) -> str:" in pyi_content
    assert '"""Returns a greeting."""' in pyi_content
    assert "..." in pyi_content
~~~~~
~~~~~python.new
    # Verify core components are present
    assert "def greet(name: str) -> str:" in pyi_content
    assert '"""Returns a greeting."""' in pyi_content
    assert "..." in pyi_content


def test_app_run_from_config(tmp_path):
    # 1. Arrange: Copy the fixture project into a temporary directory
    fixture_root = Path(__file__).parent.parent / "fixtures" / "sample_project"
    project_root = tmp_path / "sample_project"
    shutil.copytree(fixture_root, project_root)

    # 2. Act
    app = StitcherApp(root_path=project_root)
    # This new method should discover config and run generation
    generated_files = app.run_from_config()

    # 3. Assert
    main_pyi = project_root / "src" / "app" / "main.pyi"
    helpers_pyi = project_root / "src" / "app" / "utils" / "helpers.pyi"
    test_pyi = project_root / "tests" / "test_helpers.pyi"

    assert main_pyi.exists()
    assert helpers_pyi.exists()
    assert not test_pyi.exists() # Crucially, this should NOT be generated

    assert main_pyi in generated_files
    assert helpers_pyi in generated_files

    main_content = main_pyi.read_text()
    assert "def start():" in main_content
    assert '"""Starts the application."""' in main_content
~~~~~

#### Acts 5: 更新 App 占位符
最后，在 `StitcherApp` 中添加新的 `run_from_config` 方法的占位符。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # The app 'has a' generator, it uses it as a tool.
        self.generator = StubGenerator()

    def run_generate(self, files: List[Path]) -> List[Path]:
~~~~~
~~~~~python.new
from stitcher.config import load_config_from_path

class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # The app 'has a' generator, it uses it as a tool.
        self.generator = StubGenerator()

    def run_from_config(self) -> List[Path]:
        """
        Loads config, discovers files, and generates stubs.
        """
        # TODO: Implement config loading and file discovery
        return []

    def run_generate(self, files: List[Path]) -> List[Path]:
~~~~~

### 下一步建议
运行 `pytest`，新测试将失败。
下一步是 **GREEN** 阶段：
1.  在 `stitcher-config` 中实现 `load_config_from_path`，使其能真正解析 `pyproject.toml`。
2.  在 `StitcherApp.run_from_config` 中实现文件发现逻辑（使用 `Path.glob`），然后调用现有的 `run_generate` 来完成工作。
