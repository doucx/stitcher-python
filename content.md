简要回答
好的，开始实施阶段一。我们将首先创建 `stitcher-refactor` 包的基础结构，并将其注册到工作区配置中。

## [WIP] feat: 初始化 stitcher-refactor 包结构

### 用户需求
根据 `Stitcher Refactor：架构蓝图与实施路线图 (v1.0)` 的阶段一要求，需要创建 `packages/stitcher-refactor` 包，配置其依赖（包括 Griffe 和 LibCST），并将其集成到项目的工作区配置中。

### 评论
这是重构引擎的物理载体。将其作为独立的包可以保持架构的清晰，并强制执行依赖边界（`refactor` 依赖 `application` 和 `spec`，而不是反过来）。

### 目标
1.  创建 `packages/stitcher-refactor` 及其标准目录结构。
2.  配置 `pyproject.toml`，声明对 `griffe`、`libcst` 以及 Stitcher 内部核心包的依赖。
3.  创建基础的 `__init__.py` 文件。
4.  更新根目录的 `pyproject.toml`，将新包注册到 `tool.uv.sources` 和 `tool.pyright.extraPaths`。

### 基本原理
-   **独立包策略**: 遵循 Monorepo 的分包原则，将重构逻辑与核心运行时隔离。
-   **依赖声明**: 显式声明 `griffe` 和 `libcst`，确保环境准备就绪。
-   **工作区集成**: 更新根配置以确保 IDE (Pyright) 和包管理器 (uv) 能正确解析新包。

### 标签
#intent/architect #flow/ready #priority/high #comp/build #task/domain/refactor #task/object/stitcher-refactor-pkg #task/action/setup #task/state/begin

---

### Script

#### Acts 1: 创建包目录结构
我们首先创建 `packages/stitcher-refactor` 的目录骨架。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-refactor/src/stitcher/refactor/engine
mkdir -p packages/stitcher-refactor/src/stitcher/refactor/operations
mkdir -p packages/stitcher-refactor/src/stitcher/refactor/sidecar
mkdir -p packages/stitcher-refactor/src/stitcher/refactor/migration
~~~~~

#### Acts 2: 创建 pyproject.toml
配置新包的元数据和依赖。

~~~~~act
write_file
packages/stitcher-refactor/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-refactor"
version = "0.1.0"
description = "Transactional refactoring engine for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-application",
    "griffe",
    "libcst",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-application = { workspace = true }
~~~~~

#### Acts 3: 创建基础 __init__.py
为了使包可被导入，我们需要创建 `__init__.py` 文件。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/__init__.py
~~~~~
~~~~~python
# This must be the very first line to allow this package to coexist with other
# namespace packages in editable installs.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

#### Acts 4: 注册到根工作区
更新根目录的 `pyproject.toml`，确保开发环境和 IDE 能够感知到新包。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
stitcher-cli = { workspace = true }
stitcher-test-utils = { workspace = true }

[tool.pytest.ini_options]
~~~~~
~~~~~toml.new
stitcher-cli = { workspace = true }
stitcher-test-utils = { workspace = true }
stitcher-refactor = { workspace = true }

[tool.pytest.ini_options]
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
    "packages/stitcher-test-utils/src"
]

[tool.stitcher.targets.stitcher]
~~~~~
~~~~~toml.new
    "packages/stitcher-test-utils/src",
    "packages/stitcher-refactor/src"
]

[tool.stitcher.targets.stitcher]
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
    "packages/stitcher-test-utils/src",
]
stub_package = "packages/stitcher-stubs"
~~~~~
~~~~~toml.new
    "packages/stitcher-test-utils/src",
    "packages/stitcher-refactor/src",
]
stub_package = "packages/stitcher-stubs"
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
    "packages/needle-stubs/src",
]
~~~~~
~~~~~toml.new
    "packages/needle-stubs/src",
    "packages/stitcher-refactor/src",
]
~~~~~

### 下一步建议
接下来，我们将按照路线图，实现核心的基础设施组件。
建议先实现 `TransactionManager` 的原型，因为它定义了文件操作的接口，后续的 `SemanticGraph` 和 `Operations` 都将依赖它来进行副作用的隔离。
