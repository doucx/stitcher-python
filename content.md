这是一个修复 `CheckRunner` 单元测试由于 API 变更（引入 `TransactionManager`）导致失败的计划。

我们将更新 `test_check_runner.py`，在调用 `resolve_conflicts` 时注入 `TransactionManager` 的 Mock 实例，并同步更新断言以匹配新的函数签名。

## [WIP] test: 修复 CheckRunner 测试以适配事务化 resolve_conflicts

### 错误分析
测试失败的原因是 `CheckRunner.resolve_conflicts` 的方法签名在重构中发生了变更：增加了一个强制的 `tm: TransactionManager` 参数。原有的测试用例未传递此参数，导致 `TypeError`。

### 用户需求
修复 `test_check_runner.py` 中的单元测试失败。

### 评论
随着 `check` 流程的事务化，`CheckRunner` 必须能够向下游的 `Resolver` 传递事务上下文。单元测试需要反映这一编排职责。

### 目标
1.  在测试用例中创建 `TransactionManager` 的 Mock 对象。
2.  更新对 `runner.resolve_conflicts` 的所有调用。
3.  更新对 `mock_resolver.resolve_conflicts` 调用情况的断言。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/check-tests #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修复 `test_check_runner.py` 中的测试调用

我们将引入 `TransactionManager` 的 Mock，并修复两个失败的测试函数。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    ModuleDef,
    DifferProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
from stitcher.workspace import Workspace
~~~~~
~~~~~python.new
from stitcher.spec import (
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    ModuleDef,
    DifferProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
from stitcher.workspace import Workspace
from stitcher.common.transaction import TransactionManager
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
    # 配置 mock 模块
    mock_modules = [ModuleDef(file_path="src/main.py")]

    # Mock Engine 行为
    mock_engine = MagicMock()
~~~~~
~~~~~python.new
    # 配置 mock 模块
    mock_modules = [ModuleDef(file_path="src/main.py")]
    mock_tm = mocker.create_autospec(TransactionManager, instance=True)

    # Mock Engine 行为
    mock_engine = MagicMock()
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
    # 继续执行工作流
    runner.auto_reconcile_docs(results, mock_modules)
    resolution_success = runner.resolve_conflicts(results, conflicts)
    report_success = runner.report(results, [])

    # 验证与 mock 的交互
    mock_engine.analyze.assert_called_once()
    mock_resolver.auto_reconcile_docs.assert_called_once_with(results, mock_modules)
    mock_resolver.resolve_conflicts.assert_called_once_with(
        results, conflicts, force_relink=False, reconcile=False
    )
    mock_reporter.report.assert_called_once_with(results, [])
~~~~~
~~~~~python.new
    # 继续执行工作流
    runner.auto_reconcile_docs(results, mock_modules)
    resolution_success = runner.resolve_conflicts(results, conflicts, mock_tm)
    report_success = runner.report(results, [])

    # 验证与 mock 的交互
    mock_engine.analyze.assert_called_once()
    mock_resolver.auto_reconcile_docs.assert_called_once_with(results, mock_modules)
    mock_resolver.resolve_conflicts.assert_called_once_with(
        results, conflicts, mock_tm, force_relink=False, reconcile=False
    )
    mock_reporter.report.assert_called_once_with(results, [])
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
def test_check_runner_passes_relink_and_reconcile_flags_to_resolver(mocker):
    """
    确保来自 Runner 公共 API 的布尔标志被正确传递给解析器组件。
    """
    # Arrange
    mock_resolver = mocker.create_autospec(CheckResolver, instance=True)
    runner = CheckRunner(
~~~~~
~~~~~python.new
def test_check_runner_passes_relink_and_reconcile_flags_to_resolver(mocker):
    """
    确保来自 Runner 公共 API 的布尔标志被正确传递给解析器组件。
    """
    # Arrange
    mock_resolver = mocker.create_autospec(CheckResolver, instance=True)
    mock_tm = mocker.create_autospec(TransactionManager, instance=True)
    runner = CheckRunner(
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_check_runner.py
~~~~~
~~~~~python.old
    # Act
    runner.resolve_conflicts(
        mock_results, mock_conflicts, force_relink=True, reconcile=True
    )

    # Assert
    mock_resolver.resolve_conflicts.assert_called_once_with(
        mock_results, mock_conflicts, force_relink=True, reconcile=True
    )
~~~~~
~~~~~python.new
    # Act
    runner.resolve_conflicts(
        mock_results, mock_conflicts, mock_tm, force_relink=True, reconcile=True
    )

    # Assert
    mock_resolver.resolve_conflicts.assert_called_once_with(
        mock_results, mock_conflicts, mock_tm, force_relink=True, reconcile=True
    )
~~~~~

### 下一步建议
我们已经修复了 `CheckRunner` 的单元测试。考虑到 `CheckResolver` 构造函数也增加了 `lock_session` 参数，如果存在针对 `CheckResolver` 直接实例化的测试，它们也需要进行类似的修复。我建议接下来运行整个测试套件以捕捉任何遗漏的错误。
