出色的调试和修复。我们已经解决了 `stitcher generate` 在多目标 monorepo 环境下创建可安装存根包的所有已知问题。

## [COMMIT] feat(build): Generate complete pyproject.toml for stub packages

### 用户需求
在多目标配置下，生成完整的 PEP 561 存根包结构，确保其 `pyproject.toml` 包含正确的 Hatchling 配置，使得存根包能够被 `uv` 或其他现代 Python 工具链正确识别、构建和作为可编辑依赖安装。

### 评论
这个修复是 Monorepo 兼容性的关键一步。它通过在 `StubPackageManager` 中添加 Hatchling 配置，并改进 `StitcherApp` 中的命名空间推导逻辑，彻底解决了存根包作为工作空间成员时的构建问题。我们现在能够通过 `uv pip install -e` 命令直接安装生成的存根包。

### 目标
1.  将所有修改过的文件添加到 Git 暂存区。
2.  创建一个描述性的 Git Commit。

### 基本原理
我们增强了 `StubPackageManager.scaffold`，使其能够接收并配置正确的顶级 Python 命名空间。同时，我们在 `StitcherApp` 中添加了启发式逻辑来从 `scan_paths` 自动推导出命名空间（如 `stitcher` 或 `needle`），确保了 `pyproject.toml` 中的 `[tool.hatch.build.targets.wheel].packages` 配置是完整且正确的。

### 标签
#intent/build #flow/ready #priority/critical #comp/application #comp/io #comp/tests #concept/tooling #scope/core #ai/instruct #task/domain/build #task/object/stub-package #task/action/build-fix #task/state/end #task/status/completed

---
### Script

#### Acts 1: 暂存所有修改文件

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
tests/integration/test_stub_package.py
~~~~~

#### Acts 2: 提交变更

~~~~~act
git_commit
~~~~~
~~~~~text
feat(build): Generate complete pyproject.toml for stub packages

This commit resolves an issue where auto-generated stub packages were missing essential build metadata, preventing their correct installation via tools like `uv` (especially as workspace members).

Changes introduced:

1.  **Refactor StubPackageManager**: Updated `StubPackageManager.scaffold` to accept the `package_namespace` (e.g., 'needle' or 'stitcher'). It now includes the required `[tool.hatch.build.targets.wheel].packages` configuration in the generated `pyproject.toml`.
2.  **Add Namespace Deduction**: Implemented logic in `StitcherApp._scaffold_stub_package` to heuristically derive the top-level Python namespace from the `scan_paths` of the current target configuration.
3.  **Update Test**: The integration test `test_stub_package.py` was updated to assert the presence and correctness of the new Hatchling build configuration.

This ensures all generated stub packages are fully compliant and immediately usable within the project workspace.
~~~~~
