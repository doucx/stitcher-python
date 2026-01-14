I have analyzed the `pyright` error report. The errors are direct consequences of the previous refactoring to break circular dependencies. The fixes fall into two categories:

1.  **Dangling Function Call**: After moving `_enrich_typing_imports` from `analysis/visitors.py` to `parser/griffe.py`, a call to it was mistakenly left behind in its original location (`visitors.py`). This needs to be removed.
2.  **Incorrect Import Paths**: The `RefactorContext` class was moved from `stitcher.refactor.engine.context` to a new, lower-level `stitcher.refactor.types` module. While I updated the internal references within the `stitcher-refactor` package, I did not update the external consumers of this class, such as `stitcher-application` and numerous test files.

Critically, the provided file listing (my D1 knowledge) does not contain the `tests` directory for `stitcher-refactor`, which is where the majority of the `pyright` errors are reported. According to my core protocol, I cannot operate on files that are not in my knowledge base.

Therefore, I will perform a partial fix, addressing all the errors in the files I *can* see. I will then explain which files I was unable to modify due to this limitation.

## [WIP] fix: Partially resolve pyright errors after dependency refactoring

### 错误分析

The `pyright` errors stem from two issues introduced in the last refactoring:

1.  **Incomplete Refactoring**: A helper function (`_enrich_typing_imports`) was moved from `analysis/visitors.py` to `parser/griffe.py` to break a dependency cycle, but the original call to this function in `visitors.py` was not removed, resulting in an `UndefinedVariable` error.
2.  **Broken External Contracts**: The `RefactorContext` data class was moved from `stitcher.refactor.engine.context` to `stitcher.refactor.types` to break a major architectural cycle. While internal imports were fixed, external modules that depend on this class (like the application runner and the entire test suite) were not updated to point to the new location, causing widespread `Import could not be resolved` errors.

### 用户需求

Fix all reported `pyright` errors to ensure the project's static analysis passes.

### 评论

This plan addresses the errors that are within my current knowledge scope. The provided file listing is missing the contents of the `stitcher-refactor/tests` directory, which accounts for the vast majority of the reported `pyright` errors. **Therefore, this plan is a partial but necessary fix.** I will correct the errors in the application and library code. A complete fix will require the contents of the missing test files.

### 目标

1.  Remove the dangling function call to `_enrich_typing_imports` in `analysis/visitors.py`.
2.  Update the import path for `RefactorContext` in `stitcher-application`'s `refactor.py` runner.
3.  Update the import path for `RefactorContext` in the `rename_namespace.py` operation within `stitcher-refactor`.
4.  Defer fixing the test files until their contents are provided.

### 基本原理

1.  **Dangling Call Removal**: I will apply a `patch_file` operation to `analysis/visitors.py` to delete the single line that calls the now-nonexistent function. The function's logic is correctly handled in its new location within the `griffe.py` parser, so this removal is safe.
2.  **Import Path Correction**: For all files that I can access and that report an import error for `RefactorContext`, I will use `patch_file` to change the import statement from `from stitcher.refactor.engine.context import RefactorContext` to the new, correct path: `from stitcher.refactor.types import RefactorContext`.

### 标签

#intent/fix #flow/ready #priority/high #comp/build #scope/core #ai/instruct #task/domain/testing #task/object/dependency-graph #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Remove dangling function call in `visitors.py`

This removes the call to `_enrich_typing_imports` from its old location, fixing the `UndefinedVariable` error.

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/visitors.py
~~~~~
~~~~~python.old
    _enrich_typing_imports(module_def)

    return module_def
~~~~~
~~~~~python.new
    return module_def
~~~~~

#### Acts 2: Correct `RefactorContext` import paths in visible modules

These patches update the import statements to point to the new location of `RefactorContext`, fixing the `Import could not be resolved` errors for the application and library code.

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine import (
    SemanticGraph,
    RefactorContext,
    Planner,
    TransactionManager,
)
~~~~~
~~~~~python.new
from stitcher.refactor.engine import (
    SemanticGraph,
    Planner,
    TransactionManager,
)
from stitcher.refactor.types import RefactorContext
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_namespace.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.context import RefactorContext
~~~~~
~~~~~python.new
from stitcher.refactor.types import RefactorContext
~~~~~

### 下一步建议

This plan corrects all `pyright` errors for the files within my current knowledge base. However, the majority of errors are in the test files located under `packages/stitcher-refactor/tests/`, which were not included in the initial file listing.

To complete the fix, please provide the contents of the following files. I will then generate the necessary patches to update their `RefactorContext` imports.

*   `packages/stitcher-refactor/tests/integration/test_bug_init_relative_import.py`
*   `packages/stitcher-refactor/tests/integration/test_bug_relative_import_refactor.py`
*   `packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py`
*   ...and all other test files listed in the `pyright` error report.
