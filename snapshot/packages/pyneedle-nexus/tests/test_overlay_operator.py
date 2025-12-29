from needle.nexus import OverlayOperator
from needle.operators import DictOperator


def test_overlay_priority_and_fallback():
    # Arrange
    # Level 1: User Overrides (High Priority)
    user_op = DictOperator(
        {
            "app.title": "User Title",
            # "app.version" is missing here
        }
    )

    # Level 2: System Defaults (Low Priority)
    system_op = DictOperator(
        {"app.title": "System Title", "app.version": "1.0.0", "sys.core": "CoreLib"}
    )

    # Compose them: user first
    overlay = OverlayOperator([user_op, system_op])

    # Act & Assert

    # 1. Shadowing: User value should win
    assert overlay("app.title") == "User Title"

    # 2. Fallback: Missing in user, found in system
    assert overlay("app.version") == "1.0.0"

    # 3. Deep Fallback
    assert overlay("sys.core") == "CoreLib"

    # 4. Missing: Not in either
    assert overlay("unknown.key") is None


def test_overlay_returns_first_match_strictly():
    # If the first operator returns a value (even empty string), it wins.
    # It should only fall back on None.

    op1 = DictOperator({"key": ""})  # Empty string
    op2 = DictOperator({"key": "fallback"})

    overlay = OverlayOperator([op1, op2])

    assert overlay("key") == ""
