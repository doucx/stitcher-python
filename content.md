好的，我们现在将“阶段三：核心服务抽象化”中关于索引存储协议化以及协议文件结构化的变更作为一个完整的逻辑单元提交。

## [COMMIT] refactor(app): 索引存储协议化与协议架构结构化

### 用户需求
完成对 `IndexStore` 的抽象化，解耦应用层与索引层的具体实现，并按照重构路线图要求优化协议文件的物理组织结构。

### 目标
1.  提交 `stitcher-spec` 中新增的 `storage.py` (包含 `IndexStoreProtocol`) 和 `managers.py` (包含 `DocumentManagerProtocol` 和 `SignatureManagerProtocol`)。
2.  提交对 `stitcher-spec/protocols.py` 的清理以及包入口 `__init__.py` 的导出更新。
3.  提交 `stitcher-application` 中所有 Runner 和子组件对新协议的引用及其导入路径的更新。
4.  提交对 `CheckAnalyzer` 构造函数的协议化更新。
5.  提交对 `StitcherApp.run_index_build` 返回类型的修正。

### 基本原理
通过引入 `IndexStoreProtocol`，我们彻底切断了应用层对 `stitcher-index` 具体实现类的物理依赖，实现了路线图 3.1 的目标。同时，通过按领域（存储、管理）拆分协议文件，我们将 `stitcher-spec` 的内部结构调整为可扩展的模块化布局，为后续引入更多语言和存储后端打下了坚实基础。

### 标签
#intent/refine #flow/done #priority/high
#comp/interfaces #comp/runtime #comp/index
#concept/architecture #scope/core
#ai/instruct
#task/domain/architecture #task/object/service-abstraction #task/action/restructure-protocols
#task/state/end

---

### Script

#### Acts 1: 提交代码变更

我们将所有涉及协议定义、文件重组以及依赖更新的文件添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/storage.py
packages/stitcher-spec/src/stitcher/spec/managers.py
packages/stitcher-spec/src/stitcher/spec/protocols.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
packages/stitcher-application/src/stitcher/app/runners/check/analyzer.py
packages/stitcher-application/src/stitcher/app/runners/pump.py
packages/stitcher-application/src/stitcher/app/runners/init.py
packages/stitcher-application/src/stitcher/app/runners/transform.py
packages/stitcher-application/src/stitcher/app/runners/coverage.py
packages/stitcher-application/src/stitcher/app/runners/refactor.py
packages/stitcher-application/src/stitcher/app/core.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(app): abstract index store and restructure spec protocols

Implemented Stage 3.1 of the roadmap by introducing IndexStoreProtocol and restructured the spec package for better domain isolation.

Key Changes:
- Created `stitcher.spec.storage` and defined `IndexStoreProtocol` to decouple application logic from concrete database implementations.
- Created `stitcher.spec.managers` and moved `DocumentManagerProtocol` and `SignatureManagerProtocol` there, aligning with the planned architectural layout.
- Updated all Runners in `stitcher-application` (Check, Pump, Init, Transform, Coverage, Refactor) to depend on these new protocols.
- Refactored `CheckAnalyzer` to use `DifferProtocol` and updated subject adapters to use `IndexStoreProtocol`.
- Fixed all cascading import paths across the application layer.
- Corrected `StitcherApp.run_index_build` return type implementation.

This commit achieves full dependency inversion for the index storage layer and optimizes the organizational structure of the system's core contracts.
~~~~~

### 下一步建议
我们已经圆满完成了阶段三的核心抽象工作。由于 `stitcher-refactor` 包当前处于卸载状态，路线图中的阶段四（Refactor 引擎泛化）和阶段五（Sidecar 标准化）将暂时挂起。

如果你准备好了，我们可以探讨接下来的方向，例如：
1.  **细化现有协议**：检查协议中是否还存在暴露实现细节的方法，并进一步收敛。
2.  **增强单元测试**：利用现在已经解耦的 Runner，编写基于 Mock 协议的单元测试，验证重构后的健壮性。
3.  **重新加载并重构 Refactor 包**：如果你希望继续执行阶段四和阶段五。
