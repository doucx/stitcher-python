太棒了！所有测试通过意味着我们已经成功完成了这次复杂的重构，不仅消除了冗余代码，还显著优化了 `stitcher` 的内部架构，使其更具扩展性和可测试性。

现在，我们将执行 `[COMMIT]` 计划，将这些变更作为一个原子逻辑单元永久记录在历史中。

## [COMMIT] refactor: 迁移 stitcher-needle 至 pyneedle 并实现依赖注入

### 用户需求
彻底移除 `stitcher-needle` 冗余包，并将整个项目迁移至 `pyneedle` 生态系统，同时通过依赖注入优化 `MessageBus` 的架构。

### 评论
这是一次具有里程碑意义的重构。我们不仅遵循了 DRY 原则，消除了库与应用之间的代码重复，还通过引入显式的依赖注入（Dependency Injection）解决了潜在的循环依赖问题。这种架构上的提升为 `stitcher` 未来的长期稳定性提供了坚实保障。

### 目标
1.  将所有文件系统变更（删除 `stitcher-needle`、修改导入路径、重写 `MessageBus` 和测试工具）提交至 Git 仓库。
2.  提供详尽的提交记录，说明重构的原因和技术细节。

### 基本原理
由于本次重构涉及多个包的跨文件、跨组件修改，且所有修改已通过集成测试验证。我们将使用 `git add .` 将所有变更暂存，并创建一个包含完整架构变更说明的提交记录。

### 标签
#intent/refine #flow/ready #priority/high #comp/build #comp/common #comp/cli #comp/application #scope/core #ai/instruct #task/domain/architecture #task/object/stitcher-needle #task/action/removal #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存所有变更

我们将所有已验证的重构变更添加到 Git 暂存区。

~~~~~act
git_add
.
~~~~~

#### Acts 2: 提交重构记录

我们将创建一个详尽的提交消息，详细说明从 `stitcher-needle` 到 `pyneedle` 的迁移过程。

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: migrate stitcher-needle to pyneedle ecosystem

This commit completes the migration of Stitcher's semantic addressing runtime
to the generic 'pyneedle' library suite, following DRY principles.

Key changes:
- Deleted 'packages/stitcher-needle' and updated all internal references.
- Established 'stitcher.common' as the composition root for core services.
- Refactored 'MessageBus' to use constructor injection for the Nexus instance, 
  eliminating circular dependencies between 'common' and its sub-modules.
- Switched from global singletons to localized instances (stitcher_nexus, bus)
  controlled by the Stitcher application.
- Modernized test utilities: Renamed 'MockNeedle' to 'MockNexus' and 
  fully embraced dependency injection in unit and integration tests.
- Cleaned up workspace configurations in pyproject.toml and pyrightconfig.json.

This architectural shift improves testability and decouples the Stitcher core 
from the underlying pyneedle implementation details.
~~~~~

### 下一步建议
- **代码审查**: 虽然测试已通过，但建议对 `stitcher.common` 的新组装逻辑进行一次最后的代码审查。
- **文档更新**: 如果有开发者文档记录了如何使用 `needle`，现在需要更新为新的 `stitcher_nexus` 调用方式。
- **发布准备**: 确认 `pyneedle` 系列包的版本号和发布策略，因为它们现在是 `stitcher` 的核心外部依赖。
