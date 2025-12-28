好的，我们已经顺利完成了代码修改、Bug 修复以及消息定义的标准化工作。所有测试现在均已通过。现在是时候将这个完整的特性——“签名与文档哈希校验状态机模型”及其配套的哈希命名规范重构——作为一个完整的逻辑单元提交到版本库中了。

我将生成一个 `[COMMIT]` 计划，记录这一里程碑式的进展。

## [COMMIT] feat(app): 实现签名与文档哈希校验状态机模型并强制长命名规范

### 用户需求
完成并提交“签名与文档哈希校验状态机模型”的实现。这包括核心逻辑开发、配套的哈希变量命名规范重构、消息总线键名标准化以及相关测试套件的完善。

### 评论
这个特性的落地是 Stitcher 迈向工程化和智能化的关键一步。通过引入四状态确定性状态机，我们现在能够精准地识别“签名漂移”和“协同演进”等复杂场景，并为用户提供清晰的调和路径（`--reconcile`, `--force-relink`）。同时，遵循《哈希强制长命名规范》的代码库现在变得极具自解释性，彻底消除了哈希处理中的概念歧义，为未来的扩展打下了坚实的架构基础。

### 目标
1.  将所有相关的代码变更、配置文件修改和新创建的测试文件正式提交到 Git。
2.  提供详尽的提交说明，记录状态机逻辑和命名规范重构的要点。

### 基本原理
根据《元规范：WIP 与 COMMIT》，在确认功能完整且测试通过后，我们将使用 `[COMMIT]` 状态的计划。按照脚本原则，此计划仅包含 `git_add` 和 `git_commit` 指令，确保操作的原子性和纯净性。

### 标签
#intent/build #flow/ready #priority/high #comp/engine #comp/app #comp/common #comp/tests #concept/state #concept/parser #scope/core #scope/dx #ai/instruct #task/domain/app #task/object/hash-state-machine #task/action/implementation #task/state/end #task/status/completed

---
### Script

#### Acts 1: 提交状态机模型与命名规范重构

我们将所有受影响的文件添加到暂存区，并创建一个详细的提交。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.stitcher.yaml
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
packages/stitcher-application/src/stitcher/app/services/signature_manager.stitcher.yaml
packages/stitcher-application/tests/test_signature_manager.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/state.json
tests/integration/test_check_signatures.py
tests/integration/test_check_state_machine.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(app): implement hash consistency state machine and naming convention

Implements the "Signature and Documentation Hash Consistency State Machine" 
to provide deterministic analysis of changes between source code and 
external documentation.

Key Features:
- Implemented a 4-state state machine: Synchronized, Documentation 
  Improvement, Signature Drift, and Co-evolution.
- Introduced '--reconcile' and '--force-relink' flags in CLI for 
  intent-based resolution of drifts.
- Integrated auto-reconciliation for Documentation Improvements.

Refactoring:
- Enforced "Hash Mandatory Long Naming Convention" across the app and 
  storage layer. Composite hashes now use explicit keys like 
  'baseline_code_structure_hash' and 'baseline_yaml_content_hash'.
- Standardized message assets in 'state.json' to use full FQN keys 
  matching the Semantic Pointer (L) IDs.

Testing:
- Added comprehensive integration tests in 'test_check_state_machine.py' 
  covering all state transitions and reconciliation logic.
- Updated existing tests to comply with the new naming convention and 
  data structures.
~~~~~

### 下一步建议
- **多语言支持**: 既然已经标准化了 `en/check/state.json`，可以考虑同步更新 `zh` 分支下的对应资源，确保中文环境下也能获得一致的体验。
- **交互模式**: 根据提案，后续可以在 CLI 中实现交互式引导（TTY 检测），当检测到状态三或状态四且未提供标志位时，主动询问用户解决策略。
