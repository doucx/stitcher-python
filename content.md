## 我将修改 `test_pump_executor.py`，使用一个真实的 `Path` 对象（由 `tmp_path` 提供）来代替 `MagicMock`，并使用 `ANY` 来进行更稳健的断言。

You've found another excellent and subtle flaw in my tests. Your analysis is spot on.

### 错误分析

1.  **根本原因: Mock 对象的滥用导致路径计算失败**
    -   在 `test_pump_executor.py` 的 `executor` fixture 中，我将 `root_path` 初始化为一个 `MagicMock()`。
    -   `PumpExecutor` 的代码依赖于标准的 `pathlib.Path` 操作来构建输出文件的路径，例如 `(self.root_path / module.file_path).with_suffix(...)`。
    -   当 `self.root_path` 是一个 `MagicMock` 时，这些路径操作 (`/`, `.with_suffix()`, `.relative_to()`) 不会返回真实的 `Path` 对象，而是返回**新的 `MagicMock` 对象**。
    -   因此，传递给 `mock_tm.add_write()` 的第一个参数不是一个字符串路径（如 `"src/main.stitcher.yaml"`），而是一个 `MagicMock` 实例。这导致了 `AssertionError`，因为测试断言期望的是一个字符串。

2.  **次要原因: `assert_any_call` 中不稳定的 `MagicMock()`**
    -   在断言 `mock_tm.add_write.assert_any_call("...", MagicMock())` 中，第二个参数 `MagicMock()` 在每次调用时都会创建一个**新的、唯一的 Mock 对象**。
    -   `assert_any_call` 在内部进行相等性比较。一个新的 `MagicMock()` 实例永远不会等于 `add_write` 实际接收到的那个 `MagicMock` 实例。
    -   **解决方案**: 当我们只想验证某个参数被传入，而不关心其具体值时，应该使用 `unittest.mock.ANY`。

### 修复计划

我将修改 `test_pump_executor.py`，使用一个真实的 `Path` 对象（由 `tmp_path` 提供）来代替 `MagicMock`，并使用 `ANY` 来进行更稳健的断言。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
~~~~~
~~~~~python.old
from unittest.mock import create_autospec, MagicMock

import pytest

