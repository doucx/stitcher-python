这是一个修复 `PumpExecutor` 测试套件因构造函数变更导致报错的计划。

我们将更新 `test_pump_executor.py` 和 `test_execution_planner.py`，为 `PumpExecutor` 注入 Mock 形式的 `LockSession`。同时，我们将更新 `test_pump_executor.py` 中的断言，使其验证 `LockSession` 的调用而非手动的 `tm.add_write` 调用。

## [WIP] test: 修复 PumpExecutor 测试套件以适配 LockSession

### 用户需求
修复由于 `PumpExecutor` 构造函数增加 `lock_session` 强制参数导致的单元测试失败。

### 评论
随着架构的演进，测试套件必须同步更新。由于现在 Lock 文件的写入由 `StitcherApp` 统一负责，而 `PumpExecutor` 仅负责向 `LockSession` 登记变更，我们需要将测试的焦点从“是否产生了文件写入”转向“是否向 Session 报告了正确的状态”。

### 目标
1.  在两个测试文件中引入 `mock_lock_session` 夹具。
2.  修复 `executor` 夹具的实例化代码。
3.  更新集成性质的断言，验证 `lock_session` 的交互。

### 基本原理
-   **Mocking**: 使用 `unittest.mock` 模拟 `LockSession`，隔离外部依赖。
-   **行为验证 (Behavior Verification)**: 既然持久化逻辑已经外迁，执行器的单元测试应断言其是否正确发出了“状态登记”指令。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/pump-tests #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修复 `test_pump_executor.py`

我们需要增加 `mock_lock_session` 夹具，并更新 `executor` 的构造函数和测试断言。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
@pytest.fixture
def mock_lock_manager(mocker) -> MagicMock:
    mock = mocker.create_autospec(LockManagerProtocol, instance=True)
    mock.load.return_value = {}
    mock.serialize.return_value = '{"version": "1.0", "fingerprints": {}}'
    return mock


@pytest.fixture
def executor(
    tmp_path: Path,
    mocker,
    mock_doc_manager: DocumentManagerProtocol,
    mock_lock_manager: LockManagerProtocol,
) -> PumpExecutor:
    mock_workspace = mocker.create_autospec(Workspace, instance=True)
~~~~~
~~~~~python.new
@pytest.fixture
def mock_lock_manager(mocker) -> MagicMock:
    mock = mocker.create_autospec(LockManagerProtocol, instance=True)
    mock.load.return_value = {}
    mock.serialize.return_value = '{"version": "1.0", "fingerprints": {}}'
    return mock


@pytest.fixture
def mock_lock_session(mocker) -> MagicMock:
    from stitcher.app.services.lock_session import LockSession
    return mocker.create_autospec(LockSession, instance=True)


@pytest.fixture
def executor(
    tmp_path: Path,
    mocker,
    mock_doc_manager: DocumentManagerProtocol,
    mock_lock_manager: LockManagerProtocol,
    mock_lock_session: MagicMock,
) -> PumpExecutor:
    mock_workspace = mocker.create_autospec(Workspace, instance=True)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
    mock_workspace.find_owning_package.return_value = tmp_path
    # Use the real tmp_path instead of a MagicMock for root_path
    return PumpExecutor(
        root_path=tmp_path,
        workspace=mock_workspace,
        doc_manager=mock_doc_manager,
        lock_manager=mock_lock_manager,
        uri_generator=mocker.create_autospec(URIGeneratorProtocol, instance=True),
        transformer=mocker.create_autospec(LanguageTransformerProtocol, instance=True),
        merger=mocker.create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=mocker.create_autospec(
            FingerprintStrategyProtocol, instance=True
        ),
    )
~~~~~
~~~~~python.new
    mock_workspace.find_owning_package.return_value = tmp_path
    # Use the real tmp_path instead of a MagicMock for root_path
    return PumpExecutor(
        root_path=tmp_path,
        workspace=mock_workspace,
        doc_manager=mock_doc_manager,
        lock_manager=mock_lock_manager,
        uri_generator=mocker.create_autospec(URIGeneratorProtocol, instance=True),
        transformer=mocker.create_autospec(LanguageTransformerProtocol, instance=True),
        merger=mocker.create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=mocker.create_autospec(
            FingerprintStrategyProtocol, instance=True
        ),
        lock_session=mock_lock_session,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
    executor.execute([sample_module], decisions={}, tm=mock_tm, strip=False)

    # Assert YAML file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert lock file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call("stitcher.lock", ANY)
~~~~~
~~~~~python.new
    executor.execute([sample_module], decisions={}, tm=mock_tm, strip=False)

    # Assert YAML file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert lock session is notified
    executor.lock_session.record_fresh_state.assert_called()
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
    executor.execute([sample_module], decisions=decisions, tm=mock_tm, strip=True)

    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert lock file is written
    mock_tm.add_write.assert_any_call("stitcher.lock", ANY)
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()  # type: ignore[reportAttributeAccessIssue]
~~~~~
~~~~~python.new
    executor.execute([sample_module], decisions=decisions, tm=mock_tm, strip=True)

    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert lock session is notified
    executor.lock_session.record_fresh_state.assert_called()
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()  # type: ignore[reportAttributeAccessIssue]
~~~~~

#### Acts 2: 修复 `test_execution_planner.py`

此文件仅需修复 `executor` 夹具的实例化。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_execution_planner.py
~~~~~
~~~~~python.old
@pytest.fixture
def executor(tmp_path, mocker) -> PumpExecutor:
    """A PumpExecutor instance for testing its internal methods."""
    return PumpExecutor(
        root_path=tmp_path,
        workspace=mocker.create_autospec(Workspace, instance=True),
        doc_manager=DocumentManager(
            root_path=tmp_path, uri_generator=PythonURIGenerator()
        ),
        lock_manager=mocker.create_autospec(LockManagerProtocol, instance=True),
        uri_generator=mocker.create_autospec(URIGeneratorProtocol, instance=True),
        transformer=MagicMock(),
        merger=DocstringMerger(),
        fingerprint_strategy=MagicMock(),
    )
~~~~~
~~~~~python.new
@pytest.fixture
def executor(tmp_path, mocker) -> PumpExecutor:
    """A PumpExecutor instance for testing its internal methods."""
    from stitcher.app.services.lock_session import LockSession

    return PumpExecutor(
        root_path=tmp_path,
        workspace=mocker.create_autospec(Workspace, instance=True),
        doc_manager=DocumentManager(
            root_path=tmp_path, uri_generator=PythonURIGenerator()
        ),
        lock_manager=mocker.create_autospec(LockManagerProtocol, instance=True),
        uri_generator=mocker.create_autospec(URIGeneratorProtocol, instance=True),
        transformer=MagicMock(),
        merger=DocstringMerger(),
        fingerprint_strategy=MagicMock(),
        lock_session=mocker.create_autospec(LockSession, instance=True),
    )
~~~~~

### 下一步建议
修复测试后，请重新运行测试套件。如果 `TypeError` 消失，我们将进入**阶段 3：重构 Check 流程**，将 `CheckResolver` 接入 `LockSession`。
