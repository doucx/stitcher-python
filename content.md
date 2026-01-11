好的，我们继续执行重构计划。现在，我们将更新整个代码库，使其适应新的 `stitcher-workspace` 包。这包括修改所有 `import` 语句，以及调整各个包的 `pyproject.toml` 文件来声明正确的依赖关系。

## [WIP] feat(arch): 全局迁移 Workspace 的依赖和导入

### 用户需求

在 `stitcher-workspace` 包创建完成后，需要更新整个项目，将所有对旧 `stitcher.refactor.workspace.Workspace` 的引用切换到新的 `stitcher.workspace.Workspace`。同时，必须修正各个包的依赖关系，确保 `stitcher-application` 等核心包不再错误地依赖 `stitcher-refactor`。

### 评论

这是重构的核心执行阶段。通过批量修改 `import` 语句和 `pyproject.toml` 文件，我们将消除错误的模块间耦合，使项目的依赖关系图恢复健康。这一步完成后，`Workspace` 将正式成为一个被所有相关方正确依赖的核心共享组件，架构的清晰度和健壮性将得到实质性提升。

### 目标

1.  修改 `stitcher-application`、`stitcher-refactor` 和 `stitcher-test-utils` 的 `pyproject.toml`，使其正确依赖 `stitcher-workspace`。
2.  从 `stitcher-application` 的依赖中移除 `stitcher-refactor`。
3.  使用 `sed` 命令在整个项目中原子化地、全局地将 `from stitcher.refactor.workspace import Workspace` 替换为 `from stitcher.workspace import Workspace`。
4.  清理 `stitcher-refactor` 包中因 `Workspace` 模块移出而不再需要的 `__init__.py` 条目。

### 基本原理

我们采用“依赖倒置”原则。高层模块（如 `application`）和功能模块（如 `refactor`）都应依赖于抽象或基础组件（如 `workspace`），而不是相互依赖。通过精确修改 `pyproject.toml`，我们重新定义了模块间的契约。同时，使用全局命令式工具（如 `sed`）可以确保所有代码文件中的引用都被一致、快速地更新，避免了手动修改可能带来的遗漏。

### 标签

#intent/refine #flow/ready #priority/high #comp/build #scope/core #scope/dx #ai/instruct #task/domain/architecture #task/object/workspace-component #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新各包的 pyproject.toml 依赖

首先，我们修正 `application`, `refactor`, 和 `test-utils` 三个核心包的依赖关系。

修改 `stitcher-application`，使其依赖 `stitcher-workspace` 而不是 `stitcher-refactor`。
~~~~~act
patch_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml
    "stitcher-stubgen",
    "stitcher-refactor",
    "stitcher-index",
    "pyneedle",
~~~~~
~~~~~toml
    "stitcher-stubgen",
    "stitcher-workspace",
    "stitcher-index",
    "pyneedle",
~~~~~

~~~~~act
patch_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml
stitcher-stubgen = { workspace = true }
stitcher-refactor = { workspace = true }
stitcher-index = { workspace = true }
pyneedle = { workspace = true }
~~~~~
~~~~~toml
stitcher-stubgen = { workspace = true }
stitcher-workspace = { workspace = true }
stitcher-index = { workspace = true }
pyneedle = { workspace = true }
~~~~~

修改 `stitcher-refactor`，为其添加对新 `stitcher-workspace` 包的依赖。
~~~~~act
patch_file
packages/stitcher-refactor/pyproject.toml
~~~~~
~~~~~toml
    "stitcher-common",
    "griffe",
    "libcst",
~~~~~
~~~~~toml
    "stitcher-common",
    "stitcher-workspace",
    "griffe",
    "libcst",
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/pyproject.toml
~~~~~
~~~~~toml
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-python-analysis = { workspace = true }
~~~~~
~~~~~toml
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-python-analysis = { workspace = true }
stitcher-workspace = { workspace = true }
~~~~~

修改 `stitcher-test-utils`，为其添加对 `stitcher-workspace` 的显式依赖，修复潜在的隐式依赖问题。
~~~~~act
patch_file
packages/stitcher-test-utils/pyproject.toml
~~~~~
~~~~~toml
    "stitcher-application",
    "stitcher-python-adapter",
    "stitcher-index",
]
~~~~~
~~~~~toml
    "stitcher-application",
    "stitcher-python-adapter",
    "stitcher-index",
    "stitcher-workspace",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-test-utils/pyproject.toml
~~~~~
~~~~~toml
pyneedle = { workspace = true }
stitcher-application = { workspace = true }
stitcher-python-adapter = { workspace = true }
~~~~~
~~~~~toml
pyneedle = { workspace = true }
stitcher-application = { workspace = true }
stitcher-python-adapter = { workspace = true }
stitcher-workspace = { workspace = true }
~~~~~

#### Acts 2: 全局替换 Workspace 的 import 语句

现在，我们使用 `find` 和 `sed` 命令，在整个 `packages` 目录下查找并替换所有 Python 文件中对旧 `Workspace` 路径的导入。

~~~~~act
run_command
~~~~~
~~~~~
find packages -type f -name "*.py" -exec sed -i 's/from stitcher.refactor.workspace import Workspace/from stitcher.workspace import Workspace/g' {} +
~~~~~

#### Acts 3: 清理 stitcher.refactor 包

最后，清理 `stitcher-refactor` 包中残留的、与 `Workspace` 相关的 `__init__.py` 导出声明。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/__init__.py
~~~~~
~~~~~python
# This must be the very first line to allow this package to coexist with other
# namespace packages in editable installs.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

### 下一步建议

我们已经成功地将 `Workspace` 组件重构到了一个新的核心包中，并更新了所有相关的代码和配置。

下一步，我们将继续执行代码审查报告中的第二项建议：**合并 `WorkspaceScanner` 的职责到 `Workspace`**。这将进一步消除代码重复，使 `Workspace` 成为项目文件系统信息的唯一权威来源。

如果你同意，我将开始分析 `WorkspaceScanner` 的实现，并制定一个计划将其文件发现逻辑迁移到 `Workspace` 类中。
