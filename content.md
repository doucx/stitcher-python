好的，既然代码修改和测试适配都已经完成，现在我们将这些变更作为一个完整的逻辑单元提交到 Git 仓库。

这个提交标志着我们成功解决了困扰系统的架构性循环依赖问题，使包结构更加清晰和健壮。

## [COMMIT] fix(arch): resolve circular dependencies and move services

### 用户需求
将之前所有用于解决循环依赖和修复导入错误的变更提交到 Git。

### 评论
这是一个非常重要的“清洁”提交。它不仅修复了技术上的缺陷（循环依赖），还通过移动服务层和解耦包初始化，在架构层面上确立了更清晰的依赖原则。这将显著降低未来的维护成本，并防止类似的回归问题。

### 目标
1.  将所有受影响的文件添加到 Git 暂存区。
2.  创建一个包含详尽说明的提交，记录重构的动机和结果。

### 基本原理
按照 Quipu 的工作流规范，在完成文件系统层面的修改并确认逻辑正确后，我们需要创建一个 `[COMMIT]` 计划。这能确保代码库的每一个快照都是稳定的、经过测试的，并且有据可查。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #comp/cli #comp/tests #concept/dependency-graph #scope/core #ai/instruct #task/domain/architecture #task/object/circular-dependency #task/action/elimination #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交变更

我们将把重构涉及的所有文件加入暂存区并提交。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/__init__.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/services
packages/stitcher-stubgen/src/stitcher/stubgen/__init__.py
packages/stitcher-stubgen/src/stitcher/stubgen/runners.py
packages/stitcher-cli/src/stitcher/cli/__init__.py
packages/stitcher-cli/src/stitcher/cli/factories.py
packages/stitcher-application/tests/unit/test_doc_manager.py
packages/stitcher-application/tests/unit/test_doc_manager_strategies.py
packages/stitcher-application/tests/unit/test_doc_overlay.py
packages/stitcher-application/tests/unit/test_docstring_hybrid.py
packages/stitcher-application/tests/unit/test_execution_planner.py
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(arch): resolve circular dependencies and move services

This commit addresses the architectural circular dependencies identified by 'stitcher check'.

Key changes:
- Moved the common service layer ('DocumentManager', 'ScannerService', etc.) from 'stitcher.app.services' to a top-level 'stitcher.services' package. This breaks the cross-package cycle between stitcher-application and stitcher-stubgen.
- Cleaned up '__init__.py' files in 'stitcher.app' and 'stitcher.cli'. By removing implementation-heavy imports (like 'StitcherApp' or 'app' instance), we prevent initialization-time cycles when modules use absolute import paths.
- Updated all affected modules, tests, and test-utils to use the new service paths and explicit class import paths.

These changes ensure a clean separation of concerns and allow for independent testing and verification of components.
~~~~~

### 下一步建议
- **回归测试**: 执行 `stitcher check` 确认系统中不再有任何循环依赖。
- **架构文档更新**: 如果有相关的设计文档或图表，现在应该更新它们以反映新的 `stitcher.services` 层级结构。
- **继续功能开发**: 既然地基已经修补完成，我们可以安全地继续进行后续的功能迭代或性能优化。
