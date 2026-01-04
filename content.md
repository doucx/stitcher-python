你的洞察力非常敏锐。在我上次的重构中，虽然我正确地将 UI 逻辑从应用层 (`StitcherApp`) 移除了，但你怀疑“检查似乎失败了”，这恰好点出了一个更深层次的隐藏缺陷：**`PumpRunner` 从未正确地将其执行结果（哪些文件被更新了）返回给调用方**。

因此，无论是之前应用层的重复逻辑，还是现在 CLI 层的编排逻辑，都因为收到了一个始终为空的 `redundant_files` 列表而无法触发交互提示。

我将遵循 TDD 流程来修复这个问题：
1.  **创建测试 (`Test`)**: 首先，在 `stitcher-cli` 的集成测试中添加一个新的测试用例，它将模拟用户执行 `pump` 命令并期望看到交互式 strip 提示。这个测试目前会失败，从而明确地暴露我们正在解决的问题。
2.  **修复缺陷 (`Develop`)**: 然后，我将修改 `PumpRunner` 的实现，使其在 `PumpResult` DTO 中正确填充被更新的文件列表。
3.  **验证 (`Test`)**: 最终，我们新创建的测试用例将会通过，证明整个流程（从核心逻辑到 CLI 交互）都已按预期工作。

## [WIP] fix(pump): 修复 pump 未返回冗余文件列表导致交互失效的问题

### 错误分析
在 `packages/stitcher-application/src/stitcher/app/runners/pump.py` 中，`PumpRunner.run` 方法在执行完毕后，硬编码返回了一个 `PumpResult(..., redundant_files=[])`。这导致上层调用者（无论是旧的 `StitcherApp` 还是现在的 `pump_command`）永远无法得知哪些文件刚刚被更新，从而无法触发后续的“交互式 strip”提示。

### 用户需求
1.  创建一个集成测试，验证 `stitcher pump` 在成功更新 YAML 文件且未提供 `--strip` 标志时，会向用户发起交互式 strip 提示。
2.  修复 `PumpRunner.run` 方法，使其正确返回被成功更新（pumped）的文件列表。

### 评论
这是一个典型的因 DTO（数据传输对象）未被正确填充而导致的逻辑中断。通过 TDD 的方式，我们可以先用一个失败的测试来精确锁定这个跨层通信的问题，然后精准地修复它，确保整个端到端的流程健壮可靠。

### 目标
1.  在 `packages/stitcher-cli/tests/integration/` 目录下创建一个新的测试文件 `test_pump_command_flow.py`。
2.  在该文件中实现一个测试用例，使用 `typer.testing.CliRunner` 来模拟用户输入 `y` 并断言 strip 操作是否被成功触发。
3.  修改 `packages/stitcher-application/src/stitcher/app/runners/pump.py` 中的 `PumpRunner.run` 方法，使其收集并返回所有被修改过的文件的路径。

### 基本原理
我们将首先编写一个集成测试，它会因为 `result.redundant_files` 为空而导致 `typer.confirm` 从未被调用，从而断言失败。接着，我们将在 `PumpRunner.run` 方法中添加一个列表来收集所有内容被修改的模块路径，并在方法结束时将其填充到返回的 `PumpResult` 对象中。修复后，测试将通过，证明从数据产生到用户交互的整个链路已被打通。

### 标签
#intent/fix #flow/ready #priority/high
#comp/cli #comp/runtime #concept/ui #scope/core
#ai/brainstorm
#task/domain/architecture #task/object/application-layer #task/action/decouple-ui
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 创建失败的集成测试

我们将创建一个新的测试文件，用于验证 `pump` 命令的端到端交互流程。此测试在修复 Bug 之前将会失败。

~~~~~act
write_file
packages/stitcher-cli/tests/integration/test_pump_command_flow.py
~~~~~
~~~~~python
from typer.testing import CliRunner
from stitcher.cli.main import app
from stitcher.test_utils import WorkspaceFactory


def test_pump_command_prompts_for_strip_on_redundant_files(tmp_path):
    """
    Integration test to ensure the CLI's pump command correctly orchestrates
    the secondary, interactive strip prompt.
    """
    # Arrange
    runner = CliRunner()
    ws_factory = WorkspaceFactory(tmp_path)
    source_content = 'def func():\\n    """Docstring to be pumped."""'
    source_path = "src/main.py"
    project_root = (
        ws_factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, source_content)
        .build()
    )

    # Act
    # We change the CWD for the runner to simulate running from the project root.
    # We provide "y\n" to stdin to answer the confirmation prompt affirmatively.
    with runner.isolated_filesystem(temp_dir=project_root):
        result = runner.invoke(app, ["pump"], input="y\\n", catch_exceptions=False)

    # Assert
    assert result.exit_code == 0, f"CLI command failed:\\n{result.stdout}\\n{result.stderr}"

    # Assert that the interactive prompt was shown to the user.
    # Note: typer.confirm typically prints to stderr.
    assert "Do you want to strip them now?" in result.stderr

    # Assert that the strip operation was successful after user confirmation.
    final_code = (project_root / source_path).read_text()
    assert '"""Docstring to be pumped."""' not in final_code

    # Assert that the initial pump operation was also successful.
    yaml_path = (project_root / source_path).with_suffix(".stitcher.yaml")
    assert yaml_path.exists()
~~~~~

