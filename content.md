完成对 `StitcherApp` 的修复，确保在多目标配置下，每个存根包都以其目标名称作为基础名称进行脚手架。所有测试，包括新添加的复现测试，均已通过。

## [COMMIT] fix(app): Use target name instead of global project name for stub package scaffolding

### 用户需求
确保在多目标配置中（例如 Monorepo），每个配置目标都能正确派生其存根包的名称，而不是统一使用全局项目名称，从而避免名称冲突和配置错误。

### 评论
这个修复解决了 Monorepo 配置中一个关键的 Bug。它使得 `stitcher generate` 在处理多个 target 时，能够为每个 target 创建一个逻辑独立的、名称正确的 PEP 561 存根包，极大地增强了工具在复杂项目结构中的可用性。

### 目标
1.  将修改后的文件和新的测试文件添加到 Git 暂存区。
2.  创建一个描述清晰的 Git Commit，记录此 bug 修复。

### 基本原理
我们在调用 `_scaffold_stub_package` 时，通过检查当前配置目标的名称 (`config.name`) 是否为默认值来决定应该使用目标名称还是全局项目名称。这样既修复了多目标模式的 bug，又维护了向后兼容性。

### 标签
#intent/fix #flow/ready #priority/high #comp/application #comp/tests #concept/config #scope/core #ai/instruct #task/domain/cli #task/object/multi-target #task/action/bug-fix #task/state/end #task/status/completed

---
### Script

#### Acts 1: 暂存修改文件和新增的测试文件

将修改过的应用核心逻辑和用于复现/验证修复的测试文件添加到暂存区。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
tests/integration/test_multi_target_stub_names.py
~~~~~

#### Acts 2: 提交变更

使用 Conventional Commit 规范记录此修复。

~~~~~act
git_commit
~~~~~
~~~~~text
fix(app): Use target name instead of global project name for stub package scaffolding

The `StitcherApp.run_from_config` method was incorrectly using the global `project_name` (from pyproject.toml's `[project].name`) when scaffolding stub packages for all targets in multi-target mode.

This caused all generated stub packages to share the same name (e.g., `monorepo-stubs`), leading to errors when attempting to create the `pyproject.toml` multiple times for different target stubs.

The fix determines the correct base name for the stub package:
- If `config.name` is not "default" (i.e., multi-target mode), use the target name.
- Otherwise, fall back to the global `project_name` for single-target compatibility.
~~~~~
