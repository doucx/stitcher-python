太棒了。所有测试均已通过，这标志着 Stitcher 对 PEP 561 存根包的支持已经从“功能实现”进化到了“质量可验证”的阶段。

通过 `test_ide_proxy.py` 中的 shadowing 验证，我们确信生成的 `pyi` 文件在 site-packages 中具有正确的优先级，且不会破坏同名命名空间的其他运行时子包。

我将生成一个 `[COMMIT]` 计划，将这些关键的改进和测试套件正式合入仓库。

## [COMMIT] test: add integration tests for PEP 561 stub package resolution and compliance

### 用户需求
将近期关于存根包 (Stub Package) 生成逻辑的重构，以及配套的集成测试套件（包括隔离环境测试工具 `VenvHarness`）提交到 Git 仓库。

### 评论
这是一次重要的提交。它不仅修复了存根包生成时的命名规范问题（遵循 PEP 561），还引入了一套基于隔离虚拟环境的集成测试方法论。这套方法论为后续验证 Stitcher 在复杂 Monorepo 环境下的行为提供了坚实的基础。

### 目标
1.  提交 `stitcher-application` 中关于 PEP 561 路径计算的修复。
2.  提交 `stitcher-test-utils` 中新增的 `VenvHarness` 工具，用于创建隔离的测试环境。
3.  提交完整的集成测试套件，覆盖结构合规性、类型解析、命名空间共存以及 IDE Proxy 优先级验证。

### 基本原理
按照计划，我们先执行文件变更，确认无误后通过独立的 `[COMMIT]` 计划进行提交。这符合“脚本与提交隔离”的原则。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/runtime #comp/build #concept/executor #scope/dx #ai/instruct #task/domain/testing #task/object/stub-package-integration #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交变更

我们将所有涉及到的文件添加到暂存区，并创建一个描述详尽的提交。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
packages/stitcher-test-utils/src/stitcher/test_utils/__init__.py
packages/stitcher-test-utils/src/stitcher/test_utils/harness.py
tests/integration/conftest.py
tests/integration/test_ide_proxy.py
tests/integration/test_stub_package_namespace.py
tests/integration/test_stub_package_pep561.py
tests/integration/test_stub_package_resolution.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
test: add integration tests for PEP 561 stub package resolution

This commit introduces a robust integration testing suite for generated 
PEP 561 "Stub-only Packages" and refactors the generation logic to 
ensure full compliance with naming conventions.

Key changes:
- Refactored `StubPackageManager` and `StitcherApp` to use standardized 
  `<namespace>-stubs` naming for the internal source directory, 
  preventing namespace collisions as per PEP 561.
- Introduced `VenvHarness` in `stitcher-test-utils`, providing an 
  automated way to create isolated virtual environments, install 
  generated packages, and run type checkers (Mypy/Pyright).
- Added E2E tests for:
    - Structure compliance (correct directory nesting and pyproject.toml).
    - Installation and resolution (verifying types are read from stubs).
    - Namespace coexistence (ensuring stubs don't "kill" runtime siblings).
    - Shadowing priority (verifying stubs take precedence over implementation).
~~~~~

### 下一步建议
- **CI 集成**: 建议将这些集成测试集成到项目的 GitHub Actions 或其他 CI 流水中，因为它们依赖真实的 `pip` 和类型检查器，是防止回归的最佳手段。
- **发布准备**: 随着测试链路的打通，下一步可以考虑优化存根包的版本控制逻辑（目前是占位符 `0.1.0`），使其能自动同步主项目的版本。
