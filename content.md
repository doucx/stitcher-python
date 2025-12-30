当然。我们来为这个新功能编写集成测试，以确保其行为符合预期，并且足够健壮。

我将生成一个计划，在 `packages/stitcher-application/tests/integration/test_check_interactive_flow.py` 文件中添加三个新的测试用例：

1.  **测试清除功能**：验证当用户选择 `[P]urge` 时，悬空的文档条目会被正确地从 YAML 文件中删除。
2.  **测试跳过功能**：验证当用户选择 `[S]kip` 时，悬空文档被报告为错误，并且命令以失败状态退出。
3.  **测试文件删除**：验证当最后一个条目被清除后，空的 `.stitcher.yaml` 文件会被自动删除。

这将确保整个交互式清除工作流的正确性。

## [WIP] test: 为交互式清除悬空文档功能添加集成测试

### 用户需求
为新实现的“交互式清除悬空文档”功能编写一套全面的集成测试，以验证其在不同用户选择下的行为，并防止未来出现回归。

### 评论
为核心功能编写自动化测试是保障软件质量的关键步骤。这组测试将覆盖成功路径、失败路径以及边缘情况（如删除最后一个条目），确保新功能的稳定性和可靠性。

### 目标
1.  在 `test_check_interactive_flow.py` 中添加一个 `pytest` fixture，用于创建包含悬空文档的测试工作区。
2.  实现一个测试用例，模拟用户选择“Purge”并断言 YAML 文件被正确修改。
3.  实现一个测试用例，模拟用户选择“Skip”并断言命令失败且文件未被修改。
4.  实现一个测试用例，验证当最后一个文档条目被清除时，整个 YAML 文件会被删除。

### 基本原理
我们将利用现有的 `WorkspaceFactory` 和 `MockResolutionHandler` 测试工具来构建测试场景。通过 `monkeypatch` 注入 Mock 处理器，我们可以精确地模拟用户的交互选择，并通过 `SpyBus` 捕获应用的输出，从而验证其行为。对文件系统的直接断言（检查 YAML 文件的内容或存在性）将确保操作的最终结果符合预期。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/tests #comp/application
#ai/instruct
#task/domain/cli #task/object/interactive-check #task/action/feature-enhancement
#task/state/end

---
### Script

#### Acts 1: 更新测试文件的导入语句

首先，我们需要向 `test_check_interactive_flow.py` 添加 `pytest`, `yaml` 和 `ConflictType` 的导入。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python.old
from typing import List
from stitcher.test_utils import create_test_app
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction
from stitcher.test_utils import WorkspaceFactory, SpyBus, get_stored_hashes
from needle.pointer import L
~~~~~
~~~~~python.new
import pytest
import yaml
from typing import List
from stitcher.test_utils import create_test_app
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType
from stitcher.test_utils import WorkspaceFactory, SpyBus, get_stored_hashes
from needle.pointer import L
~~~~~

#### Acts 2: 添加新的测试用例和 Fixture

现在，我们将新的测试代码追加到文件末尾。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python.old
    # func_b should have updated code hash due to RELINK
    assert "baseline_code_structure_hash" in final_hashes["func_b"]
    assert final_hashes["func_b"]["baseline_code_structure_hash"] is not None
~~~~~
~~~~~python.new
    # func_b should have updated code hash due to RELINK
    assert "baseline_code_structure_hash" in final_hashes["func_b"]
    assert final_hashes["func_b"]["baseline_code_structure_hash"] is not None


@pytest.fixture
def dangling_doc_workspace(tmp_path):
    """Creates a workspace with a doc file containing an extra key."""
    factory = WorkspaceFactory(tmp_path)
    return (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "def func_a(): pass")
        .with_docs(
            "src/app.stitcher.yaml",
            {"func_a": "Doc A.", "dangling_func": "This one is extra."},
        )
        .build()
    )


def test_check_interactive_purge_removes_dangling_doc(
    dangling_doc_workspace, monkeypatch
):
    """
    Verify that choosing [P]urge correctly removes the dangling entry from the YAML file.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Purge'
    handler = MockResolutionHandler([ResolutionAction.PURGE_DOC])
    app = create_test_app(root_path=dangling_doc_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True, "Check should succeed after interactive purge."

    # Assert correct context was passed to handler
    assert len(handler.called_with) == 1
    assert handler.called_with[0].fqn == "dangling_func"
    assert handler.called_with[0].conflict_type == ConflictType.DANGLING_DOC

    # Assert correct bus message was sent
    spy_bus.assert_id_called(L.check.state.purged, level="success")

    # Assert YAML file was modified
    doc_file = dangling_doc_workspace / "src/app.stitcher.yaml"
    with doc_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "dangling_func" not in data
    assert "func_a" in data

    # A subsequent check should be clean
    app_verify = create_test_app(root_path=dangling_doc_workspace)
    spy_verify = SpyBus()
    with spy_verify.patch(monkeypatch, "stitcher.common.bus"):
        assert app_verify.run_check() is True
    spy_verify.assert_id_called(L.check.run.success)


def test_check_interactive_skip_dangling_doc_fails(dangling_doc_workspace, monkeypatch):
    """
    Verify that skipping a dangling doc conflict results in a check failure.
    """
    # 1. Arrange: Handler simulates choosing 'Skip'
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=dangling_doc_workspace, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False
    spy_bus.assert_id_called(L.check.issue.extra, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")

    # Assert YAML was not changed
    doc_file = dangling_doc_workspace / "src/app.stitcher.yaml"
    with doc_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "dangling_func" in data


def test_check_interactive_purge_deletes_empty_yaml(tmp_path, monkeypatch):
    """
    Verify that if purging the last entry makes the YAML file empty, the file is deleted.
    """
    # 1. Arrange: Workspace with only a dangling doc
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "")
        .with_docs("src/app.stitcher.yaml", {"dangling": "doc"})
        .build()
    )
    doc_file = project_root / "src/app.stitcher.yaml"
    assert doc_file.exists()

    handler = MockResolutionHandler([ResolutionAction.PURGE_DOC])
    app = create_test_app(root_path=project_root, interaction_handler=handler)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.state.purged, level="success")
    assert not doc_file.exists(), "YAML file should have been deleted after last entry was purged."
~~~~~
