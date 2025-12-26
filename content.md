好的，测试全部通过。这标志着 `stitcher-python` 已经完成了从文档提取、解耦生成到生命周期管理的完整闭环。现在我们将这些变更提交到仓库。

## [COMMIT] feat: 实现 `strip` 和 `eject` 命令以完善文档生命周期管理

### 用户需求
实现并集成 `strip`（瘦身）和 `eject`（弹出）功能，允许用户在“完全解耦模式”和“传统嵌入模式”之间自由切换。

### 评论
这是 `stitcher-python` 走向成熟的关键一步。通过提供 `strip` 命令，我们让“单一事实来源”原则在物理层面上得到了强制执行；而 `eject` 命令则消除了用户的“锁定恐惧”，确保了工具的开放性和透明性。

### 目标
1.  提交 `stitcher-scanner` 中的 AST 变换器（Stripper/Injector）。
2.  提交 `StitcherApp` 中的业务逻辑集成。
3.  提交 `stitcher-cli` 中的新命令及确认交互逻辑。
4.  提交相关的本地化资源和端到端测试。

### 基本原理
按照 `[COMMIT]` 协议，仅执行 Git 操作。我们在提交说明中详细描述了如何利用 LibCST 实现无损的代码变换，以及如何在 CLI 层通过确认提示保障操作的安全性。

### 标签
#intent/build #flow/done #priority/high 
#comp/cli #comp/application #comp/scanner #comp/common #scope/ux #concept/parser
#ai/instruct
#task/domain/dev-tools #task/object/lifecycle-management #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交生命周期管理功能

~~~~~act
git_add
.stitcher/needle/en/eject/main.json
.stitcher/needle/en/strip/main.json
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-common/src/stitcher/common/messaging/bus.py
packages/stitcher-scanner/src/stitcher/scanner/__init__.py
packages/stitcher-scanner/src/stitcher/scanner/transformer.py
packages/stitcher-scanner/tests/test_transformer.py
tests/integration/test_lifecycle_commands.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat: implement 'strip' and 'eject' commands for docstring lifecycle management

Completes the documentation decoupling loop by providing tools to safely 
remove docstrings from source or inject them back from external YAML files.

Key changes:
- Scanner: Implemented StripperTransformer and InjectorTransformer using LibCST
  for robust, format-preserving AST transformations.
- Application: Added 'run_strip' and 'run_eject' methods to handle file I/O 
  and orchestration.
- CLI: Added 'stitcher strip' and 'stitcher eject' commands with interactive 
  confirmation prompts to prevent accidental data loss.
- Common: Added 'render_to_string' to MessageBus to support UI components 
  requiring raw strings (like prompts).
- i18n: Added comprehensive English localization for the new commands.
- Tests: Added unit tests for AST transformers and integration tests for 
  the full CLI-to-disk workflow.

This provides users with a safe "exit strategy" and enables full compliance 
with the "Single Source of Truth" documentation principle.
~~~~~

### 下一步建议
- **性能优化**: 目前的所有操作都是全量扫描。随着项目规模增长，建议引入基于文件修改时间或 Git 状态的 **增量扫描机制**（任务 3.2）。
- **CI 集成文档**: 既然核心功能已完备，可以开始编写如何将 `stitcher check` 集成到 GitHub Actions 或 pre-commit 的指南。
