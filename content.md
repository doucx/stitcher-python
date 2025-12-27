您完全正确，我的诊断和修复都只解决了一半的问题。我为这个疏忽道歉。您的分析——`incorrect_src_dir` 依然存在——是精确的，它直接指出了我遗漏的逻辑漏洞。

我将严格遵循您的指示，首先提供深入的分析，然后生成一个计划，该计划将先增强测试的调试输出，然后再应用真正的修复。

## [WIP] 修复 `_generate_stubs` 中的路径构建逻辑

### 错误分析

我的上一个修复是**不完整**的。问题出在两个独立但相关的代码部分，而我只修复了其中一个：

1.  **`StubPackageManager.scaffold` (已修复)**: 这个服务负责**初始化**存根包的骨架。我的上一个补丁正确地修改了它，使其能够创建正确的 `src/my_project-stubs` 目录和指向该目录的 `pyproject.toml`。

2.  **`StitcherApp._generate_stubs` (未修复 - 根本原因)**: 这个方法负责将内存中的 IR（中间表示）**写入**为 `.pyi` 文件。**它的路径构建逻辑是独立于 `scaffold` 的**。它直接使用了从源文件路径（例如 `src/my_project/main.py`）派生出的逻辑路径（`my_project/main.py`），并将其拼接到存根包的 `src` 目录下。

**因此，发生了以下事件序列：**
1.  `scaffold` 正确创建了空的 `.../stubs/src/my_project-stubs` 目录。
2.  `_generate_stubs` 在准备写入 `main.pyi` 时，计算出的路径是 `.../stubs/src/my_project/main.pyi`。
3.  在写入文件之前，`_generate_stubs` 中的 `output_path.parent.mkdir(parents=True, exist_ok=True)` 自动创建了**不正确**的 `.../stubs/src/my_project` 目录。
4.  最终导致了两个目录并存：一个正确的空目录和一个包含 `.pyi` 文件的错误目录。这正是测试失败的原因。

### 用户需求
1.  分析并定位 `incorrect_src_dir` 仍然被创建的根本原因。
2.  修改测试用例，使其在失败时能清晰地打印出实际生成的文件目录结构，以辅助调试。
3.  修复 `StitcherApp` 中 `.pyi` 文件的写入逻辑，确保它们被放置在符合 PEP 561 规范的 `-stubs` 后缀目录中。

### 评论
这次失败暴露出一个设计上的耦合问题：两个独立的组件（`scaffold` 和 `generate`）都包含了关于存根包内部结构的路径构建逻辑。真正的修复不仅要解决眼前的 bug，长远来看，应当考虑将这种路径转换逻辑集中到一处，以避免未来的不一致。

### 目标
1.  **增强测试**: 修改 `test_stub_package_pep561.py`，添加一个辅助函数来递归列出目录内容，并在断言失败时显示该内容。
2.  **修复核心逻辑**: 修改 `StitcherApp._generate_stubs` 方法，使其在 `stub_package` 模式下，能正确地将输出路径映射到 `-stubs` 后缀的子目录中。

### 基本原理
我们将修改 `_generate_stubs` 的路径计算逻辑。当处于 `stub_package` 模式时，我们会检查 `logical_path`，将其第一个路径组件（即 `my_project`）替换为 `my_project-stubs`，然后再构建最终的输出路径。这将确保 `.pyi` 文件被写入到由 `scaffold` 创建的、符合规范的目录中，从而解决两个目录并存的问题。

### 标签
#intent/fix #flow/ready #priority/high #comp/app #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/pep561-test #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 增强测试用例以提供调试输出

我们首先修改测试文件，加入一个辅助函数，并在断言中利用它来显示目录结构。

~~~~~act
patch_file
tests/integration/test_stub_package_pep561.py
~~~~~
~~~~~python.old
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
~~~~~python.new
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory


