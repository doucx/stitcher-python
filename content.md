好的，我们来创建“IDE 自动补全模拟测试”。

这个测试的核心是验证 `stitcher` 生成的存根包（stub package）能被 `pyright`（VS Code Python 语言服务器的核心引擎）正确识别。如果 `pyright` 能够无错误地解析使用了存根类型的代码，就证明了 IDE 的自动补全、类型检查和定义跳转等功能可以正常工作。

我将分两步实现这个目标：
1.  首先，扩展我们的测试工具 `VenvHarness`，增加一个执行 `pyright` 的新方法。
2.  然后，创建一个新的集成测试文件，利用这个新方法来执行端到端的验证。

## [WIP] feat(tests): 添加使用 pyright 的 IDE 代理测试

### 用户需求

实现“IDE 自动补全模拟测试”，以验证 `stitcher` 生成的存根对 IDE 工具链的有效性。

### 评论

这是一个至关重要的测试，它直接验证了 `stitcher` 项目的核心价值主张——改善开发体验（DX）。通过使用 `pyright` 这个业界标准的类型检查器作为 IDE 行为的代理，我们可以高置信度地确保生成的 `.pyi` 文件不仅结构正确，而且能被主流开发工具实际消费。

### 目标

1.  在测试工具 `VenvHarness` 中新增一个 `run_pyright_check` 方法，用于在隔离环境中执行 `pyright`。
2.  创建一个新的集成测试文件 `tests/integration/test_ide_proxy.py`。
3.  在该文件中实现一个完整的测试用例，流程如下：
    a.  构建一个源项目。
    b.  运行 `stitcher` 生成存根包。
    c.  在隔离环境中安装该存根包。
    d.  编写一个消费该包的客户端脚本。
    e.  使用 `pyright` 对客户端脚本进行类型检查，并断言其无错误通过。

### 基本原理

我们将遵循“黑盒环境隔离”的测试策略。通过 `WorkspaceFactory` 和 `VenvHarness`，我们模拟了一个完整的用户工作流：一个开发者创建了代码，使用 `stitcher` 生成类型提示，然后将其发布（在此处简化为本地安装），最后另一个开发者（或同一个开发者在另一个项目中）安装并使用这个包。`pyright` 的成功运行证明了 `stitcher` 生成的产物是符合标准且有效的，能够被静态分析工具链无缝集成，从而为 IDE 提供了正确的类型信息。

### 标签
#intent/build #intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/ide-simulation #task/action/implementation #task/state/continue

---
### Script

#### Acts 1: 扩展测试工具

首先，我将为 `VenvHarness` 添加执行 `pyright` 的能力。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/harness.py
~~~~~
~~~~~python.old
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
~~~~~python.new
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

    def run_pyright_check(self, script_path: Path) -> subprocess.CompletedProcess:
        """
        Runs pyright on a given script within the virtual environment.

        Args:
            script_path: The path to the Python script to type-check.

        Returns:
            The result of the subprocess call.
        """
        self.install("pyright")
        # Pyright is a JS application, so it provides an entry point script.
        # We find it in the venv's bin directory.
        bin_dir = "Scripts" if sys.platform == "win32" else "bin"
        pyright_exe = self.venv_dir / bin_dir / "pyright"
        return subprocess.run(
            [str(pyright_exe), str(script_path)], capture_output=True, text=True
        )
~~~~~

#### Acts 2: 创建 IDE 代理测试

现在，我将创建新的测试文件，并实现端到端的验证逻辑。

~~~~~act
write_file
tests/integration/test_ide_proxy.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory, VenvHarness


def test_pyright_resolves_types_from_stubs(
    tmp_path: Path, isolated_env: VenvHarness
):
    """
    Verifies that Pyright (the engine for VSCode's Pylance) can successfully
    resolve types from a generated stub package, simulating the IDE experience.
    """
    # 1. Arrange: Create a source project to generate stubs for.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_project_name("ide-proxy-proj")
        .with_config({"scan_paths": ["src/ide_proxy"], "stub_package": "stubs"})
        .with_source(
            "src/ide_proxy/models.py",
            """
            class ProxyModel:
                def get_id(self) -> int:
                    return 1
            """,
        )
        .build()
    )

    # 2. Act: Generate the stub package from the source project.
    app = StitcherApp(root_path=project_root)
    app.run_from_config()
    stub_pkg_path = project_root / "stubs"
    assert (
        stub_pkg_path / "src/ide_proxy-stubs/models.pyi"
    ).exists(), "Stub .pyi file was not generated."

    # 3. Act: Install the generated stubs into the isolated venv.
    isolated_env.install(str(stub_pkg_path))

    # 4. Act: Create a client script that consumes the code.
    client_script = tmp_path / "client.py"
    client_script.write_text(
        """
from ide_proxy.models import ProxyModel

# If stubs are working, pyright will know ProxyModel and its methods.
instance = ProxyModel()
reveal_type(instance.get_id())
"""
    )

    # 5. Act: Run pyright inside the isolated environment.
    result = isolated_env.run_pyright_check(client_script)

    # 6. Assert
    assert (
        result.returncode == 0
    ), f"Pyright failed with errors:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    # Verify Pyright's output confirms successful type analysis.
    assert (
        "0 errors" in result.stdout
    ), f"Pyright reported errors:\n{result.stdout}"
    assert (
        'Type of "instance.get_id()" is "int"' in result.stdout
    ), f"Pyright did not resolve the return type correctly.\nOutput:\n{result.stdout}"
~~~~~
