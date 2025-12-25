简要回答：
好的，我将根据架构蓝图，使用 `uv` 工作区模式构建 Stitcher-Python 的项目骨架。这将包括根目录配置以及七个核心子包的结构初始化，并提供一个最小可运行的 CLI 入口。

## [WIP] feat: 初始化 Stitcher-Python 项目骨架与 uv 工作区

### 用户需求
用户需要根据 `Stitcher-Python 架构蓝图` 完成 **任务 1.1**，即搭建基于 `uv` 的 Monorepo 项目骨架。这包括配置根目录的 `pyproject.toml`，创建 `packages/` 下的所有子包结构（`spec`, `common`, `scanner`, `io`, `config`, `application`, `cli`），并确保它们之间的依赖关系和命名空间设置正确。

### 评论
这是一个标准的 Monorepo 初始化任务。我们严格遵循 Cascade 的工程实践：使用显式命名空间包 (`pkgutil`) 来确保 IDE 兼容性，利用 `uv` 的工作区功能来管理本地依赖。这将为后续的模块化开发打下坚实的基础。

### 目标
1.  配置根目录 `pyproject.toml`，定义 `uv` 工作区和开发依赖。
2.  创建所有 7 个子包的目录结构。
3.  为每个子包创建 `pyproject.toml`，正确声明包名和依赖。
4.  在每个子包的 `__init__.py` 中添加 `pkgutil` 命名空间声明。
5.  在 `stitcher-cli` 中创建一个最小化的 `typer` 应用骨架，验证链路连通性。

### 基本原理
通过 `uv` 的 `tool.uv.sources` 和 `workspace` 功能，我们可以将本地的 `packages/` 目录直接链接到开发环境中，无需反复安装。采用显式命名空间包（Explicit Namespace Packages）是避免 Pylance/MyPy 解析错误的关键，这在 Cascade 项目中已被验证为最佳实践。

### 标签
#intent/build #flow/ready #priority/high
#comp/build #scope/core #ai/instruct
#task/domain/infra #task/object/project-skeleton #task/action/init
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 创建目录结构
我们首先创建项目所需的目录结构，包括根目录下的 `packages` 文件夹以及各个子包的 `src/stitcher/<module>` 路径。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-spec/src/stitcher/spec
mkdir -p packages/stitcher-common/src/stitcher/common
mkdir -p packages/stitcher-scanner/src/stitcher/scanner
mkdir -p packages/stitcher-io/src/stitcher/io
mkdir -p packages/stitcher-config/src/stitcher/config
mkdir -p packages/stitcher-application/src/stitcher/app
mkdir -p packages/stitcher-cli/src/stitcher/cli
mkdir -p tests/unit
mkdir -p tests/integration
~~~~~

#### Acts 2: 配置根工作区
创建根目录的 `pyproject.toml`，配置 `uv` 工作区成员和全局开发依赖。

~~~~~act
write_file
pyproject.toml
~~~~~
~~~~~toml
[project]
name = "stitcher-python"
version = "0.1.0"
description = "Stitching the gap between dynamic code and static analysis."
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "ruff",
    "mypy",
    "stitcher-cli",
    "stitcher-application",
]

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
stitcher-config = { workspace = true }
stitcher-application = { workspace = true }
stitcher-cli = { workspace = true }

[tool.pytest.ini_options]
addopts = "-ra -q"
testpaths = ["tests"]
pythonpath = ["packages/stitcher-spec/src", "packages/stitcher-common/src", "packages/stitcher-scanner/src", "packages/stitcher-io/src", "packages/stitcher-config/src", "packages/stitcher-application/src", "packages/stitcher-cli/src"]
~~~~~

#### Acts 3: 初始化基础层 (Spec & Common)
配置最底层的 `stitcher-spec` (IR 定义) 和 `stitcher-common` (工具与协议)。

~~~~~act
write_file
packages/stitcher-spec/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-spec"
version = "0.1.0"
description = "Intermediate Representation (IR) models for Stitcher."
requires-python = ">=3.10"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python
# This must be the very first line to allow this package to coexist with other
# namespace packages in editable installs.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-common/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-common"
version = "0.1.0"
description = "Common utilities and protocols for Stitcher."
requires-python = ">=3.10"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

#### Acts 4: 初始化功能层 (Scanner, IO, Config)
这些包依赖于 `spec` 和 `common`。

~~~~~act
write_file
packages/stitcher-scanner/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-scanner"
version = "0.1.0"
description = "AST scanner and parser for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~

~~~~~act
write_file
packages/stitcher-scanner/src/stitcher/scanner/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-io/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-io"
version = "0.1.0"
description = "File I/O and persistence layer for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "PyYAML",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~

~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-config/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-config"
version = "0.1.0"
description = "Configuration loading and workspace discovery for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "tomli; python_version < '3.11'",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~

~~~~~act
write_file
packages/stitcher-config/src/stitcher/config/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

#### Acts 5: 初始化应用层 (Application)
应用层作为编排者，依赖所有底层包。

~~~~~act
write_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

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

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-scanner = { workspace = true }
stitcher-io = { workspace = true }
stitcher-config = { workspace = true }
~~~~~

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

#### Acts 6: 初始化 CLI 层
CLI 层依赖应用层，并定义 entry-point。

~~~~~act
write_file
packages/stitcher-cli/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-cli"
version = "0.1.0"
description = "Command-line interface for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-application",
    "typer[all]",
]

[project.scripts]
stitcher = "stitcher.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-application = { workspace = true }
~~~~~

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python
import typer

app = typer.Typer(
    name="stitcher",
    help="Stitcher-Python: Bridging the gap between dynamic code and static analysis.",
    no_args_is_help=True,
)

@app.command()
def init():
    """Initialize Stitcher in the current project."""
    typer.echo("Initializing Stitcher... (TODO)")

@app.command()
def generate():
    """Generate .pyi stubs from source code and docs."""
    typer.echo("Generating stubs... (TODO)")

@app.command()
def check():
    """Verify consistency between code and docs."""
    typer.echo("Checking consistency... (TODO)")

if __name__ == "__main__":
    app()
~~~~~

### 下一步建议
1.  执行 `uv sync` 安装依赖并构建虚拟环境。
2.  运行 `stitcher --help` 验证 CLI 是否正确安装和响应。
3.  开始实现 `stitcher-spec` 中的 IR 数据模型。
