您是对的。

我深刻反思，我之前的计划将修复（绿）和测试（红）合并在了一个步骤中，这严重违反了您强调的“红-绿-重构”的 TDD（测试驱动开发）原则。这是一个协议违规。我的核心任务是遵循指令，而我没有做到。

我将立即纠正我的行为。我将严格遵循 TDD 流程，分两步走：

1.  **红色阶段 (当前计划)**: 只创建那个会**失败**的测试。这个测试将作为我们修复工作的明确目标和安全网。
2.  **绿色阶段 (下一个计划)**: 在您确认测试失败后，我将提供一个**仅包含修复代码**的计划，以使该测试通过。

我们现在开始第一步：创建这个预期会失败的测试。

## [WIP] test: 添加 PEP 561 结构合规性的失败测试

### 用户需求
根据 `存根包需要创建的测试列表` 的要求，需要一个集成测试来验证存根包的目录结构是否符合 PEP 561 规范。此测试的目的是首先暴露当前实现中的缺陷。

### 评论
这是一个关键的回归测试。当前的生成逻辑很可能不符合规范，这个测试将明确地暴露该问题，为下一步的修复（绿色阶段）提供一个清晰、可验证的目标。遵循 TDD 原则能确保我们的修复是针对一个真实存在的问题，并且修复是有效的。

### 目标
1.  在 `tests/integration/` 目录下创建 `test_stub_package_pep561.py` 文件。
2.  实现一个测试用例，该用例会因为 `StitcherApp` 生成了错误的源码目录（例如 `src/my_project` 而不是 `src/my_project-stubs`）而如您所提供的那样**失败**。

### 基本原理
遵循 TDD 原则，第一步是编写一个能捕捉当前 bug 的测试。通过首先确认测试会失败，我们能确保我们的修复是真正有效的，并且我们正在解决一个实际存在的问题。这个失败的测试构成了 TDD 流程中的“红色”阶段。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/pep561-test #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建预期会失败的 PEP 561 合规性测试

此操作将创建集成测试文件。当您运行 `pytest` 时，这个测试应该会失败，正如您所指出的那样。

~~~~~act
write_file
tests/integration/test_stub_package_pep561.py
~~~~~
~~~~~python
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory


def test_pep561_structure_compliance(tmp_path: Path):
    """
    Verifies that generated stub packages comply with PEP 561 naming conventions
    for both package name and the source directory inside the package.

    THIS TEST IS EXPECTED TO FAIL until the generation logic is fixed.
    """
    # 1. Arrange
    project_name = "my-project"
    namespace = "my_project"
    stub_dir_name = "stubs"

    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_project_name(project_name)
        .with_config({"scan_paths": [f"src/{namespace}"], "stub_package": stub_dir_name})
        .with_source(f"src/{namespace}/main.py", "def func(): ...")
        .build()
    )

    app = StitcherApp(root_path=project_root)

    # 2. Act
    app.run_from_config()

    # 3. Assert
    stub_pkg_path = project_root / stub_dir_name
    stub_toml_path = stub_pkg_path / "pyproject.toml"

    # 3.1. Assert pyproject.toml name is correct
    assert stub_toml_path.is_file()
    with stub_toml_path.open("rb") as f:
        config = tomllib.load(f)
    assert config["project"]["name"] == f"{project_name}-stubs"

    # 3.2. Assert src directory is named correctly (<namespace>-stubs)
    expected_src_dir = stub_pkg_path / "src" / f"{namespace}-stubs"
    incorrect_src_dir = stub_pkg_path / "src" / namespace

    assert expected_src_dir.is_dir()
    assert not incorrect_src_dir.exists(), "Incorrectly named src dir found."

    # 3.3. Assert Hatch config points to the correct directory
    hatch_packages = config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert hatch_packages == [f"src/{namespace}-stubs"]
~~~~~

### 下一步建议

现在这个测试已经就绪，并且预期会失败（红色阶段）。

请您运行测试并确认它的失败。一旦确认，请告诉我，我将立即为您生成一个修复计划（绿色阶段），该计划将只包含对 `StubPackageManager` 的修改，以使这个新添加的测试通过。
