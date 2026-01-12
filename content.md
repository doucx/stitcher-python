好的，依赖关系调整是模块重构后的关键一步。我将生成一个计划来更新 `stitcher-analysis` 和 `stitcher-refactor` 的 `pyproject.toml` 文件，以正确反映 `SemanticGraph` 的新家。

## [WIP] chore: 更新 SemanticGraph 迁移后的包依赖关系

### 用户需求

在 `SemanticGraph` 从 `stitcher-refactor` 移动到 `stitcher-analysis` 后，需要更新 `pyproject.toml` 文件来反映新的依赖关系。

### 评论

这是一个必要的维护步骤，以确保我们的 monorepo 依赖图保持正确和一致。此更改将正式确立 `stitcher-refactor` 对 `stitcher-analysis` 的依赖，符合我们“脑手分离”的架构目标。

### 目标

1.  为 `stitcher-analysis` 添加 `griffe` 和 `stitcher-workspace` 依赖，因为 `SemanticGraph` 需要它们。
2.  为 `stitcher-refactor` 添加对 `stitcher-analysis` 的依赖。
3.  从 `stitcher-refactor` 中移除不再需要的 `griffe` 依赖。

### 基本原理

`SemanticGraph` 的核心功能依赖于 `griffe` 来解析代码和 `stitcher-workspace` 来理解项目结构。既然 `SemanticGraph` 现在是 `stitcher-analysis` 的一部分，这些依赖项也必须随之迁移。

相应地，`stitcher-refactor` 现在作为一个消费者，需要显式依赖 `stitcher-analysis` 来获取图谱服务，同时它自身不再直接与 `griffe` 交互，因此可以移除该依赖。

### 标签

#intent/tooling #flow/ready #priority/high #comp/build #comp/analysis #comp/refactor #scope/dx #task/domain/refactor #task/object/dependency-graph #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新 `stitcher-analysis` 的依赖

我们将 `griffe` 和 `stitcher-workspace` 添加到 `stitcher-analysis` 的依赖项中。

~~~~~act
patch_file
packages/stitcher-analysis/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-index",
    "stitcher-config",
    "pyneedle-pointer",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-config = { workspace = true }
pyneedle-pointer = { workspace = true }
~~~~~
~~~~~toml
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-index",
    "stitcher-config",
    "stitcher-workspace",
    "pyneedle-pointer",
    "griffe",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-config = { workspace = true }
pyneedle-pointer = { workspace = true }
stitcher-workspace = { workspace = true }
~~~~~

#### Acts 2: 更新 `stitcher-refactor` 的依赖

我们将 `griffe` 替换为 `stitcher-analysis`。

~~~~~act
patch_file
packages/stitcher-refactor/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "stitcher-lang-python",
    "stitcher-spec",
    "stitcher-common",
    "stitcher-workspace",
    "griffe",
    "libcst",
    "tomli>=2.0.1; python_version < '3.11'",
    "stitcher-index",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-lang-python = { workspace = true }
stitcher-workspace = { workspace = true }
~~~~~
~~~~~toml
dependencies = [
    "stitcher-lang-python",
    "stitcher-spec",
    "stitcher-common",
    "stitcher-workspace",
    "stitcher-analysis",
    "libcst",
    "tomli>=2.0.1; python_version < '3.11'",
    "stitcher-index",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-lang-python = { workspace = true }
stitcher-workspace = { workspace = true }
stitcher-analysis = { workspace = true }
~~~~~

### 下一步建议

依赖更新完成后，建议在项目根目录运行 `uv sync` 命令。这将验证新的依赖关系是否正确解析，并更新你的虚拟环境。
