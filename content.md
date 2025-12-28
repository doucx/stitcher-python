好的，为了确保“交互式调和模式”及其相关的两阶段执行逻辑能够长期稳定运行，我们需要建立一套严密的回归测试。

我们将重点测试以下三个维度：
1.  **自动调和逻辑**：确保“文档改进”场景下的自动哈希更新不会再次丢失（防止之前的回归）。
2.  **应用层流转**：验证 `StitcherApp` 是否正确地按照“分析 -> 决策 -> 执行”的顺序处理冲突。
3.  **CLI 行为决策**：验证 TTY 环境检测及 `--non-interactive` 标志是否能正确控制控制处理器的注入。

## [WIP] test: 为交互式调和模式建立回归测试套件

### 用户需求
为新实现的交互式调和模式建立回归测试，确保自动调和逻辑、双阶段执行流以及 CLI 标志位的正确性。

### 评论
这些测试是该特性生命周期的“保险柜”。特别是针对“自动调和”的测试，将永远防止我们之前遇到的那个回归错误再次发生。通过模拟 `click.getchar` 的输入序列，我们甚至可以在不启动真实终端的情况下，验证复杂的“问卷”交互逻辑是否正确地生成了调和计划。

### 目标
1.  **集成测试**：在 `tests/integration/test_check_interactive_flow.py` 中验证 `StitcherApp` 的四阶段工作流（分析、自动执行、交互决策、批量执行）。
2.  **CLI 测试**：在 `packages/stitcher-cli/tests/test_check_cli_behavior.py` 中验证 `--non-interactive` 和 TTY 检测逻辑。
3.  **交互逻辑测试**：通过 Mock `click.getchar` 验证 `TyperInteractionHandler` 的单键响应和撤销逻辑。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/interactive-check #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建应用层集成测试

我们将验证 `StitcherApp` 如何处理“文档改进”（自动）和“签名漂移”（交互）的组合场景。

~~~~~act
write_file
tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python
import pytest
from stitcher.app import StitcherApp
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L

class MockResolutionHandler(InteractionHandler):
    """A handler that returns a pre-defined sequence of actions."""
    def __init__(self, actions: list[ResolutionAction]):
        self.actions = actions
        self.called_with = []

    def process_interactive_session(self, contexts: list[InteractionContext]) -> list[ResolutionAction]:
        self.called_with = contexts
        return self.actions

def test_check_workflow_mixed_auto_and_interactive(tmp_path, monkeypatch):
    """
    Ensures that auto-reconciliation and interactive decisions can co-exist
    and are executed correctly in their respective phases.
    """
    factory = WorkspaceFactory(tmp_path)
    # 1. Setup: A module with two functions
    # func_a: will have doc improvement (auto)
    # func_b: will have signature drift (interactive)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", '''
def func_a():
    """Old Doc A."""
    pass
def func_b(x: int):
    """Doc B."""
    pass
''')
        .build()
    )
    
    app = StitcherApp(root_path=project_root)
    app.run_init()

    # 2. Trigger Changes
    # Change A: Modify YAML directly (Doc Improvement)
    doc_file = project_root / "src/app.stitcher.yaml"
    doc_file.write_text('func_a: "New Doc A."\nfunc_b: "Doc B."\n', encoding="utf-8")
    
    # Change B: Modify Source Code (Signature Drift)
    (project_root / "src/app.py").write_text('''
def func_a():
    pass
def func_b(x: str): # int -> str
    pass
