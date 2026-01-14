You are absolutely correct. My apologies. The previous refactoring was incomplete and failed to account for the impact on the test suite and helper utilities, which is a direct violation of the "Regression Driven Development" axiom. The errors you've provided are the direct result of this oversight.

The test suite is the safety net for the architecture, and breaking it means the refactoring is not truly complete. I will now generate a plan to fix these import errors and bring the test suite back into alignment with the new, de-coupled architecture.

## [WIP] fix(imports): Update test suite and helpers to reflect service layer refactoring

### 错误分析

The `ImportError` and `pyright` failures are a direct and expected consequence of the previous architectural changes. My last plan correctly identified and broke the circular dependencies in the application code but failed to update the modules that depend on those original structures—namely, the test files and shared test utilities.

The errors can be broken down into two root causes:

1.  **Service Layer Move (`Import "stitcher.app.services" could not be resolved`)**:
    *   I moved the `services` directory from `packages/stitcher-application/src/stitcher/app/services` to `packages/stitcher-application/src/stitcher/services`.
    *   All test files within `packages/stitcher-application/tests/` that relied on these services via `from stitcher.app.services import ...` are now pointing to a non-existent path. They must be updated to import from the new top-level `stitcher.services` package.

2.  **`__init__.py` Cleanup (`"StitcherApp" is unknown import symbol`)**:
    *   I intentionally emptied `stitcher/app/__init__.py` and `stitcher/cli/__init__.py` to break the initialization-time import cycles.
    *   This means that helper modules like `stitcher-test-utils/src/stitcher/test_utils/helpers.py` and `stitcher-cli/src/stitcher/cli/factories.py` can no longer use the convenient `from stitcher.app import StitcherApp` shortcut.
    *   They must now use the explicit, direct import path: `from stitcher.app.core import StitcherApp`.

### 用户需求

Fix the `ImportError` and `pyright` errors introduced by the previous architectural refactoring.

### 評論

This is a critical and necessary follow-up. A refactoring is only successful if the system's verification mechanisms (tests and static analysis) are also updated to reflect the new design. This plan completes the previous work by ensuring the entire codebase, including its test harness, is consistent with the improved, de-coupled architecture. This directly supports the "Regression Driven Development" principle, ensuring large-scale changes are validated.

### 目标

1.  Update all import statements in the `stitcher-application` test suite to point from `stitcher.app.services` to the new `stitcher.services`.
2.  Update `stitcher-test-utils` and `stitcher-cli` to use the direct import path `from stitcher.app.core import StitcherApp` instead of the now-defunct `from stitcher.app import StitcherApp`.
3.  Bring the project back to a state where both `pytest` and `pyright` pass successfully.

### 基本原理

The principle is simple: consistency. The test code must mirror the dependency structure of the application code it is testing. When the application's import paths change, the tests' import paths must change in lockstep. This plan systematically identifies every location where the old, incorrect import paths are used and replaces them with the new, correct ones.

### 标签

#intent/fix #flow/ready #priority/critical #comp/tests #comp/cli #scope/dx #ai/instruct #task/domain/architecture #task/object/circular-dependency #task/action/elimination #task/state/continue

---

### Script

#### Acts 1: Fix Test Imports in `stitcher-application`

I will now correct the import paths in all the affected test files within the `stitcher-application` package.

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_doc_manager.py
~~~~~
~~~~~python.old
from stitcher.app.services import DocumentManager
~~~~~
~~~~~python.new
from stitcher.services import DocumentManager
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_doc_manager_strategies.py
~~~~~
~~~~~python.old
from stitcher.app.services import DocumentManager
~~~~~
~~~~~python.new
from stitcher.services import DocumentManager
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_doc_overlay.py
~~~~~
~~~~~python.old
from stitcher.app.services import DocumentManager
~~~~~
~~~~~python.new
from stitcher.services import DocumentManager
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_docstring_hybrid.py
~~~~~
~~~~~python.old
from stitcher.app.services import DocumentManager
~~~~~
~~~~~python.new
from stitcher.services import DocumentManager
~~~~~

~~~~~act
patch_file
packages/stitcher-application/tests/unit/test_execution_planner.py
~~~~~
~~~~~python.old
from stitcher.app.runners.pump.executor import PumpExecutor
from stitcher.app.services import DocumentManager, DocstringMerger
~~~~~
~~~~~python.new
from stitcher.app.runners.pump.executor import PumpExecutor
from stitcher.services import DocumentManager, DocstringMerger
~~~~~

#### Acts 2: Fix `StitcherApp` Import in `stitcher-test-utils`

This patch will fix the `ImportError` that caused the `pytest` run to fail by using the correct, explicit path to `StitcherApp`.

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~
~~~~~python.old
from stitcher.app import StitcherApp
~~~~~
~~~~~python.new
from stitcher.app.core import StitcherApp
~~~~~

#### Acts 3: Fix `StitcherApp` Import in `stitcher-cli`

Finally, I will fix the same import issue within the `stitcher-cli`'s factory module.

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/factories.py
~~~~~
~~~~~python.old
from stitcher.app import StitcherApp
~~~~~
~~~~~python.new
from stitcher.app.core import StitcherApp
~~~~~

### 下一步建议

The plan is now complete and addresses all reported errors. Please apply these changes.

After execution, immediately re-run both the test suite (`pytest`) and the static analysis (`pyright packages/stitcher-*`). This will provide definitive confirmation that the architectural refactoring is now complete, correct, and fully integrated with its test harness.
