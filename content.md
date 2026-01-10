好的，我们将创建一个逻辑提交来记录当前的开发进度。虽然集成测试目前处于失败状态，但这准确地记录了我们当前的架构边界和已识别的技术债务。

根据 **ADAP v1.0** 和 **HFEA v1.0** 协议，我们不应该为了让测试变绿而引入更多的启发式补丁，而是应当将当前的失败作为迈向“扫描-链接”二相架构的基石。

## [COMMIT] feat(index): 实现初步的别名解析与引用分析逻辑

### 用户需求
记录并提交针对 **Debt 1.2 (引用分析)** 和 **Debt 1.3 (别名解析)** 的核心实现代码，包括：
1. `Attribute` 模型的扩展。
2. `PythonAdapter` 对别名符号的提取与持久化。
3. 增强的本地符号映射逻辑。
4. 用于验证当前状态（并暴露猜测算法缺陷）的集成测试。

### 评论
这是一个重要的里程碑。我们已经打通了从源代码提取别名意图到索引库持久化的物理链路。虽然当前的猜测逻辑 (`_guess_suri`) 在处理顶层包导入时存在语义歧义，但这种“诚实的失败”为下一步引入全局链接器 (Linker) 提供了明确的诊断依据。

### 目标
1. 将 `stitcher-spec`、`stitcher-python-adapter` 的修改以及新创建的集成测试添加到 Git 暂存区。
2. 创建一个详细的提交记录，说明实现的逻辑和已知的架构局限。

### 基本原理
按照工程规范，即便在重构中途，也应保持频繁的、具有逻辑意义的提交。当前的代码已经实现了别名解析的“数据流”部分，这是确定性改进。测试的失败是由于“解析算法”部分的启发式残留，这将在后续的架构演进（Phase 2: Linker）中解决。

### 标签
#intent/build #flow/ready #priority/high #comp/core #comp/index #comp/adapter #concept/state #concept/history #scope/core #ai/instruct #task/domain/testing #task/object/alias-resolution #task/action/integration #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交当前状态

我们将把所有相关的变更打包进一个提交中。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/models.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
packages/stitcher-index/tests/integration/test_scanner_aliases.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(index): implement alias resolution and enhanced reference analysis

This commit addresses technical debts 1.2 and 1.3 by establishing a formal
pipeline for capturing and resolving symbol aliases (imports) in Python.

Key Changes:
- Model: Added 'alias_target' to 'Attribute' spec to store logical FQNs.
- Adapter: Updated 'PythonAdapter' to extract griffe aliases and persist
  them as SymbolRecords with kind='alias' and computed 'alias_target_id'.
- Analysis: Enriched the local symbol mapping in '_extract_references' to
  include imported aliases, allowing 'UsageScanVisitor' to resolve
  references to external symbols via their local aliases.
- Testing: Added 'test_scanner_aliases.py' which captures the full
  E2E flow from source to index.

Known Debt & State:
The integration test currently fails on 'import pkg' scenarios due to
heuristic limitations in '_guess_suri'. The adapter currently guesses a
fragment (#pkg) for top-level module imports. This is a recorded debt
that will be resolved in the upcoming "Scan-Link" architecture phase,
where a global linker will replace heuristics with deterministic
cross-file resolution.
~~~~~

### 下一步建议

由于我们已经确立了“二相架构 (Scan-Link)”作为解决 SURI 猜测问题的长期方案，接下来的任务重点应转向该架构的实施：

1. **Phase 1: 数据库架构演进**：修改 `IndexStore` 和 SQL Schema，为符号和引用增加逻辑 FQN 字段，并允许 `target_id` 暂时为空。
2. **Phase 2: Canonical FQN 提取**：修改 `PythonAdapter`，在扫描时为每个定义的符号计算并存储其在项目全局中的“唯一逻辑名 (Canonical FQN)”。
3. **Phase 3: 链接器实现**：构建 `StitcherLinker` 组件，用于在扫描结束后，通过匹配逻辑 FQN 来回填物理 `target_id`。

您可以决定何时开始上述任一阶段的实施。目前，当前的进展已通过 Git 安全记录。
