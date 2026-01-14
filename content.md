I have analyzed the circular dependency errors you've provided. They reveal several architectural tangles where modules that should be at different layers of abstraction are depending on each other, creating cycles. This is a critical issue that violates the "Acyclic Dependencies Principle" and must be fixed to maintain system health.

My plan involves two main thrusts:
1.  A minor correction in `stitcher-lang-python` to use a relative import, which is a common and simple fix for package-level cycles.
2.  A more significant structural refactoring within `stitcher-refactor`. The core data structure for refactoring, `intent`, is currently misplaced within the `engine` package, causing the `engine` (a low-level component) to be a dependency for higher-level components like `operations` and `migration`, while the `engine` itself depends back on them. By elevating `intent` to a more neutral location, we can break all related cycles at once and restore a clean, one-way dependency flow.

Here is the detailed plan to execute this refactoring.

## [WIP] refactor(arch): Decouple refactor components to resolve circular dependencies

### 用户需求

Fix all reported circular dependency errors across the `stitcher-lang-python` and `stitcher-refactor` packages.

### 评论

The presence of numerous circular dependencies is a significant architectural smell (`异味即缺陷`). It indicates that the separation of concerns between different components has broken down, making the system difficult to reason about, maintain, and test. The proposed refactoring is not just a bug fix but a necessary step to restore architectural integrity and adhere to the principles of a well-layered system.

### 目标

1.  Resolve the import cycle within `stitcher.lang.python.analysis` by correcting an absolute import to be relative.
2.  Break the complex, multi-file dependency cycles within `stitcher-refactor` by relocating the core `intent` data structures.
3.  Update all modules that previously imported `intent` from the `engine` package to use its new, decoupled location.
4.  Refine the public API of the `engine` package to reflect that it no longer owns or exports the `intent` definitions.

### 基本原理

-   **`stitcher-lang-python` Cycle**: The cycle is caused by `usage_visitor.py` using an absolute import path (`from stitcher.lang.python.analysis.models import ...`). This forces the Python interpreter to load the top-level `stitcher.lang.python` package `__init__.py`, which in turn imports modules that eventually lead back to `usage_visitor.py`. Changing this to a direct relative import (`from .models import ...`) bypasses this unnecessary traversal and breaks the cycle cleanly.

-   **`stitcher-refactor` Cycles**: The fundamental issue is a layering violation.
    -   `MigrationSpec` and `Operation` are high-level concepts defining *what* a refactoring is.
    -   `Intent` is a mid-level data structure representing a concrete, planned change.
    -   `Planner` (inside `engine`) is a low-level component that processes `Intents` to generate file operations, defining *how* a refactoring is executed.
    
    The cycle `Migration -> Operation -> Intent(in engine) -> Planner(in engine) -> Migration` exists because `Intent` was incorrectly coupled with the `engine`. By extracting `intent.py` from `engine` and placing it at the `stitcher/refactor/` level, it becomes a neutral, foundational data structure. This re-establishes a clean, acyclic dependency flow: high-level components (`Migration`, `Operation`) can depend on `Intent`, and low-level components (`Engine`) can also depend on `Intent`, without creating a dependency on each other.

### 标签

#intent/refine #flow/ready #priority/critical #comp/refactor #comp/lang-python #concept/architecture #scope/core #ai/brainstorm #task/domain/architecture #task/object/dependency-graph #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: Resolve cycle in `stitcher-lang-python`

We will start by fixing the simpler cycle in the Python language package with a relative import.

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/usage_visitor.py
~~~~~
~~~~~python.old
from stitcher.lang.python.analysis.models import UsageLocation, ReferenceType
~~~~~
~~~~~python.new
from .models import UsageLocation, ReferenceType
~~~~~

#### Acts 2: Decouple `intent` from the refactor `engine`

Next, we execute the core architectural change by moving the `intent` module and its sidecar file out of the `engine` directory.

~~~~~act
move_file
packages/stitcher-refactor/src/stitcher/refactor/engine/intent.py
packages/stitcher-refactor/src/stitcher/refactor/intent.py
~~~~~

~~~~~act
move_file
packages/stitcher-refactor/src/stitcher/refactor/engine/intent.stitcher.yaml
packages/stitcher-refactor/src/stitcher/refactor/intent.stitcher.yaml
~~~~~

#### Acts 3: Update modules to use the new `intent` location

Now we update all modules that previously referenced the `intent` module, pointing them to its new, decoupled path. This is the crucial step that breaks the cycles.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~python.new
from stitcher.refactor.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.intent import RefactorIntent
~~~~~
~~~~~python.new
from stitcher.refactor.intent import RefactorIntent
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~python.new
from stitcher.refactor.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~python.new
from stitcher.refactor.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    LockSymbolUpdateIntent,
)
~~~~~
~~~~~python.new
from stitcher.refactor.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    LockSymbolUpdateIntent,
)
~~~~~

#### Acts 4: Clean up the `engine` package API

Finally, we remove the `intent` symbols from the `engine` package's `__init__.py`, as it no longer owns them. This finalizes the decoupling.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/__init__.py
~~~~~
~~~~~python.old
from .planner import Planner
from .intent import (
    RefactorIntent,
    RenameIntent,
    FileSystemIntent,
    MoveFileIntent,
    DeleteFileIntent,
    ScaffoldIntent,
    SidecarUpdateIntent,
    DeleteDirectoryIntent,
)

__all__ = [
    "TransactionManager",
    "SemanticGraph",
    "Planner",
    "RefactorIntent",
    "RenameIntent",
    "FileSystemIntent",
    "MoveFileIntent",
    "DeleteFileIntent",
    "ScaffoldIntent",
    "SidecarUpdateIntent",
    "DeleteDirectoryIntent",
]
~~~~~
~~~~~python.new
from .planner import Planner

__all__ = [
    "TransactionManager",
    "SemanticGraph",
    "Planner",
]
~~~~~

### 下一步建议

The architectural refactoring is now complete. The immediate next step should be to run the dependency analysis tool again to confirm that all reported cycles have been resolved. After that, running the full test suite (`pytest`) is essential to ensure that these structural changes have not introduced any regressions in behavior.
