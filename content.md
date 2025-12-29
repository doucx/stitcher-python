## [WIP] refactor(pyneedle): 将 nexus 包合并到 runtime 中以简化架构

### 用户需求
合并 `pyneedle-nexus` 包到 `pyneedle-runtime` 包中，以减少项目中的包数量并简化依赖关系。

### 评论
这是一个出色的架构简化提议。`OverlayOperator` 是运行时组合机制的核心，将其与 `FileSystemOperator` 等其他核心算子放在同一个 `runtime` 包中，可以显著提高代码的内聚性。相比于创建一个新的 `operators` 包，这种合并方式更直接地降低了项目的整体复杂度。

### 目标
1.  将 `OverlayOperator` 的源代码及其测试文件从 `pyneedle-nexus` 迁移至 `pyneedle-runtime`。
2.  更新所有代码中对 `OverlayOperator` 的导入路径。
3.  从整个项目（包括依赖配置、测试配置、静态分析配置）中完全移除 `pyneedle-nexus` 包。
4.  确保重构后的测试全部通过。

### 基本原理
我们将采用直接迁移文件的方式。首先，将 `nexus` 包中的核心逻辑 `operators.py` 移动到 `runtime` 包的 `operators` 目录下，并重命名为 `overlay_operator.py` 以保持清晰。然后，迁移相关的测试文件。接下来，通过一系列精确的 `patch_file` 操作，更新代码库中所有对旧路径的引用。最后，修改 `pyproject.toml` 文件，从依赖和工作区配置中移除 `nexus` 包，并执行物理删除。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #comp/build #scope/core #dx #ai/instruct #task/domain/architecture #task/object/package-structure #task/action/refactor #task/state/begin

---
### Script

#### Acts 1: 迁移 `OverlayOperator` 核心逻辑和测试

首先，我们将 `OverlayOperator` 的源文件和测试文件移动到 `pyneedle-runtime` 包中。

~~~~~act
move_file
packages/pyneedle-nexus/src/needle/nexus/operators.py
packages/pyneedle-runtime/src/needle/operators/overlay_operator.py
~~~~~

~~~~~act
move_file
packages/pyneedle-nexus/tests/test_overlay_operator.py
packages/pyneedle-runtime/tests/test_overlay_operator.py
~~~~~

#### Acts 2: 更新代码中的导入路径

现在，我们需要更新所有引用了旧 `nexus` 路径的代码。

首先，让 `runtime` 的 `operators` 模块导出新的 `OverlayOperator`。
~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/operators/__init__.py
~~~~~
~~~~~python.old
from .dict_operator import DictOperator
from .fs_operator import FileSystemOperator
from .i18n_factory import I18NFactoryOperator

__all__ = ["DictOperator", "FileSystemOperator", "I18NFactoryOperator"]
~~~~~
~~~~~python.new
from .dict_operator import DictOperator
from .fs_operator import FileSystemOperator
from .i18n_factory import I18NFactoryOperator
from .overlay_operator import OverlayOperator

__all__ = [
    "DictOperator",
    "FileSystemOperator",
    "I18NFactoryOperator",
    "OverlayOperator",
]
~~~~~

更新 `runtime` 自身对 `OverlayOperator` 的引用。
~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/runtime.py
~~~~~
~~~~~python.old
from pathlib import Path
from typing import Optional
from needle.pointer import L, SemanticPointer, PointerSet
from needle.nexus import OverlayOperator
~~~~~
~~~~~python.new
from pathlib import Path
from typing import Optional
from needle.pointer import L, SemanticPointer, PointerSet
from needle.operators import OverlayOperator
~~~~~

更新 `stitcher-common` 中对 `OverlayOperator` 的引用。
~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python.old
import os
from pathlib import Path
from typing import Dict
from needle.pointer import L
from needle.nexus import OverlayOperator
from needle.operators import I18NFactoryOperator
~~~~~
~~~~~python.new
import os
from pathlib import Path
from typing import Dict
from needle.pointer import L
from needle.operators import I18NFactoryOperator, OverlayOperator
~~~~~

更新迁移过来的测试文件中的导入。
~~~~~act
patch_file
packages/pyneedle-runtime/tests/test_overlay_operator.py
~~~~~
~~~~~python.old
from needle.nexus import OverlayOperator
from needle.operators import DictOperator
~~~~~
~~~~~python.new
from needle.operators import OverlayOperator, DictOperator
~~~~~

更新集成测试中的导入。
~~~~~act
patch_file
packages/pyneedle-runtime/tests/test_pipeline_integration.py
~~~~~
~~~~~python.old
from pathlib import Path
from needle.pointer import L
from needle.operators import FileSystemOperator
from needle.nexus import OverlayOperator
~~~~~
~~~~~python.new
from pathlib import Path
from needle.pointer import L
from needle.operators import FileSystemOperator, OverlayOperator
~~~~~

