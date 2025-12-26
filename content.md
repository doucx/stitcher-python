简要回答
发现并修复了 `stitcher-test-utils` 中的模块导入错误（`tomllib_w` 不存在），增强 `WorkspaceFactory` 以支持插件配置，并使用该工厂重构所有剩余的集成测试，使其不再依赖外部 fixture 文件。

## [WIP] test: 修复测试工具并重构集成测试

### 错误分析
用户遇到了 `ModuleNotFoundError: No module named 'tomllib_w'`。这是因为在 `stitcher-test-utils` 的 `workspace.py` 中，试图根据 Python 版本动态导入 TOML 写入库时，错误地引用了一个不存在的标准库名称 `tomllib_w`。实际上，写入 TOML 始终需要依赖第三方库 `tomli-w`（在代码中应导入为 `tomli_w`），即使在 Python 3.11+ 中，标准库 `tomllib` 也仅支持读取。

### 用户需求
1.  修复 `test_init_command.py` 收集测试时的导入错误。
2.  将 `WorkspaceFactory` 应用到剩余的集成测试 (`test_check_command.py`, `test_end_to_end.py`) 中，以统一测试风格并消除对文件系统 Fixture 的依赖。

### 评论
当前的集成测试混合使用了 `tmp_path` 手动创建文件、`shutil.copytree` 复制 Fixtures 以及新的 `WorkspaceFactory`。统一使用 `WorkspaceFactory` 将极大地提高测试的可读性和可维护性，并且使测试用例自包含（Self-contained），不再依赖散落在目录树各处的静态文件。

### 目标
1.  修正 `workspace.py` 中的导入逻辑。
2.  增强 `WorkspaceFactory`，使其支持构建包含 `project.entry-points` 的 `pyproject.toml`，以便测试插件系统。
3.  重构 `test_check_command.py` 和 `test_end_to_end.py`，完全使用 `WorkspaceFactory` 构建测试环境。

### 基本原理
通过修复 Import 错误解决当前的阻塞问题。通过增强 Factory 模式，我们可以以声明式的方式构建复杂的测试场景（如插件注册），而无需在测试代码中手动拼接 TOML 字符串。这将显著降低编写和维护集成测试的认知负荷。

### 标签
#intent/tooling #intent/refine #intent/fix #flow/ready #priority/high #comp/tests #task/domain/testing #task/object/integration-tests #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 修复 workspace.py 并增强功能
修复 `tomli_w` 的导入错误，并重构 `WorkspaceFactory` 以内部维护 `pyproject.toml` 的状态，从而支持通过多个方法（`with_config`, `with_entry_points`）逐步构建配置。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py
~~~~~
~~~~~python.old
import sys
from pathlib import Path
from textwrap import dedent
from typing import Dict, Any, List

import yaml

if sys.version_info < (3, 11):
    import tomli_w as tomlib_w
else:
    import tomllib_w


class WorkspaceFactory:
    """
    A test utility providing a fluent API to build virtual project workspaces.
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._files_to_create: List[Dict[str, Any]] = []

    def with_config(self, stitcher_config: Dict[str, Any]) -> "WorkspaceFactory":
        """Adds a pyproject.toml with a [tool.stitcher] section."""
        content = {"tool": {"stitcher": stitcher_config}}
        self._files_to_create.append(
            {"path": "pyproject.toml", "content": content, "format": "toml"}
        )
        return self

    def with_source(self, path: str, content: str) -> "WorkspaceFactory":
~~~~~
~~~~~python.new
from pathlib import Path
from textwrap import dedent
from typing import Dict, Any, List

import yaml
import tomli_w


class WorkspaceFactory:
    """
    A test utility providing a fluent API to build virtual project workspaces.
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._files_to_create: List[Dict[str, Any]] = []
        self._pyproject_data: Dict[str, Any] = {}

    def with_config(self, stitcher_config: Dict[str, Any]) -> "WorkspaceFactory":
        """Adds/Updates [tool.stitcher] section in pyproject.toml."""
        tool = self._pyproject_data.setdefault("tool", {})
        tool["stitcher"] = stitcher_config
        return self

    def with_entry_points(
        self, group: str, entry_points: Dict[str, str]
    ) -> "WorkspaceFactory":
        """Adds/Updates [project.entry-points] section in pyproject.toml."""
        project = self._pyproject_data.setdefault("project", {})
        eps = project.setdefault("entry-points", {})
        eps[group] = entry_points
        return self

    def with_source(self, path: str, content: str) -> "WorkspaceFactory":
~~~~~

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py
~~~~~
~~~~~python.old
    def build(self) -> Path:
        """Creates all specified files and directories in the workspace."""
        for file_spec in self._files_to_create:
            output_path = self.root_path / file_spec["path"]
            output_path.parent.mkdir(parents=True, exist_ok=True)

            content_to_write = ""
            fmt = file_spec["format"]
            content = file_spec["content"]

            if fmt == "toml":
                content_to_write = tomlib_w.dumps(content)
            elif fmt == "yaml":
                content_to_write = yaml.dump(content, indent=2)
            else:  # raw
                content_to_write = content

            output_path.write_text(content_to_write, encoding="utf-8")

        return self.root_path
