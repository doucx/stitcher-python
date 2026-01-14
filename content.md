OK. The provided output indicates a significant number of circular dependency errors across the `stitcher-lang-python` and `stitcher-refactor` packages. These are serious architectural issues that violate the "zero smell" principle of the High-Fidelity Engineering Axioms (HFEA). I will proceed to fix them.

The root cause is a combination of overly broad `__init__.py` files creating import tangles, and incorrect layering of modules (e.g., high-level modules depending on low-level ones, which in turn depend back on the high-level ones).

My strategy will be twofold:
1.  **For `stitcher-lang-python`**: I will restructure the modules by moving the IR-building logic (`visitors.py`) from the `analysis` package to the `parser` package, as it's fundamentally a parsing concern. This will break the main cycle of `adapter -> parser -> analysis -> adapter`. I will also clean up imports to be more direct and relative where appropriate.
2.  **For `stitcher-refactor`**: I will apply the Dependency Inversion Principle. The core data structures (`RefactorContext`, `RefactorIntent`) are currently in the high-level `engine` package, but are needed by the lower-level `operations` package, creating a cycle. I will extract these shared types into a new, lower-level `stitcher.refactor.types` module that both `engine` and `operations` can safely depend on.

This plan adheres to the HFEA by not patching the problem but by fundamentally correcting the architecture to achieve ontological correctness.

## [WIP] refactor(lang, refactor): Break circular dependencies in language and refactoring packages

### 錯誤分析

The build is failing due to multiple circular dependency errors, primarily within `stitcher-lang-python` and `stitcher-refactor`.

1.  **In `stitcher-lang-python`**: The `adapter` module depends on the `parser`, which depends on `analysis`, which in turn has transitive dependencies that lead back to `adapter` and the top-level package `__init__.py`. The core of this issue is `analysis/visitors.py`, which is more related to parsing (IR generation) than analysis, creating an incorrect dependency link.
2.  **In `stitcher-refactor`**: The `operations` modules (e.g., `rename_symbol.py`) depend on `engine.context` and `engine.intent` for type definitions. However, the `engine.planner` depends on `migration`, which depends on `operations`. This creates a cycle: `engine -> migration -> operations -> engine`.

### 用户需求

Resolve all circular dependency errors reported by the architecture analysis tool to ensure a stable and maintainable codebase.

### 评论

These circular dependencies represent a critical architectural flaw. They make the system rigid, hard to understand, and difficult to test or change. Fixing this is a high-priority task that aligns with the "Architecture Incorruptibility" principle. The proposed solution involves structural changes to enforce a directed acyclic graph (DAG) for dependencies, which is the correct and most robust solution.

### 目标

1.  Relocate the IR-building logic in `stitcher-lang-python` to break the `parser <-> analysis` cycle.
2.  Extract shared data structures in `stitcher-refactor` into a common `types` module to break the `engine <-> operations` cycle.
3.  Update all affected modules to use the new structure and import paths.
4.  Ensure the codebase remains fully functional after the refactoring.

### 基本原理

The principle of this refactoring is to enforce a clear, top-down dependency flow.
- In `stitcher-lang-python`, `parsing` is a foundational step. `analysis` of the parsed structure is a subsequent step. By moving the IR generation from `analysis` to `parser`, we align the code structure with the logical flow of data, breaking the cycle.
- In `stitcher-refactor`, shared data structures (`types`) should not belong to any specific high-level component (`engine`). By extracting them to a neutral, lower-level location, we allow multiple components to depend on them without depending on each other, thereby breaking the circular dependency.

### 标签

#intent/refine #flow/ready #priority/critical #comp/tests #comp/engine #scope/core #scope/dx #ai/brainstorm #task/domain/architecture #task/object/dependency-graph #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: Refactor `stitcher-lang-python` to break cycles

First, I'll move the IR-building visitor to the `parser` package, where it logically belongs. Then, I'll update all modules that used it to point to the new location and clean up other local imports to be more explicit.

~~~~~act
move_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/visitors.py
packages/stitcher-lang-python/src/stitcher/lang/python/parser/visitors.py
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/parser/cst.py
~~~~~
~~~~~
from stitcher.spec import ModuleDef
from stitcher.lang.python.analysis.visitors import parse_source_code


class PythonParser:
~~~~~
~~~~~
from stitcher.spec import ModuleDef
from .visitors import parse_source_code


class PythonParser:
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/parser/griffe.py
~~~~~
~~~~~
    SourceLocation,
)
from stitcher.lang.python.analysis.visitors import _enrich_typing_imports


class _ImportVisitor(ast.NodeVisitor):
~~~~~
~~~~~
    SourceLocation,
)
from .visitors import _enrich_typing_imports


class _ImportVisitor(ast.NodeVisitor):
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/docstring/factory.py
~~~~~
~~~~~
from typing import Tuple

from stitcher.spec import DocstringParserProtocol, DocstringRendererProtocol
from stitcher.lang.python.docstring.parsers import (
    RawDocstringParser,
    GriffeDocstringParser,
)
from stitcher.lang.python.docstring.renderers import (
    GoogleDocstringRenderer,
    NumpyDocstringRenderer,
)
from stitcher.lang.python.docstring.serializers import (
    RawSerializer,
    GoogleSerializer,
    NumpySerializer,
)
from stitcher.spec import DocstringSerializerProtocol
~~~~~
~~~~~
from typing import Tuple

from stitcher.spec import DocstringParserProtocol, DocstringRendererProtocol
from .parsers import (
    RawDocstringParser,
    GriffeDocstringParser,
)
from .renderers import (
    GoogleDocstringRenderer,
    NumpyDocstringRenderer,
)
from .serializers import (
    RawSerializer,
    GoogleSerializer,
    NumpySerializer,
)
from stitcher.spec import DocstringSerializerProtocol
~~~~~
~~~~~