''')

    # 3. Define Interactive Decision
    handler = MockResolutionHandler([ResolutionAction.RELINK])
    app.interaction_handler = handler

    # 4. Run Check
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 5. Assertions
    assert success is True
    # Verify Auto-reconcile report
    spy_bus.assert_id_called(L.check.state.doc_updated, level="info")
    # Verify Interactive resolution report
    spy_bus.assert_id_called(L.check.state.relinked, level="success")
    
    # Verify Hashes are actually updated in storage
    from tests.integration.test_check_state_machine import _get_stored_hashes
    final_hashes = _get_stored_hashes(project_root, "src/app.py")
    
    # func_a should have updated yaml hash
    expected_doc_a_hash = app.doc_manager.compute_yaml_content_hash("New Doc A.")
    assert final_hashes["func_a"]["baseline_yaml_content_hash"] == expected_doc_a_hash
    
    # func_b should have updated code hash due to RELINK
    assert final_hashes["func_b"]["baseline_code_structure_hash"] is not None
~~~~~

#### Acts 2: 创建 CLI 行为测试

验证 `--non-interactive` 是否能正确阻止交互式处理器的注入。

~~~~~act
write_file
packages/stitcher-cli/tests/test_check_cli_behavior.py
~~~~~
~~~~~python
import sys
from unittest.mock import MagicMock
from typer.testing import CliRunner
from stitcher.cli.main import app
import pytest

runner = CliRunner()

def test_check_non_interactive_flag_disables_handler(monkeypatch):
    """
    Verifies that --non-interactive flag prevents TyperInteractionHandler
    from being instantiated even if in a TTY.
    """
    # Mock TTY to True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    
    # Mock StitcherApp to see what handler it gets
    mock_app_cls = MagicMock()
    monkeypatch.setattr("stitcher.cli.main.StitcherApp", mock_app_cls)
    
    # Run with flag
    runner.invoke(app, ["check", "--non-interactive"])
    
    # Assert: interaction_handler passed to constructor was None
    args, kwargs = mock_app_cls.call_args
    assert kwargs["interaction_handler"] is None

def test_check_interactive_by_default_in_tty(monkeypatch):
    """
    Verifies that in a TTY, an InteractionHandler is injected by default.
    """
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    
    mock_app_cls = MagicMock()
    monkeypatch.setattr("stitcher.cli.main.StitcherApp", mock_app_cls)
    
    runner.invoke(app, ["check"])
    
    args, kwargs = mock_app_cls.call_args
    assert kwargs["interaction_handler"] is not None
    assert "TyperInteractionHandler" in str(type(kwargs["interaction_handler"]))
~~~~~

#### Acts 3: 验证交互向导的内部逻辑

我们将模拟用户的按键序列，验证 `TyperInteractionHandler` 的决策生成。

~~~~~act
write_file
packages/stitcher-cli/tests/test_handler_logic.py
~~~~~
~~~~~python
from stitcher.cli.handlers import TyperInteractionHandler
from stitcher.app.protocols import InteractionContext
from stitcher.spec import ResolutionAction, ConflictType
import click

def test_handler_single_key_and_sticky_default(monkeypatch):
    handler = TyperInteractionHandler()
    contexts = [
        InteractionContext("f1.py", "a", ConflictType.SIGNATURE_DRIFT),
        InteractionContext("f1.py", "b", ConflictType.SIGNATURE_DRIFT),
    ]
    
    # Simulating: 
    # 1. User presses 'f' for the first conflict
    # 2. User presses 'Enter' (\r) for the second conflict (should use 'f' as sticky default)
    input_sequence = iter(['f', '\r'])
    monkeypatch.setattr(click, "getchar", lambda: next(input_sequence))
    
    actions = handler.process_interactive_session(contexts)
    
    assert actions[0] == ResolutionAction.RELINK
    assert actions[1] == ResolutionAction.RELINK

def test_handler_undo_logic(monkeypatch):
    handler = TyperInteractionHandler()
    contexts = [
        InteractionContext("f1.py", "a", ConflictType.SIGNATURE_DRIFT),
        InteractionContext("f1.py", "b", ConflictType.SIGNATURE_DRIFT),
    ]
    
    # Simulating:
    # 1. User presses 'f' (Relink) for first
    # 2. User presses 'z' (Undo) to go back
    # 3. User presses 's' (Skip) to overwrite the first decision
    # 4. User presses 'r' (Reconcile - though not valid for drift, but handler will handle it or we test flow)
    # Actually, let's keep it simple: f -> z -> s -> s
    input_sequence = iter(['f', 'z', 's', 's'])
    monkeypatch.setattr(click, "getchar", lambda: next(input_sequence))
    
    actions = handler.process_interactive_session(contexts)
    
    assert actions[0] == ResolutionAction.SKIP
    assert actions[1] == ResolutionAction.SKIP
~~~~~

### 下一步建议
- **运行测试**：执行这些新创建的测试文件。
- **完善边界条件**：考虑添加针对“无效按键”或“中途 ABORT”的交互测试。
- **性能评估**：在拥有大量冲突（例如 100+）的大型项目中测试交互向导的响应速度和内存占用。
