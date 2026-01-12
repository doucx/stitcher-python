好的，Phase 1 的所有开发和清理工作已圆满完成。我们已经成功建立了一个解耦、类型安全且易于扩展的分析架构。

现在，我们将执行 `[COMMIT]` 计划，将这些架构改进正式固化。

## [COMMIT] refactor: 剥离分析逻辑至新包并现代化 check 数据流

### 用户需求

按照 Phase 1 路线图，完成 `stitcher-analysis` 包的提取，并将 `check` 与 `pump` 命令的核心逻辑迁移至基于规则的引擎。同时，彻底清理遗留的数据模型，统一全系统的分析契约。

### 评论

这次提交标志着项目架构的一个重大里程碑。通过将“判断逻辑”与“业务编排”分离，我们不仅消除了大量的面条代码，还为未来引入更复杂的代码关联分析（如 Phase 2 的图算法）扫清了障碍。

### 目标

1.  **物理分离**: 成功创建 `stitcher-analysis` 包，承载所有静态分析逻辑。
2.  **引擎化**: 实现 `ConsistencyEngine` 和 `PumpEngine`，将分析逻辑从过程式代码转变为基于规则的声明式执行。
3.  **数据流现代化**: 完成从“字典驱动”到“Violation 对象驱动”的转型，大幅提升了 Reporter 和 Resolver 的类型安全性。
4.  **架构纯净化**: 删除了所有遗留的冗余协议和模型，实现了单一部分（SSoT）。

### 标签

#intent/refine #flow/ready #priority/high #comp/analysis #comp/app #scope/core #ai/instruct #task/domain/architecture #task/object/analysis-logic #task/action/extraction #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交 Phase 1 成果

我们将所有变更添加到暂存区，并创建一个内容详尽的提交记录。

~~~~~act
git_add
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: extract analysis logic to stitcher-analysis and modernize check data flow

This commit completes Phase 1 of the architecture refactoring, focusing on the separation of analysis logic from application orchestration.

Key changes:
- Created 'stitcher-analysis' package to house all logical reasoning and rule-based checks.
- Implemented 'ConsistencyEngine' and 'PumpEngine' using a pluggable 'AnalysisRule' architecture.
- Migrated legacy 'Check' and 'Pump' logic into discrete rules: ContentRule, ExistenceRule, SignatureRule, and UntrackedRule.
- Overhauled 'CheckReporter' and 'CheckResolver' to directly consume 'Violation' objects instead of legacy dictionaries.
- Removed redundant protocols and 'stitcher.app.types.FileCheckResult', establishing 'stitcher-analysis' as the SSoT for analysis data models.
- Updated all unit tests to align with the new architecture and fixed Pyright type access issues on Mypy/autospec mocks.

This structural separation enables independent testing of analysis rules and paves the way for advanced cross-file semantic analysis in future phases.
~~~~~

### 下一步建议

Phase 1 已正式关闭。系统现在拥有一个非常干净的基础，可以开始 **Phase 2: 语义扩展 (Semantic Extension)** 的工作了。

在 Phase 2 中，我们可以利用新建立的 `ConsistencyEngine` 来添加更深层次的规则，例如：
- **交叉引用校验 (Cross-Reference Validation)**: 检查 `.stitcher.yaml` 中的 `See Also` 标签是否指向了代码中真实存在的符号。
- **关联逻辑分析**: 当一个函数的签名改变时，不仅标记该函数，还标记所有引用了该函数的文档条目。

由于分析逻辑现在是模块化的，添加这些强大的功能将只需要在 `stitcher-analysis` 中添加新的 `AnalysisRule` 实现即可。

如果你准备好了，我们可以开始讨论 Phase 2 的具体需求。
