简要回答
我已经为 `check` 命令添加了全面的交互式回归测试。现在我将生成一个 `[COMMIT]` 计划来固化这些更改。

## [COMMIT] test(app): 增强 check 命令的交互式回归测试

### 用户需求
将为 `check` 命令添加的所有新的交互式回归测试固化到代码库中。

### 评论
这些测试使用了 Mock Handler Factory 模式，极大地提升了 `check` 命令核心状态机（签名漂移、协同演进、冗余文档）在交互模式下的可测试性和鲁棒性。通过同时验证 Bus 消息和底层签名文件的状态，我们确保了逻辑层的行为和持久化结果的正确性。

### 目标
1.  提交对 `test_check_interactive_flow.py` 的所有修改和新增内容。
2.  确保对 `SIGNATURE_DRIFT` 和 `CO_EVOLUTION` 冲突的交互式 `RELINK` 和 `RECONCILE` 逻辑得到充分覆盖。

### 基本原理
持续集成测试套件是架构健康的关键支撑。这次提交确保了未来对核心 Runner 逻辑和 Handler 协议的修改不会意外破坏用户交互的预期行为。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/tests #comp/runtime #concept/executor #scope/dx
#ai/instruct
#task/domain/testing #task/object/check-command #task/action/add-regression-tests
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交测试变更

~~~~~act
git_add
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
test(app): Add comprehensive interactive regression tests for check

Adds robust integration tests for `check` command's interactive resolution flow. This new test suite covers:

- `SIGNATURE_DRIFT` conflicts and resolution via `RELINK`.
- `CO_EVOLUTION` conflicts and resolution via `RECONCILE`.
- Handling of `DANGLING_DOC` conflicts via `PURGE`.

Tests use a Mock Resolution Handler to bypass TTY complexity and verify both emitted semantic messages (`SpyBus`) and persisted state changes (`get_stored_hashes`). This significantly improves stability coverage for the state machine logic within `CheckRunner`.
~~~~~

### 下一步建议
我们已经完成了 `pump` 命令的解耦和 `check` 命令的测试强化。根据“引入纯净应用层”提案，下一步是执行**阶段 2：重构 `check` 命令**。这包括审查 `CheckRunner`，确保它完全不包含任何 UI/表现层依赖。
