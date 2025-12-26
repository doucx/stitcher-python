好的，遵照指示。

我将创建一个计划，用于搭建 `stitcher-needle` 包的基础结构。这包括创建目录、符合 `uv` 工作区规范的 `pyproject.toml` 文件，以及设置必要的 `__init__.py` 文件以支持命名空间包。

## [WIP] feat: 搭建 stitcher-needle 零依赖包的骨架

### 用户需求
根据项目路线图，需要创建 `packages/stitcher-needle` 这个新的子包。它必须被正确集成到现有的 `uv` 工作区中，并从一开始就严格遵守“零依赖”的核心设计原则。

### 评论
这是实现“语义化寻址”架构的第一步，也是最关键的一步。通过建立一个干净、独立的 `stitcher-needle` 包，我们为整个项目未来的可维护性和架构纯粹性奠定了坚实的基础。

### 目标
1.  创建 `packages/stitcher-needle/src/stitcher/needle` 的目录结构。
2.  生成一个符合项目规范的 `pyproject.toml` 文件，其中 `dependencies` 列表必须为空。
3.  创建 `__init__.py` 文件，并添加命名空间包支持，确保它能与工作区中的其他 `stitcher-*` 包正确共存。

### 基本原理
我们将遵循项目中既定的 `src` 布局和 `hatchling` 构建配置，以确保新包的一致性。`pyproject.toml` 中将明确声明其零依赖的特性，这是 `stitcher-needle` 作为轻量级运行时的核心要求。`__init__.py` 中的 `extend_path` 调用是实现 `uv` 工作区内命名空间包无缝协作的标准做法。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #scope/core #ai/instruct #task/domain/runtime #task/object/needle-kernel #task/action/implementation #task/state/begin

---
### Script

#### Acts 1: 创建目录结构和 `__init__.py` 文件

首先，我们创建新包所需的完整目录结构，并生成支持命名空间包的 `__init__.py` 文件。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-needle/src/stitcher/needle
~~~~~

~~~~~act
write_file
packages/stitcher-needle/src/stitcher/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-needle/src/stitcher/needle/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

#### Acts 2: 创建 `pyproject.toml` 配置文件

接下来，我们创建 `pyproject.toml` 文件，定义包的元数据、构建系统，并明确其零依赖的特性。

~~~~~act
write_file
packages/stitcher-needle/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-needle"
version = "0.1.0"
description = "Zero-dependency semantic addressing runtime for Stitcher."
requires-python = ">=3.10"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~
