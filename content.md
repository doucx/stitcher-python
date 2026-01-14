你的分析完全正确，我的上一个计划不够详尽，遗漏了这些分散在各处的导入语句，导致了当前代码库处于一个不一致的、无法编译的状态。非常感谢你提供了这份详尽的列表。

我将使用你建议的 `sed` 命令，因为对于这种遍布多个文件的、模式统一的字符串替换，它无疑是最高效、最正确的工具。

我将生成一个修正计划来纠正这些遗漏。

## [WIP] fix: Correct remaining stitcher.config imports

### 错误分析
上一个 `[WIP]` 计划在执行 `stitcher-config` 到 `stitcher-workspace` 的物理迁移时，未能完全更新代码库中所有对 `stitcher.config` 的引用。这导致了多个文件中存在悬空的 `import` 语句，破坏了项目的可编译性和开发者体验 (DX)。

### 用户需求
用户提供了一份详尽的列表，指出了所有仍然错误地从 `stitcher.config` 导入模块的文件。需要将这些导入语句全部修正为从 `stitcher.workspace` 导入。

### 评论
这是一个关键的修正步骤，用于完成物理迁移阶段。使用 `sed` 批量处理这些简单的导入路径变更是最高效的策略，避免了为每个文件创建单独的 `patch_file` 操作的繁琐。

### 目标
1.  使用 `sed` 命令，原子化地将所有 Python 文件中 `from stitcher.config import` 的引用替换为 `from stitcher.workspace import`。
2.  单独处理 `packages/stitcher-workspace/pyproject.toml` 文件中遗漏的对 `stitcher-config` 的依赖引用。

### 基本原理
通过一个单一的、范围明确的 `run_command` 来执行所有 Python 文件的文本替换，可以确保一致性和效率。对于结构化文件 `pyproject.toml` 中更具体的条目，使用 `patch_file` 仍然是更精确和安全的选择。这个计划旨在以最小的代价完成迁移的收尾工作，使代码库恢复到健康状态，以便进行下一步的逻辑重构。

### 标签
#intent/fix #flow/ready #priority/high #comp/workspace #comp/build #scope/dx #ai/instruct #task/domain/architecture #task/object/package-dependency #task/action/merge #task/state/continue

---

### Script

#### Acts 1: 批量修正 Python 文件的导入路径

我们将使用一个 `sed` 命令来查找并替换所有指定的 Python 文件中的错误导入语句。

~~~~~act
run_command
~~~~~
~~~~~bash
sed -i 's/from stitcher.config import/from stitcher.workspace import/g' \
    packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py \
    packages/stitcher-application/tests/unit/runners/pump/test_pump_runner.py \
    packages/stitcher-stubgen/src/stitcher/stubgen/runners.py \
    packages/stitcher-stubgen/src/stitcher/stubgen/__init__.py \
    packages/stitcher-application/tests/integration/test_end_to_end.py \
    packages/stitcher-cli/tests/integration/test_refactor_internals.py \
    packages/stitcher-application/src/stitcher/app/core.py \
    packages/stitcher-application/src/stitcher/services/scanner.py \
    packages/stitcher-workspace/src/stitcher/workspace/core.py \
    packages/stitcher-application/src/stitcher/app/runners/pump/runner.py \
    packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~

#### Acts 2: 修正 `stitcher-workspace` 的 `pyproject.toml`

我的上一个计划未能正确处理 `[tool.uv.sources]` 部分，现在进行修正。

~~~~~act
patch_file
packages/stitcher-workspace/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
stitcher-config = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
stitcher-common = { workspace = true }
~~~~~

### 下一步建议
非常感谢你的精确修正。现在代码库的物理结构和导入路径应该已经完全一致了。

我们现在可以安全地回到之前的主线任务：**进行逻辑重构**。
下一步，我建议修改 `stitcher.workspace.core.Workspace` 类，让它在初始化时自动加载配置，从而消除应用层的耦合，并移除冗余的根目录查找逻辑。

如果你同意，我将生成执行此逻辑重构的计划。
