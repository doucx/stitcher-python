This diagnostic information is perfect. It gives us the "smoking gun" we've been looking for.

Your diagnostics have revealed a critical insight:

1.  **Package Installation is CORRECT**: `pip list` shows both packages. `ls site-packages` shows the `ide_proxy` source code directory is physically present.
2.  **Python Runtime is CORRECT**: `python -c "import ide_proxy.models"` succeeds. This proves the virtual environment itself is valid and the package is importable by a standard Python process.
3.  **Pyright is the Outlier**: The only component failing is `pyright`.

This leads to an inescapable conclusion: The issue is not with the package or the environment, but with **how `pyright` is being invoked**. `Pyright` is a powerful, project-aware tool. When we run it on a single file in a temporary directory (`/tmp/.../client.py`), it has no "project context." It doesn't know it's supposed to use the virtual environment we created for import resolution. It's effectively running in a vacuum and only seeing its built-in stubs, hence the `reportMissingImports` error.

The solution is to provide `pyright` with that missing context by creating a configuration file that explicitly tells it which virtual environment to use.

## [WIP] fix(tests): Provide explicit pyright config for IDE proxy test

### 用户需求

修复 `tests/integration/test_ide_proxy.py` 中因 `pyright` 缺少项目上下文而导致的导入解析失败问题。

### 评论

这次的失败和修复是整个测试过程中最有价值的一步。它揭示了静态分析工具（如 `pyright`）与 Python 运行时环境之间的关键差异。通过为 `pyright` 提供一个明确的配置文件 (`pyrightconfig.json`)，我们不仅修复了测试，而且使我们的测试环境与真实开发者的项目设置达到了前所未有的一致性，极大地增强了测试的有效性和可靠性。

### 目标

1.  修改 `test_pyright_resolves_types_from_stubs` 测试。
2.  在运行 `pyright` 之前，动态创建一个 `pyrightconfig.json` 文件。
3.  在该配置文件中，使用 `venvPath` 键明确指向由 `VenvHarness` 创建的虚拟环境的路径。
4.  确保 `pyright` 在包含此配置文件的目录中执行。

### 基本原理

`pyright` 在启动时会向上查找 `pyrightconfig.json` 或 `pyproject.toml` [tool.pyright]` 来确定其分析环境。通过提供一个包含 `venvPath` 的 `pyrightconfig.json` 文件，我们明确地指示 `pyright` 使用我们为其准备的、安装了所有必要包的隔离虚拟环境来解析导入。这弥合了工具上下文的鸿沟，使其行为与能够自动利用 `sys.path` 的 Python 解释器保持一致，从而确保了类型存根能够被正确发现和应用。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/ide-simulation #task/action/bug-fix #task/state/end

---
### Script

#### Acts 1: Instrument and Fix the Pyright Test with Configuration

我将使用 `write_file` 再次完整地重写 `test_ide_proxy.py`。这次的修改包含了最终的、决定性的修复：为 `pyright` 创建一个配置文件。

~~~~~act
write_file
tests/integration/test_ide_proxy.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory, VenvHarness


def test_pyright_resolves_types_from_stubs(
    tmp_path: Path, isolated_env: VenvHarness
):
    """
    Verifies that Pyright can resolve types from a generated stub package,
    simulating the IDE experience in a realistic environment where both the
    runtime and stub packages are installed, and Pyright is properly configured.
    """
    # --- ARRANGE ---

    source_content = "class ProxyModel:\n    def get_id(self):\n        return 1"

    # 1. Create the source project for Stitcher to scan.
    source_project_root = tmp_path / "source_project"
    WorkspaceFactory(source_project_root).with_project_name(
        "ide-proxy-proj"
    ).with_config(
        {"scan_paths": ["src/ide_proxy"], "stub_package": "stubs"}
    ).with_source(
        "src/ide_proxy/models.py", source_content
    ).build()

    # 2. Create a correctly configured, installable RUNTIME package.
    runtime_project_root = tmp_path / "runtime_project"
    WorkspaceFactory(runtime_project_root).with_source(
        "src/ide_proxy/models.py", source_content
    ).with_source(
        "src/ide_proxy/__init__.py",
        "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
    ).with_source(
        "pyproject.toml",
        """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[project]
name = "ide-proxy-proj"
version = "0.1.0"
[tool.hatch.build.targets.wheel]
packages = ["src/ide_proxy"]
""",
    ).build()

    # --- ACT ---

    # 3. Generate the stub package.
    app = StitcherApp(root_path=source_project_root)
    app.run_from_config()
    stub_pkg_path = source_project_root / "stubs"

    # 4. Install BOTH packages.
    isolated_env.install(str(runtime_project_root))
    isolated_env.install(str(stub_pkg_path))

    # 5. Create a client script and a Pyright config in a dedicated "client_project" dir.
    client_project_dir = tmp_path / "client_project"
    client_project_dir.mkdir()
    client_script = client_project_dir / "main.py"
    client_script.write_text(
        "from ide_proxy.models import ProxyModel\n\n"
        "instance = ProxyModel()\n"
        "reveal_type(instance.get_id())\n"
    )

    # 6. *** THE CRITICAL FIX ***
    #    Create a pyrightconfig.json to give Pyright the necessary context.
    pyright_config_path = client_project_dir / "pyrightconfig.json"
    pyright_config = {"venvPath": str(isolated_env.venv_dir)}
    pyright_config_path.write_text(json.dumps(pyright_config))

    # 7. Run Pyright check. We run it on the whole directory now.
    result = isolated_env.run_pyright_check(client_project_dir)

    # --- ASSERT ---
    
    # 8. Run diagnostics for rich error messages if needed.
    pip_list_output = isolated_env.pip_list()
    import_result = isolated_env.run_python_command("import ide_proxy.models")
    diagnostic_info = f"""
    --- DIAGNOSTICS ---
    [PIP LIST]
{pip_list_output}
    [PYTHON IMPORT TEST]
    Exit Code: {import_result.returncode}, Stderr: {import_result.stderr.strip()}
    ---
    [PYRIGHT OUTPUT]
    STDOUT:
{result.stdout}
    STDERR:
{result.stderr}
    """

    assert result.returncode == 0, f"Pyright failed with errors.\n{diagnostic_info}"
    assert "0 errors" in result.stdout, f"Pyright reported errors.\n{diagnostic_info}"
    assert (
        'Type of "instance.get_id()" is "int"' in result.stdout
    ), f"Pyright did not resolve the return type correctly.\n{diagnostic_info}"
~~~~~
