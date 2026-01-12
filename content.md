好的，既然测试已通过且类型检查错误已修复，我们现在将这些变更作为“阶段三”的第一个逻辑单元进行提交。

## [COMMIT] refactor(app): 核心服务协议化并更新各 Runner 依赖

### 用户需求
完成核心服务（DocumentManager, SignatureManager, Differ, DocstringMerger）的抽象化，使 `stitcher-application` 中的业务逻辑不再依赖于具体实现。

### 目标
1.  提交 `stitcher-spec` 中新增的协议定义及导出设置。
2.  提交 `stitcher-application` 中各 Runner（Check, Pump, Init, Transform, Coverage）对协议的引用。
3.  提交 `StitcherApp` 中关于索引构建返回类型的修正。

### 基本原理
通过在 `stitcher-spec` 中定义协议，我们实现了代码库的“契约先行”。这不仅为后续的解耦打下了基础，还极大地增强了各模块的独立测试能力，使我们能够使用标准 Mock 对象代替复杂的领域服务实例。

### 标签
#intent/refine #flow/done #priority/medium
#comp/interfaces #comp/runtime
#concept/architecture #scope/core
#ai/instruct
#task/domain/architecture #task/object/service-abstraction #task/action/define-protocols
#task/state/end

---

### Script

#### Acts 1: 提交代码变更

我们将所有涉及协议定义、导出以及 Runner 更新的文件添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/protocols.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
packages/stitcher-application/src/stitcher/app/runners/pump.py
packages/stitcher-application/src/stitcher/app/runners/init.py
packages/stitcher-application/src/stitcher/app/runners/transform.py
packages/stitcher-application/src/stitcher/app/runners/coverage.py
packages/stitcher-application/src/stitcher/app/core.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(app): abstract core services into protocols and update runners

Completed the abstraction of core domain services into formal protocols to achieve dependency inversion and better decoupling within the monorepo.

Changes:
- Defined `DocumentManagerProtocol`, `SignatureManagerProtocol`, `DifferProtocol`, and `DocstringMergerProtocol` in `stitcher-spec`.
- Exported new protocols from `stitcher.spec` entry point for downstream consumption.
- Updated all application Runners (`CheckRunner`, `PumpRunner`, `InitRunner`, `TransformRunner`, `CoverageRunner`) to depend on these protocols rather than concrete service implementations.
- Refactored sub-components of the Check runner (Resolver, Subject adapters) to adhere to the new protocol-based signatures.
- Fixed a type mismatch in `StitcherApp.run_index_build` where a Dict was being returned instead of the declared bool.

This refactor enables easier mocking of core services in unit tests and prepares the architecture for potential alternative implementations of document and signature management.
~~~~~

### 下一步建议
我们已经完成了核心服务协议的第一阶段。下一步建议：
1.  **清理 `CheckAnalyzer`**: 虽然 `CheckRunner` 已经解耦，但内部的 `CheckAnalyzer` 可能仍在 `__init__` 中保留具体类型的注解。
2.  **Scanner 抽象化**: `ScannerService` 目前还在 `app.services` 中且涉及 `Config` 对象，可以考虑将其核心逻辑（扫描、插件处理）也进行协议化，以彻底完成 `StitcherApp` 的依赖倒置。
