好的，`Stitcher` 的依赖迁移已经完成。我们成功解除了与本地 `Needle` 源码的耦合，现在 `Stitcher` 使用的是 PyPI 上的正式发布版本。

我将生成一个 `[COMMIT]` 计划，记录这次重要的依赖重构。

## [COMMIT] chore(deps): 将 pyneedle 系列依赖切换至 PyPI 正式版 v0.1.0

### 用户需求
将 `Stitcher` monorepo 中所有对 `pyneedle` 系列包的本地路径依赖更新为 PyPI 托管的正式版本。

### 评论
这是一次关键的解耦操作。将依赖项从本地文件系统路径（`path = "../Needle/..."`）转向正式的包管理分发渠道（PyPI），标志着 `Stitcher` 项目达到了更高的工程成熟度。这极大地方便了外部贡献者，并确保了 CI/CD 环境的一致性。

### 目标
1. 暂存 6 个子包及根目录中受影响的 `pyproject.toml` 文件。
2. 提交这些变更，并详细记录迁移的背景（`pyneedle` 已发布）。

### 基本原理
按照 Conventional Commits 规范，使用 `chore(deps)` 类型记录此次依赖变更。通过移除 `uv` 的 `sources` 覆盖并固定版本号，我们使构建过程变得确定且可重现。

### 标签
#intent/tooling #flow/ready #priority/high #comp/build #concept/config #scope/dx #ai/instruct #task/domain/tooling #task/object/dependency-migration #task/action/commit #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交依赖迁移变更

我们将暂存所有修改后的配置文件，并执行逻辑提交。

~~~~~act
git_add
pyproject.toml
packages/stitcher-spec/pyproject.toml
packages/stitcher-bus/pyproject.toml
packages/stitcher-analysis/pyproject.toml
packages/stitcher-application/pyproject.toml
packages/stitcher-cli/pyproject.toml
packages/stitcher-test-utils/pyproject.toml
uv.lock
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
chore(deps): switch pyneedle dependencies to PyPI version 0.1.0

With the successful release of pyneedle and its components to PyPI, this commit migrates the Stitcher monorepo to use these official distributions instead of local path-based overrides.

Changes:
- Updated dependencies in all sub-packages to pin 'pyneedle', 'pyneedle-pointer', and 'pyneedle-spec' to version 0.1.0.
- Removed local path mappings from [tool.uv.sources] in the root pyproject.toml.
- Updated project and dev-dependencies to reflect the new versioned requirements.

This decouples the Stitcher build process from the local 'Needle' repository, improving portability and build reproducibility.
~~~~~

### 下一步建议
- **更新文档**: 如果 `Stitcher` 的 `README` 中包含有关如何设置开发环境的说明，请更新它们，现在不再需要将 `Needle` 仓库放在同级目录了。
- **发布 Stitcher**: 随着底层依赖的稳定，下一步可以考虑为 `Stitcher` 自身也建立类似的发布流。
