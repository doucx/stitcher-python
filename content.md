You are absolutely correct. I missed this during the cleanup. The `compute_fingerprint` method was removed from the `FunctionDef` model, but the unit test `test_fingerprint_stability`, which was specifically designed to test that algorithm, was not updated to reflect this change.

This is the last piece of fallout from the refactoring.

## [WIP] fix: Adapt fingerprint stability test to new strategy pattern

### 错误分析
1.  **根本原因**: `AttributeError: 'FunctionDef' object has no attribute 'compute_fingerprint'`.
2.  **具体分析**: The test `test_fingerprint_stability` was correctly testing the stability of the fingerprinting algorithm. However, during the refactoring, this algorithm was moved from the `FunctionDef` model into the `PythonFingerprintStrategy` class. The test was not updated and is still trying to call the old, now-deleted method.
3.  **解决方案**: The test's purpose remains valid and important. We must refactor the test itself to instantiate a `PythonFingerprintStrategy` and use its `compute()` method to get the fingerprint hash for comparison.

### 用户需求
Adapt the unit test `test_fingerprint_stability` to correctly test the fingerprinting algorithm in its new location within the `PythonFingerprintStrategy`.

### 评论
This is a crucial fix. This unit test is the primary safeguard ensuring that our change-detection mechanism is deterministic. By adapting it to the new architecture, we preserve this safety net.

### 目标
1.  In `test_fingerprint_stability`, instantiate `PythonFingerprintStrategy`.
2.  Replace all calls to `func.compute_fingerprint()` with `strategy.compute(func)`.
3.  Update the assertions to extract the specific `current_code_structure_hash` from the `Fingerprint` object returned by the strategy.

### 基本原理
Unit tests must evolve with the code they are intended to cover. The responsibility for fingerprinting now lies with the Strategy, so the test must target the Strategy to be effective.

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/architecture #task/object/test-suite #task/action/fix-regressions #task/state/end

---

### Script

#### Acts 1: Refactor test_fingerprint_stability
We will rewrite the test to use the `PythonFingerprintStrategy`.

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_signature_manager.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
def test_fingerprint_stability():
    # Arrange: The object under test is now the strategy
    strategy = PythonFingerprintStrategy()
    hash_key = "current_code_structure_hash"

    # 1. Base case
    arg_a = Argument(
        name="a", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="int"
    )
    func1 = create_func(name="my_func", args=[arg_a], ret="str")
    fp1 = strategy.compute(func1)[hash_key]

    # 2. Identical function should have identical fingerprint
    func2 = create_func(name="my_func", args=[arg_a], ret="str")
    fp2 = strategy.compute(func2)[hash_key]
    assert fp1 == fp2

    # 3. Change in parameter name -> Different
    arg_b = Argument(
        name="b", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="int"
    )
    func3 = create_func(name="my_func", args=[arg_b], ret="str")
    assert fp1 != strategy.compute(func3)[hash_key]

    # 4. Change in annotation -> Different
    arg_a_str = Argument(
        name="a", kind=ArgumentKind.POSITIONAL_OR_KEYWORD, annotation="str"
    )
    func4 = create_func(name="my_func", args=[arg_a_str], ret="str")
    assert fp1 != strategy.compute(func4)[hash_key]

    # 5. Change in return type -> Different
    func5 = create_func(name="my_func", args=[arg_a], ret="int")
    assert fp1 != strategy.compute(func5)[hash_key]
~~~~~

### 下一步建议
After this final fix, the entire test suite should pass. This signals the successful completion of the architectural refactoring. I will now generate the final `[COMMIT]` plan to wrap up this significant body of work.
