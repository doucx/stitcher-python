太棒了。所有测试通过意味着我们不仅成功实现了功能增强，还通过“双模初始化”策略完美地修复了架构契约冲突，恢复了系统的稳定性。

现在，我将生成一个 `[COMMIT]` 计划，将这些高质量的变更正式提交到代码库。

## [COMMIT] refactor(config): unify workspace discovery and enhance config model

### 用户需求
完成 Stitcher 重构路线图中的任务 2.1 和 2.2。这包括：
1. 增强 `StitcherConfig` 以支持 `peripheral_paths`。
2. 重构 `Workspace` 构建逻辑，实现基于配置的注入模式与基于文件系统的自发现模式的统一。
3. 调整 `refactor apply` 命令的调用链，使其支持统一配置。

### 评论
这次提交标志着 Stitcher 架构对齐的一个里程碑。我们通过引入 `peripheral_paths` 解决了“周边组件”（如 examples/）无法被重构引擎观测到的问题。同时，通过在 `Workspace` 中实现“双模初始化”策略，我们展示了如何在引入新能力的同时，通过尊重组件的核心契约来保持大规模测试套件的健壮性和向后兼容性。这是一个典型的通过架构思考来解决工程冲突的案例。

### 目标
1. 将 `peripheral_paths` 字段添加到 `StitcherConfig` 并实现解析逻辑。
2. 重构 `Workspace` 以支持可选的 `StitcherConfig` 注入，保留其自发现能力。
3. 确保 `refactor` 流程在 CLI 层面能够加载并正确利用项目配置。
4. 修复受影响的集成测试并增加诊断性单元测试。

### 基本原理
我们采用了“增强而非破坏”的原则：
- 在 `stitcher-config` 层，我们扩展了模型以包含更丰富的项目拓扑信息。
- 在 `stitcher-refactor` 层，我们将 `Workspace` 升级为一个智能调度器，它能根据输入环境自动选择最佳的构建策略。
- 在 `stitcher-application` 层，我们将配置加载逻辑提前，确保它是后续所有复杂操作（如重构规划）的权威事实来源。

### 标签
#intent/refine #intent/build #flow/ready #priority/high #comp/config #comp/refactor #comp/application #comp/cli #concept/config #scope/core #ai/instruct #task/domain/architecture #task/object/config-unification #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有修改过的文件以及新创建的测试文件添加到暂存区，并创建一个内容详尽的提交记录。

~~~~~act
git_add
packages/stitcher-config/src/stitcher/config/loader.py
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
packages/stitcher-application/src/stitcher/app/runners/refactor.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/tests/integration/test_refactor_command.py
packages/stitcher-cli/tests/integration/test_refactor_internals.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(config): unify workspace discovery and enhance config model

This commit implements tasks 2.1 and 2.2 of the Stitcher Refactor Roadmap, 
eliminating the architectural rift between the refactoring engine and the 
rest of the system regarding project structure and discovery.

Key changes:
- Enhanced `StitcherConfig` with `peripheral_paths` to allow defining 
  non-package code areas like `examples/` or `scripts/`.
- Refactored `Workspace` to support a "Dual-Mode" initialization. It now
  accepts an optional `StitcherConfig` for explicit configuration (used by
  the `refactor` command) while retaining its self-discovery logic via 
  filesystem scanning for backward compatibility with unit tests and standalone 
  usage.
- Integrated configuration loading into the `refactor apply` command flow 
  within `StitcherApp` and `RefactorRunner`.
- Fixed existing integration tests and added a new diagnostic test 
  `test_refactor_internals.py` to verify the unified discovery logic.

This unification ensures a Single Source of Truth for the project's semantic 
domain, enabling future support for holistic refactoring across the entire 
workspace.
~~~~~

### 下一步建议

随着阶段二（发现与配置统一）的圆满完成，我们的重构引擎现在已经具备了观测整个项目的视野。

下一步，我建议根据路线图进入 **阶段四：全域重构支持**：
- **任务 4.1：实现“观测域”逻辑**：增强 `SemanticGraph.load()`。利用我们刚刚在 `StitcherConfig` 中添加的 `peripheral_paths`，让图谱能够加载并解析那些非包目录（无 `__init__.py`）中的脚本文件。
- **任务 4.2：调整 Planner 策略**：确保在重构这些周边组件时，系统能够正确地跳过 Sidecar 更新，因为这些文件通常没有 `.stitcher.yaml` 伴随。

我们将真正实现“即便没有文档侧记，代码也能被优雅重构”的目标。如果你准备好了，请指示我开始 4.1 任务。
