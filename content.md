You are absolutely right to call this out. My apologies. In moving the `utils.py` file to break the circular dependency, I failed to update all the files that were importing it. The Pyright errors clearly show the broken import paths that resulted from my incomplete refactoring.

Thank you for running the type checker and providing the precise feedback. I will now generate the plan to fix these remaining import errors.

## [WIP] fix: Correct broken import paths after utility module relocation

### 错误分析

The `reportMissingImports` errors are a direct consequence of the previous plan's action to move `stitcher-refactor/src/stitcher/refactor/engine/utils.py` to `stitcher-refactor/src/stitcher/refactor/utils.py`. I correctly updated some of the importers but missed two key files:

1.  **`planner.py`**: It was using a relative import (`from .utils import ...`) which is now incorrect because `utils.py` is no longer in the same directory (`engine`).
2.  **`rename_symbol.py`**: It was using an import path (`from ..engine.utils import ...`) that explicitly pointed to the old location.

### 用户需求

Fix the two `reportMissingImports` errors reported by Pyright in `planner.py` and `rename_symbol.py`.

### 评论

This is a necessary and straightforward cleanup. Your rigorous verification process caught the oversight perfectly. This final set of changes will complete the architectural refactoring of the `stitcher-refactor` package.

### 目标

1.  Update the import statement in `planner.py` to correctly point to the new location of `utils.py`.
2.  Update the import statement in `rename_symbol.py` to do the same.

### 基本原理

The principle is simple: ensure all import paths accurately reflect the current file system structure. Both files need to change their import from pointing inside the `engine` directory to pointing at the higher-level `utils.py` in the `refactor` package.

### 标签

#intent/fix #flow/ready #priority/high #comp/refactor #scope/core #ai/instruct #task/domain/testing #task/object/architecture-linting #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Correct the import in `rename_symbol.py`

We will change the import path to reflect that `utils.py` is now a sibling to the `operations` directory, not inside `engine`.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python.old
from .base import AbstractOperation
from ..engine.utils import path_to_fqn
from stitcher.refactor.types import RefactorContext
from stitcher.analysis.semantic import SymbolNode
~~~~~
~~~~~python.new
from .base import AbstractOperation
from ..utils import path_to_fqn
from stitcher.refactor.types import RefactorContext
from stitcher.analysis.semantic import SymbolNode
~~~~~

#### Acts 2: Correct the import in `planner.py`

The import in `planner.py` needs to go up one directory level (`..`) to find the new `utils.py`. *However, upon reviewing the file, it appears `planner.py` does not use this utility. I will remove the unused import entirely.*

Wait, I have re-examined the code. The `path_to_fqn` utility *is* used within the `Planner`. My previous analysis was incorrect. The correct action is to fix the import path. My apologies for the confusion.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
from .utils import path_to_fqn
~~~~~
~~~~~python.new
from ..utils import path_to_fqn
~~~~~

### 下一步建议

These corrections should resolve the final outstanding issues. Please run Pyright one last time to confirm that the `stitcher-refactor` package is now free of import and architectural errors.
