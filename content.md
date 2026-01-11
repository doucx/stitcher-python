所有的测试用例都已经顺利通过，这标志着我们对 `check` 指令进行的架构升级——**引入协议抽象层**——已经完全成功并达到了稳定状态。

现在，`CheckAnalyzer` 已经彻底摆脱了对具体数据来源的依赖，所有逻辑都建立在纯粹的 `SymbolState` 比对之上。我们成功地在保持现有功能完全不变的前提下，完成了最关键的“心脏搭桥”。

## [COMMIT] refactor(check): 实现 CheckSubject 协议抽象并重构分析逻辑

### 用户需求

通过引入协议层，将 `CheckAnalyzer` 的比对逻辑与其数据获取逻辑解耦，为后续迁移到基于数据库的 Zero-IO 检查模式铺平道路。

### 评论

这是一次极具战略意义的重构。我们不仅优化了 `CheckAnalyzer` 的代码质量，使其从一个臃肿的命令执行器转变为一个纯粹的、易于测试的状态机；更重要的是，我们建立了一个名为 `CheckSubject` 的契约。这个契约允许我们在不触动任何核心检查逻辑的情况下，随时切换后端数据源。测试的全绿证明了这种抽象对原始复杂逻辑的完美覆盖。

### 目标

1.  **确立契约**：定义 `CheckSubject` 协议和 `SymbolState` 数据类，统一了符号状态的描述语言。
2.  **逻辑重写**：将 `CheckAnalyzer` 的 100+ 行过程式代码重构为基于状态机的协议驱动逻辑。
3.  **适配旧世界**：实现 `ASTCheckSubjectAdapter`，将现有的 `ModuleDef` 和 `DocumentManager` 能力封装在协议之下，确保完全的向后兼容。
4.  **消除歧义**：针对 `__doc__` 模块文档在 AST 模式下的可选性进行了精确的逻辑对齐。

### 基本原理

通过“适配器模式”隔离不稳定性。我们将最易变的“如何解析代码”部分隔离在适配器中，保持了“如何判定一致性”这一核心领域逻辑的纯粹和稳定。这种分层确保了系统在面对未来索引驱动（DB-driven）的需求时，具备极高的灵活性。

### 标签

#intent/refine #flow/ready #priority/high #comp/application #concept/state #scope/core #ai/refine #task/domain/quality #task/object/check-runner #task/action/refactor #task/state/end

---

### Script

#### Acts 1: 提交重构代码

我们将协议定义、适配器实现以及重构后的分析器和运行器代码添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/runners/check/protocols.py
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
packages/stitcher-application/src/stitcher/app/runners/check/analyzer.py
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(check): introduce CheckSubject protocol and refactor logic

Implemented a protocol-based abstraction layer for the check command to
decouple inspection logic from data acquisition.

Key changes:
- Defined `CheckSubject` protocol and `SymbolState` data class as the core contract.
- Implemented `ASTCheckSubjectAdapter` to wrap existing AST-based analysis logic.
- Rewrote `CheckAnalyzer` to be a pure state machine driven by the protocol.
- Refined visibility and optionality rules for `__doc__` to ensure 100% backward compatibility.

This architecture enables a seamless transition to the upcoming database-driven
(Zero-IO) check mode by simply swapping adapters.
~~~~~

### 下一步建议

既然舞台已经搭好，演员（Analyzer）已经熟悉了剧本（Protocol），现在是时候引入新的主角了：**`IndexCheckSubjectAdapter`**。

在下一个计划中，我将：
1.  实现 `IndexCheckSubjectAdapter`：它将直接从我们在上上个步骤中升级过的 SQLite 索引中拉取 `SymbolRecord`，并填充 `SymbolState`。
2.  由于索引中现在存有 `docstring_content`，它将能够直接为 `CheckAnalyzer` 提供生成 Diff 所需的文本，而**完全不需要再打开 .py 文件**。
3.  修改 `StitcherApp`，将 `run_check` 的默认驱动方式从“扫描文件”改为“读取索引”，彻底开启 **Zero-IO Check** 时代。