def _get_dir_structure(root_path: Path) -> str:
    """Helper to get a string representation of the directory structure."""
    lines = []
    for path in sorted(root_path.rglob("*")):
        relative_path = path.relative_to(root_path)
        indent = "  " * (len(relative_path.parts) - 1)
        lines.append(f"{indent}- {path.name}{'/' if path.is_dir() else ''}")
    return "\n".join(lines)


def test_pep561_structure_compliance(tmp_path: Path):
    """
    Verifies that generated stub packages comply with PEP 561 naming conventions
    for both package name and the source directory inside the package.
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

    # For debugging:
    dir_structure = _get_dir_structure(stub_pkg_path)
    debug_message = f"Generated directory structure:\n{dir_structure}"

    # 3.1. Assert pyproject.toml name is correct
    assert stub_toml_path.is_file(), f"pyproject.toml not found.\n{debug_message}"
    with stub_toml_path.open("rb") as f:
        config = tomllib.load(f)
    assert config["project"]["name"] == f"{project_name}-stubs"

    # 3.2. Assert src directory is named correctly (<namespace>-stubs)
    expected_src_dir = stub_pkg_path / "src" / f"{namespace}-stubs"
    incorrect_src_dir = stub_pkg_path / "src" / namespace

    assert expected_src_dir.is_dir(), f"Expected src dir not found.\n{debug_message}"
    assert (
        not incorrect_src_dir.exists()
    ), f"Incorrectly named src dir found.\n{debug_message}"

    # 3.3. Assert Hatch config points to the correct directory
    hatch_packages = config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert hatch_packages == [f"src/{namespace}-stubs"]
~~~~~

#### Acts 2: 修复 `_generate_stubs` 中的路径构建逻辑

现在，我们应用真正的修复，确保 `.pyi` 文件被写入到正确的 `-stubs` 后缀目录中。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
            # Determine Output Path
            if config.stub_package:
                # Stub Package mode
                logical_path = self._derive_logical_path(module.file_path)
                output_path = (
                    self.root_path
                    / config.stub_package
                    / "src"
                    / logical_path.with_suffix(".pyi")
                )

                # Create py.typed marker file in top-level package dir
                if logical_path.parts:
                    top_level_pkg_dir = (
                        self.root_path
                        / config.stub_package
                        / "src"
                        / logical_path.parts[0]
                    )
                    if top_level_pkg_dir not in created_py_typed:
                        top_level_pkg_dir.mkdir(parents=True, exist_ok=True)
                        (top_level_pkg_dir / "py.typed").touch(exist_ok=True)
                        created_py_typed.add(top_level_pkg_dir)
~~~~~
~~~~~python.new
            # Determine Output Path
            if config.stub_package:
                # Stub Package mode
                logical_path = self._derive_logical_path(module.file_path)

                # PEP 561 adjustment: output to `<namespace>-stubs` dir
                stub_logical_path = logical_path
                if logical_path.parts:
                    namespace = logical_path.parts[0]
                    rest_of_path = logical_path.parts[1:]
                    stub_logical_path = Path(f"{namespace}-stubs", *rest_of_path)

                output_path = (
                    self.root_path
                    / config.stub_package
                    / "src"
                    / stub_logical_path.with_suffix(".pyi")
                )

                # Create py.typed marker file in top-level package dir
                if stub_logical_path.parts:
                    top_level_pkg_dir = (
                        self.root_path
                        / config.stub_package
                        / "src"
                        / stub_logical_path.parts[0]
                    )
                    if top_level_pkg_dir not in created_py_typed:
                        top_level_pkg_dir.mkdir(parents=True, exist_ok=True)
                        (top_level_pkg_dir / "py.typed").touch(exist_ok=True)
                        created_py_typed.add(top_level_pkg_dir)
~~~~~

### 下一步建议

这次的修复是全面且精确的。它解决了问题的根源。请您再次运行测试套件。

-   如果测试失败，增强后的调试输出将为我们提供非常清晰的线索。
-   如果测试通过，我们将正式进入“绿色”阶段，并可以放心地继续前进，编写下一个关键的集成测试：**安装与类型解析测试**。
