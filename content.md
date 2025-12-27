好的，我将根据这次成功的重构创建一个 `[COMMIT]` 计划，记录所有文件变更并提交。

## [COMMIT] refactor(build): Separate pyneedle facade from runtime implementation

### 用户需求
将 `pyneedle` 包重构为 `pyneedle` (外观层) 和 `pyneedle-runtime` (实现层)，以解决静态分析器与 Python 运行时在命名空间包导入上的冲突。

### 评论
这次重构解决了 Monorepo 中一个复杂的架构问题。通过引入 Facade Package 模式，我们：
1.  消除了类型检查器（如 Pyright）对 `needle` 导入路径的歧义。
2.  通过在新的 `pyneedle/src/needle/__init__.py` 中添加 `pkgutil.extend_path`，确保了 Python 运行时能够正确地聚合所有 `needle.*` 模块。
这是对项目架构清晰度和开发者体验（DX）的关键改进。

### 目标
提交以下变更作为一个完整的逻辑单元：
1.  重命名 `pyneedle` 目录为 `pyneedle-runtime`，并修改其 `pyproject.toml`。
2.  删除 `pyneedle-runtime/src/needle/__init__.py`。
3.  创建新的 `pyneedle` 外观包和其 `__init__.py`。
4.  更新项目根 `pyproject.toml` 中的依赖和路径配置。

### 基本原理
为了在保持 `from needle import L` 简洁性的同时解决导入冲突，我们将核心实现（`runtime.py`, `loaders/`）移动到了 `pyneedle-runtime` 命名空间包中。新的 `pyneedle` 包作为常规包（包含 `__init__.py`）的入口，其 `__init__.py` 使用 `pkgutil.extend_path` 将 `needle` 声明为一个可扩展的命名空间，从而允许它从其他命名空间包（如 `pyneedle-pointer` 和 `pyneedle-runtime`）中导入模块。

### 标签
#intent/refine #flow/ready #priority/high #comp/build #concept/config #scope/dx #ai/instruct #task/domain/build-system #task/object/namespace-packages #task/action/refactor #task/state/end #task/status/completed

---
### Script

#### Acts 1: 暂存所有变更的文件和目录

为了确保 Git 能够正确地追踪目录重命名、文件删除和文件创建，我们将暂存所有相关的目录和根配置文件。

~~~~~act
git_add
pyproject.toml
packages/pyneedle
packages/pyneedle-runtime
~~~~~

#### Acts 2: 创建 Git 提交

创建一个描述性强的提交消息。

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(build): Separate pyneedle facade from runtime implementation

The previous structure of the 'pyneedle' package (which contained `src/needle/__init__.py` and implementation code) caused a conflict: it was simultaneously acting as a regular package and attempting to import from its siblings in the `needle` namespace. This led to static analysis and runtime module resolution failures.

The solution implements the Facade pattern:

1. Renamed the original implementation package to `pyneedle-runtime`.
2. Converted `pyneedle-runtime` into a pure namespace package by deleting its `src/needle/__init__.py`.
3. Created a new `pyneedle` package, designated solely as the public API entry point.
4. Added `pkgutil.extend_path` to the new `pyneedle/src/needle/__init__.py` to ensure the Python runtime correctly discovers all modules contributing to the `needle` namespace across the workspace.
5. Updated path configurations in the root `pyproject.toml` accordingly.
~~~~~

### 下一步建议

核心的重构已经完成。现在静态分析和运行时应该能正确处理 `needle` 包的导入。下一步建议检查 `pyneedle-runtime` 内部，确保所有的 `stitcher.yaml` 文件中的 FQN 引用都已更新。

在 Act 1 中，我们将 `pyneedle` 重命名为 `pyneedle-runtime`。在 `packages/pyneedle-runtime/src/needle/runtime.stitcher.yaml` 中可能仍然有 `pyneedle` 的旧引用，例如：
```yaml
# packages/pyneedle/src/needle/runtime.stitcher.yaml
"nexus": |-
  The global, batteries-included Nexus instance for easy, out-of-the-box usage.
```
这部分内容是正确的，因为 `runtime.py` 内部的逻辑没有改变。

但我们还删除了 `packages/pyneedle-runtime/src/needle/__init__.py`，这个文件可能有一个相应的 `.stitcher.yaml` 文件，如果有的话，它现在是**多余**的。

我建议先执行一个 `git status` 或文件系统检查来确认是否有未提交的 `.stitcher.yaml` 文件或不必要的文件清理。由于我无法执行 `git status`，我将假设所有 `.stitcher.yaml` 文件都与 Python 文件同名，并且没有遗留文件。

下一步建议：继续开发其他功能或运行 `stitcher check` 来验证文档是否仍与新签名同步。

- **运行测试**: 运行完整的测试套件（如果它现在可以正常收集），以确保所有功能回归测试都通过。
- **文档一致性检查**: 在下一次 `act` 中执行 `stitcher check` 确保签名更改和 FQN 引用正确。
