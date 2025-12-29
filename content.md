好的，非常棒！我们已经完成了 `PyNeedle` 函数式内核演进路线图的第一阶段和第二阶段，这标志着一个重要的里程碑。

我将生成一个 `[COMMIT]` 计划，其中包含所有自上次提交以来的文件修改，并附带一个详细的提交信息，总结我们所取得的成就。

## [COMMIT] feat(architecture): 完成 PyNeedle 操作符架构的阶段 1 & 2

### 用户需求
创建一次 Git 提交，以固化 `PyNeedle` 函数式内核演进路线图中的第一阶段和第二阶段的所有变更。

### 评论
本次提交包含了对 `PyNeedle` 核心架构的重大重构和功能增强。我们成功从旧的 `Nexus/Loader` 模型过渡到了更简洁、更强大的 `Operator` 模型，并解决了在此过程中出现的所有依赖和功能问题。这一里程碑为 `Stitcher` 项目的长期可维护性、可扩展性和用户体验奠定了坚实的基础。

### 目标
1.  将所有与 `PyNeedle` Operator 架构迁移和 `MessageBus` 适配相关的代码变更添加到 Git 暂存区。
2.  创建一个描述性强的 Git 提交，记录这些重要的架构改进和修复。

### 基本原理
按照项目的“焦土政策”和清晰的架构演进路线图，我们系统性地移除了所有对旧 `OverlayNexus` 和 `BaseLoader` 模式的依赖，并用新的 `Operator` 统一模型取代了它们。这不仅修复了在迁移过程中产生的 `ImportError` 和功能退化（如语言检测、嵌套资源加载），还显著提升了整体架构的纯粹性和可测试性。通过此次提交，我们固化了阶段性的成果，为接下来的阶段三（功能增强与全面推广）铺平了道路。

### 标签
#intent/build #intent/refine #intent/fix #flow/done #priority/high #comp/runtime #comp/common #comp/cli #concept/config #concept/api #scope/core #scope/ux #ai/instruct #task/domain/architecture #task/object/functional-kernel #task/action/refactor #task/state/end #insight

---

### Script

#### Acts 1: 添加更改的文件

我们将所有在 `PyNeedle` Operator 架构迁移过程中修改过的文件添加到 Git 暂存区。

~~~~~act
git_add
packages/stitcher-common/src/stitcher/common/__init__.py
packages/stitcher-common/src/stitcher/common/__init__.stitcher.yaml
packages/pyneedle-runtime/src/needle/runtime.py
packages/pyneedle/src/needle/__init__.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-cli/src/stitcher/cli/commands/pump.py
packages/stitcher-cli/src/stitcher/cli/factories.py
packages/stitcher-cli/src/stitcher/cli/interactive.py
packages/pyneedle-runtime/src/needle/operators/fs_operator.py
~~~~~

#### Acts 2: 创建提交

创建一个详细的 Git 提交，总结我们已经完成的里程碑。

~~~~~act
git_commit
~~~~~
~~~~~text
feat(pipeline): Complete PyNeedle operator architecture phases 1 & 2

This commit marks the completion of the first two phases of the PyNeedle functional kernel evolution roadmap as outlined in "实施路线图：PyNeedle 函数式内核演进.md".

The core objective was to transition PyNeedle from a static, `BaseLoader`-based resource query system to a dynamic system built upon callable operators and a declarative composition root. This refactor has significantly enhanced the architecture's elegance, flexibility, and maintainability.

**Key Changes & Achievements:**

*   **Operator Unified Model**: Formalized the `OperatorProtocol` (`__init__` for configuration, `__call__` for execution) across all operator types.
*   **Core Operator Implementation**: Implemented and refined `DictOperator`, `FileSystemOperator`, and `I18NFactoryOperator` as core building blocks. `FileSystemOperator` now robustly handles recursive directory scanning and flattened key mapping (restoring previous multi-level asset loading capability).
*   **Composition Root (`stitcher-common`)**: Established `stitcher-common` as the authoritative composition root, assembling operators into a complete message rendering pipeline. This includes dynamic language detection, prioritizing `STITCHER_LANG` over system `LANG` (`zh_CN.UTF-8` -> `zh`), and falling back to `en`.
*   **Decoupled Message Bus**: `MessageBus` no longer holds `nexus` instances; it now consumes a dynamically resolved `stitcher_operator` callable, making it more flexible and testable.
*   **CLI Adaptation**: The `stitcher-cli` has been fully adapted to consume the `stitcher_operator` directly for help messages and interactive prompts, eliminating reliance on the deprecated `stitcher_nexus.get()` method.
*   **Dependency Graph Clean-up**: All `ImportError`s related to `NexusProtocol` and `ResourceLoaderProtocol` have been resolved, and their obsolete references removed from `pyneedle`'s public API and `stitcher-common`'s documentation.

This milestone lays a solid, functional-programming-aligned foundation for future enhancements and full system rollout, drastically simplifying resource management and I18N within Stitcher.
~~~~~

### 下一步建议
我们已经成功完成了架构演进的阶段一和二。接下来，我们可以根据路线图进入**阶段三：功能增强与全面推广**，例如：
*   **实现高阶执行器 `ThemeOperator`**: 构建第一个高阶算子，演示如何在不修改现有算子的情况下，通过“包装”来扩展系统功能（例如样式化输出）。
*   **全面迁移**: 审计并更新整个 `stitcher` 项目代码库中所有对旧 `OverlayNexus` 等遗留接口的直接依赖。
*   **废弃兼容垫片**: 彻底删除 `OverlayNexus` shim 类。

请告诉我您希望接下来开始阶段三的哪一部分。
