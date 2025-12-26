## [WIP] refactor: Enforce direct dependency on stitcher-needle

### 用户需求
移除 `stitcher-common` 对 `L` 对象的重新导出。强制所有消费者（如 `stitcher-cli` 和 `stitcher-application`）直接依赖 `stitcher-needle` 并从中导入 `L`。

### 评论
这是一个重要的架构重构，它消除了 `stitcher-common` 作为“中间人”的角色，实现了更清晰、更纯粹的依赖关系。通过强制直接依赖，我们确保了 `stitcher-needle` 作为一个独立运行时的完整性，并使整个项目的依赖图谱更加清晰和可维护。

### 目标
1.  从 `stitcher-common` 的 `pyproject.toml` 和 `__init__.py` 中移除对 `stitcher-needle` 的依赖和 `L` 的重新导出。
2.  在 `stitcher-cli` 的 `pyproject.toml` 中添加对 `stitcher-needle` 的直接依赖。
3.  在 `stitcher-application` 的 `pyproject.toml` 中添加对 `stitcher-needle` 的直接依赖。
4.  更新 `stitcher-cli` 和 `stitcher-application` 中的 import 语句，使其直接从 `stitcher.needle` 导入 `L`。

### 基本原理
此重构将依赖关系从 `Consumer -> Common -> Needle` 的链式结构，转变为 `Consumer -> Common` 和 `Consumer -> Needle` 的星形结构。这降低了包之间的耦合度，并使每个包的职责更加明确。

### 标签
#intent/refine #flow/ready #priority/high #comp/common #comp/cli #comp/application #scope/core #scope/dx #ai/instruct #task/domain/runtime #task/object/dependency-graph #task/action/refactor #task/state/continue

---
### Script

#### Acts 1: Decouple `stitcher-common` from `needle`

First, we sever the link between `common` and `needle`.

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python.old
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Make core singletons easily accessible
from .messaging import bus
from stitcher.needle import L

__all__ = ["bus", "L"]
~~~~~
~~~~~python.new
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# Make core singletons easily accessible
from .messaging import bus

__all__ = ["bus"]
~~~~~

~~~~~act
patch_file
packages/stitcher-common/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "stitcher-common"
version = "0.1.0"
description = "Common utilities and protocols for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-needle",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-needle = { workspace = true }
~~~~~
~~~~~toml.new
[project]
name = "stitcher-common"
version = "0.1.0"
description = "Common utilities and protocols for Stitcher."
requires-python = ">=3.10"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~

#### Acts 2: Update `stitcher-cli` to depend on `needle`

Now, we make `stitcher-cli` a direct consumer of `needle`.

~~~~~act
patch_file
packages/stitcher-cli/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "stitcher-cli"
version = "0.1.0"
description = "Command-line interface for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-application",
    "typer[all]",
]
~~~~~
~~~~~toml.new
[project]
name = "stitcher-cli"
version = "0.1.0"
description = "Command-line interface for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-application",
    "stitcher-needle",
    "typer[all]",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
stitcher-application = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
stitcher-application = { workspace = true }
stitcher-needle = { workspace = true }
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
from stitcher.app import StitcherApp
from stitcher.common import L, bus
from .rendering import CliRenderer
~~~~~
~~~~~python.new
from stitcher.app import StitcherApp
from stitcher.common import bus
from stitcher.needle import L
from .rendering import CliRenderer
~~~~~

#### Acts 3: Update `stitcher-application` to depend on `needle`

Finally, we do the same for `stitcher-application`.

~~~~~act
patch_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "stitcher-application"
version = "0.1.0"
description = "Orchestration layer for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-scanner",
    "stitcher-io",
    "stitcher-config",
]
~~~~~
~~~~~toml.new
[project]
name = "stitcher-application"
version = "0.1.0"
description = "Orchestration layer for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-scanner",
    "stitcher-io",
    "stitcher-config",
    "stitcher-needle",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
stitcher-config = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
stitcher-config = { workspace = true }
stitcher-needle = { workspace = true }
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from stitcher.io import StubGenerator
from stitcher.spec import ModuleDef, FunctionDef
from stitcher.common import L, bus
from stitcher.config import load_config_from_path
~~~~~
~~~~~python.new
from stitcher.io import StubGenerator
from stitcher.spec import ModuleDef, FunctionDef
from stitcher.common import bus
from stitcher.needle import L
from stitcher.config import load_config_from_path
~~~~~
