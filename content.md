简要回答
好的，我将创建一个集成测试来复现 `pump` 命令在存在冗余文档时未能正确提示用户进行 strip 操作的问题。

经过代码审查，我发现了潜在的故障点：`PumpRunner.run` 方法似乎始终返回空的 `redundant_files` 列表，导致 CLI 层的交互逻辑 (`if result.redundant_files:`) 永远无法触发。

我将编写一个测试，模拟一个应当产生冗余文档的场景，并断言 CLI 在用户确认后执行了 strip 操作。由于当前逻辑存在缺陷，预计此测试将失败（Red 阶段）。

## [WIP] test(cli): 添加 pump 命令交互式 strip 提示的集成测试

### 用户需求
验证 `stitcher pump` 命令在检测到源码中的文档字符串已成功提取到 YAML 后，能够在交互模式下提示用户将其从源码中剥离（Strip）。

### 评论
这个测试不仅仅是为了覆盖率，它直接针对了一个隐蔽的逻辑缺陷。通过模拟 TTY 环境和用户输入，我们可以验证整个“检测冗余 -> 提示 -> 执行剥离”的链路是否通畅。使用 `SpyBus` 验证最终结果（`L.strip.run.complete`）比匹配脆弱的 stdout 字符串更符合我们的测试哲学。

### 目标
1.  创建 `packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py`。
2.  编写测试 `test_pump_prompts_for_strip_when_redundant`。
    *   **Arrange**: 创建包含 docstring 的源码文件。
    *   **Act**: 在模拟 TTY 环境下运行 `pump` 命令（不带 `--strip`），并注入 `'y'` 作为确认输入。
    *   **Assert**: 验证 `SpyBus` 是否收到了 `L.strip.run.complete` 消息（意味着 strip 逻辑被触发并执行了）。

### 基本原理
我们利用 `SpyBus` 验证“意图”而非“实现”。如果交互逻辑正常工作，用户确认后必然会触发 `run_strip`，进而产生 `strip.run.complete` 消息。如果 Bus 没有收到该消息，即证明交互逻辑未触发或执行失败，从而在不依赖具体 UI 文案的情况下精准捕获 Bug。

### 标签
#intent/tooling #flow/draft #priority/high
#comp/cli #comp/tests #scope/core
#ai/instruct
#task/domain/testing #task/object/pump-command #task/action/reproduce-bug
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 创建复现测试

~~~~~act
write_file
packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py
~~~~~
~~~~~python
import sys
from typer.testing import CliRunner
from stitcher.cli.main import app
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L


def test_pump_prompts_for_strip_when_redundant(tmp_path, monkeypatch):
    """
    Verifies that when 'pump' extracts docstrings (making source docs redundant),
    it prompts the user to strip them, and performs the strip if confirmed.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    # Create a file with a docstring that will be extracted
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            '''
def func():
    """This docstring should become redundant."""
    pass
''',
        )
        .build()
    )

    runner = CliRunner()
    spy_bus = SpyBus()

    # Mock isatty to True to force interactive mode (so handler is created)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    # 2. Act
    # Run pump without --strip, but provide 'y' to the potential prompt
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        # We need to change cwd so the CLI picks up the pyproject.toml
        result = runner.invoke(app, ["pump"], input="y\n", cwd=str(project_root))

    # 3. Assert
    assert result.exit_code == 0

    # Critical Assertion:
    # If the prompt appeared and worked, 'run_strip' should have been called,
    # and it should have emitted a success message via the bus.
    # If this fails, it means the CLI never prompted or never executed the strip.
    spy_bus.assert_id_called(L.strip.run.complete, level="success")

    # Verify physical file content (docstring should be gone)
    content = (project_root / "src/main.py").read_text()
    assert '"""' not in content
    assert "pass" in content
~~~~~

### 下一步建议

运行测试 `pytest packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py`。
预计测试将失败，因为 `PumpRunner` 目前返回空的 `redundant_files`。
确认失败后，我将生成修复计划，修正 `stitcher-application` 中的 `PumpRunner` 逻辑。