~~~~~
~~~~~python.new
    def build(self) -> Path:
        """Creates all specified files and directories in the workspace."""
        # 1. Finalize pyproject.toml if data was added
        if self._pyproject_data:
            self._files_to_create.append(
                {
                    "path": "pyproject.toml",
                    "content": self._pyproject_data,
                    "format": "toml",
                }
            )

        # 2. Write all files
        for file_spec in self._files_to_create:
            output_path = self.root_path / file_spec["path"]
            output_path.parent.mkdir(parents=True, exist_ok=True)

            content_to_write = ""
            fmt = file_spec["format"]
            content = file_spec["content"]

            if fmt == "toml":
                content_to_write = tomli_w.dumps(content)
            elif fmt == "yaml":
                content_to_write = yaml.dump(content, indent=2)
            else:  # raw
                content_to_write = content

            output_path.write_text(content_to_write, encoding="utf-8")

        return self.root_path
~~~~~

#### Acts 2: 重构 test_check_command.py
使用 `WorkspaceFactory` 重写 `test_check_command.py`，移除手动的路径拼接和文件写入。

~~~~~act
write_file
tests/integration/test_check_command.py
~~~~~
~~~~~python
from stitcher.app import StitcherApp
from stitcher.needle import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_check_detects_missing_and_extra(tmp_path, monkeypatch):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            """
            def new_func():
                pass
            """,
        )
        .with_docs(
            "src/main.stitcher.yaml",
            {"__doc__": "Module doc", "deleted_func": "Old doc"},
        )
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False

    spy_bus.assert_id_called(L.check.file.fail, level="error")
    spy_bus.assert_id_called(L.check.issue.missing, level="error")
    spy_bus.assert_id_called(L.check.issue.extra, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_check_passes_when_synced(tmp_path, monkeypatch):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(): pass")
        .with_docs(
            "src/main.stitcher.yaml",
            {"__doc__": "Doc", "func": "Doc"},
        )
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.run.success, level="success")
~~~~~

#### Acts 3: 重构 test_end_to_end.py
重构端到端测试。利用新的 `with_entry_points` 功能来设置插件测试，并用 Factory 替代 `shutil.copytree` 来构建示例项目。

~~~~~act
write_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python
import sys
from pathlib import Path

from stitcher.app import StitcherApp
from stitcher.needle import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_app_scan_and_generate_single_file(tmp_path, monkeypatch):
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_source(
            "greet.py",
            """
            def greet(name: str) -> str:
                \"\"\"Returns a greeting.\"\"\"
                return f"Hello, {name}!"
            """,
        )
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        # Accessing internal methods directly for this specific test case
        # as per original test logic
        source_file = project_root / "greet.py"
        module = app._scan_files([source_file])[0]
        app._generate_stubs([module])

    spy_bus.assert_id_called(L.generate.file.success, level="success")

    error_messages = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not error_messages, f"Found unexpected error messages: {error_messages}"


def test_app_run_from_config_with_source_files(tmp_path, monkeypatch):
    # Recreating the structure previously held in tests/fixtures/sample_project
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src/app"]})
        .with_source(
            "src/app/main.py",
            """
            def start():
                \"\"\"Starts the application.\"\"\"
                pass
            """,
        )
        .with_source(
            "src/app/utils/helpers.py",
            """
            def assist():
                \"\"\"Provides assistance.\"\"\"
                pass
            """,
        )
        # This file should remain untouched/unscanned
        .with_source("src/app/tests/test_helpers.py", "def test_assist(): pass")
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    spy_bus.assert_id_called(L.generate.file.success, level="success")
    spy_bus.assert_id_called(L.generate.run.complete, level="success")

    success_messages = [m for m in spy_bus.get_messages() if m["level"] == "success"]
    # 2 files generated (main.py, helpers.py), 1 run complete message
    assert len(success_messages) == 3


def test_app_generates_stubs_for_plugins_and_sources(tmp_path, monkeypatch):
    # 1. Arrange: Setup a workspace with both source code and a plugin definition
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def static_func(): ...")
        # Define the plugin source code in a separate package within the workspace
        .with_source(
            "plugin_pkg/main.py",
            """
            def dynamic_util() -> bool:
                \"\"\"A dynamically discovered utility.\"\"\"
                return True
            """,
        )
        .with_source("plugin_pkg/__init__.py", "")
        # Register the plugin via entry points
        .with_entry_points(
            "stitcher.plugins", {"dynamic.utils": "plugin_pkg.main:dynamic_util"}
        )
        .build()
    )

    # Add the workspace root to sys.path so the plugin can be imported
    sys.path.insert(0, str(project_root))

    try:
        app = StitcherApp(root_path=project_root)
        spy_bus = SpyBus()

        # 2. Act
        with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
            app.run_from_config()

        # 3. Assert
        # Assert stubs were created
        assert (project_root / "src" / "main.pyi").exists()
        assert (project_root / "dynamic" / "utils.pyi").exists()
        # Intermediate __init__.pyi should be created for the virtual module
        assert (project_root / "dynamic" / "__init__.pyi").exists()

        # Assert bus messages
        spy_bus.assert_id_called(L.generate.file.success, level="success")
        spy_bus.assert_id_called(L.generate.run.complete, level="success")

        success_messages = [
            m for m in spy_bus.get_messages() if m["level"] == "success"
        ]
        # 3 files generated (src/main, dynamic/utils, dynamic/__init__), 1 run complete
        assert len(success_messages) == 4

    finally:
        # Cleanup sys.path
        sys.path.pop(0)
~~~~~

### 下一步建议
运行测试以确认修复有效。如果测试通过，可以考虑删除不再需要的 `tests/fixtures/sample_project` 目录，以清理项目结构。
