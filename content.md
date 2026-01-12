Of course. Let's proceed with building the Consistency Engine, which will orchestrate the rules we've just created.

## [WIP] feat(analysis): Implement ConsistencyEngine to orchestrate rules

### 用户需求

实施 Phase 1.4：构建一致性引擎 (`ConsistencyEngine`)。
创建一个编排器，负责加载、运行所有一致性检查规则，并聚合它们的分析结果，为 `stitcher-application` 提供一个统一的分析入口。

### 评论

这是将我们零散的规则 (`Rule`) 转化为一个 cohesive (内聚的) 分析能力的关键一步。`ConsistencyEngine` 将扮演 CPU 的角色，执行我们编写的指令（规则）。通过依赖注入的方式提供规则，我们保持了引擎的通用性，未来可以轻松地增删或替换规则集，而无需修改引擎本身。

### 目标

1.  创建 `stitcher.analysis.engines.consistency` 模块。
2.  实现 `ConsistencyEngine` 类，其核心职责是接收 `AnalysisSubject`，遍历运行一组 `AnalysisRule`，并返回一个聚合了所有 `Violation` 的 `FileCheckResult`。
3.  提供一个 `create_consistency_engine` 工厂函数，用于方便地创建带有默认规则集的引擎实例。
4.  为 `ConsistencyEngine` 编写单元测试，验证其编排和聚合逻辑的正确性。

### 基本原理

`ConsistencyEngine` 的设计遵循了“组合优于继承”和“依赖注入”的原则。它本身不包含任何具体的检查逻辑，而是通过其构造函数接收一个规则列表。它的 `analyze` 方法是整个分析流程的核心，它确保了每个规则都被执行，并且所有结果都被统一收集。工厂函数的引入进一步解耦了引擎的使用者（如 `CheckRunner`）与引擎的具体配置细节。

### 标签

#intent/build #flow/ready #priority/high #comp/logic #scope/core #ai/instruct #task/domain/architecture #task/object/analysis-engine #task/action/implement-engine #task/state/continue

---

### Script

#### Acts 1: 创建引擎目录结构

首先，为我们的引擎和相关测试创建目录。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-analysis/src/stitcher/analysis/engines/consistency
mkdir -p packages/stitcher-analysis/tests/unit/engines
touch packages/stitcher-analysis/src/stitcher/analysis/engines/__init__.py
touch packages/stitcher-analysis/src/stitcher/analysis/engines/consistency/__init__.py
~~~~~

#### Acts 2: 实现 `ConsistencyEngine` 及其工厂函数

这是分析引擎的核心实现。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/engines/consistency/engine.py
~~~~~
~~~~~python
from typing import List

from stitcher.app.services import Differ
from stitcher.spec import DifferProtocol
from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import FileCheckResult
from stitcher.analysis.rules.protocols import AnalysisRule
from stitcher.analysis.rules.consistency.content import ContentRule
from stitcher.analysis.rules.consistency.existence import ExistenceRule
from stitcher.analysis.rules.consistency.signature import SignatureRule
from stitcher.analysis.rules.consistency.untracked import UntrackedRule


class ConsistencyEngine:
    """
    Orchestrates the execution of a set of analysis rules against a subject.
    """

    def __init__(self, rules: List[AnalysisRule]):
        self._rules = rules

    def analyze(self, subject: AnalysisSubject) -> FileCheckResult:
        """
        Runs all configured rules against the subject and aggregates the results.
        """
        all_violations = []
        for rule in self._rules:
            violations = rule.check(subject)
            all_violations.extend(violations)

        return FileCheckResult(path=subject.file_path, violations=all_violations)


def create_consistency_engine(
    differ: DifferProtocol | None = None,
) -> ConsistencyEngine:
    """
    Factory function to create a ConsistencyEngine with a default set of rules.
    """
    # If no differ is provided, create a default one.
    # This allows consumers to inject a mock or custom differ if needed.
    effective_differ = differ or Differ()

    default_rules = [
        SignatureRule(differ=effective_differ),
        ContentRule(differ=effective_differ),
        ExistenceRule(),
        UntrackedRule(),
    ]
    return ConsistencyEngine(rules=default_rules)
~~~~~

#### Acts 3: 暴露引擎

通过 `__init__.py` 文件暴露 `ConsistencyEngine` 和工厂函数。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/engines/consistency/__init__.py
~~~~~
~~~~~python
from .engine import ConsistencyEngine, create_consistency_engine

__all__ = ["ConsistencyEngine", "create_consistency_engine"]
~~~~~

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/engines/__init__.py
~~~~~
~~~~~python
from .consistency import ConsistencyEngine, create_consistency_engine

__all__ = ["ConsistencyEngine", "create_consistency_engine"]
~~~~~

#### Acts 4: 编写 `ConsistencyEngine` 的单元测试

验证引擎的编排和结果聚合逻辑是否正确。

~~~~~act
write_file
packages/stitcher-analysis/tests/unit/engines/test_consistency_engine.py
~~~~~
~~~~~python
from unittest.mock import Mock
from needle.pointer import L

from stitcher.analysis.schema import Violation
from stitcher.analysis.engines.consistency import ConsistencyEngine


def test_consistency_engine_aggregates_violations_from_all_rules():
    # 1. Setup
    mock_subject = Mock()
    mock_subject.file_path = "path/to/file.py"

    violation1 = Violation(kind=L.rule1.error, fqn="func1")
    violation2 = Violation(kind=L.rule2.warning, fqn="func2")
    violation3 = Violation(kind=L.rule2.info, fqn="class1")

    mock_rule1 = Mock()
    mock_rule1.check.return_value = [violation1]

    mock_rule2 = Mock()
    mock_rule2.check.return_value = [violation2, violation3]
    
    mock_rule3 = Mock()
    mock_rule3.check.return_value = [] # A rule that finds nothing

    # 2. Execute
    engine = ConsistencyEngine(rules=[mock_rule1, mock_rule2, mock_rule3])
    result = engine.analyze(mock_subject)

    # 3. Assert
    # All rules should have been called once with the subject
    mock_rule1.check.assert_called_once_with(mock_subject)
    mock_rule2.check.assert_called_once_with(mock_subject)
    mock_rule3.check.assert_called_once_with(mock_subject)

    # The result should contain all violations from all rules
    assert result.path == "path/to/file.py"
    assert len(result.violations) == 3
    assert violation1 in result.violations
    assert violation2 in result.violations
    assert violation3 in result.violations
~~~~~

### 下一步建议

我们已经成功构建了分析引擎。现在，`stitcher-analysis` 包已经具备了完整的、独立的“一致性检查”能力。

接下来的 **Phase 1.6: 集成与替换** 是整个重构工作的收官阶段。我们需要修改 `stitcher-application` 中的 `CheckRunner`，让它放弃旧的 `CheckAnalyzer`，转而调用我们新创建的 `ConsistencyEngine`。

这将会是激动人心的一步，因为它将正式启用我们的新架构。如果你准备好了，我将生成执行此集成步骤的计划。
