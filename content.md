## [WIP] 我将生成补丁来修复这两个问题。

好的，分析这些测试失败的原因非常清晰。它们指向了我代码中两个不同但相关的逻辑错误。

### 错误分析

1.  **`test_analyzer_no_changes` 失败原因: 错误的乐观路径假设**
    -   `PumpAnalyzer.analyze()` 的逻辑是：首先检查哪些文件中的 docstring 是“脏的”（即与基线哈希不匹配），然后**只对这些脏文件**调用 `doc_manager.hydrate_module()` 进行冲突分析。
    -   在 `test_analyzer_no_changes` 测试中，我没有为 `mock_index_store` 或 `mock_sig_manager` 提供任何数据。这导致 `_get_dirty_source_docs()` 内部逻辑认为**没有任何文件是脏的**。
    -   因此，`doc_manager.hydrate_module()` 从未被调用，导致 `assert_called_once()` 失败。
    -   **解决方案**: 我需要模拟一个“脏文档”的场景，让 `_get_dirty_source_docs` 返回一个非空字典，从而触发 `hydrate_module` 的调用。

2.  **`test_executor_*` 失败原因: `deepcopy` 与 Mock 对象的兼容性问题**
    -   `PumpExecutor.execute()` 在开始时会调用 `copy.deepcopy(stored_hashes)`。`stored_hashes` 是从 `sig_manager.load_composite_hashes()` 返回的。
    -   在测试中，`sig_manager` 是一个 `create_autospec(SignatureManagerProtocol, instance=True)` 创建的 Mock 对象。它的 `load_composite_hashes` 方法返回的是一个**新的 `MagicMock` 对象**，而不是一个普通的字典。
    -   `copy.deepcopy` 无法序列化（pickle）`unittest.mock` 内部的一些对象（如 `_abc._abc_data`），这导致了 `TypeError: cannot pickle '_abc._abc_data' object`。
    -   **解决方案**: 在测试设置中，我们必须确保 `mock_sig_manager.load_composite_hashes` 返回的是一个**真实的、可被深拷贝的数据结构**（例如，一个普通的字典），而不是一个 Mock 对象。

### 修复计划

我将生成补丁来修复这两个问题。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_analyzer.py
~~~~~
~~~~~python.old
def test_analyzer_no_changes(analyzer: PumpAnalyzer, mock_doc_manager: DocumentManagerProtocol, mock_index_store: IndexStoreProtocol):
    """Verify analyzer returns no conflicts if hydrate dry_run is successful."""
    module = ModuleDef(file_path="src/main.py")
    mock_index_store.get_symbols_by_file_path.return_value = []
    mock_doc_manager.hydrate_module.return_value = {"success": True, "conflicts": []}

    conflicts = analyzer.analyze([module])

    assert not conflicts
    mock_doc_manager.hydrate_module.assert_called_once()
~~~~~
~~~~~python.new
def test_analyzer_no_changes(analyzer: PumpAnalyzer, mock_doc_manager: DocumentManagerProtocol, mock_index_store: IndexStoreProtocol, mock_sig_manager: SignatureManagerProtocol):
    """Verify analyzer returns no conflicts if a dirty doc is resolved by hydrate."""
    module = ModuleDef(file_path="src/main.py")
    
    # Arrange: Simulate a dirty docstring to trigger the hydrate_module call
    mock_symbol = MagicMock()
    mock_symbol.logical_path = "func"
    mock_symbol.docstring_hash = "new_hash"
    mock_index_store.get_symbols_by_file_path.return_value = [mock_symbol]
    mock_sig_manager.load_composite_hashes.return_value = {} # Baseline is empty

    # Arrange: Configure hydrate_module to report success (no conflicts)
    mock_doc_manager.hydrate_module.return_value = {"success": True, "conflicts": []}
    mock_doc_manager.flatten_module_docs.return_value = {"func": DocstringIR(summary="New doc")}


    conflicts = analyzer.analyze([module])

    assert not conflicts
    mock_doc_manager.hydrate_module.assert_called_once()
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
@pytest.fixture
def executor(
    mock_doc_manager: DocumentManagerProtocol,
) -> PumpExecutor:
    return PumpExecutor(
        root_path=MagicMock(),
        doc_manager=mock_doc_manager,
        sig_manager=create_autospec(SignatureManagerProtocol, instance=True),
        transformer=create_autospec(LanguageTransformerProtocol, instance=True),
        merger=create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=create_autospec(FingerprintStrategyProtocol, instance=True),
    )
~~~~~
~~~~~python.new
@pytest.fixture
def mock_sig_manager() -> SignatureManagerProtocol:
    mock = create_autospec(SignatureManagerProtocol, instance=True)
    # IMPORTANT: Return a real dict to avoid deepcopy issues with mocks.
    mock.load_composite_hashes.return_value = {}
    return mock


@pytest.fixture
def executor(
    mock_doc_manager: DocumentManagerProtocol,
    mock_sig_manager: SignatureManagerProtocol,
) -> PumpExecutor:
    return PumpExecutor(
        root_path=MagicMock(),
        doc_manager=mock_doc_manager,
        sig_manager=mock_sig_manager,
        transformer=create_autospec(LanguageTransformerProtocol, instance=True),
        merger=create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=create_autospec(FingerprintStrategyProtocol, instance=True),
    )
~~~~~

这些修复确保了 `PumpAnalyzer` 的测试能正确触发其核心逻辑，并解决了 `PumpExecutor` 测试中由 `deepcopy` 和 Mock 对象不兼容引起的技术问题。现在，所有测试应该都能通过。