from stitcher.app.runners.pump.executor import PumpExecutor
from stitcher.spec import (
    DocstringMergerProtocol,
    FingerprintStrategyProtocol,
    LanguageTransformerProtocol,
    ModuleDef,
    FunctionDef,
    ResolutionAction,
    DocstringIR,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.common.transaction import TransactionManager


@pytest.fixture
def mock_doc_manager() -> DocumentManagerProtocol:
    # Configure flatten_module_docs to return a mock IR
    mock = create_autospec(DocumentManagerProtocol, instance=True)
    mock.flatten_module_docs.return_value = {
        "func_a": DocstringIR(summary="Source Doc A")
    }
    return mock


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


@pytest.fixture
def sample_module() -> ModuleDef:
    return ModuleDef(
        file_path="src/main.py", functions=[FunctionDef(name="func_a")]
    )


def test_executor_hydrates_new_doc(executor: PumpExecutor, sample_module: ModuleDef):
    """Test standard pumping of a new docstring without conflicts."""
    mock_tm = create_autospec(TransactionManager, instance=True)

    executor.execute([sample_module], decisions={}, tm=mock_tm, strip=False)

    # Assert YAML file is written to
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", MagicMock())
    # Assert signature file is written to
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", MagicMock())


def test_executor_overwrite_and_strip(
    executor: PumpExecutor,
    sample_module: ModuleDef,
    mock_doc_manager: DocumentManagerProtocol,
):
    """Test HYDRATE_OVERWRITE decision with stripping enabled."""
    mock_tm = create_autospec(TransactionManager, instance=True)
    decisions = {"func_a": ResolutionAction.HYDRATE_OVERWRITE}
    
    # Mock transformer strip call
    executor.transformer.strip.return_value = "stripped content"
    
    # Mock Path.read_text for the source file read in _execute_strip_jobs
    source_path = executor.root_path / "src/main.py"
    source_path.read_text.return_value = "original content"

    executor.execute([sample_module], decisions=decisions, tm=mock_tm, strip=True)
    
    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", MagicMock())
    # Assert signature is written
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", MagicMock())
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()
    mock_tm.add_write.assert_any_call("src/main.py", "stripped content")
~~~~~
~~~~~python.new
from unittest.mock import create_autospec, MagicMock, ANY
from pathlib import Path

import pytest

from stitcher.app.runners.pump.executor import PumpExecutor
from stitcher.spec import (
    DocstringMergerProtocol,
    FingerprintStrategyProtocol,
    LanguageTransformerProtocol,
    ModuleDef,
    FunctionDef,
    ResolutionAction,
    DocstringIR,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.common.transaction import TransactionManager


@pytest.fixture
def mock_doc_manager() -> DocumentManagerProtocol:
    # Configure flatten_module_docs to return a mock IR
    mock = create_autospec(DocumentManagerProtocol, instance=True)
    mock.flatten_module_docs.return_value = {
        "func_a": DocstringIR(summary="Source Doc A")
    }
    mock.dump_data.return_value = "yaml content"
    return mock


@pytest.fixture
def mock_sig_manager(tmp_path: Path) -> SignatureManagerProtocol:
    mock = create_autospec(SignatureManagerProtocol, instance=True)
    # IMPORTANT: Return a real dict to avoid deepcopy issues with mocks.
    mock.load_composite_hashes.return_value = {}
    # Configure path generation to return a concrete Path
    mock.get_signature_path.return_value = (
        tmp_path / ".stitcher/signatures/src/main.json"
    )
    mock.serialize_hashes.return_value = "json content"
    return mock


@pytest.fixture
def executor(
    tmp_path: Path,
    mock_doc_manager: DocumentManagerProtocol,
    mock_sig_manager: SignatureManagerProtocol,
) -> PumpExecutor:
    # Use the real tmp_path instead of a MagicMock for root_path
    return PumpExecutor(
        root_path=tmp_path,
        doc_manager=mock_doc_manager,
        sig_manager=mock_sig_manager,
        transformer=create_autospec(LanguageTransformerProtocol, instance=True),
        merger=create_autospec(DocstringMergerProtocol, instance=True),
        fingerprint_strategy=create_autospec(FingerprintStrategyProtocol, instance=True),
    )


@pytest.fixture
def sample_module() -> ModuleDef:
    return ModuleDef(
        file_path="src/main.py", functions=[FunctionDef(name="func_a")]
    )


def test_executor_hydrates_new_doc(executor: PumpExecutor, sample_module: ModuleDef):
    """Test standard pumping of a new docstring without conflicts."""
    mock_tm = create_autospec(TransactionManager, instance=True)

    executor.execute([sample_module], decisions={}, tm=mock_tm, strip=False)

    # Assert YAML file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert signature file is written to the correct relative path with ANY content
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", ANY)


def test_executor_overwrite_and_strip(
    executor: PumpExecutor,
    sample_module: ModuleDef,
    mock_doc_manager: DocumentManagerProtocol,
):
    """Test HYDRATE_OVERWRITE decision with stripping enabled."""
    mock_tm = create_autospec(TransactionManager, instance=True)
    decisions = {"func_a": ResolutionAction.HYDRATE_OVERWRITE}

    # Mock transformer strip call
    executor.transformer.strip.return_value = "stripped content"

    # We need to mock read_text on the real Path object that will be constructed
    source_path = executor.root_path / "src/main.py"
    # To mock a method on an object we don't own, we can't just assign.
    # We can, however, mock the entire object if needed, but for simplicity,
    # let's assume the transformer is correctly tested elsewhere and focus on tm calls.
    # For strip to work, it needs to read a file. We can create it.
    source_path.parent.mkdir(exist_ok=True)
    source_path.write_text("original content")

    executor.execute([sample_module], decisions=decisions, tm=mock_tm, strip=True)

    # Assert YAML is written
    mock_tm.add_write.assert_any_call("src/main.stitcher.yaml", ANY)
    # Assert signature is written
    mock_tm.add_write.assert_any_call(".stitcher/signatures/src/main.json", ANY)
    # Assert source file is stripped and written back
    executor.transformer.strip.assert_called_once()
    mock_tm.add_write.assert_any_call("src/main.py", "stripped content")
~~~~~

我已经重构了 `test_pump_executor.py` 来解决这些问题。现在，`executor` fixture 使用了由 `tmp_path` 提供的真实 `Path` 对象，并且断言使用了 `unittest.mock.ANY` 来避免不稳定的 Mock 比较。这应该能让所有测试都通过。
