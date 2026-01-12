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
    mock_rule3.check.return_value = []  # A rule that finds nothing

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
