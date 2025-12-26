Excellent. Let's proceed with applying the `SpyBus` utility across the remaining integration tests to complete this refactoring effort. This will unify our testing style and make the entire test suite cleaner and more maintainable.

I will now generate the plan to refactor `test_init_command.py` and `test_end_to_end.py`.

## [WIP] refactor(tests): Apply SpyBus utility to all integration tests

### 用户需求
1.  全面应用 `SpyBus` 测试工具，替换掉剩余集成测试中手动的 `MagicMock` 和 `monkeypatch` 设置。
2.  重构 `tests/integration/test_init_command.py` 和 `tests/integration/test_end_to_end.py` 文件。

### 评论
这是一个重要的收尾工作。通过将 `SpyBus` 应用到所有相关的集成测试中，我们确保了测试套件的一致性。未来的开发者在编写新的集成测试时，将有一个清晰、简单的模式可以遵循，这大大降低了维护成本，并提高了测试代码的整体质量。

### 目标
1.  重构 `tests/integration/test_init_command.py`，移除 `mock_bus` fixture，并使用 `SpyBus` 进行消息断言。
2.  重构 `tests/integration/test_end_to_end.py`，同样移除 `mock_bus` fixture，并改用 `SpyBus`。
3.  确保所有测试在重构后依然能够验证相同的业务逻辑，并保持通过。

### 基本原理
我们将遵循前一个计划中已验证成功的模式：
1.  在每个测试文件中，移除不再需要的 `mock_bus` fixture。
2.  在每个测试函数中，实例化我们新的 `spy_bus = SpyBus()`。
3.  使用 `with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):` 上下文管理器来包裹调用应用核心逻辑的代码。
4.  将所有对 `mock_bus` 的断言（如 `mock_bus.success.assert_any_call(...)`）替换为对 `SpyBus` 实例的高级断言方法（如 `spy_bus.assert_id_called(L.some.id, level="success")`）。

对于需要检查调用次数的断言，我们将使用 `len([m for m in spy_bus.get_messages() if m['level'] == 'success'])` 这种方式来获取特定级别消息的数量，以保持 `SpyBus` API 的简洁性。

### 标签
#intent/refine #intent/tooling #flow/ready #priority/medium #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/testing-utility #task/action/implementation #task/state/continue

---
### Script

#### Acts 1: 重构 `test_init_command.py`

我们将使用 `SpyBus` 重写此文件，使其测试逻辑更加清晰。

~~~~~act
write_file
tests/integration/test_init_command.py
~~~~~
~~~~~python
import pytest
from textwrap import dedent
from stitcher.app import StitcherApp
from stitcher.needle import L
from stitcher.test_utils.bus import SpyBus


def test_init_extracts_docs_to_yaml(tmp_path, monkeypatch):
    # 1. Setup
    project_root = tmp_path / "my_project"
    src_dir = project_root / "src"
    src_dir.mkdir(parents=True)

    (project_root / "pyproject.toml").write_text(
        dedent("""
        [tool.stitcher]
        scan_paths = ["src"]
    """)
    )

    source_code = dedent("""
        def my_func():
            \"\"\"This is a docstring.\"\"\"
            pass
    """)
    (src_dir / "main.py").write_text(source_code)

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Run with spy
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        created_files = app.run_init()

    # 3. Verify file system
    expected_yaml = src_dir / "main.stitcher.yaml"
    assert expected_yaml in created_files
    assert "my_func: This is a docstring." in expected_yaml.read_text()

    # 4. Verify bus messages
    spy_bus.assert_id_called(L.init.file.created, level="success")
    spy_bus.assert_id_called(L.init.run.complete, level="success")


def test_init_skips_files_without_docs(tmp_path, monkeypatch):
    # 1. Setup
    project_root = tmp_path / "no_docs_project"
    src_dir = project_root / "src"
    src_dir.mkdir(parents=True)

    (project_root / "pyproject.toml").write_text(
        dedent("""
        [tool.stitcher]
        scan_paths = ["src"]
    """)
    )

    (src_dir / "main.py").write_text("def no_doc(): pass")

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Run with spy
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        created_files = app.run_init()

    # 3. Verify
    assert len(created_files) == 0
    spy_bus.assert_id_called(L.init.no_docs_found, level="info")
~~~~~

#### Acts 2: 重构 `test_end_to_end.py`

