You are absolutely correct. My previous refactoring successfully decoupled the application logic but left the test suite behind, causing these import errors. The tests are still trying to import `intent` from its old location within the `engine` package.

This is an expected and easily correctable part of the refactoring process. I will now generate a plan to update the test files to use the new, correct import path for the `intent` module.

## [WIP] test(refactor): Update test imports after decoupling `intent` module

### 错误分析

The `pytest` and `pyright` failures are due to `ModuleNotFoundError`. The test files `test_planner.py` and `test_rename_symbol_operation.py` are still using the old import path `stitcher.refactor.engine.intent`, which was removed in the previous step when `intent.py` was moved to `stitcher.refactor.intent` to resolve circular dependencies.

### 用户需求

Update the test files in `stitcher-refactor` to use the correct import paths for the refactored `intent` module, thereby fixing the test suite.

### 评论

Fixing tests immediately after a refactoring is a crucial step in maintaining a healthy codebase. This ensures that our safety net is restored and confirms that the refactoring did not break the intended behavior, only its internal structure. This is a routine follow-up action.

### 目标

1.  Modify `packages/stitcher-refactor/tests/unit/engine/test_planner.py` to import `RefactorIntent` from `stitcher.refactor.intent`.
2.  Modify `packages/stitcher-refactor/tests/unit/operations/test_rename_symbol_operation.py` to import `RenameIntent` from `stitcher.refactor.intent`.

### 基本原理

The solution is a straightforward path correction. By changing the import statements in the affected test files from `from stitcher.refactor.engine.intent import ...` to `from stitcher.refactor.intent import ...`, we align the tests with the new, decoupled module structure. This will resolve the `ModuleNotFoundError` and allow the tests to run successfully.

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #comp/refactor #scope/dx #ai/instruct #task/state/continue

---

### Script

#### Acts 1: Update test files to use the new intent path

I will now patch the two failing test files to use the correct import location for the `intent` module.

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/engine/test_planner.py
~~~~~
~~~~~python.old
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.intent import RefactorIntent
from stitcher.workspace import Workspace
~~~~~
~~~~~python.new
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.intent import RefactorIntent
from stitcher.workspace import Workspace
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/operations/test_rename_symbol_operation.py
~~~~~
~~~~~python.old
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.analysis.semantic import SemanticGraph


from stitcher.refactor.engine.intent import RenameIntent
~~~~~
~~~~~python.new
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.analysis.semantic import SemanticGraph


from stitcher.refactor.intent import RenameIntent
~~~~~

### 下一步建议

Now that the tests have been updated to reflect the new architecture, the next logical step is to run the test suite again to confirm that all import errors are resolved and the system is stable. If the tests pass, we can mark this refactoring task as complete.
