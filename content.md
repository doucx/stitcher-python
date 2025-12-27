好的，你的分析非常敏锐。这是一个典型的由全局状态（项目名称）在局部循环（处理不同目标）中被错误重用的问题。

你的观察是正确的：尽管 `pyproject.toml` 中为每个目标（`stitcher-python` 和 `pyneedle`）都定义了独立的 `stub_package` 路径，但在搭建脚手架时，系统似乎总是错误地使用根项目的名称 `stitcher-python` 来派生存根包的名称，导致了第二次错误的输出 `正在搭建存根包 'stitcher-python-stubs'...`。

这显然是一个逻辑错误，而不是配置问题。

遵从你的 TDD 流程，我将首先创建一个新的集成测试，该测试会精确地复现这个 bug。这个测试在当前的代码库下应该会失败。

## [WIP] test: 复现多目标模式下存根包脚手架名称错误的 bug

### 错误分析
当前 `StitcherApp.run_from_config` 方法在加载配置时，会获取一个全局的 `project_name`。随后，它会遍历所有 `targets` 配置。在循环内部调用 `_scaffold_stub_package` 时，它总是传入这个固定的、全局的 `project_name`，而不是与当前正在处理的 `target` 相关联的名称。

`StubPackageManager.scaffold` 方法接收这个全局项目名称，并用它来生成存根包的元数据（例如 `pyproject.toml` 里的 `name` 字段，格式为 `{project_name}-stubs`）。

这就导致了无论处理哪个 `target`，脚手架逻辑始终尝试创建基于同一个全局项目名的存根包，这在多目标场景下是完全错误的。正确的行为应该是使用 `target` 的名称（例如 `stitcher-python` 或 `pyneedle`）来派生其对应的存根包名称。

### 用户需求
创建一个会失败的集成测试，用于捕获在多目标配置下 `stitcher generate` 命令为第二个及后续目标生成存根包时使用错误项目名称的 bug。

### 评论
这是一个非常好的问题。它暴露了当前实现中一个隐藏的假设，即一个项目只有一个输出目标。在 monorepo 结构中，修复这个问题对于确保每个目标能够生成正确独立的存根包至关重要。

### 目标
1.  在 `tests/integration/` 目录下创建一个新的测试文件。
2.  在该文件中，定义一个测试用例，使用 `WorkspaceFactory` 构建一个包含两个不同 `target` 的虚拟项目。
3.  每个 `target` 都配置为生成一个独立的 `stub_package`。
4.  执行 `app.run_from_config()`。
5.  断言两个独立的、名称正确的存根包都被创建了，并且它们各自的 `pyproject.toml` 中包含了正确的 `[project].name`。这个断言在当前代码下应该会失败。

### 基本原理
我们将创建一个名为 `test_multi_target_stub_names.py` 的新测试文件。测试函数 `test_multi_target_scaffolds_correct_stub_package_names` 会模拟一个典型的 monorepo `pyproject.toml`，其中包含一个全局项目名（`monorepo`）和两个目标（`app-a` 和 `app-b`），每个目标都有自己的 `stub_package` 路径。

测试的核心是检查文件系统，验证是否生成了 `stubs-a/pyproject.toml` 和 `stubs-b/pyproject.toml`，并读取其内容，断言 `[project].name` 分别为 `app-a-stubs` 和 `app-b-stubs`。当前错误的逻辑会尝试创建两次 `monorepo-stubs`，导致测试失败。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/application #concept/config #scope/core #ai/instruct #task/domain/testing #task/object/multi-target #task/action/bug-repro #task/state/begin

---
### Script

#### Acts 1: 创建复现 bug 的集成测试文件

我将创建一个新的测试文件 `tests/integration/test_multi_target_stub_names.py`。这个测试会模拟一个多目标项目，并断言每个目标都能生成名称正确的独立存根包。

~~~~~act
write_file
tests/integration/test_multi_target_stub_names.py
~~~~~
~~~~~python
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory


def test_multi_target_scaffolds_correct_stub_package_names(tmp_path):
    """
    Verifies that in a multi-target setup, each target's stub package
    is scaffolded with a name derived from its target name, not the
    global project name.
    """
    # 1. Arrange: Create a workspace with a global project name
    # and two distinct targets.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_project_name("monorepo-project")
        .with_source("src/app_a/main.py", "def func_a(): ...")
        .with_source("src/app_b/main.py", "def func_b(): ...")
        .build()
    )

    # Manually write the multi-target config
    (project_root / "pyproject.toml").write_text(
        """
[project]
name = "monorepo-project"

[tool.stitcher.targets.app-a]
scan_paths = ["src/app_a"]
stub_package = "stubs-a"

[tool.stitcher.targets.app-b]
scan_paths = ["src/app_b"]
stub_package = "stubs-b"
        """,
        encoding="utf-8",
    )

    app = StitcherApp(root_path=project_root)

    # 2. Act
    app.run_from_config()

    # 3. Assert
    # --- Assert Structure for Target A ---
    stub_a_path = project_root / "stubs-a"
    stub_a_toml_path = stub_a_path / "pyproject.toml"
    assert stub_a_toml_path.is_file(), "pyproject.toml for app-a was not created"

    with stub_a_toml_path.open("rb") as f:
        config_a = tomllib.load(f)
    assert (
        config_a["project"]["name"] == "app-a-stubs"
    ), "Stub package for app-a has the wrong project name"

    # --- Assert Structure for Target B ---
    stub_b_path = project_root / "stubs-b"
    stub_b_toml_path = stub_b_path / "pyproject.toml"
    assert stub_b_toml_path.is_file(), "pyproject.toml for app-b was not created"

    with stub_b_toml_path.open("rb") as f:
        config_b = tomllib.load(f)
    assert (
        config_b["project"]["name"] == "app-b-stubs"
    ), "Stub package for app-b has the wrong project name"

~~~~~
