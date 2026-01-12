简要回答
测试失败是因为单元测试 `test_check_runner` 仍然断言旧的行为（即交互式违规在分析阶段立即被记为错误），而我们刚刚修改了架构，将这一记录推迟到了解决阶段。这证实了我们的修改生效了，但需要更新过时的测试。

## [WIP] test(app): 更新 CheckRunner 单元测试以匹配新的生命周期逻辑

### 用户需求
修复 `packages/stitcher-application/tests/unit/runners/check/test_check_runner.py` 中的回归失败。

### 评论
这是一个预期的回归。在上一轮重构中，我们明确改变了 `CheckRunner.analyze_batch` 的契约：它不再负责将交互式违规（如 `signature_drift`）立即归类为错误，而是将它们放入 `conflicts` 列表，留待 `CheckResolver` 处理。单元测试使用 Mock Resolver，因此看不到“错误被加回来”的过程，它只验证了第一步的状态，而第一步的状态定义已经改变。

### 目标
更新 `test_check_runner_orchestrates_analysis_and_resolution`，断言 `signature_drift` **不** 出现在 `results[0].errors` 中，但 **出现** 在 `conflicts` 中。

### 基本原理
测试必须反映代码的真实行为。新的架构要求交互式违规在初始阶段保持“中立”，直到解决器介入。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/check-lifecycle #task/action/update #task/state/continue

---

### Script

#### Acts 1: 更新单元测试断言

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
    # Verify translation results
    assert len(results) == 1
    assert results[0].path == "src/main.py"
    assert "func" in results[0].errors["signature_drift"]
    assert len(conflicts) == 1
    assert conflicts[0].violation_type == L.check.state.signature_drift
~~~~~
~~~~~python.new
    # Verify translation results
    assert len(results) == 1
    assert results[0].path == "src/main.py"
    # ARCHITECTURE CHANGE: Interactive violations are now deferred to the resolver phase.
    # They should NOT appear in errors immediately after analysis.
    assert "func" not in results[0].errors["signature_drift"]
    assert len(conflicts) == 1
    assert conflicts[0].violation_type == L.check.state.signature_drift
~~~~~

### 下一步建议
运行单元测试以确认修复。如果通过，可以提交本次任务的所有变更（包含上一轮的架构修复和本轮的测试更新）。
