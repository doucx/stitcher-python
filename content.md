我分析了错误日志。这些测试失败是由于上一轮重构（将 `SignatureManager` 解耦）引入的 API 不兼容导致的，主要涉及构造函数的参数变化和方法签名的更新。

我将生成一个计划来修复这些测试，使其与新的 API 保持一致。

## [WIP] fix(tests): 适配 SignatureManager 解耦后的测试用例

### 错误分析
1.  **`test_execution_planner.py`**: `PumpRunner` 的构造函数增加了 `fingerprint_strategy` 参数，但测试 Fixture 未提供，导致 `TypeError`。
2.  **`test_signature_manager.py`**: `SignatureManager` 的构造函数移除了 `fingerprint_strategy` 参数，但测试仍在传递它。此外，其 `save/load` 方法的参数已从 `ModuleDef` 对象变更为 `file_path` 字符串，测试调用未更新。
3.  **`test_signature_extraction.py`**: 此测试的核心目标是验证指纹计算逻辑。该逻辑已从 `SignatureManager` 移至 `PythonFingerprintStrategy`。因此，测试本身需要重构，直接测试 `PythonFingerprintStrategy`，而不是通过一个不再包含该逻辑的 `SignatureManager`。

### 用户需求
修复因 `SignatureManager` 重构而损坏的所有单元测试。

### 评论
这是一次标准的“重构后修复测试”操作。修复这些测试不仅能使 CI 恢复绿灯，更重要的是，它能验证我们的重构是正确且完整的，确保新旧逻辑在行为上保持一致。特别是对 `test_signature_extraction.py` 的重写，将使测试目标更精确。

### 目标
1.  更新 `test_execution_planner.py` 中的 Fixture，为 `PumpRunner` 注入 Mock 的 `fingerprint_strategy`。
2.  更新 `test_signature_manager.py`，移除 `SignatureManager` 构造函数中的无效参数，并修改方法调用以传递 `file_path`。
3.  重写 `test_signature_extraction.py`，使其直接测试 `PythonFingerprintStrategy` 的 `compute` 方法。

### 基本原理
通过精确地调整测试代码以匹配新的类构造函数和方法签名，我们可以快速修复这些类型错误。对于逻辑已经转移的测试，直接重写测试用例以对准新的责任承担者（`PythonFingerprintStrategy`），是保持测试覆盖率和意图清晰的最佳实践。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/app #task/object/stitcher-app #task/action/integrate-index #task/state/continue

---

### Script

#### Acts 1: 修复 `test_execution_planner.py`

为 `PumpRunner` 构造函数提供缺失的 `fingerprint_strategy` Mock。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_execution_planner.py
~~~~~
~~~~~python.old
@pytest.fixture
def runner(tmp_path) -> PumpRunner:
    """一个用于调用内部方法的PumpRunner实例。"""
    # _generate_execution_plan 仅依赖 doc_manager
    doc_manager = DocumentManager(root_path=tmp_path)
    return PumpRunner(
        root_path=tmp_path,
        doc_manager=doc_manager,
        sig_manager=MagicMock(),
        transformer=MagicMock(),
        differ=MagicMock(spec=Differ),
        merger=MagicMock(spec=DocstringMerger),
        interaction_handler=None,
    )
~~~~~
~~~~~python.new
@pytest.fixture
def runner(tmp_path) -> PumpRunner:
    """一个用于调用内部方法的PumpRunner实例。"""
    # _generate_execution_plan 仅依赖 doc_manager
    doc_manager = DocumentManager(root_path=tmp_path)
    return PumpRunner(
        root_path=tmp_path,
        doc_manager=doc_manager,
        sig_manager=MagicMock(),
        transformer=MagicMock(),
        differ=MagicMock(spec=Differ),
        merger=MagicMock(spec=DocstringMerger),
        interaction_handler=None,
        fingerprint_strategy=MagicMock(),
    )
~~~~~

#### Acts 2: 重写 `test_signature_extraction.py`

此测试的目标是验证指纹计算，该职责已移至 `PythonFingerprintStrategy`。我们将重写此测试以直接验证新策略。

~~~~~act
write_file
packages/stitcher-application/tests/unit/test_signature_extraction.py
~~~~~
~~~~~python
from stitcher.spec import Argument, ArgumentKind, FunctionDef
from stitcher.adapter.python import PythonFingerprintStrategy


def test_extract_signature_text_simple():
    """验证简单函数的签名文本是否正确生成。"""
    # Arrange
    func = FunctionDef(
        name="my_func",
        args=[
            Argument(
                name="a",
                kind=ArgumentKind.POSITIONAL_OR_KEYWORD,
                annotation="int",
            ),
            Argument(
                name="b",
                kind=ArgumentKind.POSITIONAL_OR_KEYWORD,
                annotation="str",
                default="'default'",
            ),
        ],
        return_annotation="bool",
    )
    strategy = PythonFingerprintStrategy()

    # Act
    fingerprint = strategy.compute(func)

    # Assert
    expected = "def my_func(a: int, b: str = 'default') -> bool:"
    assert fingerprint["current_code_signature_text"] == expected


def test_extract_signature_text_async():
    """验证异步函数的签名文本是否正确生成。"""
    # Arrange
    func = FunctionDef(
        name="run",
        is_async=True,
        args=[],
        return_annotation="None",
    )
    strategy = PythonFingerprintStrategy()

    # Act
    fingerprint = strategy.compute(func)

    # Assert
    expected = "async def run() -> None:"
    assert fingerprint["current_code_signature_text"] == expected
~~~~~

#### Acts 3: 修复 `test_signature_manager.py`

更新 `SignatureManager` 的实例化和方法调用。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_signature_manager.py
~~~~~
~~~~~python.old
def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(
        root_path=tmp_path, fingerprint_strategy=PythonFingerprintStrategy()
    )
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])
~~~~~
~~~~~python.new
def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(root_path=tmp_path)
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_signature_manager.py
~~~~~
~~~~~python.old
    }

    # Act: Save
    manager.save_composite_hashes(module, hashes_to_save)

    # Assert: File exists and has correct structure
    sig_path = tmp_path / ".stitcher/signatures/src/main.json"
~~~~~
~~~~~python.new
    }

    # Act: Save
    manager.save_composite_hashes(module.file_path, hashes_to_save)

    # Assert: File exists and has correct structure
    sig_path = tmp_path / ".stitcher/signatures/src/main.json"
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_signature_manager.py
~~~~~
~~~~~python.old
        assert "baseline_yaml_content_hash" not in data["bar"]

    # Act: Load
    loaded = manager.load_composite_hashes(module)
    assert loaded == hashes_to_save
~~~~~
~~~~~python.new
        assert "baseline_yaml_content_hash" not in data["bar"]

    # Act: Load
    loaded = manager.load_composite_hashes(module.file_path)
    assert loaded == hashes_to_save
~~~~~

### 下一步建议
测试已修复，CI 应该会恢复正常。我们现在可以安全地进行下一步的重构了：

**将 `CheckRunner` 改造为 "Query-First" 模式**。

这将是整个架构升级中最核心、价值最高的一步，因为它将彻底消除 `check` 命令的性能瓶颈。
