好的，遵照指示，我们开始实施第一步：创建 `stitcher-stubgen` 包并将其集成到我们的 monorepo 工作区中。

我将生成一个计划，该计划会创建必要的目录和文件，并更新根 `pyproject.toml` 以识别这个新包。

## [WIP] feat(arch): Create stitcher-stubgen package

### 用户需求

根据我们的架构重构决策，需要创建 `stitcher-stubgen` 包的基础结构。这包括创建目录、定义其 `pyproject.toml`，并将其整合到整个 monorepo 的构建和测试体系（UV Workspace, Pytest, Pyright）中。

### 评论

这是将存根生成能力从 `stitcher-application` 中解耦出来的关键第一步。通过首先建立新包的“物理边界”和“契约”（`pyproject.toml`），我们为后续平稳、安全地迁移代码逻辑奠定了坚实的基础。此举完全符合我们分离关注点和建立清晰领域边界的架构原则。

### 目标

1.  创建 `packages/stitcher-stubgen` 的标准目录结构。
2.  为 `stitcher-stubgen` 创建一个 `pyproject.toml` 文件，明确其名称、描述和对 `stitcher-spec` 与 `stitcher-common` 的依赖。
3.  更新根 `pyproject.toml`，将 `stitcher-stubgen` 添加到 UV Workspace、Pytest 的 `pythonpath`、Pyright 的 `extraPaths` 以及开发依赖中。

### 基本原理

我们采用“基础先行”的策略。首先通过 `mkdir` 和 `touch` 快速搭建起新包的骨架。然后，使用 `write_file` 定义新包的元数据和依赖关系。最后，通过对根 `pyproject.toml` 的一系列 `patch_file` 操作，将新包无缝地“注册”到 monorepo 的工具链中。这种方法确保了在迁移任何一行代码之前，整个项目的结构和环境都是一致且可用的，从而将风险降至最低。

### 标签

#intent/architect #flow/ready #priority/high #comp/build #scope/dx #task/domain/architecture #task/object/stubgen-package #task/action/scaffolding #task/state/begin

---

### Script

#### Acts 1: 创建目录与基础文件

首先，我们创建 `stitcher-stubgen` 包所需的完整目录结构和空的 `__init__.py` / `py.typed` 文件。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-stubgen/src/stitcher/stubgen
touch packages/stitcher-stubgen/src/stitcher/stubgen/__init__.py
touch packages/stitcher-stubgen/src/stitcher/stubgen/py.typed
~~~~~

#### Acts 2: 定义 `stitcher-stubgen` 的 `pyproject.toml`

接下来，我们为新包创建 `pyproject.toml`，定义其身份和依赖关系。

~~~~~act
write_file
packages/stitcher-stubgen/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-stubgen"
version = "0.1.0"
description = "Specialized stub generation engine for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-config",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-config = { workspace = true }
~~~~~

#### Acts 3: 将新包集成到 Monorepo 工作区

最后，我们更新根 `pyproject.toml`，让整个项目环境感知到 `stitcher-stubgen` 的存在。

这是对开发依赖的更新。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
    "stitcher-application",
    "stitcher-test-utils",
    "stitcher-refactor",
]
~~~~~
~~~~~toml
    "stitcher-application",
    "stitcher-stubgen",
    "stitcher-test-utils",
    "stitcher-refactor",
]
~~~~~

这是对 UV 工作区源的更新。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
stitcher-cli = { workspace = true }
stitcher-test-utils = { workspace = true }
stitcher-refactor = { workspace = true }
~~~~~
~~~~~toml
stitcher-cli = { workspace = true }
stitcher-stubgen = { workspace = true }
stitcher-test-utils = { workspace = true }
stitcher-refactor = { workspace = true }
~~~~~

这是对 Pytest `pythonpath` 的更新。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
    "packages/stitcher-test-utils/src",
    "packages/stitcher-refactor/src"
]
~~~~~
~~~~~toml
    "packages/stitcher-test-utils/src",
    "packages/stitcher-refactor/src",
    "packages/stitcher-stubgen/src"
]
~~~~~

这是对 Pyright `extraPaths` 的更新。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
    "packages/needle-stubs/src",
    "packages/stitcher-refactor/src",
]
~~~~~
~~~~~toml
    "packages/needle-stubs/src",
    "packages/stitcher-refactor/src",
    "packages/stitcher-stubgen/src",
]
~~~~~

### 下一步建议

我们已经成功地为 `stitcher-stubgen` 包搭建了骨架并将其融入了项目。

下一步，我们将执行**第 2 步：逻辑迁移**。我会生成一个新的计划，将 `PythonStubGenerator`、`GenerateRunner` 和 `StubPackageManager` 的代码从它们原来的位置移动到这个新创建的包中。
