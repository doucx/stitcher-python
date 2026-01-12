根据 **Stitcher 架构重构路线图** 的阶段二规划，我现在开始构建 `stitcher-lang-python` 包的骨架，并将其集成到 Monorepo 的工作区中。

## [WIP] feat: 初始化 stitcher-lang-python 包骨架

### 用户需求
在 `packages/` 目录下创建新包 `stitcher-lang-python` 的结构，建立符合协议的命名空间初始化文件，并更新全局配置以支持该新包。

### 评论
这是合并语言能力的关键一步。通过将 `python-adapter` 和 `python-analysis` 的功能整合进统一的 `lang-python` 插件模型，我们将消除冗余的物理隔离，并为后续的重构引擎泛化（阶段四）打下基础。

### 目标
1.  创建 `packages/stitcher-lang-python` 目录结构。
2.  建立符合 `pkgutil` 扩展协议的 `__init__.py` 文件，确保命名空间包能够正确协同工作。
3.  配置 `stitcher-lang-python` 的 `pyproject.toml`，声明对 `spec`、`common`、`libcst` 和 `griffe` 的依赖。
4.  更新根目录 `pyproject.toml`，将新包纳入 `uv` 工作区管理、`pytest` 路径和 `pyright` 类型检查范围。

### 基本原理
我们遵循 Python 命名空间包的标准做法，在顶级 `stitcher` 目录下使用 `extend_path`。新包的设计目标是作为 Python 语言的完整适配层，因此它直接依赖于底层的 `spec` 定义。

### 标签
#intent/build #flow/ready #priority/high
#comp/build #concept/parser #scope/dx
#ai/instruct
#task/domain/language-support
#task/object/stitcher-lang-python
#task/action/initialization
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 创建 stitcher-lang-python 基础结构

首先创建目录并写入初始化文件和项目配置。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-lang-python/src/stitcher/lang/python
~~~~~

~~~~~act
write_file
packages/stitcher-lang-python/src/stitcher/__init__.py
~~~~~
~~~~~python
# This allows this package to coexist with other distribution packages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-lang-python/src/stitcher/lang/__init__.py
~~~~~
~~~~~python
# This allows this package to coexist with other distribution packages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-lang-python/src/stitcher/lang/python/__init__.py
~~~~~
~~~~~python
"""Python language support for Stitcher."""
~~~~~

~~~~~act
write_file
packages/stitcher-lang-python/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-lang-python"
version = "0.1.0"
description = "Unified Python language support for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "libcst>=1.1.0",
    "griffe>=0.36.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~

#### Acts 2: 更新根目录 pyproject.toml 配置

将新包注册到全局工作区和开发环境中。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "pytest-timeout",
    "pytest-mock",
    "ruff",
    "mypy",
    "pyneedle",
    "pyneedle-pointer",
    "pyneedle-spec",
    "stitcher-cli",
    "stitcher-application",
    "stitcher-stubgen",
    "stitcher-test-utils",
    "stitcher-refactor",
    "stitcher-index",
    "stitcher-workspace",
]

[tool.setuptools.packages.find]
exclude = ["migrations*"]

[tool.uv.workspace]
members = ["packages/*", "packages/stitcher-test-utils", "packages/stitcher-python-analysis", "packages/stitcher-index"]

[tool.uv.sources]
~~~~~
~~~~~toml.new
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "pytest-timeout",
    "pytest-mock",
    "ruff",
    "mypy",
    "pyneedle",
    "pyneedle-pointer",
    "pyneedle-spec",
    "stitcher-cli",
    "stitcher-application",
    "stitcher-stubgen",
    "stitcher-test-utils",
    "stitcher-refactor",
    "stitcher-index",
    "stitcher-workspace",
    "stitcher-lang-python",
]

[tool.setuptools.packages.find]
exclude = ["migrations*"]

[tool.uv.workspace]
members = [
    "packages/*",
    "packages/stitcher-test-utils",
    "packages/stitcher-python-analysis",
    "packages/stitcher-index",
    "packages/stitcher-lang-python",
]

[tool.uv.sources]
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
stitcher-refactor = { workspace = true }
stitcher-index = { workspace = true }
stitcher-python-analysis = { workspace = true }
stitcher-workspace = { workspace = true }

[tool.pytest.ini_options]
addopts = "-ra --cov=stitcher --cov=needle --cov-report=term-missing"
testpaths = ["tests", "packages"]
norecursedirs = ["tests/fixtures"]
pythonpath = [
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-common/src",
    "packages/stitcher-config/src",
    "packages/stitcher-index/src",
    "packages/stitcher-python-adapter/src",
    "packages/stitcher-python-analysis/src",
    "packages/stitcher-refactor/src",
    "packages/stitcher-spec/src",
    "packages/stitcher-workspace/src",
    "packages/stitcher-stubgen/src",
    "packages/stitcher-test-utils/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle-spec/src",
]

[tool.stitcher.targets.stitcher]
scan_paths = [
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-common/src",
    "packages/stitcher-config/src",
    "packages/stitcher-index/src",
    "packages/stitcher-python-adapter/src",
    "packages/stitcher-python-analysis/src",
    "packages/stitcher-refactor/src",
    "packages/stitcher-spec/src",
    "packages/stitcher-stubgen/src",
    "packages/stitcher-workspace/src",
    "packages/stitcher-test-utils/src",
]
~~~~~
~~~~~toml.new
stitcher-refactor = { workspace = true }
stitcher-index = { workspace = true }
stitcher-python-analysis = { workspace = true }
stitcher-workspace = { workspace = true }
stitcher-lang-python = { workspace = true }

[tool.pytest.ini_options]
addopts = "-ra --cov=stitcher --cov=needle --cov-report=term-missing"
testpaths = ["tests", "packages"]
norecursedirs = ["tests/fixtures"]
pythonpath = [
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-common/src",
    "packages/stitcher-config/src",
    "packages/stitcher-index/src",
    "packages/stitcher-python-adapter/src",
    "packages/stitcher-python-analysis/src",
    "packages/stitcher-refactor/src",
    "packages/stitcher-spec/src",
    "packages/stitcher-workspace/src",
    "packages/stitcher-stubgen/src",
    "packages/stitcher-test-utils/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-runtime/src",
    "packages/pyneedle-spec/src",
    "packages/stitcher-lang-python/src",
]

[tool.stitcher.targets.stitcher]
scan_paths = [
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-common/src",
    "packages/stitcher-config/src",
    "packages/stitcher-index/src",
    "packages/stitcher-python-adapter/src",
    "packages/stitcher-python-analysis/src",
    "packages/stitcher-refactor/src",
    "packages/stitcher-spec/src",
    "packages/stitcher-stubgen/src",
    "packages/stitcher-workspace/src",
    "packages/stitcher-test-utils/src",
    "packages/stitcher-lang-python/src",
]
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
    "packages/stitcher-index/src",
    "packages/stitcher-workspace/src",
]
~~~~~
~~~~~toml.new
    "packages/stitcher-index/src",
    "packages/stitcher-workspace/src",
    "packages/stitcher-lang-python/src",
]
~~~~~

### 下一步建议
1.  **迁移解析能力**：按照路线图 2.2，开始将 `stitcher-python-adapter` 中的 Griffe 和 LibCST 解析代码迁移到 `stitcher-lang-python` 对应的子目录下。
2.  **验证环境**：运行 `uv sync` 确保新包及其依赖被正确安装在本地虚拟环境中。
