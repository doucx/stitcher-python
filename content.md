非常感谢您的澄清。您指出的点非常关键：**我们不应使用不完备的启发式逻辑（Guessing），而应要求上游（Check Command/Index）提供明确的事实。**

这也是 **HFEA (高保真工程)** 原则的体现：系统状态必须建立在确定性的事实之上。

### 修正方案

1.  **协议变更**: 修改 `AnalysisSubject` 协议，增加 `is_tracked` 属性。这意味着“是否存在对应的 YAML 文件”这一事实，应由数据提供者（Adapter）明确告知分析引擎。
2.  **规则修正**: 重写 `UntrackedRule`。不再猜测，而是基于 `subject.is_tracked == False` 这一事实。
3.  **行为对齐**: 您提到“不需要文件级别的 untracked，我们需要的是符号级别的”。
    *   在现有逻辑（Legacy `analyzer.py`）中，`Untracked` 确实是一个文件级状态，用于提示用户运行 `stitcher init`。
    *   为了在 **Phase 1 (Extract)** 阶段保持行为一致性（不丢失功能），我建议保留 `UntrackedRule`，但将其逻辑严格限制为：**“当文件未初始化（无 YAML）且包含可文档化符号时，提示文件级警告”**。
    *   具体的符号级缺失（Missing/Pending）由 `ExistenceRule` 继续负责。

我们将执行以下操作来修复这个问题。

## [WIP] fix(analysis): Explicit tracking state in AnalysisSubject

### 用户需求

修正 `UntrackedRule` 的实现逻辑。
1.  放弃基于“YAML 内容是否为空”的启发式判断。
2.  在 `AnalysisSubject` 协议中显式增加 `is_tracked` 属性。
3.  更新规则以利用此属性。

### 评论

这是一个必要的修正。它消除了分析引擎中的不确定性，将 IO 状态（文件是否存在）的获取责任归还给了负责 IO 的层级（Adapter），分析引擎只负责基于事实进行判断。

### 目标

1.  修改 `stitcher/analysis/protocols/subject.py`，添加 `is_tracked` 属性。
2.  重写 `stitcher/analysis/rules/consistency/untracked.py`。
3.  更新 `tests/unit/rules/consistency/test_rules.py` 以适配新协议。

### 基本原理

通过协议明确契约，确保所有进入分析引擎的数据都是完备的。

### 标签

#intent/refine #intent/fix #flow/ready #priority/high #comp/interfaces #scope/core #ai/instruct #task/domain/architecture #task/object/analysis-engine #task/action/fix-rule #task/state/continue

---

### Script

#### Acts 1: 更新 `AnalysisSubject` 协议

添加 `is_tracked` 属性。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/protocols/subject.py
~~~~~
~~~~~python.old
    @property
    def file_path(self) -> str:
        """The relative path of the file being analyzed."""
        ...

    def is_documentable(self) -> bool:
~~~~~
~~~~~python.new
    @property
    def file_path(self) -> str:
        """The relative path of the file being analyzed."""
        ...

    @property
    def is_tracked(self) -> bool:
        """
        Whether the file is currently tracked by Stitcher
        (i.e., has a corresponding .stitcher.yaml file).
        """
        ...

    def is_documentable(self) -> bool:
~~~~~

#### Acts 2: 重写 `UntrackedRule`

使用明确的 `is_tracked` 属性。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/rules/consistency/untracked.py
~~~~~
~~~~~python
from dataclasses import dataclass
from typing import List

from needle.pointer import L
from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import Violation
from stitcher.analysis.rules.protocols import AnalysisRule


@dataclass
class UntrackedRule(AnalysisRule):
    def check(self, subject: AnalysisSubject) -> List[Violation]:
        # 1. If explicitly tracked, this rule does not apply.
        if subject.is_tracked:
            return []

        # 2. If not tracked, but has nothing to document, we don't care.
        if not subject.is_documentable():
            return []

        # 3. It is untracked and documentable.
        # We now identify which specific public symbols are missing documentation.
        states = subject.get_all_symbol_states()
        undocumented_keys = [
            s.fqn
            for s in states.values()
            if s.is_public
            and s.fqn != "__doc__"
            and not s.source_doc_content
        ]

        # Mimic legacy behavior:
        # If there are specific symbols needing docs, give a detailed warning.
        # Otherwise (e.g. only __doc__ or all have docs but just no YAML), generic warning.
        if undocumented_keys:
            return [
                Violation(
                    kind=L.check.file.untracked_with_details,
                    fqn=subject.file_path,
                    context={"count": len(undocumented_keys), "keys": undocumented_keys}
                )
            ]
        else:
            return [
                Violation(
                    kind=L.check.file.untracked,
                    fqn=subject.file_path
                )
            ]
~~~~~

#### Acts 3: 更新测试

Mock 对象需要增加 `is_tracked` 属性。

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/rules/consistency/test_rules.py
~~~~~
~~~~~python.old
@pytest.fixture
def mock_subject():
    subject = Mock()
    subject.file_path = "test.py"
    return subject
~~~~~
~~~~~python.new
@pytest.fixture
def mock_subject():
    subject = Mock()
    subject.file_path = "test.py"
    subject.is_tracked = True  # Default to tracked
    return subject
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/tests/unit/rules/consistency/test_rules.py
~~~~~
~~~~~python.old
def test_untracked_rule_untracked_file(mock_subject):
    # Setup: No symbols exist in YAML
    state = create_state(exists_in_yaml=False)
    mock_subject.get_all_symbol_states.return_value = {"test.func": state}
    mock_subject.is_documentable.return_value = True

    rule = UntrackedRule()
    # Since test.func is public and missing doc (create_state default has doc, let's remove it)
    state.source_doc_content = None
    
    violations = rule.check(mock_subject)
    
    # Should report untracked_with_details because we have an undocumented public symbol
    assert len(violations) == 1
    assert violations[0].kind == L.check.file.untracked_with_details
    assert violations[0].fqn == "test.py"
~~~~~
~~~~~python.new
def test_untracked_rule_untracked_file(mock_subject):
    # Setup: File is explicitly untracked
    mock_subject.is_tracked = False
    
    state = create_state(exists_in_yaml=False)
    # Ensure no source doc so it triggers 'untracked_with_details' logic
    state.source_doc_content = None
    
    mock_subject.get_all_symbol_states.return_value = {"test.func": state}
    mock_subject.is_documentable.return_value = True

    rule = UntrackedRule()
    violations = rule.check(mock_subject)
    
    assert len(violations) == 1
    assert violations[0].kind == L.check.file.untracked_with_details
    assert violations[0].fqn == "test.py"


def test_untracked_rule_tracked_file_ignored(mock_subject):
    # Setup: File IS tracked
    mock_subject.is_tracked = True
    mock_subject.is_documentable.return_value = True
    
    rule = UntrackedRule()
    violations = rule.check(mock_subject)
    assert len(violations) == 0
~~~~~

### 下一步建议

现在规则定义已经完善且基于明确的协议。

接下来的步骤是 **Phase 1.4: 构建一致性引擎 (Build Consistency Engine)**。
我们需要在 `stitcher.analysis.engines.consistency` 中实现 `ConsistencyEngine` 类。这个类将负责：
1.  接受 `AnalysisSubject`。
2.  实例化并运行所有已定义的规则（`SignatureRule`, `ContentRule` 等）。
3.  聚合所有规则产生的 `Violation`。
4.  构造并返回 `FileCheckResult`。

这个引擎将是 `CheckRunner` 调用分析层的唯一入口。
