好的，收到 `rg` 分析结果。这些残留的导入路径是预料之中的，现在我们将使用 `sed` 这一精确的“外科手术”工具来完成重构的最后一步：修复代码中的所有引用，以恢复系统的内部一致性。

## [WIP] refactor: Fix import paths after config/workspace merge

### 用户需求

使用 `sed` 命令修复因 `stitcher-config` 并入 `stitcher-workspace` 以及 `workspace.py` 重命名为 `core.py` 而导致的所有损坏的 Python 导入路径。

### 评论

这是一个典型的“大规模重构”后的清理阶段。物理文件的移动只是第一步，确保整个代码库的逻辑引用与新的物理结构保持一致是恢复系统可工作性的关键。使用 `sed` 是一种高效、可脚本化的方式，完全符合“正规军”的工程标准。

### 目标

1.  将所有对 `stitcher.workspace.workspace` 的导入重定向到 `stitcher.workspace.core`。
2.  将所有对 `stitcher.config` 的导入重定向到 `stitcher.workspace`。

### 基本原理

我们收到了用户提供的 `rg` 输出，这为我们提供了需要修复的目标文件的精确清单。我们将构造两个独立的 `sed` 命令，每个命令针对一类特定的导入问题。这种方法确保了操作的原子性和清晰性，并且每个命令都只影响其预期的目标，避免了意外的副作用。

### 标签

#intent/refine #flow/ready #priority/high #comp/config #comp/workspace #scope/core #scope/dx #ai/instruct #task/domain/architecture #task/object/package-merge #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重定向 `workspace.workspace` 到 `workspace.core`

根据 `rg` 的分析，以下文件仍然在引用已被重命名的旧模块路径。我们将修正它们。

~~~~~act
run_command
~~~~~
~~~~~sh
sed -i 's/from stitcher.workspace.workspace import find_workspace_root/from stitcher.workspace.core import find_workspace_root/g' \
  packages/stitcher-cli/src/stitcher/cli/factories.py \
  packages/stitcher-workspace/tests/unit/test_workspace.py
~~~~~

#### Acts 2: 重定向 `stitcher.config` 到 `stitcher.workspace`

以下文件仍然在引用已被删除的 `stitcher.config` 包。我们将把这些导入全部重定向到新的权威位置 `stitcher.workspace`。

~~~~~act
run_command
~~~~~
~~~~~sh
sed -i 's/from stitcher.config/from stitcher.workspace/g' \
  packages/stitcher-stubgen/src/stitcher/stubgen/runners.py \
  packages/stitcher-stubgen/src/stitcher/stubgen/__init__.py \
  packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py \
  packages/stitcher-application/src/stitcher/services/scanner.py \
  packages/stitcher-cli/tests/integration/test_refactor_internals.py \
  packages/stitcher-application/src/stitcher/app/core.py \
  packages/stitcher-application/tests/integration/test_end_to_end.py \
  packages/stitcher-application/src/stitcher/app/runners/pump/runner.py \
  packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~

### 下一步建议

我们已经完成了代码的静态修复。现在，最关键的步骤是通过运行测试套件来**验证**我们的重构是否成功，以及是否无意中破坏了任何功能。

我建议下一步运行 `pytest` 来确保整个项目的功能完整性。