最后，更新 `pyneedle` 的聚合 `__init__.py`，使其也能导出 `OverlayOperator`。
~~~~~act
patch_file
packages/pyneedle/src/needle/__init__.py
~~~~~
~~~~~python.old
# This is the crucial line. It makes this regular package
# "porous" and allows the namespace to be extended.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Now that the full 'needle' namespace is assembled, we can safely import from it.
from needle.pointer import L, SemanticPointer, PointerSet
from needle.runtime import nexus
from needle.spec import (
    OperatorProtocol,
    SemanticPointerProtocol,
    PointerSetProtocol,
)

__all__ = [
    "L",
    "SemanticPointer",
    "PointerSet",
    "nexus",
    "OperatorProtocol",
    "SemanticPointerProtocol",
    "PointerSetProtocol",
]
~~~~~
~~~~~python.new
# This is the crucial line. It makes this regular package
# "porous" and allows the namespace to be extended.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Now that the full 'needle' namespace is assembled, we can safely import from it.
from needle.pointer import L, SemanticPointer, PointerSet
from needle.runtime import nexus
from needle.spec import (
    OperatorProtocol,
    SemanticPointerProtocol,
    PointerSetProtocol,
)
from needle.operators import OverlayOperator


__all__ = [
    "L",
    "SemanticPointer",
    "PointerSet",
    "nexus",
    "OperatorProtocol",
    "SemanticPointerProtocol",
    "PointerSetProtocol",
    "OverlayOperator",
]
~~~~~

#### Acts 3: 更新项目配置文件

从各个 `pyproject.toml` 文件中移除对 `pyneedle-nexus` 的依赖。
~~~~~act
patch_file
packages/pyneedle/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle-spec",
    "pyneedle-pointer",
    "pyneedle-nexus",
    "pyneedle-runtime",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle-spec",
    "pyneedle-pointer",
    "pyneedle-runtime",
]
~~~~~

~~~~~act
patch_file
packages/pyneedle/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyneedle-spec = { workspace = true }
pyneedle-pointer = { workspace = true }
pyneedle-nexus = { workspace = true }
pyneedle-runtime = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyneedle-spec = { workspace = true }
pyneedle-pointer = { workspace = true }
pyneedle-runtime = { workspace = true }
~~~~~

~~~~~act
patch_file
packages/pyneedle-runtime/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle-spec",
    "pyneedle-pointer",
    "pyneedle-nexus",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle-spec",
    "pyneedle-pointer",
]
~~~~~

~~~~~act
patch_file
packages/pyneedle-runtime/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyneedle-spec = { workspace = true }
pyneedle-pointer = { workspace = true }
pyneedle-nexus = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyneedle-spec = { workspace = true }
pyneedle-pointer = { workspace = true }
~~~~~

最后，清理根 `pyproject.toml` 文件。
~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
dev = [
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "ruff",
    "mypy",
    "pyneedle",
    "pyneedle-nexus",
    "pyneedle-pointer",
    "pyneedle-spec",
    "stitcher-cli",
    "stitcher-application",
    "stitcher-test-utils",
]
~~~~~
~~~~~toml.new
dev = [
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "ruff",
    "mypy",
    "pyneedle",
    "pyneedle-pointer",
    "pyneedle-spec",
    "stitcher-cli",
    "stitcher-application",
    "stitcher-test-utils",
]
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyneedle = { workspace = true }
pyneedle-runtime = { workspace = true }
pyneedle-nexus = { workspace = true }
pyneedle-pointer = { workspace = true }
pyneedle-spec = { workspace = true }
stitcher-spec = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyneedle = { workspace = true }
pyneedle-runtime = { workspace = true }
pyneedle-pointer = { workspace = true }
pyneedle-spec = { workspace = true }
stitcher-spec = { workspace = true }
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-nexus/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle/src",
    "packages/stitcher-test-utils/src"
]
~~~~~
~~~~~toml.new
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle/src",
    "packages/stitcher-test-utils/src"
]
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
scan_paths = [
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-nexus/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle/src",
]
stub_package = "packages/needle-stubs"
~~~~~
~~~~~toml.new
scan_paths = [
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle/src",
]
stub_package = "packages/needle-stubs"
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-nexus/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle/src",
    # Add the new stub packages' source directories
    "packages/stitcher-stubs/src",
~~~~~
~~~~~toml.new
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle/src",
    # Add the new stub packages' source directories
    "packages/stitcher-stubs/src",
~~~~~

#### Acts 4: 物理删除 `pyneedle-nexus` 包

所有引用都已更新，现在可以安全地删除 `pyneedle-nexus` 目录了。
~~~~~act
run_command
~~~~~
~~~~~
rm -rf packages/pyneedle-nexus
~~~~~

### 下一步建议
重构已经完成。现在建议运行完整的测试套件，以确保所有更改都按预期工作且没有引入任何回归。

`uv run pytest`
