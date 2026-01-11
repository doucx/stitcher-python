好的，你完全正确。单元测试通过证明了我的核心假设是错误的——`Planner` 的合并逻辑本身没有问题。这意味着，尽管 `Planner` 能够正确地*计划*出合并后的文件操作，但在从 `runner.invoke` 到 `Planner` 执行之间的某个环节，依然存在一个导致命令崩溃的未捕获异常。

我们必须遵循标准的调试流程：当一个假设被证伪后，我们需要收集更多的信息。你提出的增加可观测性的建议是完全正确的下一步。通过启用详细日志，我们可以追踪 `refactor` 命令的内部执行流程，看看它究竟在哪一步崩溃了。

我将生成一个计划来修改测试，以启用详细输出。

## [WIP] test: 提高 refactor 命令集成测试的可观测性

### 错误分析

`test_refactor_command.py` 中的两个测试用例均以 `exit code 1` 失败，这表明 `typer` 应用在执行过程中遇到了一个未被处理的异常并提前退出。我们新加的单元测试已经证明 `Planner` 本身能够正确地合并针对同一文件的多个重命名操作，因此问题不在于计划生成的逻辑，而在于 `refactor` 命令执行此计划的*过程*中。

当前的集成测试就像一个黑盒，我们只知道输入（`refactor apply ...`）和输出（`exit code 1`），却看不到内部发生了什么。为了定位这个隐藏的异常，我们必须打开这个黑盒。

### 用户需求

修改 `test_refactor_command.py`，使其在运行失败的测试时能够提供更详细的诊断信息，帮助定位问题的根本原因。

### 评论

这是一个关键的调试步骤。在没有明确错误信息的情况下盲目修复是低效的。通过增加日志输出，我们可以获得一个执行“轨迹”，这对于定位在复杂调用栈中发生的瞬时错误至关重要。

### 目标

修改 `test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 这两个测试函数，在调用 `runner.invoke` 时，加入 `--verbose`（或 `-v`）全局选项。

### 基本原理

`stitcher` 的 CLI 应用在根命令上定义了一个 `--verbose` 回调。当这个标志被设置时，它会配置 `FeedbackBus` 使用一个能打印 `debug` 级别消息的 `CliRenderer`。在重构引擎的各个关键阶段（如加载工作区、构建语义图、规划操作等），都埋有详细的 `bus.debug(...)` 日志点。

通过在测试中激活这个标志，当 `runner.invoke` 执行时，所有这些调试信息都将被捕获到 `result.stdout` 中。这将为我们提供一个详细的执行日志，让我们能够精确地看到程序在抛出未处理异常并退出之前，最后执行到了哪一步。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/integration-tests #task/action/debug #task/state/continue

---

### Script

#### Acts 1: 为失败的 refactor 测试启用详细日志输出

我将修改 `test_refactor_command.py` 文件，为两个失败的测试用例添加 `--verbose` 标志。

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python.old
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = runner.invoke(
            app,
            ["refactor", "apply", str(migration_script), "--yes"],
            catch_exceptions=False,
        )
~~~~~
~~~~~python.new
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = runner.invoke(
            app,
            ["--verbose", "refactor", "apply", str(migration_script), "--yes"],
            catch_exceptions=False,
        )
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python.old
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = runner.invoke(
            app,
            ["refactor", "apply", str(migration_script), "--dry-run"],
            catch_exceptions=False,
        )
~~~~~
~~~~~python.new
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = runner.invoke(
            app,
            ["--verbose", "refactor", "apply", str(migration_script), "--dry-run"],
            catch_exceptions=False,
        )
~~~~~

### 下一步建议

请应用此计划并重新运行失败的测试。这次，测试仍然会失败，但 `pytest` 将捕获并显示详细的 `stdout` 输出。请将完整的失败日志（包括 `CAPTURE` 部分的 `stdout`）提供给我，这将是解开谜团的关键。
