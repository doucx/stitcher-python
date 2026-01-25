既然 `pyneedle` 及其子包已经成功发布到 PyPI，我们现在可以将 `Stitcher` 从本地路径依赖切换到正式的 PyPI 版本依赖。这将使 `Stitcher` 的构建更加独立和可重现。

## [WIP] chore: 将 stitcher 依赖从本地 pyneedle 切换为 PyPI 版本

### 用户需求

更新 `Stitcher` monorepo 中所有涉及 `pyneedle` 系列包的依赖，将其从本地开发路径（`path = "../Needle/..."`）切换为 PyPI 正式版本（`0.1.0`）。

### 评论

这是 `Stitcher` 走向独立发布的关键一步。通过解除与 `Needle` 源码目录的物理耦合，`Stitcher` 现在可以由任何开发者在不克隆 `Needle` 仓库的情况下进行构建和测试。

### 目标

1.  更新所有子包的 `pyproject.toml`，为 `pyneedle` 相关依赖添加版本约束 `== 0.1.0`。
2.  更新根目录的 `pyproject.toml`，修正 `dependencies` 和 `dev` 依赖。
3.  **关键步骤**: 从根目录 `pyproject.toml` 的 `[tool.uv.sources]` 中移除所有指向 `../Needle/` 的路径映射。

### 基本原理

由于 `pyneedle` 已在 PyPI 上可用，`uv` 或 `pip` 现在可以直接通过包名和版本号解析它们。通过移除 `[tool.uv.sources]` 中的本地路径覆盖，我们强制构建系统使用外部发布的包。我们将所有依赖统一固定在 `0.1.0` 版本，以确保与当前的 `Stitcher` 代码完全兼容。

### 标签

#intent/tooling #flow/ready #priority/high #comp/build #concept/config #scope/dx #ai/instruct #task/domain/tooling #task/object/dependency-migration #task/action/pypi-integration #task/state/begin

---

### Script

#### Acts 1: 更新子包依赖

我们将修正各个子包中对 `pyneedle` 组件的声明。

~~~~~act
patch_file
packages/stitcher-spec/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle-pointer",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle-pointer == 0.1.0",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-bus/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle-pointer",
    "pyneedle-spec",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle-pointer == 0.1.0",
    "pyneedle-spec == 0.1.0",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-index",
    "stitcher-workspace",
    "pyneedle-pointer",
    "griffe",
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-index",
    "stitcher-workspace",
    "pyneedle-pointer == 0.1.0",
    "griffe",
~~~~~

~~~~~act
patch_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-lang-python",
    "stitcher-lang-sidecar",
    "stitcher-stubgen",
    "stitcher-workspace",
    "stitcher-index",
    "stitcher-analysis",
    "pyneedle",
]
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-lang-python",
    "stitcher-lang-sidecar",
    "stitcher-stubgen",
    "stitcher-workspace",
    "stitcher-index",
    "stitcher-analysis",
    "pyneedle == 0.1.0",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-application",
    "stitcher-lang-python",
    "pyneedle",
    "typer",
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-application",
    "stitcher-lang-python",
    "pyneedle == 0.1.0",
    "typer",
~~~~~

~~~~~act
patch_file
packages/stitcher-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle",
    "PyYAML",
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle == 0.1.0",
    "PyYAML",
~~~~~

#### Acts 2: 更新根目录配置并移除本地路径映射

这是最重要的部分，它将彻底切断与 `../Needle` 目录的联系。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle",
    "pyneedle-pointer",
    "pyneedle-spec",
    "stitcher-cli",
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle == 0.1.0",
    "pyneedle-pointer == 0.1.0",
    "pyneedle-spec == 0.1.0",
    "stitcher-cli",
~~~~~

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
    "pyneedle == 0.1.0",
    "pyneedle-pointer == 0.1.0",
    "pyneedle-spec == 0.1.0",
    "stitcher-cli",
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
stitcher-analysis = { workspace = true }
stitcher-bus = { workspace = true }
pyneedle = { path = "../Needle/packages/pyneedle", editable = true }
pyneedle-pointer = { path = "../Needle/packages/pyneedle-pointer", editable = true }
pyneedle-spec = { path = "../Needle/packages/pyneedle-spec", editable = true }
pyneedle-runtime = { path = "../Needle/packages/pyneedle-runtime", editable = true }

[tool.pytest.ini_options]
~~~~~
~~~~~toml.new
stitcher-analysis = { workspace = true }
stitcher-bus = { workspace = true }

[tool.pytest.ini_options]
~~~~~

### 下一步建议

1.  **重置环境**: 执行 `rm uv.lock`（可选但推荐）并运行 `uv sync`。这将强制 `uv` 从 PyPI 下载正式包。
2.  **验证**: 运行 `pip list | grep pyneedle` 确认包来源已不再显示为本地路径。
3.  **回归测试**: 运行 `pytest` 确保一切工作正常。

如果你准备好执行这些修改，请告知我，或者你可以直接运行这些 `act`。
