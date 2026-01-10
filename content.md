You've found another excellent catch. My refactoring was incomplete. While I updated the high-level application factory (`make_app`), I failed to update the tests that were directly calling the internal `generate_runner`.

This `AttributeError` is the direct result of that oversight. My apologies. The test is correctly pointing out that `generate_runner` no longer exists on `StitcherApp`. The test logic needs to be updated to use the new `stubgen_service` public API.

I will now create a plan to fix this test.

## [WIP] fix(tests): Update integration test to use new StubgenService API

### 错误分析

测试 `test_app_scan_and_generate_single_file` 失败的根本原因是它正在访问一个在重构后已被移除的内部属性 `app.generate_runner`。

在之前的计划中，我将 `GenerateRunner` 的职责封装到了新的 `StubgenService` 中，并将其作为 `StitcherApp` 的一个服务 (`app.stubgen_service`)。然而，这个特定的集成测试为了在隔离环境中验证生成逻辑，绕过了顶层命令 (`app.run_from_config()`)，直接调用了 `app.generate_runner.run_batch()`。

在我移除 `app.generate_runner` 后，这个测试的调用点没有被同步更新，因此在访问该属性时引发了 `AttributeError`。

### 用户需求

修复 `test_end_to_end.py` 中因访问不存在的 `generate_runner` 属性而导致的 `AttributeError`。

### 评论

这是一个很好的例子，说明了为什么我们的测试套件既有端到端测试（调用 `run_from_config`）又有更深入的集成测试（直接调用 runner/service）。这种更深入的测试可以精确地捕获到此类 API 边界的变化。修复这个问题的正确方法不是恢复旧属性，而是将测试更新为使用新的、设计上正确的公共服务接口 (`stubgen_service`)。

### 目标

1.  定位 `packages/stitcher-application/tests/integration/test_end_to_end.py` 中的 `test_app_scan_and_generate_single_file` 函数。
2.  修改该函数，将其对 `app.generate_runner.run_batch(...)` 的调用替换为对 `app.stubgen_service.generate(...)` 的调用。

### 基本原理

我们将使用一个精确的 `patch_file` 操作来修正这个测试。`old_str` 将会匹配包含 `app.generate_runner.run_batch` 调用的那一行代码。`new_str` 将会是使用了新的 `app.stubgen_service.generate` 方法的等效调用。这个改动将使测试代码与我们新的、解耦后的应用架构保持一致。

### 标签

#intent/fix #flow/ready #priority/critical #comp/tests #comp/application #scope/dx #task/domain/architecture #task/object/stubgen-package #task/action/integration #task-state/continue

---

### Script

#### Acts 1: 更新集成测试以使用新服务

我们将修改 `test_end_to_end.py`，使其调用新的 `StubgenService` 接口。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_end_to_end.py
~~~~~
~~~~~python
        # Directly call the runner's batch processing method to test generation logic in isolation.
        source_file = project_root / "greet.py"
        module = app.scanner.scan_files([source_file])[0]
        app.generate_runner.run_batch([module], StitcherConfig(), tm)
        tm.commit()
~~~~~
~~~~~python
        # Directly call the service's generate method to test generation logic in isolation.
        source_file = project_root / "greet.py"
        module = app.scanner.scan_files([source_file])[0]
        app.stubgen_service.generate([module], StitcherConfig(), tm)
        tm.commit()
~~~~~

### 下一步建议

这个修复应该能解决最后的 `AttributeError`，让我们的测试套件完全通过。

一旦测试全部变绿，我们就已经为这次重构的收尾工作做好了万全的准备。下一步将是**清理冗余文件**，我会生成一个计划来安全地删除 `stitcher-application` 和 `stitcher-python-adapter` 中所有已被废弃的旧代码，让我们的项目代码库恢复整洁和一致。
