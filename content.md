好的，我来处理这些过时的测试。

测试失败的根本原因是我在之前的步骤中重构了 `SignatureManager`，将 `save_signatures` 和 `check_signatures` 等方法替换为了更能反映新数据模型的 `save_hashes` 和 `load_hashes`，并且将校验逻辑上移到了 `StitcherApp`。测试用例没有随之更新，导致了 `AttributeError`。

我将更新 `test_signature_manager.py` 文件，使其与当前的 `SignatureManager` 实现保持一致。这包括：
1.  重写 `test_manager_save_and_load` 测试，使其验证新的复合哈希结构（`signature_hash` 和 `document_hash`）的存取。
2.  删除 `test_manager_check_detects_mismatch` 测试，因为它所测试的 `check_signatures` 方法已经不存在。这部分逻辑现在是 `StitcherApp` 的职责，将在更高层级的集成测试中覆盖。

## [WIP] fix: 更新 SignatureManager 的测试用例以匹配重构后的 API

### 错误分析
`AttributeError: 'SignatureManager' object has no attribute 'save_signatures'` 表明测试用例正在调用一个已经被重构移除或重命名的旧方法。这是因为 `SignatureManager` 的 API 已经更新，以支持新的“签名-文档”复合哈希模型，但相关的测试文件 `test_signature_manager.py` 尚未同步更新。

### 用户需求
修复 `test_signature_manager.py` 中的测试失败，使其与 `SignatureManager` 的新 API（`save_hashes`, `load_hashes` 等）保持一致。

### 评论
修复这些过时的测试是保证代码库健康度的必要步骤。通过使测试与实现同步，我们可以确保 `SignatureManager` 的核心持久化逻辑在新架构下依然是正确和可靠的。

### 目标
1.  打开 `packages/stitcher-application/tests/test_signature_manager.py` 文件。
2.  将 `test_manager_save_and_load` 重命名并重写为 `test_manager_save_and_load_composite_hashes`，以测试新的数据结构。
3.  完全移除 `test_manager_check_detects_mismatch` 测试函数，因为它已过时。
4.  保留 `test_fingerprint_stability`，因为它测试的是 `FunctionDef` 的行为，仍然有效。

### 基本原理
由于 `SignatureManager` 的职责已经收缩为纯粹的 I/O 操作（保存和加载哈希数据），其单元测试也应相应地简化。我们将不再测试“校验”逻辑（因为它已移走），而是专注于验证 `save_hashes` 和 `load_hashes` 能否正确地对新的复合数据结构进行序列化和反序列化。使用 `write_file` 可以一次性完成对测试文件的重写和清理。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/validation #task/object/state-machine #task/state/continue

---
### Script

#### Acts 1: 更新 SignatureManager 的测试文件

我们将重写 `test_signature_manager.py` 文件，使其与重构后的 `SignatureManager` API 同步。

~~~~~act
write_file
packages/stitcher-application/tests/test_signature_manager.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.spec import ModuleDef, FunctionDef, Argument, ArgumentKind
from stitcher.app.services import SignatureManager


def create_func(name="func", args=None, ret=None):
    return FunctionDef(
        name=name,
        args=args or [],
        return_annotation=ret,
    )


def test_fingerprint_stability():
    # 1. Base case
    arg_a = Argument(
        name="a", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="int"
    )
    func1 = create_func(name="my_func", args=[arg_a], ret="str")
    fp1 = func1.compute_fingerprint()

    # 2. Identical function should have identical fingerprint
    func2 = create_func(name="my_func", args=[arg_a], ret="str")
    fp2 = func2.compute_fingerprint()
    assert fp1 == fp2

    # 3. Change in parameter name -> Different
    arg_b = Argument(
        name="b", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="int"
    )
    func3 = create_func(name="my_func", args=[arg_b], ret="str")
    assert fp1 != func3.compute_fingerprint()

    # 4. Change in annotation -> Different
    arg_a_str = Argument(
        name="a", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="str"
    )
    func4 = create_func(name="my_func", args=[arg_a_str], ret="str")
    assert fp1 != func4.compute_fingerprint()

    # 5. Change in return type -> Different
    func5 = create_func(name="my_func", args=[arg_a], ret="int")
    assert fp1 != func5.compute_fingerprint()


def test_manager_save_and_load_composite_hashes(tmp_path: Path):
    # Arrange
    manager = SignatureManager(root_path=tmp_path)
    module = ModuleDef(file_path="src/main.py", functions=[create_func(name="foo")])

    hashes_to_save = {
        "foo": {"signature_hash": "abc", "document_hash": "def"},
        "bar": {"signature_hash": "123", "document_hash": None},
    }

    # Act: Save
    manager.save_hashes(module, hashes_to_save)

    # Assert: File exists and has correct structure
    sig_path = tmp_path / ".stitcher/signatures/src/main.json"
    assert sig_path.exists()

    with sig_path.open("r") as f:
        data = json.load(f)
        assert data["foo"]["signature_hash"] == "abc"
        assert data["foo"]["document_hash"] == "def"
        assert data["bar"]["signature_hash"] == "123"
        assert data["bar"]["document_hash"] is None

    # Act: Load
    loaded = manager.load_hashes(module)
    assert loaded == hashes_to_save


# The test 'test_manager_check_detects_mismatch' was removed because
# the 'check_signatures' method was removed from SignatureManager.
# This logic is now handled in StitcherApp and will be tested at the integration level.
~~~~~
