好的，我们现在进入阶段 4 的核心：通过一个端到端的集成测试来最终验证整个渲染管线。

这个测试将模拟真实的用户场景，确保从 `pyproject.toml` 的配置读取到最终 `.pyi` 文件的生成，所有环节都能正确协同工作。

## [WIP] test: 添加结构化文档渲染的端到端集成测试

### 用户需求
创建一个端到端的集成测试，模拟用户在 `pyproject.toml` 中设置 `docstring_style = "google"`，然后运行 `stitcher generate` 命令，并断言生成的 `.pyi` 文件内容是否符合预期。

### 评论
这是对整个“结构化文档”特性最高保真度的验证。通过模拟完整的用户工作流，我们可以确保所有组件——配置加载器、文档管理器、渲染器和存根生成器——能够无缝集成，产生正确的结果。

### 目标
1.  在 `packages/stitcher-application/tests/integration/` 目录下创建一个新的测试文件 `test_generate_docstring_styles.py`。
2.  在该文件中，编写一个测试用例，使用 `WorkspaceFactory` 来构建一个配置了 `docstring_style = "google"` 的虚拟项目。
3.  项目应包含一个带有类型注解的 Python 源文件和一个使用结构化格式（`Args`, `Returns`）的 `.stitcher.yaml` 文件。
4.  执行 `generate` 命令。
5.  读取生成的 `.pyi` 文件，并断言其内容与预期的、合并了类型和描述的 Google 风格文档字符串完全一致。

### 基本原理
此集成测试是验证阶段的基石。它超越了单元测试的范围，通过一个真实的、从头到尾的场景来捕捉在组件交互边界可能出现的问题，为整个功能的正确性提供了最终的信心。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/application #concept/docstring #scope/core #ai/instruct #task/domain/testing #task/object/e2e-test #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建端到端渲染测试

我们将在 `stitcher-application` 的集成测试目录中创建一个新文件，专门用于测试不同文档风格的生成。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_generate_docstring_styles.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.test_utils import WorkspaceFactory, create_test_app


def test_generate_with_google_style_renders_correctly(tmp_path):
    """
    E2E test to verify that setting docstring_style = "google" in pyproject.toml
    results in a correctly rendered .pyi file with merged type and doc info.
    """
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_config({"scan_paths": ["src"], "docstring_style": "google"})
        .with_source(
            "src/main.py",
            "def calculate(value: int, multiplier: float = 1.0) -> float: ...",
        )
        .with_docs(
            "src/main.stitcher.yaml",
            {
                "calculate": {
                    "Summary": "Performs a calculation.",
                    "Args": {
                        "value": "The input integer.",
                        "multiplier": "The factor to multiply by.",
                    },
                    "Returns": {
                        "float": "The calculated result."
                    },
                }
            },
        )
        .build()
    )

    app = create_test_app(root_path=project_root)
    app.run_from_config()

    pyi_path = project_root / "src/main.pyi"
    assert pyi_path.exists()

    expected_content = dedent(
        '''
        def calculate(value: int, multiplier: float = 1.0) -> float:
            """
            Performs a calculation.

            Args:
                value (int): The input integer.
                multiplier (float): The factor to multiply by.

            Returns:
                float: The calculated result.
            """
            ...
        '''
    ).strip()

    actual_content = pyi_path.read_text().strip()
    assert actual_content == expected_content
~~~~~

### 下一步建议
我们已经成功地为整个“结构化文档渲染管线”特性添加了从底层到顶层的完整测试覆盖。宏观任务的核心目标已经达成。

我建议将这次重大的架构升级作为一个完整的单元进行提交。如果你同意，我将生成一个 `[COMMIT]` 计划，将所有相关的代码和测试变更包含在一个原子提交中，并正式结束本次任务。
