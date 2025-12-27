You've hit on a crucial and subtle aspect of how type checkers like `pyright` work with stub packages.

Your analysis is correct. The error `Import "ide_proxy.models" could not be resolved` happens because `pyright` is stricter than `mypy` in this scenario. It expects the *actual* runtime package (`ide-proxy-proj`) to be installed in the environment before it will look for and apply types from an associated stub package (`ide-proxy-proj-stubs`). Our test was only installing the stubs, creating a "ghost" namespace that `pyright` rightfully refused to resolve.

To fix this, we must create a more realistic test environment that mimics a user's setup:
1.  Create a basic, installable **runtime package** (even one without type hints).
2.  Generate the **stub package** using `stitcher`.
3.  Install **both** packages into the isolated virtual environment.

This ensures `pyright` can find the runtime code and then correctly apply the high-fidelity types from our stub package. I will now generate a plan to implement this more robust test.

## [WIP] fix(tests): Simulate full package installation for Pyright test

### 错误分析

`pyright` 测试失败的根本原因是测试环境不完整。我们只安装了 `stitcher` 生成的存根包 (`-stubs`)，而没有安装它所要提供类型信息的实际运行时包。`pyright` 遵循 PEP 561 的严格解释，它需要一个基础包存在，然后才会查找并应用存根包中的类型。由于找不到名为 `ide-proxy-proj` 的已安装包，它无法解析 `import ide_proxy.models`，导致测试失败。

### 用户需求

修复 `test_ide_proxy.py` 中的 `test_pyright_resolves_types_from_stubs` 测试，使其能够通过 `pyright` 的严格检查。

### 评论

这是一个非常有价值的失败，它迫使我们编写了更真实的集成测试。通过模拟运行时包和存根包同时存在的环境，我们能更准确地验证 `stitcher` 的产出在真实世界场景中的行为，确保了对 VS Code (Pylance) 等主流 IDE 的兼容性。

### 目标

1.  重构测试 `test_pyright_resolves_types_from_stubs` 的 Arrange 阶段。
2.  创建一个基础的、可安装的**运行时包**，它包含无类型提示的 Python 源代码和一个简单的 `pyproject.toml`。
3.  保持现有的逻辑，使用 `stitcher` 从源码生成一个独立的**存根包**。
4.  在 `isolated_env` 中，**同时安装**上述两个包。
5.  保持测试的 Act 和 Assert 阶段不变，验证 `pyright` 现在可以正确解析类型。

### 基本原理

本修复遵循 PEP 561 的核心思想：存根包是对运行时包的**增强**，而非替代。通过在测试环境中同时提供这两个组件，我们创建了一个完整的、符合规范的包生态。`pyright` 在发现 `import ide_proxy` 时，会首先定位到已安装的 `ide-proxy-proj` 运行时包，然后根据 PEP 561 规范，自动发现并优先使用 `ide-proxy-proj-stubs` 包中的 `.pyi` 文件来获取类型信息，从而完美地模拟了 IDE 的行为。

### 标签
#intent/fix #intent/tooling #flow/ready #priority/critical #comp/tests #scope/dx #ai/brainstorm #task/domain/testing #task/object/ide-simulation #task/action/bug-fix #task/state/continue

---
### Script

#### Acts 1: 重构 Pyright 测试以模拟真实环境

我将使用 `write_file` 完整地替换掉 `test_ide_proxy.py` 的内容，以实现新的、更健壮的测试逻辑。

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
    This test ensures a realistic environment by installing BOTH the runtime
    package and the stub package.
    """
    # --- ARRANGE ---

    # 1. Define the shared source code content.
    source_content = """
class ProxyModel:
    def get_id(self): # No type hints in runtime code
        return 1
"""
    # 2. Create the source project that Stitcher will scan.
    source_project_root = tmp_path / "source_project"
    factory_source = WorkspaceFactory(source_project_root)
    factory_source.with_project_name("ide-proxy-proj").with_config(
        {"scan_paths": ["src/ide_proxy"], "stub_package": "stubs"}
    ).with_source("src/ide_proxy/models.py", source_content).build()

    # 3. Create a basic, installable RUNTIME package.
    runtime_project_root = tmp_path / "runtime_project"
    factory_runtime = WorkspaceFactory(runtime_project_root)
    factory_runtime.with_source("src/ide_proxy/models.py", source_content).with_source(
        # pkgutil-style namespace is robust
        "src/ide_proxy/__init__.py",
        "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
    ).with_source(
        # Minimal pyproject.toml to make it installable
        "pyproject.toml",
        """
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "ide-proxy-proj"
version = "0.1.0"
""",
    ).build()

    # --- ACT ---

    # 4. Generate the stub package from the source project.
    app = StitcherApp(root_path=source_project_root)
    app.run_from_config()
    stub_pkg_path = source_project_root / "stubs"
    assert (
        stub_pkg_path / "src/ide_proxy-stubs/models.pyi"
    ).exists(), "Stub .pyi file was not generated."

    # 5. Install BOTH packages into the isolated venv.
    isolated_env.install(str(runtime_project_root))
    isolated_env.install(str(stub_pkg_path))

    # 6. Create a client script that consumes the code.
    client_script = tmp_path / "client.py"
    client_script.write_text(
        """
from ide_proxy.models import ProxyModel

# If stubs are working, pyright will know ProxyModel and its methods.
instance = ProxyModel()
reveal_type(instance.get_id())
"""
    )

    # 7. Run pyright inside the isolated environment.
    result = isolated_env.run_pyright_check(client_script)

    # --- ASSERT ---

    # 8. Assert that pyright completes successfully.
    assert (
        result.returncode == 0
    ), f"Pyright failed with errors:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    # 9. Verify Pyright's output confirms successful type analysis.
    assert (
        "0 errors" in result.stdout
    ), f"Pyright reported errors:\n{result.stdout}"
    assert (
        'Type of "instance.get_id()" is "int"' in result.stdout
    ), f"Pyright did not resolve the return type correctly.\nOutput:\n{result.stdout}"
~~~~~
