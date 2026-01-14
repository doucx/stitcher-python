太棒了！测试全部通过意味着我们的“高保真工程”重构方案已经在物理上得到了验证。协议的分离不仅消除了语义模糊，还成功解决了 `PumpExecutor` 产生的隐性 Bug。

我将生成一个 `[COMMIT]` 计划，将这些高质量的变更正式提交到 Git 历史中。

## [COMMIT] refactor(serializer): 在协议层分离数据传输与视图序列化

### 用户需求
在测试验证通过后，提交所有关于序列化协议重构及其相关适配的变更。

### 评论
这次重构是“Sidecar 一等公民化”架构的关键前置步骤。通过在 `stitcher-spec` 中建立清晰的 `to/from_transfer_data` 和 `to/from_view_data` 契约，我们确保了系统在处理“高性能索引”和“美观文件输出”这两个需求时拥有独立且正确的代码路径。

### 目标
1.  将所有修改后的文件添加到 Git 暂存区。
2.  创建一个具有详尽说明的提交，记录协议变更的动机和解决的 Bug。

### 基本原理
完成逻辑上的一个完整工作单元。这次提交建立了一个稳定的基础，使得后续的 Sidecar 索引化工作能够在一个类型安全、语义清晰的环境中进行。

### 标签
#intent/refine #flow/ready #priority/high #comp/spec #comp/lang-python #comp/lang-sidecar #comp/application #comp/tests #ai/instruct #task/domain/testing #task/object/serialization-protocol #task/action/refactor #task/state/end

---

### Script

#### Acts 1: 提交重构变更

我们将修改后的核心协议、实现类、应用代码以及修正后的测试用例全部提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/protocols.py
packages/stitcher-lang-python/src/stitcher/lang/python/docstring/serializers.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/manager.py
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
packages/stitcher-lang-python/tests/adapter/unit/docstring/test_serializers.py
packages/stitcher-application/tests/unit/test_doc_manager_strategies.py
packages/stitcher-application/tests/unit/test_docstring_hybrid.py
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
packages/stitcher-application/tests/integration/test_check_state_machine.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(serializer): split DTO and View serialization in protocol

Refactored `DocstringSerializerProtocol` to explicitly separate two distinct serialization concerns:

1. Data Transfer (DTO): `to_transfer_data`/`from_transfer_data` for DB storage, hashing, and IPC. These methods ensure pure, deterministic, and JSON-safe output.
2. Human View: `to_view_data`/`from_view_data` for high-fidelity YAML file I/O, allowing for format-specific objects like `LiteralScalarString`.

This change resolves a critical architectural smell where the two roles were previously conflated, leading to serialization issues with JSON/SQLite.

Highlights:
- Updated `RawSerializer` and `StructuredSerializer` to implement the new protocol.
- Fixed a bug in `PumpExecutor` where it was using the transfer path for YAML output.
- Updated `DocumentManager` to use the transfer path for stable hash calculation.
- Aligned the entire test suite (unit and integration) with the new API.
~~~~~

### 下一步建议
变更已安全提交。
现在地基已经打好，我们可以正式进入性能优化的核心阶段：**实现 `SidecarIndexerAdapter` 并修改 `Workspace.discover_files` 以支持 `.stitcher.yaml` 的自动索引**。这将彻底消除 `check` 命令中的瓶颈。如果你准备好了，我将生成实施该方案的第一个计划。
