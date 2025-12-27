好的，我们开始。

根据你的需求和你提供的文档 `存根包需要创建的测试列表`，我将为你实现 `VenvHarness` 这个测试工具类。

这个工具类是进行可靠集成测试的基石。它将被放置在 `stitcher-test-utils` 包中以便于在整个测试套件中复用，并会创建一个对应的 pytest fixture，让测试用例可以方便地获取一个干净、隔离的虚拟环境。

## [WIP] tooling: 实现 VenvHarness 测试工具类

### 用户需求
根据 `存根包需要创建的测试列表` 文档中的规划，需要创建一个可复用的 Python 测试工具类 `VenvHarness`。该类应利用 `subprocess` 和 `venv` 模块来管理独立的虚拟环境，用于后续的集成测试，特别是存根包的安装与类型检查验证。

### 评论
这是一个至关重要的开发工具。通过将测试环境与开发者本地环境彻底隔离，`VenvHarness` 将从根本上消除因环境差异导致的测试不稳定性。它为实现“声明式环境构建”和“零副作用保证”这两条核心测试原则（来自 `架构原则：测试体系与验证规范.md`）提供了物理基础。

### 目标
1.  在 `stitcher-test-utils` 包中创建 `harness.py` 文件，用于存放 `VenvHarness` 类。
2.  实现 `VenvHarness` 类，使其具备创建虚拟环境、在其中安装包以及运行 `mypy` 类型检查的能力。
3.  更新 `stitcher-test-utils` 的 `__init__.py` 以导出 `VenvHarness`。
4.  在 `tests/integration` 目录下创建 `conftest.py` 文件，并定义一个名为 `isolated_env` 的 pytest fixture，该 fixture 将为测试用例提供一个 `VenvHarness` 实例。

### 基本原理
我们将 `VenvHarness` 设计为一个封装了 `venv` 和 `subprocess` 复杂性的高级 API。
- **封装**: 测试用例的编写者无需关心 `venv` 的创建细节或 `subprocess` 的参数，只需调用如 `harness.install()` 和 `harness.run_type_check()` 等高级方法。
- **可复用性**: 将其放置在 `stitcher-test-utils` 包中，并提供一个全局的 fixture，使得任何集成测试都可以通过简单地请求 `isolated_env` fixture 来获得一个干净的、即用型的测试环境。
- **隔离**: 所有操作都基于 `pytest` 的 `tmp_path` fixture，确保每次测试运行都在一个全新的临时目录中进行，杜绝了测试间的相互干扰。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/integration-harness #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建 VenvHarness 工具类

我们首先在 `stitcher-test-utils` 包中创建 `harness.py` 并实现 `VenvHarness` 类。

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/harness.py
~~~~~
~~~~~python
import subprocess
import venv
from pathlib import Path
from typing import List


class VenvHarness:
    """A test utility for creating and managing isolated virtual environments."""

    def __init__(self, root: Path):
        """
        Initializes the harness.

        Args:
            root: The temporary directory where the venv will be created.
        """
        self.root = root
        self.venv_dir = self.root / ".venv"
        self._python_exe: Path | None = None
        self.create()

    @property
    def python_exe(self) -> Path:
        """Returns the path to the Python executable in the virtual environment."""
        if self._python_exe is None:
            # Determine executable path based on OS
            bin_dir = "Scripts" if sys.platform == "win32" else "bin"
            self._python_exe = self.venv_dir / bin_dir / "python"
        return self._python_exe

    def create(self) -> None:
        """Creates a clean virtual environment."""
        venv.create(self.venv_dir, with_pip=True, clear=True)

    def install(self, *packages: str) -> subprocess.CompletedProcess:
        """
        Installs packages into the virtual environment using pip.

        Args:
            *packages: A list of packages to install (can be paths or names).

        Returns:
            The result of the subprocess call.
        """
        return subprocess.run(
            [str(self.python_exe), "-m", "pip", "install", *packages],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_type_check(self, script_path: Path) -> subprocess.CompletedProcess:
        """
        Runs mypy on a given script within the virtual environment.

        Args:
            script_path: The path to the Python script to type-check.

        Returns:
            The result of the subprocess call.
        """
        # Ensure mypy is installed for the check
        self.install("mypy")
        return subprocess.run(
            [str(self.python_exe), "-m", "mypy", str(script_path)],
            capture_output=True,
            text=True,
        )
~~~~~

#### Acts 2: 导出 VenvHarness

现在，我们更新 `stitcher-test-utils` 的 `__init__.py`，使其导出新创建的 `VenvHarness` 类。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/__init__.py
~~~~~
~~~~~python.old
from .bus import SpyBus
from .nexus import MockNexus
from .workspace import WorkspaceFactory

__all__ = ["SpyBus", "MockNexus", "WorkspaceFactory"]
~~~~~
~~~~~python.new
from .bus import SpyBus
from .nexus import MockNexus
from .workspace import WorkspaceFactory
from .harness import VenvHarness

__all__ = ["SpyBus", "MockNexus", "WorkspaceFactory", "VenvHarness"]
~~~~~

#### Acts 3: 在集成测试中提供 Fixture

最后，我们在 `tests/integration` 目录中创建一个 `conftest.py` 文件，定义一个 `isolated_env` fixture，以便所有集成测试都能方便地使用 `VenvHarness`。

~~~~~act
write_file
tests/integration/conftest.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from stitcher.test_utils import VenvHarness


@pytest.fixture
def isolated_env(tmp_path: Path) -> VenvHarness:
    """
    Provides an isolated virtual environment harness for integration testing.
    """
    return VenvHarness(tmp_path)
~~~~~

### 下一步建议

我们已经成功创建了 `VenvHarness` 工具和对应的 `isolated_env` fixture。

下一步，我们将利用这个新工具来编写第一个集成测试：**结构合规性测试 (Structure Compliance Test)**。该测试将：
1.  调用 `StitcherApp` 在临时目录中生成一个存根包。
2.  使用 `isolated_env` 来验证生成的 `pyproject.toml` 中的包名是否正确（以 `-stubs` 结尾）。
3.  验证生成的源码目录名称是否为 `src/<name>-stubs`，以符合 PEP 561 规范。

如果你同意，我将为你生成实现此测试的计划。
