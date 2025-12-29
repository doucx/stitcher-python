简要回答:
好的，我们将专注于验证新架构的核心：`OverlayOperator` 的纯粹组合能力，以及 `FileSystemOperator` 在真实管道中的行为。

## [WIP] feat: 阶段一 Part 4 - 重建 Operator 组合与集成测试

### 用户需求
1.  **单元测试**: 验证 `OverlayOperator` 能正确处理优先级和回退。
2.  **集成测试**: 模拟真实场景，验证 `FileSystemOperator` 与 `OverlayOperator` 结合使用时，能否正确实现“用户覆盖默认值”的逻辑。

### 评论
随着旧的 Loader 和 Nexus 被移除，我们之前依赖于它们的、复杂的测试用例都已清除。现在的测试将非常纯粹：只关注算子的输入输出。这将极大地提高测试的可读性和维护性。

### 目标
1.  **test_overlay_operator.py**: 验证内存中的算子组合。
2.  **test_pipeline_integration.py**: 验证基于文件系统的真实管道组装。

### 基本原理
*   使用 `DictOperator` 进行轻量级的单元测试，因为它不涉及 I/O，能精确控制“数据源”。
*   使用 `tmp_path` 动态构建文件结构，测试 `FileSystemOperator` 的懒加载和 `OverlayOperator` 的查找顺序。

### 标签
#intent/test #flow/ready #priority/high #comp/runtime #comp/nexus #concept/executor #scope/core #ai/instruct #task/domain/testing #task/object/operators #task/action/implement

---

### Script

#### Acts 1: 重建 test_overlay_operator.py

这个文件之前因为 `MemoryLoader` 的移除而出错，现在我们用 `DictOperator` 重新实现它。测试逻辑非常简单：两个字典，一个覆盖另一个。

~~~~~act
write_file
packages/pyneedle-nexus/tests/test_overlay_operator.py
~~~~~
~~~~~python
import pytest
from needle.nexus import OverlayOperator
from needle.operators import DictOperator


def test_overlay_priority_and_fallback():
    # Arrange
    # Level 1: User Overrides (High Priority)
    user_op = DictOperator({
        "app.title": "User Title",
        # "app.version" is missing here
    })
    
    # Level 2: System Defaults (Low Priority)
    system_op = DictOperator({
        "app.title": "System Title", 
        "app.version": "1.0.0",
        "sys.core": "CoreLib"
    })
    
    # Compose them: user first
    overlay = OverlayOperator([user_op, system_op])
    
    # Act & Assert
    
    # 1. Shadowing: User value should win
    assert overlay("app.title") == "User Title"
    
    # 2. Fallback: Missing in user, found in system
    assert overlay("app.version") == "1.0.0"
    
    # 3. Deep Fallback
    assert overlay("sys.core") == "CoreLib"
    
    # 4. Missing: Not in either
    assert overlay("unknown.key") is None


def test_overlay_returns_first_match_strictly():
    # If the first operator returns a value (even empty string), it wins.
    # It should only fall back on None.
    
    op1 = DictOperator({"key": ""}) # Empty string
    op2 = DictOperator({"key": "fallback"})
    
    overlay = OverlayOperator([op1, op2])
    
    assert overlay("key") == ""
~~~~~

#### Acts 2: 创建 test_pipeline_integration.py

这个测试模拟 `stitcher-common` 中定义的真实管道逻辑。

~~~~~act
write_file
packages/pyneedle-runtime/tests/test_pipeline_integration.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from needle.pointer import L
from needle.operators import FileSystemOperator
from needle.nexus import OverlayOperator


def test_fs_pipeline_overrides(tmp_path: Path):
    """
    Simulate the full Stitcher pipeline:
    Project Root (.stitcher/needle/en) -> Overrides -> Common Assets (needle/en)
    """
    
    # 1. Setup "Common Assets" (Low Priority)
    common_root = tmp_path / "common" / "needle" / "en"
    common_root.mkdir(parents=True)
    (common_root / "cli.json").write_text('{"help": "Default Help"}', encoding="utf-8")
    (common_root / "error.json").write_text('{"404": "Not Found"}', encoding="utf-8")
    
    # 2. Setup "User Project" (High Priority)
    project_root = tmp_path / "project" / ".stitcher" / "needle" / "en"
    project_root.mkdir(parents=True)
    (project_root / "cli.json").write_text('{"help": "Custom Help"}', encoding="utf-8")
    
    # 3. Build Operators
    common_op = FileSystemOperator(common_root)
    project_op = FileSystemOperator(project_root)
    
    # 4. Compose Pipeline (Project > Common)
    pipeline = OverlayOperator([project_op, common_op])
    
    # Act & Assert
    
    # A. Override: Project value wins
    assert pipeline(L.cli.help) == "Custom Help"
    
    # B. Fallback: Project doesn't have error.json, falls back to common
    assert pipeline(L.error["404"]) == "Not Found"
    
    # C. Missing
    assert pipeline(L.cli.unknown) is None
    
    
def test_fs_pipeline_nested_keys(tmp_path: Path):
    """
    Verify nested key access works through the pipeline.
    """
    root = tmp_path / "assets"
    root.mkdir()
    (root / "check.json").write_text(
        '{"messages": {"success": "OK", "fail": "NO"}}', 
        encoding="utf-8"
    )
    
    op = FileSystemOperator(root)
    
    # Flattening happens inside FileSystemOperator -> JsonHandler
    # check.json -> messages -> success
    assert op(L.check.messages.success) == "OK"
~~~~~

### 下一步建议
通过上述测试，我们验证了新架构在逻辑上的正确性。现在我们需要回头处理之前 `stitcher-common/__init__.py` 中留下的 `stitcher_operator` 变量。
因为 `MessageBus` 依赖于 `get` 方法（原 Nexus 协议），而我们的 `OverlayOperator` 只有 `__call__`。这会导致 `bus.info(...)` 调用失败。

下一步必须修改 `MessageBus`，使其只依赖 `OperatorProtocol` (`__call__`)，而不是可以 `get` 的对象。这是一个微小但关键的适配。
