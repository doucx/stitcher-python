Excellent, we've resolved almost all the test failures. This last one is a direct result of our refactoring and is simple to fix.

The test `test_app_scan_and_generate_single_file` was written to test the stub generation logic directly by calling a private method, `_generate_stubs`. During our refactoring, we moved this logic into the new public method `run_batch` and removed `_generate_stubs`. The test now needs to be updated to use the new public API.

I will generate a plan to fix this final test.

## [WIP] fix: Update test to use new GenerateRunner.run_batch API

### 错误分析
The test `test_app_scan_and_generate_single_file` fails with an `AttributeError` because it attempts to call `app.generate_runner._generate_stubs`, a private method that was removed during the recent Runner architecture refactoring. The correct public method is now `run_batch`.

### 用户需求
Fix the final remaining test failure to get a fully passing test suite.

### 评论
This is a straightforward and necessary change. The test was previously coupled to an internal implementation detail. Updating it to use the new public API (`run_batch`) makes the test more robust and correctly verifies the refactored contract of the `GenerateRunner`.

### 目标
1.  Modify `packages/stitcher-application/tests/integration/test_end_to_end.py`.
2.  Replace the call to the non-existent `_generate_stubs` method with a call to the new `run_batch` method.
3.  Update the accompanying comment to reflect that a public method is now being called.

### 基本原理
Aligning the test case with the refactored public API of the `GenerateRunner` will resolve the `AttributeError` and ensure the test accurately validates the intended functionality.

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #task/domain/architecture #task/object/runners #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Update test to use `run_batch`

We will patch the failing test to call the correct method and update its explanatory comment.

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        # Accessing internal methods directly for this specific test case
        # as per original test logic
        source_file = project_root / "greet.py"
        module = app.scanner.scan_files([source_file])[0]
        app.generate_runner._generate_stubs([module], StitcherConfig())
~~~~~
~~~~~python.new
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        # Directly call the runner's batch processing method to test generation logic in isolation.
        source_file = project_root / "greet.py"
        module = app.scanner.scan_files([source_file])[0]
        app.generate_runner.run_batch([module], StitcherConfig())
~~~~~

### 下一步建议
After applying this fix, the entire test suite should pass. We can then confidently proceed with the next feature implementation, knowing our refactored architecture is sound. I suggest we continue with the "核心解耦与集成" plan to add multi-style docstring support.
