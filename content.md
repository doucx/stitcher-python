为了彻底解决这个问题并获得更好的调试信息，我们将采取两步走的策略：
1.  **增强工具**: 修改 `VenvHarness`，使其在安装失败时明确打印 `stdout` 和 `stderr`，防止关键错误信息被吞没。
2.  **隔离并修复测试**: 修改测试用例，将两个包的安装步骤分开（以便精确定位哪个包构建失败），并将 `proj_with_runtime` 恢复为标准的 `src` 布局（这通常是 `hatchling` 支持得最好的布局），同时确保 `__init__.py` 存在。

## [WIP] fix(test): 增强 Harness 调试能力并修复命名空间测试布局

### 用户需求
1.  修复 `test_namespace_coexistence` 测试中的 `pip install` 错误。
2.  增强 `VenvHarness` 的错误报告能力，以便在未来发生类似构建错误时能快速诊断。

### 评论
盲目猜测构建错误的原因效率极低。通过增强 `VenvHarness`，我们能确切看到 `pip`（以及底层的 `hatchling`）在抱怨什么。同时，将测试中的包布局恢复为 Python 社区推荐的 `src` 布局，并显式配置 `hatchling`，是解决构建问题的最正统路径。分步安装则能让我们确定到底是存根包还是运行时包出了问题。

### 目标
1.  修改 `packages/stitcher-test-utils/src/stitcher/test_utils/harness.py`，在 `install` 方法中捕获 `CalledProcessError` 并打印输出。
2.  修改 `tests/integration/test_stub_package_namespace.py`：
    *   将 `proj_with_runtime` 的布局改回 `src/my_project/...`。
    *   在 `pyproject.toml` 中使用 `packages = ["src/my_project"]`。
    *   将 `isolated_env.install` 调用拆分为两步。

### 基本原理
*   **调试增强**: `print` 语句在 `pytest` 失败时会被捕获并显示在 "Captured stdout call" 部分，这比异常消息中的截断文本更完整。
*   **标准布局**: `src` 布局避免了许多隐式的导入问题，`hatchling` 对其有良好的支持。明确指定 `packages = ["src/my_project"]` 告诉构建后端将 `src/my_project` 目录作为包的根目录打包到 wheel 中。

### 标签
#intent/fix #intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/namespace-test #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 增强 VenvHarness 错误报告

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/harness.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
    def install(self, *packages: str) -> subprocess.CompletedProcess:
        """
        Installs packages into the virtual environment using pip.

        Args:
            *packages: A list of packages to install (can be paths or names).

        Returns:
            The result of the subprocess call.
        """
        try:
            return subprocess.run(
                [str(self.python_exe), "-m", "pip", "install", *packages],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            # Print output to ensure it's captured by pytest even if exception msg is truncated
            print(f"--- PIP INSTALL FAILED ---\nCMD: {e.args}\n")
            print(f"STDOUT:\n{e.stdout}\n")
            print(f"STDERR:\n{e.stderr}\n")
            print("--------------------------")
            raise
~~~~~

#### Acts 2: 修复测试用例的包布局和安装步骤

~~~~~act
patch_file
tests/integration/test_stub_package_namespace.py
~~~~~
~~~~~python.old
    # --- Part 2: Arrange a separate, installable RUNTIME package ---
    # We use a flat layout (no src/ dir) here to simplify the build config and avoid
    # potential src-layout configuration issues in the test fixture.
    factory_runtime = WorkspaceFactory(tmp_path / "proj_with_runtime")
    project_root_runtime = (
        factory_runtime.with_project_name("my-project-plugin")
        # This project provides the my_project.plugin namespace
        .with_source(
            "my_project/plugin.py",
            """
            def plugin_function():
                return True
            """,
        )
        # This __init__.py makes `my_project` a package.
        .with_source("my_project/__init__.py", "")
        # We need a pyproject.toml to make it an installable package
        .with_source(
            "pyproject.toml",
            """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-project-plugin"
version = "0.1.0"

[tool.hatch.build.targets.wheel]
packages = ["my_project"]
            """,
        )
        .build()
    )

    # --- Part 3: Install BOTH packages into the isolated environment ---
    isolated_env.install(str(stub_pkg_path), str(project_root_runtime))
~~~~~
~~~~~python.new
    # --- Part 2: Arrange a separate, installable RUNTIME package ---
    factory_runtime = WorkspaceFactory(tmp_path / "proj_with_runtime")
    project_root_runtime = (
        factory_runtime.with_project_name("my-project-plugin")
        # This project provides the my_project.plugin namespace
        .with_source(
            "src/my_project/plugin.py",
            """
            def plugin_function():
                return True
            """,
        )
        # This __init__.py makes `my_project` a package.
        .with_source("src/my_project/__init__.py", "")
        # We need a pyproject.toml to make it an installable package
        .with_source(
            "pyproject.toml",
            """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-project-plugin"
version = "0.1.0"

[tool.hatch.build.targets.wheel]
packages = ["src/my_project"]
            """,
        )
        .build()
    )

    # --- Part 3: Install packages into the isolated environment ---
    # Install stub package first
    isolated_env.install(str(stub_pkg_path))
    # Install runtime package second
    isolated_env.install(str(project_root_runtime))
~~~~~

### 下一步建议

请再次运行 `pytest`。

*   **如果测试通过**：我们将获得胜利，证明存根包与运行时包可以完美共存。
*   **如果测试仍然失败**：这次我们将在控制台输出中看到完整的 `pip` 错误日志，这将使我们能够立刻锁定是哪个包、因为什么具体的构建错误而失败。这将是最后一次调试所需的线索。
