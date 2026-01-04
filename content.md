好的，你说得对。我们停止猜测，直接验证核心路径。

我将创建一个新的、更简单的集成测试，专门用于验证 `pump --strip` 这个直接命令。这个测试将绕过所有复杂的交互逻辑，只检查一件事：当用户明确要求剥离时，`run_strip` 是否被调用，以及它是否按预期发出了 `strip.run.complete` 信号。

这个测试将作为我们定位问题的“试金石”。

## [WIP] test(cli): 为 `pump --strip` 添加直接执行验证测试

### 用户需求
创建一个测试，以验证 `stitcher pump --strip` 命令能够确定地执行剥离操作并发出相应的成功信号（`L.strip.run.complete`）。

### 评论
这是一个关键的诊断步骤。之前的测试因交互逻辑的复杂性而失败，使我们无法确定根源问题。这个新测试通过移除交互变量，直接测试了 `pump` 命令的核心 `strip` 功能路径。如果这个测试通过，问题就明确出在 CLI 的交互处理上；如果它失败，问题则更深地存在于应用层的 `PumpRunner` 内部。

### 目标
1.  在 `packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py` 文件中追加一个新的测试用例 `test_pump_with_strip_flag_executes_strip`。
2.  该测试将模拟 `stitcher pump --strip` 的调用。
3.  断言 `SpyBus` 成功捕获到 `L.strip.run.complete` 消息。
4.  断言物理文件中的文档字符串被移除。

### 基本原理
我们通过测试最直接、最简单的成功路径来建立一个功能基线。`pump --strip` 是一个非交互式的、确定性的操作。验证它的行为可以为我们提供一个明确的信号，判断 `PumpRunner` 内部的 `strip_jobs` 收集逻辑以及下游的 `TransformRunner` 是否正常工作。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/tests #scope/core
#ai/instruct
#task/domain/testing #task/object/pump-command #task/action/isolate-bug
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 添加 `--strip` 直接执行测试

我们将向现有测试文件中添加一个新的测试函数。

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py
~~~~~
~~~~~python.old
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
~~~~~python.new
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


def test_pump_with_strip_flag_executes_strip(tmp_path, monkeypatch):
    """
    Verifies that 'pump --strip' directly triggers a strip operation and
    emits the correct completion signal. This test bypasses interactive prompts.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            '''
def func():
    """This docstring should be stripped."""
    pass
''',
        )
        .build()
    )

    runner = CliRunner()
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        monkeypatch.chdir(project_root)
        result = runner.invoke(app, ["pump", "--strip"])

    # 3. Assert
    assert result.exit_code == 0, f"CLI command failed: {result.stdout}"

    # Assert that the strip operation was completed
    spy_bus.assert_id_called(L.strip.run.complete, level="success")

    # Verify physical file content
    content = (project_root / "src/main.py").read_text()
    assert '"""' not in content
~~~~~

### 下一步建议
请运行这个新创建的测试：
`pytest packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py::test_pump_with_strip_flag_executes_strip`

这个测试的结果将给我们一个决定性的答案。