#### Acts 2: Refactor `stitcher-refactor` to break cycles

I will now create a central `types.py` module for shared data structures, move the relevant classes into it, delete the old files, and then update all dependent modules to import from the new location.

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/types.py
~~~~~
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.workspace import Workspace
from stitcher.spec import IndexStoreProtocol, LockManagerProtocol, URIGeneratorProtocol
from stitcher.analysis.semantic import SemanticGraph


@dataclass
class RefactorContext:
    workspace: Workspace
    graph: SemanticGraph
    sidecar_manager: SidecarManager
    index_store: IndexStoreProtocol
    lock_manager: LockManagerProtocol
    uri_generator: URIGeneratorProtocol


@dataclass(frozen=True)
class RefactorIntent:
    pass


# --- Symbol-level Intents ---


@dataclass(frozen=True)
class RenameIntent(RefactorIntent):
    old_fqn: str
    new_fqn: str


# --- Filesystem-level Intents ---


@dataclass(frozen=True)
class FileSystemIntent(RefactorIntent):
    pass


@dataclass(frozen=True)
class MoveFileIntent(FileSystemIntent):
    src_path: Path
    dest_path: Path


@dataclass(frozen=True)
class DeleteFileIntent(FileSystemIntent):
    path: Path


@dataclass(frozen=True)
class DeleteDirectoryIntent(FileSystemIntent):
    path: Path


@dataclass(frozen=True)
class ScaffoldIntent(FileSystemIntent):
    path: Path
    content: str = ""


# --- Sidecar-level Intents ---


@dataclass(frozen=True)
class SidecarUpdateIntent(RefactorIntent):
    sidecar_path: Path
    module_fqn: Optional[str]
    old_fqn: str
    new_fqn: str
    # New fields for SURI updates
    old_file_path: Optional[str] = None
    new_file_path: Optional[str] = None


# --- Lock-level Intents ---


@dataclass(frozen=True)
class LockSymbolUpdateIntent(RefactorIntent):
    package_root: Path
    old_suri: str
    new_suri: str


@dataclass(frozen=True)
class LockPathUpdateIntent(RefactorIntent):
    package_root: Path
    old_path_prefix: str  # Workspace-relative path prefix
    new_path_prefix: str  # Workspace-relative path prefix
~~~~~

~~~~~act
delete_file
packages/stitcher-refactor/src/stitcher/refactor/engine/context.py
~~~~~

~~~~~act
delete_file
packages/stitcher-refactor/src/stitcher/refactor/engine/intent.py
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/__init__.py
~~~~~
~~~~~
from stitcher.common.transaction import TransactionManager
from .context import RefactorContext
from stitcher.analysis.semantic import SemanticGraph
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
    "RefactorContext",
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
~~~~~
from stitcher.common.transaction import TransactionManager
from stitcher.analysis.semantic import SemanticGraph
from .planner import Planner

__all__ = [
    "TransactionManager",
    "SemanticGraph",
    "Planner",
]
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~
from abc import ABC, abstractmethod
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.intent import RefactorIntent


class AbstractOperation(ABC):
~~~~~
~~~~~
from abc import ABC, abstractmethod
from typing import List

from stitcher.refactor.types import RefactorContext, RefactorIntent


class AbstractOperation(ABC):
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~
from pathlib import Path
from typing import List

from stitcher.refactor.types import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.utils import path_to_fqn
from stitcher.refactor.types import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~
from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~
from pathlib import Path
from typing import List

from stitcher.refactor.types import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.utils import path_to_fqn
from stitcher.refactor.types import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~
from typing import List, Optional

from .base import AbstractOperation
from ..engine.utils import path_to_fqn
from stitcher.refactor.engine.context import RefactorContext
from stitcher.analysis.semantic import SymbolNode
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    LockSymbolUpdateIntent,
)


class RenameSymbolOperation(AbstractOperation):
~~~~~
~~~~~
from typing import List, Optional

from .base import AbstractOperation
from ..engine.utils import path_to_fqn
from stitcher.refactor.types import (
    RefactorContext,
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    LockSymbolUpdateIntent,
)
from stitcher.analysis.semantic import SymbolNode


class RenameSymbolOperation(AbstractOperation):
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~
if TYPE_CHECKING:
    from stitcher.refactor.migration import MigrationSpec
from stitcher.refactor.engine.context import RefactorContext
from stitcher.common.transaction import (
    FileOp,
~~~~~
~~~~~
if TYPE_CHECKING:
    from stitcher.refactor.migration import MigrationSpec
from stitcher.refactor.types import RefactorContext
from stitcher.common.transaction import (
    FileOp,
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~
    DeleteFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~
    DeleteFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.types import (
    RefactorIntent,
    RenameIntent,
~~~~~
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/renamer.py
~~~~~
~~~~~
from typing import List, Dict
from pathlib import Path

from stitcher.refactor.engine.context import RefactorContext
from stitcher.common.transaction import WriteFileOp
from stitcher.lang.python.analysis.models import UsageLocation
~~~~~
~~~~~
from typing import List, Dict
from pathlib import Path

from stitcher.refactor.types import RefactorContext
from stitcher.common.transaction import WriteFileOp
from stitcher.lang.python.analysis.models import UsageLocation
~~~~~
~~~~~

### 下一步建议

The core architectural issues causing circular dependencies should now be resolved. I strongly recommend running the architecture analysis tool again to confirm that all reported errors are gone.

If the analysis passes, the next logical step is to run the full test suite (`pytest`) to ensure that these significant refactorings have not introduced any regressions in behavior.
