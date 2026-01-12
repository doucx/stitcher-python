## [WIP] 我将修改 `test_analyzer.py` 文件，将这个错误的测试用例替换为两个正确、独立的测试用例，分别验证**详细未追踪警告**和**简单未追踪警告**这两种情况。

分析完全正确。这个 `AssertionError` 再次暴露了我之前测试中的一个逻辑缺陷。

### 错误分析

我为 `test_analyzer_untracked_file_warning` 编写的测试用例旨在验证当 `.stitcher.yaml` 文件不存在时，系统会发出一个**简单**的 `untracked` 警告。

然而，我为其提供的 `SymbolState` 输入数据同时满足了两个条件：
1.  文件是**未追踪的**（因为我 Mock 了 `Path.exists()` 返回 `False`）。
2.  文件内包含一个**未记录的公开 API**（`source_doc_content` 为 `None` 且 `exists_in_yaml` 为 `False`）。

`CheckAnalyzer` 的实现逻辑是：如果一个文件是未追踪的，它会**优先**检查其中是否有具体缺失文档的 API。如果找到，它会发出一个更具信息量的**详细**警告（`untracked_detailed`），列出具体缺失的符号。只有当一个未追踪的文件**所有**公开 API 都已经有了文档字符串时（例如，一个等待 `pump` 的新文件），它才会回退到发出那个简单的 `untracked: ["all"]` 警告。

因此，我的测试断言是错误的。对于我提供的输入，分析器实际上正确地输出了 `untracked_detailed` 警告，而不是我所期望的 `untracked` 警告。测试失败是因为我的断言没有正确反映被测代码的智能行为。

### 修复计划

我将修改 `test_analyzer.py` 文件，将这个错误的测试用例替换为两个正确、独立的测试用例，分别验证**详细未追踪警告**和**简单未追踪警告**这两种情况。

~~~~~act
patch_file
packages/stitcher-application/tests/unit/runners/check/test_analyzer.py
~~~~~
~~~~~python.old
def test_analyzer_untracked_file_warning(analyzer: CheckAnalyzer, monkeypatch):
    """Verify warning for a documentable but untracked file."""
    # Mock filesystem to simulate an untracked file
    monkeypatch.setattr(Path, "exists", lambda self: False)

    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=False,
        source_doc_content=None,
        signature_hash=None,
        baseline_signature_hash=None,
        yaml_content_hash=None,
        baseline_yaml_content_hash=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state}, is_doc=True)

    result, conflicts = analyzer.analyze_subject(subject)

    assert result.warning_count == 2  # missing and untracked
    assert "missing" in result.warnings
    assert result.warnings["untracked"] == ["all"]
    assert not conflicts
~~~~~
~~~~~python.new
def test_analyzer_untracked_with_details(analyzer: CheckAnalyzer, monkeypatch):
    """
    Verify 'untracked_detailed' warning for an untracked file that has
    undocumented public APIs.
    """
    monkeypatch.setattr(Path, "exists", lambda self: False)

    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=False,
        source_doc_content=None,  # This makes it undocumented
        signature_hash=None,
        baseline_signature_hash=None,
        yaml_content_hash=None,
        baseline_yaml_content_hash=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state}, is_doc=True)

    result, conflicts = analyzer.analyze_subject(subject)

    # The analyzer correctly identifies 'missing' first, then adds 'untracked_detailed'.
    assert result.warning_count == 2
    assert "missing" in result.warnings
    assert "untracked_detailed" in result.warnings
    assert result.warnings["untracked_detailed"] == ["func"]
    assert "untracked" not in result.warnings  # Should not have the simple warning
    assert not conflicts


def test_analyzer_untracked_simple(analyzer: CheckAnalyzer, monkeypatch):
    """
    Verify simple 'untracked' warning for an untracked file where all
    public APIs are already documented in the source code.
    """
    monkeypatch.setattr(Path, "exists", lambda self: False)

    state = SymbolState(
        fqn="func",
        is_public=True,
        exists_in_code=True,
        exists_in_yaml=False,
        source_doc_content="I have a docstring.",  # This makes it documented
        signature_hash=None,
        baseline_signature_hash=None,
        yaml_content_hash=None,
        baseline_yaml_content_hash=None,
        signature_text=None,
        yaml_doc_ir=None,
        baseline_signature_text=None,
    )
    subject = FakeCheckSubject("src/main.py", {"func": state}, is_doc=True)

    result, conflicts = analyzer.analyze_subject(subject)

    # In this case, there's no 'missing' doc, only 'pending' and 'untracked'.
    assert result.error_count == 1  # pending
    assert result.warning_count == 1  # untracked
    assert result.errors["pending"] == ["func"]
    assert result.warnings["untracked"] == ["all"]
    assert "untracked_detailed" not in result.warnings
    assert not conflicts
~~~~~

这个补丁修复了测试逻辑，使其能够正确地验证 `CheckAnalyzer` 在两种不同“未追踪”场景下的行为。现在测试套件应该可以成功通过了。
