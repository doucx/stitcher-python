当然。根据你的 `refactor apply` 指南，这是一个非常适合的场景。`Move` 操作可以完美地处理文件移动、FQN (完全限定名) 变更、以及所有跨包引用的自动更新。

我将生成一个计划，该计划会创建迁移脚本，并更新 `stitcher-common` 的 `pyproject.toml` 文件，为其添加对新 `stitcher-bus` 包的依赖。这是必要的，因为 `stitcher-common` 的 `__init__.py` 作为组合根，仍然会负责实例化并导出全局的 `bus` 对象，因此它现在需要从 `stitcher.bus` 导入 `FeedbackBus`。

## [WIP] refactor: 将 FeedbackBus 从 stitcher-common 迁移至 stitcher-bus

### 用户需求
创建一个 `stitcher refactor apply` 迁移脚本，将 `FeedbackBus` 及其相关协议 (`bus.py`, `protocols.py`) 从 `stitcher-common` 包移动到新的 `stitcher-bus` 包中。同时，更新 `stitcher-common` 的包依赖，以确保它能够正确导入新的 `stitcher-bus`。

### 评论
这是一个出色的架构重构。将消息总线 (`FeedbackBus`) 移动到独立的 `stitcher-bus` 包中，可以打破 `stitcher-common` 的全能角色，使其职责更单一。这不仅提高了模块化程度，也为未来避免潜在的循环依赖奠定了基础，完全符合高保真工程（HFEA）的原则。

### 目标
1.  创建一个新的迁移脚本 `migrations/004_move_bus_to_dedicated_package.py`。
2.  在该脚本中使用 `Move` 操作来迁移 `bus.py` 和 `protocols.py` 及其关联的 `.stitcher.yaml` 文件。
3.  修改 `packages/stitcher-common/pyproject.toml`，为其添加对 `stitcher-bus` 的依赖。

### 基本原理
`stitcher refactor apply` 的 `Move` 操作是本次重构的核心。它具备语义感知能力，在移动文件的同时，会自动计算 FQN 的变化（从 `stitcher.common.messaging.bus` 到 `stitcher.bus.bus`），并精确地更新整个工作区中所有对 `FeedbackBus` 的 `import` 语句。操作完成后，我们只需手动更新 `pyproject.toml` 以声明新的包间依赖关系，即可完成整个重构。

### 标签
#intent/refine #flow/ready #priority/high 
#comp/build #comp/common #concept/state #scope/core 
#ai/instruct
#task/domain/refactoring #task/object/message-bus #task/action/relocation #task/state/continue

---

### Script

#### Acts 1: 创建重构迁移脚本

此脚本定义了将 `bus.py` 和 `protocols.py` 从 `stitcher-common` 移动到 `stitcher-bus` 的 `Move` 操作。

~~~~~act
write_file
migrations/004_move_bus_to_dedicated_package.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.refactor.migration import MigrationSpec, Move


def upgrade(spec: MigrationSpec):
    """
    Moves the FeedbackBus and its related protocols from the generic
    stitcher-common package to a dedicated stitcher-bus package to improve
    modularity and clarify dependencies.
    """
    # Move the core bus implementation
    spec.add(
        Move(
            Path("packages/stitcher-common/src/stitcher/common/messaging/bus.py"),
            Path("packages/stitcher-bus/src/stitcher/bus/bus.py"),
        )
    )
    # Move the supporting protocol definitions
    spec.add(
        Move(
            Path("packages/stitcher-common/src/stitcher/common/messaging/protocols.py"),
            Path("packages/stitcher-bus/src/stitcher/bus/protocols.py"),
        )
    )
~~~~~

#### Acts 2: 更新 `stitcher-common` 的依赖关系

在 `stitcher-common` 的 `pyproject.toml` 中添加对 `stitcher-bus` 的依赖，因为 `stitcher-common` 仍然是全局 `bus` 实例的创建者。

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
dependencies = []

[tool.hatch.build.targets.wheel]
~~~~~
~~~~~toml.new
[project]
name = "stitcher-common"
version = "0.1.0"
description = "Common utilities and protocols for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-bus",
]

[tool.hatch.build.targets.wheel]
~~~~~

~~~~~act
patch_file
packages/stitcher-common/pyproject.toml
~~~~~
~~~~~toml.old
[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
include = ["/src/stitcher/common/assets"]
~~~~~
~~~~~toml.new
[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
include = ["/src/stitcher/common/assets"]

[tool.uv.sources]
stitcher-bus = { workspace = true }
~~~~~

### 下一步建议
现在迁移脚本和依赖配置都已准备就绪。

你可以执行以下命令来预览并应用重构：
1.  **预览变更 (强烈推荐)**:
    ```bash
    stitcher refactor apply migrations/004_move_bus_to_dedicated_package.py --dry-run
    ```
2.  **应用变更**:
    ```bash
    stitcher refactor apply migrations/004_move_bus_to_dedicated_package.py -y
    ```
