好的，我们开始实施 **Phase 2: 图能力增强 (Graph Capability)** 的第一步：引入图计算基础设施。

我将生成一个计划，该计划会创建所需的目录结构，并向 `stitcher-analysis` 包中添加 `networkx` 依赖。

## [WIP] feat: Introduce graph computation infrastructure to stitcher-analysis

### 用户需求

根据 Phase 2 实施路线图，我们需要为 `stitcher-analysis` 包引入图计算的基础设施。这包括：
1.  添加 `networkx` 作为新的项目依赖。
2.  创建 `stitcher/analysis/graph/` 目录以及其中的初始 Python 模块文件。

### 评论

这是实现全局架构分析（如循环依赖检测）的第一块基石。通过建立标准化的目录结构并引入成熟的图计算库，我们为后续的图构建器和算法实现铺平了道路。这是一个清晰、低风险且至关重要的步骤。

### 目标

1.  在 `packages/stitcher-analysis/src/stitcher/analysis/` 目录下创建 `graph/` 子目录。
2.  在 `graph/` 目录中创建 `__init__.py`, `builder.py`, `types.py`, 和 `algorithms.py` 四个空的 Python 文件。
3.  更新 `packages/stitcher-analysis/pyproject.toml` 文件，将 `networkx` 添加到 `dependencies` 列表中。

### 基本原理

我们将使用 `run_command` 结合 `mkdir -p` 和 `touch` 来原子化地创建整个目录结构和所需文件，这是最高效的方式。随后，使用 `patch_file` 操作，精确地将 `networkx` 添加到 `pyproject.toml` 的依赖项列表中，确保对现有配置的最小化修改。

### 标签

#intent/build #flow/ready #priority/high #comp/analysis #concept/graph #scope/core #scope/dx #ai/instruct #task/domain/analysis #task/object/graph-infra #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建图基础设施目录和文件

我们首先创建 `graph` 目录及其内部的所有初始模块文件。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-analysis/src/stitcher/analysis/graph
touch packages/stitcher-analysis/src/stitcher/analysis/graph/__init__.py
touch packages/stitcher-analysis/src/stitcher/analysis/graph/builder.py
touch packages/stitcher-analysis/src/stitcher/analysis/graph/types.py
touch packages/stitcher-analysis/src/stitcher/analysis/graph/algorithms.py
~~~~~

#### Acts 2: 添加 `networkx` 依赖

接下来，我们将 `networkx` 添加到 `stitcher-analysis` 包的依赖项中。

~~~~~act
patch_file
packages/stitcher-analysis/pyproject.toml
~~~~~
~~~~~toml.old
    "pyneedle-pointer",
    "griffe",
]
~~~~~
~~~~~toml.new
    "pyneedle-pointer",
    "griffe",
    "networkx",
]
~~~~~

### 下一步建议

基础设施已经就绪。下一步是根据路线图的第二部分，**扩展 `stitcher-spec` 中的 `IndexStoreProtocol`**，为其添加批量获取所有文件和所有引用的能力，以便图构建器能够高效地拉取全量数据。如果你同意，我将开始准备这一步的计划。
