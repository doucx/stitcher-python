You've encountered a classic `ImportError`. My analysis of the traceback confirms your findings.

The error originates in `packages/stitcher-common/src/stitcher/common/__init__.py`. This file is trying to import `SemanticPointerProtocol` from `needle.pointer`. However, based on the project's architecture, the `needle.pointer` package provides the concrete *implementation* (`SemanticPointer`, `L`), while the `needle.spec` package provides the abstract *interface* (`SemanticPointerProtocol`).

The import statement incorrectly bundles the implementation and the interface from the same source. To fix this, I need to separate the imports, fetching `L` from `needle.pointer` and `SemanticPointerProtocol` from `needle.spec`.

I will now generate a plan to apply this correction.

## [WIP] fix: Correct import path for SemanticPointerProtocol

### 错误分析

The test collection process is failing due to an `ImportError` within the `stitcher-common` package.

**Traceback Analysis**:
1.  `test_check_command.py` imports from `stitcher.test_utils`.
2.  `stitcher.test_utils` imports from `stitcher.common`.
3.  The file `stitcher-common/src/stitcher/common/__init__.py` executes the line: `from needle.pointer import L, SemanticPointerProtocol`.
4.  This fails because `SemanticPointerProtocol` is not defined in the `needle.pointer` package's `__init__.py`. It is correctly defined and exported from the `needle.spec` package.

This is a dependency graph error where a module is attempting to import a symbol from the wrong location, violating the architectural separation between specifications (interfaces) and implementations.

### 用户需求

Fix the `ImportError` so that the `pytest` test collection can complete successfully and the test suite can run.

### 评论

This is a critical fix that restores the architectural integrity of the `pyneedle` packages. Separating protocol definitions (`-spec`) from their implementations (`-pointer`, `-runtime`) is essential for maintaining a clean and understandable dependency graph, which in turn prevents circular dependencies and improves overall system health.

### 目标

Modify the import statements in `packages/stitcher-common/src/stitcher/common/__init__.py` to correctly resolve `SemanticPointerProtocol`.

### 基本原理

The principle is to respect the project's package structure. `L` is the global pointer instance from `needle.pointer`, while `SemanticPointerProtocol` is the interface definition from `needle.spec`. The fix involves splitting the single incorrect import into two correct ones. I will use `patch_file` to perform this targeted replacement.

### 标签

#intent/fix #flow/ready #priority/critical #comp/build #concept/state #scope/core #ai/instruct #task/domain/build #task/object/dependency-graph #task/action/fix #task/state/begin #task/state/end

---

### Script

#### Acts 1: Correct the import statement

I will now patch the `stitcher-common` `__init__.py` file to import `SemanticPointerProtocol` from the correct package, `needle.spec`.

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Dict
from needle.pointer import L, SemanticPointerProtocol
from needle.nexus import OverlayOperator
from needle.operators import I18NFactoryOperator
~~~~~
~~~~~python
from pathlib import Path
from typing import Dict
from needle.pointer import L
from needle.spec import SemanticPointerProtocol
from needle.nexus import OverlayOperator
from needle.operators import I18NFactoryOperator
~~~~~

### 下一步建议

After applying this patch, please run your tests again. The `ImportError` during test collection should now be resolved.
