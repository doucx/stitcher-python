好的，整个阶段一的重构工作已经准备就绪。这是 Stitcher 架构演进的关键里程碑，通过“协议下沉（Protocol Sinking）”打破了包之间的隐式耦合，确立了以 `stitcher-spec` 为核心的单向依赖链。

以下是提交阶段一重构成果的计划：

## [COMMIT] refactor: Stitcher 架构重构阶段一 - 协议标准化与下沉

### 用户需求
实施架构重构的第一阶段，将所有核心协议和数据模型下沉到 `stitcher-spec` 包中，并清理全局引用、依赖关系和元数据记录。

### 评论
这是一个高保真的工程变更。通过将契约（Protocols）与实现分离，并使用 `stitcher-spec` 作为唯一的真理来源（SSoT），我们消除了功能包之间的循环依赖，为未来的插件化和多语言支持建立了稳固的地基。

### 目标
1.  **协议下沉**: 将 `InteractionHandler`、`DocumentAdapter`、`SymbolRecord` 等核心契约从功能包移动到 `stitcher-spec`。
2.  **全局适配**: 更新全量代码的导入路径，确保业务逻辑指向新的协议地址。
3.  **元数据同步**: 更新 `.stitcher/signatures` 中的元数据标识符（SURI），保持签名追踪的连续性。
4.  **配置对齐**: 修正所有包的 `pyproject.toml` 和 `uv.lock`，反映真实的依赖拓扑。
5.  **记录演进**: 通过 `migrations/001_phase_1_sinking.py` 脚本正式记录此次架构变迁。

### 基本原理
遵循“架构不可腐蚀性”原则。核心协议包不应依赖于具体实现，而所有实现都应仅依赖于协议。通过这次下沉，我们消除了 `application` 对 `index` 内部实现的硬性依赖，使其仅通过 `stitcher.spec.index` 中定义的模型进行操作。

### 标签
#intent/architect #flow/ready #priority/high #comp/interfaces #comp/build #concept/state #scope/core #ai/brainstorm #task/domain/architecture #task/object/phase-1-sinking #task/action/commit #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交阶段一重构成果

我们将所有涉及到的变更加入暂存区并创建一个结构化的提交。

~~~~~act
git_add
.stitcher/signatures/
migrations/001_phase_1_sinking.py
packages/stitcher-application/
packages/stitcher-cli/
packages/stitcher-common/
packages/stitcher-index/
packages/stitcher-python-adapter/
packages/stitcher-spec/
packages/stitcher-stubgen/
packages/stitcher-test-utils/
uv.lock
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: Stitcher Architecture Evolution Phase 1 - Protocol Sinking

This commit implements the first major phase of the architectural refactoring,
aimed at standardizing core protocols and eliminating circular dependencies
between packages.

Key Changes:
- Protocol Sinking: Moved all core interface definitions (Protocols) and
  data models from functional packages into the centralized `stitcher-spec`.
- Namespace Reorganization:
    - Interaction: `stitcher.app.protocols` -> `stitcher.spec.interaction`
    - Persistence: `stitcher.common.interfaces` -> `stitcher.spec.persistence`
    - Registry: `stitcher.index.protocols` -> `stitcher.spec.registry`
    - Index Models: `stitcher.index.types` -> `stitcher.spec.index`
- Global Refactoring: Updated all import statements across the monorepo to
  match the new structure.
- Metadata Sync: Updated `.stitcher/signatures` to reflect new SURI (Stitcher
  Uniform Resource Identifier) paths for moved symbols.
- Dependency Cleanup: Streamlined `pyproject.toml` files, removing dead
  internal dependencies and ensuring `stitcher-test-utils` visibility.
- Migration Log: Added `migrations/001_phase_1_sinking.py` to document the
  structural change.

This establishes a clean, directed dependency graph:
Implementation Packages -> stitcher-spec -> python primitives.
~~~~~

### 下一步建议

- **阶段二规划**: 下一阶段（Phase 2）将聚焦于“能力的解耦”，特别是将 Stub 生成逻辑从 `application` 中完全剥离到 `stitcher-stubgen`，并使其通过 `stitcher-spec` 中的协议与适配器交互。
- **运行冒烟测试**: 在提交后建议运行一次全量测试 `pytest`，验证在协议下沉后，各组件间的通讯是否依然畅通。
- **清理残留**: 检查是否还有任何遗漏的旧 `__init__.py` 或临时文件未被包含在内。
