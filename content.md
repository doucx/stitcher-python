任务已完成且验证通过。通过统一 `SignatureManager` 的持久化入口并引入向后兼容的加载逻辑，我们成功消除了全系统中关于 SURI 协议的最后几处模糊点。

我将生成一个 `[COMMIT]` 计划来正式提交这些关键的架构修复。

## [COMMIT] fix: 统一全系统 SURI 持久化并启用基准存档自动迁移

### 用户需求
解决 `pump` 命令会“腐蚀”SURI 键的问题，并使 `check` 命令能够识别并自动升级旧版的短键签名文件，确保全系统标识符协议的一致性。

### 评论
此次提交填补了 SURI 架构实施中的两个深层漏洞：加载时的过严校验（导致无法升级）和保存时的逻辑绕过（导致格式退化）。现在，`SignatureManager` 真正成为了基准数据的权威守护者。此外，我们也补齐了对 `ClassDef` 实体的指纹追踪，使得系统的语义地图达到了 100% 的覆盖率。

### 目标
1.  **集中化序列化**: 在 `SignatureManager` 中封装 `serialize_hashes`，强制执行 SURI 协议。
2.  **弹性加载**: 使 `SignatureManager` 能够透明地处理旧版短键，为自动迁移提供基础。
3.  **修复持久化漏洞**: 重构 `PumpRunner` 以使用集中化的序列化逻辑。
4.  **全量实体追踪**: 在 `InitRunner` 和 `PumpRunner` 的指纹计算中包含 `ClassDef`。
5.  **验证闭环**: 将 SURI 格式验证和迁移逻辑验证固化为集成测试。

### 基本原理
我们遵循了“架构不可腐蚀性”原则。通过在数据入口（加载）处提供兼容性并在出口（保存）处实施协议强制，我们实现了一个无感的、自愈的迁移机制。无论数据过去处于何种状态，只要经过一次 `check` 或 `pump` 操作，它都会被自动修复为标准的 SURI 格式。

### 标签
#intent/fix #flow/ready #priority/critical #comp/application #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/suri-protocol #task/action/unification #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将提交涉及适配器升级、Runner 逻辑修正以及新增测试文件的所有改动。

~~~~~act
git_add
packages/stitcher-python-adapter/src/stitcher/adapter/python/fingerprint.py
packages/stitcher-application/src/stitcher/app/runners/init.py
packages/stitcher-application/src/stitcher/app/runners/pump.py
packages/stitcher-application/src/stitcher/app/runners/check.py
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
packages/stitcher-application/tests/integration/test_signature_suri_format.py
packages/stitcher-application/tests/integration/test_signature_migration.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix: unify SURI persistence and enable automatic legacy migration

This commit solidifies the SURI (Stitcher Uniform Resource Identifier)
infrastructure by closing identifier gaps and ensuring data consistency.

Key Fixes:
1. Centralized Serialization: Moved SURI formatting logic into SignatureManager.
   Ensures all commands (init, pump, check) produce identical JSON structures.
2. Legacy Migration: Enhanced SignatureManager to recognize and load old
   short-key identifiers, enabling 'check --force-relink' to auto-upgrade them.
3. Pump Corruption Fix: Fixed PumpRunner's direct JSON writing that was
   incorrectly reverting SURI keys to short FQNs.
4. ClassDef Tracking: Updated Init/Pump runners and the Python adapter's
   fingerprinting to fully track ClassDef entities alongside functions.

Included Tests:
- test_signature_suri_format.py: Verifies physical JSON keys follow protocol.
- test_signature_migration.py: Captures legacy upgrade and persistence stability.
~~~~~

### 下一步建议

随着数据底座的彻底稳固和对齐，我们现在具备了进行 **阶段 3：逻辑驱动重构** 最后一项任务的最佳条件：

**重构 `PumpRunner` (Index-Assisted)**:
- 现在的 `PumpRunner` 在运行 `run_batch` 时，对于每一个文件，即便它没有任何变更，也会执行完整的 `doc_manager.hydrate_module`（涉及解析、合并逻辑）。
- 我们的重构目标是让它先查询索引库中的 `docstring_hash`。只有当代码中的文档哈希与基准哈希不一致时，才执行耗时的解析和注入操作。

如果您准备好开始 `PumpRunner` 的重构，请指示我。