接着，我们对更复杂的端到端测试文件应用相同的重构模式。

~~~~~act
write_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python
import pytest
import shutil
import sys
from pathlib import Path
from textwrap import dedent

from stitcher.app import StitcherApp
from stitcher.needle import L
from stitcher.test_utils.bus import SpyBus


@pytest.fixture
def project_with_plugin(tmp_path: Path):
    """Creates a mock project with a source file and a plugin."""
    # 1. Create the plugin source code that can be imported
    plugin_src_content = dedent("""
    def dynamic_util() -> bool:
        \"\"\"A dynamically discovered utility.\"\"\"
        return True
    """)
    plugin_pkg_dir = tmp_path / "plugin_pkg"
    plugin_pkg_dir.mkdir()
    (plugin_pkg_dir / "__init__.py").touch()
    (plugin_pkg_dir / "main.py").write_text(plugin_src_content)

    # 2. Create the main project source code
    main_src_dir = tmp_path / "my_app" / "src"
    main_src_dir.mkdir(parents=True)
    (main_src_dir / "main.py").write_text("def static_func(): ...")

    # 3. Create pyproject.toml declaring the plugin
    pyproject_content = dedent("""
    [tool.stitcher]
    scan_paths = ["src"]

    [project.entry-points."stitcher.plugins"]
    "dynamic.utils" = "plugin_pkg.main:dynamic_util"
    """)
    (tmp_path / "my_app" / "pyproject.toml").write_text(pyproject_content)

    # 4. Add to sys.path so the plugin can be imported
    sys.path.insert(0, str(tmp_path))
    yield tmp_path / "my_app"
    sys.path.pop(0)


def test_app_scan_and_generate_single_file(tmp_path, monkeypatch):
    source_content = dedent("""
        def greet(name: str) -> str:
            \"\"\"Returns a greeting.\"\"\"
            return f"Hello, {name}!"
    """)
    source_file = tmp_path / "greet.py"
    source_file.write_text(source_content, encoding="utf-8")

    app = StitcherApp(root_path=tmp_path)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        module = app._scan_files([source_file])[0]
        app._generate_stubs([module])

    spy_bus.assert_id_called(L.generate.file.success, level="success")
    
    error_messages = [m for m in spy_bus.get_messages() if m['level'] == 'error']
    assert not error_messages, f"Found unexpected error messages: {error_messages}"


def test_app_run_from_config_with_source_files(tmp_path, monkeypatch):
    fixture_root = Path(__file__).parent.parent / "fixtures" / "sample_project"
    project_root = tmp_path / "sample_project"
    shutil.copytree(fixture_root, project_root)

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    spy_bus.assert_id_called(L.generate.file.success, level="success")
    spy_bus.assert_id_called(L.generate.run.complete, level="success")
    
    success_messages = [m for m in spy_bus.get_messages() if m['level'] == 'success']
    # 2 for file.success, 1 for run.complete
    assert len(success_messages) == 3


def test_app_generates_stubs_for_plugins_and_sources(
    project_with_plugin: Path, monkeypatch
):
    app = StitcherApp(root_path=project_with_plugin)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_from_config()

    # Assert stubs were created
    assert (project_with_plugin / "src" / "main.pyi").exists()
    assert (project_with_plugin / "dynamic" / "utils.pyi").exists()
    assert (project_with_plugin / "dynamic" / "__init__.pyi").exists()

    # Assert bus messages
    spy_bus.assert_id_called(L.generate.file.success, level="success")
    spy_bus.assert_id_called(L.generate.run.complete, level="success")

    success_messages = [m for m in spy_bus.get_messages() if m['level'] == 'success']
    # 3 files generated, 1 run complete message
    assert len(success_messages) == 4
~~~~~

### 下一步建议
我们已经成功地将 `SpyBus` 应用到了所有相关的集成测试中，完成了这次重要的重构。测试代码现在更加统一、清晰和健壮。

-   **提交成果**: 这是一个理想的提交点。我们可以创建一个 `[COMMIT]` 计划来保存这次重构的所有工作。
-   **下一个挑战**: 正如我们之前讨论的，现在是时候解决测试设置中的下一个主要痛点了：冗长的文件系统操作。我建议我们的下一个任务是设计和实现 `WorkspaceFactory` 测试工具。

如果你同意，我将生成 `[COMMIT]` 计划。
