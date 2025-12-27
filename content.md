好的，重构完成，测试通过。我们现在进入下一个 TDD 周期，为“安装与类型解析测试”编写一个新的测试。

这是对我们工作的终极考验。之前的测试验证了我们生成的*文件结构*是正确的，而这个测试将验证这个结构在被 Python 工具链（pip, mypy）实际*使用*时，能否达成我们预期的效果。

## [WIP] test: 添加存根包的安装与类型解析测试

### 用户需求
根据 `存根包需要创建的测试列表` 的规划，创建一个集成测试，该测试模拟用户的完整工作流：
1.  生成一个存根包。
2.  在一个干净的虚拟环境中 `pip install` 这个包。
3.  编写一个消费该包的客户端脚本。
4.  运行 `mypy` 验证类型检查器能否从安装的存根包中正确解析类型。

### 评论
这是价值最高的一种集成测试。它不再检查 `stitcher` 的内部实现或文件输出，而是从用户的角度，以黑盒的方式验证最终产物（一个可安装的存根包）是否真正解决了核心痛点——为类型检查器提供准确的类型信息。通过这个测试，我们能绝对自信地宣称 `stitcher` 生成的包是功能完备且符合标准的。

### 目标
1.  在 `tests/integration/` 目录下创建 `test_stub_package_resolution.py` 文件。
2.  编写一个新的测试用例 `test_stubs_install_and_resolve`。
3.  该测试将利用 `isolated_env` fixture 来创建一个隔离的虚拟环境。
4.  在测试中，完整地执行“生成 -> 安装 -> 验证”的流程。
5.  断言 `mypy` 的退出码为 0，并且其输出（通过 `reveal_type`）包含了从存根文件中解析出的正确类型信息。

### 基本原理
我们将完全依赖 `VenvHarness` (`isolated_env` fixture) 来实现这个测试。
1.  `WorkspaceFactory` 会创建一个包含简单类定义的源项目。
2.  `StitcherApp` 会为该项目生成一个完整的 `-stubs` 包。
3.  `isolated_env.install()` 会将这个新生成的包安装到隔离的 venv 中。
4.  我们会动态创建一个 `client.py`，它导入并使用我们项目中的类，并用 `reveal_type` 请求 `mypy` 显示其类型。
5.  `isolated_env.run_type_check()` 会在该 venv 中执行 `mypy`。
6.  最后，我们会断言 `mypy` 的输出，如果输出中包含 `Type[my_project.models.MyModel]` 这样的精确类型，而不是 `Any`，就证明整个流程成功了。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/type-resolution-test #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建安装与类型解析集成测试

此操作将创建新的测试文件。这个测试在首次运行时可能会因为各种细微的配置问题而失败，这将帮助我们进一步完善生成逻辑。

~~~~~act
write_file
tests/integration/test_stub_package_resolution.py
~~~~~
~~~~~python
from pathlib import Path

from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory, VenvHarness


def test_stubs_install_and_resolve(tmp_path: Path, isolated_env: VenvHarness):
    """
    The ultimate end-to-end test:
    1. Generate a stub package.
    2. Install it in an isolated venv.
    3. Run mypy and verify types are resolved correctly from the stubs.
    """
    # 1. Arrange: Create a source project
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_project_name("my-project")
        .with_config({"scan_paths": ["src/my_project"], "stub_package": "stubs"})
        .with_source(
            "src/my_project/models.py",
            """
            class MyModel:
                def __init__(self, id: int):
                    self.id = id
            """,
        )
        .build()
    )

    # 2. Act: Generate the stub package
    app = StitcherApp(root_path=project_root)
    app.run_from_config()
    stub_pkg_path = project_root / "stubs"
    assert stub_pkg_path.exists()

    # 3. Act: Install the generated stubs into the isolated environment
    isolated_env.install(str(stub_pkg_path))

    # 4. Act: Create a client script that consumes the code
    client_script = tmp_path / "client.py"
    client_script.write_text(
        """
from my_project.models import MyModel
reveal_type(MyModel)
"""
    )

    # 5. Act: Run mypy inside the isolated environment
    result = isolated_env.run_type_check(client_script)

    # 6. Assert
    assert result.returncode == 0, f"Mypy failed with errors:\n{result.stderr}"

    # Mypy's output for a revealed class type is "Type[<class_name>]"
    expected_type_str = 'Revealed type is "Type[my_project.models.MyModel]"'
    assert expected_type_str in result.stdout, (
        f"Mypy did not reveal the correct type.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
~~~~~

### 下一步建议

我们已经创建了最关键的集成测试。请运行 `pytest` 来执行它。

-   **如果测试通过**，这说明我们的 `stitcher` 核心功能已经非常健壮。我们可以庆祝一下，然后继续进行下一个测试：“命名空间共存测试”，以确保我们的存根包在更复杂的 Monorepo 环境中不会产生副作用。
-   **如果测试失败**，`pytest` 的输出（特别是 `result.stderr`）将为我们提供宝贵的线索，以进行精确修复。

请执行测试并告诉我结果。
