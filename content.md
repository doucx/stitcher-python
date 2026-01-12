你的分析和提供的错误报告非常精准。这些错误是由于 Pyright 的静态检查与 `unittest.mock` 的动态特性（特别是 `autospec=True` 时生成的 `MethodType`）之间的冲突造成的。

根据 **HFEA (High-Fidelity Engineering Axioms)** 协议，我们应当追求代码的确定性。在处理 Mock 对象的“类型缝隙”时，最规范的做法是显式地告诉类型检查器在这些特定的动态点放宽限制，而不是引入复杂的包装逻辑。

以下是修复这些类型错误的计划。

## [WIP] fix(tests): 修复针对新引擎测试中的 Pyright 属性访问错误

### 错误分析

1.  **`MethodType` 属性冲突**: 在使用 `mocker.create_autospec(Protocol, instance=True)` 时，Pyright 能够识别出协议中的方法，并将其视为 `MethodType`。然而，它并不知道在运行时刻，这些方法已经被 `MagicMock` 替换，因此它会拒绝访问 `return_value` 或 `assert_called_once_with` 等 Mock 特有的属性。
2.  **深度属性访问**: 在 `test_pump_executor.py` 中，由于 `executor` 是一个真实的对象，Pyright 会严格检查其属性 `transformer` 的类型（协议）。当尝试访问协议方法的 Mock 属性时，会触发同样的检查失败。

### 解决方案

1.  **参数类型降级 (`Any`)**: 在测试函数签名中，将 Mock 对象的类型提示从具体的协议改为 `Any`。这是一种标准实践，用于告知类型检查器在该函数作用域内，该对象具有动态特性，从而停止属性访问检查。
2.  **显式忽略 (`# type: ignore`)**: 对于通过真实对象访问其 Mock 成员的情况（如 `executor.transformer.strip`），使用针对性的 `# type: ignore[reportAttributeAccessIssue]` 注释。这是最诚实的做法，它承认了静态检查在 Mock 边界上的局限性。

### 标签

#intent/fix #flow/ready #priority/medium #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/test-types #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修复 `packages/stitcher-analysis/tests/unit/engines/test_pump_engine.py`

我们将测试函数的参数类型改为 `Any`，以解决 `mock_subject` 和 `mock_differ` 的属性访问问题。

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/engines/test_pump_engine.py
~~~~~
~~~~~python.old
def test_engine_no_conflicts_when_summaries_match(
    engine: PumpEngine, mock_subject: AnalysisSubject
):
~~~~~
~~~~~python.new
def test_engine_no_conflicts_when_summaries_match(
    engine: PumpEngine, mock_subject: Any
):
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/engines/test_pump_engine.py
~~~~~
~~~~~python.old
def test_engine_detects_conflict_when_summaries_differ(
    engine: PumpEngine, mock_subject: AnalysisSubject, mock_differ: DifferProtocol
):
~~~~~
~~~~~python.new
def test_engine_detects_conflict_when_summaries_differ(
    engine: PumpEngine, mock_subject: Any, mock_differ: Any
):
~~~~~

#### Acts 2: 修复 `packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py`

由于 `executor` 是真实对象，我们需要对其 Mock 成员的访问添加显式忽略。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
    mock_tm = mocker.create_autospec(TransactionManager, instance=True)
    decisions = {"func_a": ResolutionAction.HYDRATE_OVERWRITE}

    # Mock transformer strip call
    executor.transformer.strip.return_value = "stripped content"

    # We need to mock read_text on the real Path object that will be constructed
~~~~~
~~~~~python.new
    mock_tm = mocker.create_autospec(TransactionManager, instance=True)
    decisions = {"func_a": ResolutionAction.HYDRATE_OVERWRITE}

    # Mock transformer strip call
    executor.transformer.strip.return_value = "stripped content"  # type: ignore[reportAttributeAccessIssue]

    # We need to mock read_text on the real Path object that will be constructed
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert signature is written
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", ANY)
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()
    mock_tm.add_write.assert_any_call("src/main.py", "stripped content")
~~~~~
~~~~~python.new
    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert signature is written
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", ANY)
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()  # type: ignore[reportAttributeAccessIssue]
    mock_tm.add_write.assert_any_call("src/main.py", "stripped content")
~~~~~

### 下一步建议

类型修复现已完成，所有针对新分析引擎的测试应当能够在 Pyright 的严格模式下通过，并保持逻辑正确。

我们已经完成了 Phase 1 的核心任务：**剥离分析逻辑、建立引擎/规则架构、重构 Reporter、并清理了遗留契约和测试债务**。系统现在的架构已经非常稳健。

我建议现在运行最终的全量测试，如果通过，我们将进行 `[COMMIT]` 提交，标志着 Phase 1 的正式圆满结束。如果你确认测试已 OK，请告知我，我将生成提交指令。
