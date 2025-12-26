## [WIP] refactor(tests): 在测试断言中强制使用 L 对象

### 用户需求
目前的集成测试代码在断言 `mock_bus` 调用时使用了硬编码的字符串（如 `"generate.file.success"`）。这违反了项目“消灭魔法字符串”的核心宗旨，也与业务代码中使用的 `L` 对象不一致。用户要求测试代码必须与业务代码行为完全一致，使用 `L` 对象进行断言。

### 评论
这是一个非常重要的代码质量改进。虽然 `L.key == "key"` 使得目前的测试在运行时能通过，但在代码语义层面，直接使用字符串切断了语义链接，使得重构（如重命名 Key）变得困难，且无法享受 IDE 的补全和检查。修复这一点能确保测试代码也是类型安全且语义明确的。

### 目标
1.  修改 `tests/integration/test_init_command.py`，引入 `L` 对象并替换所有字符串断言。
2.  修改 `tests/integration/test_end_to_end.py`，引入 `L` 对象并替换所有字符串断言。

### 基本原理
根据 `d3-principle-python-testing-mock-intent`，测试应验证业务意图。在 Stitcher 中，意图是由 `L` 对象携带的。
我们将：
1.  导入 `stitcher.needle.L`。
2.  将 `mock_bus.method.assert_called_with("string.key", ...)` 替换为 `mock_bus.method.assert_called_with(L.string.key, ...)`。

### 标签
#intent/refine #flow/ready #priority/medium #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/mock-bus #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 修复 `test_init_command.py`

~~~~~act
patch_file
tests/integration/test_init_command.py
~~~~~
~~~~~python.old
from unittest.mock import MagicMock
from stitcher.app import StitcherApp


@pytest.fixture
~~~~~
~~~~~python.new
from unittest.mock import MagicMock
from stitcher.app import StitcherApp
from stitcher.needle import L


@pytest.fixture
~~~~~

~~~~~act
patch_file
tests/integration/test_init_command.py
~~~~~
~~~~~python.old
    # Verify bus messages
    mock_bus.success.assert_any_call(
        "init.file.created", path=expected_yaml.relative_to(project_root)
    )
    mock_bus.success.assert_any_call("init.run.complete", count=1)


def test_init_skips_files_without_docs(tmp_path, mock_bus):
~~~~~
~~~~~python.new
    # Verify bus messages
    mock_bus.success.assert_any_call(
        L.init.file.created, path=expected_yaml.relative_to(project_root)
    )
    mock_bus.success.assert_any_call(L.init.run.complete, count=1)


def test_init_skips_files_without_docs(tmp_path, mock_bus):
~~~~~

~~~~~act
patch_file
tests/integration/test_init_command.py
~~~~~
~~~~~python.old
    app = StitcherApp(root_path=project_root)
    created_files = app.run_init()
    
    assert len(created_files) == 0
    mock_bus.info.assert_called_with("init.no_docs_found")
~~~~~
~~~~~python.new
    app = StitcherApp(root_path=project_root)
    created_files = app.run_init()
    
    assert len(created_files) == 0
    mock_bus.info.assert_called_with(L.init.no_docs_found)
~~~~~

#### Acts 2: 修复 `test_end_to_end.py`

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
from textwrap import dedent
from unittest.mock import MagicMock

# This module doesn't exist yet, driving its creation
from stitcher.app import StitcherApp
~~~~~
~~~~~python.new
from textwrap import dedent
from unittest.mock import MagicMock
from stitcher.needle import L

# This module doesn't exist yet, driving its creation
from stitcher.app import StitcherApp
~~~~~

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
    expected_relative_path = expected_pyi_path.relative_to(tmp_path)

    mock_bus.success.assert_called_once_with(
        "generate.file.success", path=expected_relative_path
    )
    mock_bus.error.assert_not_called()
~~~~~
~~~~~python.new
    expected_relative_path = expected_pyi_path.relative_to(tmp_path)

    mock_bus.success.assert_called_once_with(
        L.generate.file.success, path=expected_relative_path
    )
    mock_bus.error.assert_not_called()
~~~~~

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
    helpers_pyi = project_root / "src" / "app" / "utils" / "helpers.pyi"

    mock_bus.success.assert_any_call(
        "generate.file.success", path=main_pyi.relative_to(project_root)
    )
    mock_bus.success.assert_any_call(
        "generate.file.success", path=helpers_pyi.relative_to(project_root)
    )
    mock_bus.success.assert_any_call("generate.run.complete", count=2)
    assert mock_bus.success.call_count == 3
    mock_bus.error.assert_not_called()
~~~~~
~~~~~python.new
    helpers_pyi = project_root / "src" / "app" / "utils" / "helpers.pyi"

    mock_bus.success.assert_any_call(
        L.generate.file.success, path=main_pyi.relative_to(project_root)
    )
    mock_bus.success.assert_any_call(
        L.generate.file.success, path=helpers_pyi.relative_to(project_root)
    )
    mock_bus.success.assert_any_call(L.generate.run.complete, count=2)
    assert mock_bus.success.call_count == 3
    mock_bus.error.assert_not_called()
~~~~~

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
    static_pyi = project_with_plugin / "src" / "main.pyi"
    assert static_pyi.exists()
    mock_bus.success.assert_any_call(
        "generate.file.success", path=static_pyi.relative_to(project_with_plugin)
    )

    # Check for dynamic plugin stubs
    dynamic_pyi = project_with_plugin / "dynamic" / "utils.pyi"
    assert dynamic_pyi.exists()
    assert "def dynamic_util() -> bool:" in dynamic_pyi.read_text()
    mock_bus.success.assert_any_call(
        "generate.file.success", path=dynamic_pyi.relative_to(project_with_plugin)
    )

    # Check that intermediate __init__.pyi was created
    dynamic_init_pyi = project_with_plugin / "dynamic" / "__init__.pyi"
    assert dynamic_init_pyi.exists()
    mock_bus.success.assert_any_call(
        "generate.file.success", path=dynamic_init_pyi.relative_to(project_with_plugin)
    )

    mock_bus.success.assert_any_call("generate.run.complete", count=3)
~~~~~
~~~~~python.new
    static_pyi = project_with_plugin / "src" / "main.pyi"
    assert static_pyi.exists()
    mock_bus.success.assert_any_call(
        L.generate.file.success, path=static_pyi.relative_to(project_with_plugin)
    )

    # Check for dynamic plugin stubs
    dynamic_pyi = project_with_plugin / "dynamic" / "utils.pyi"
    assert dynamic_pyi.exists()
    assert "def dynamic_util() -> bool:" in dynamic_pyi.read_text()
    mock_bus.success.assert_any_call(
        L.generate.file.success, path=dynamic_pyi.relative_to(project_with_plugin)
    )

    # Check that intermediate __init__.pyi was created
    dynamic_init_pyi = project_with_plugin / "dynamic" / "__init__.pyi"
    assert dynamic_init_pyi.exists()
    mock_bus.success.assert_any_call(
        L.generate.file.success, path=dynamic_init_pyi.relative_to(project_with_plugin)
    )

    mock_bus.success.assert_any_call(L.generate.run.complete, count=3)
~~~~~

### 下一步建议
修复测试后，我们可以继续进行 **任务 2.4: `stitcher check` 命令** 的实现。这将在 CI/CD 流程中强制使用 `L` 对象（通过静态分析或运行时检查，虽然 Python 中这很难完全强制，但通过 Code Review 和测试规范来保证）。
