好的，测试通过证明了修复方案的有效性。

我们成功解决了 `StitcherApp.run_check` 在多目标扫描时的模块作用域覆盖问题，并完善了中文反馈信息的覆盖。现在我将生成 `[COMMIT]` 计划来提交这些变更。

## [COMMIT] fix: 修复 check 持久化失效 Bug 并完善中文本地化

### 用户需求
正式提交修复 `StitcherApp.run_check` 作用域漏洞的代码、回归测试用例以及 `stitcher-common` 中的汉化更新。

### 评论
通过引入 `all_modules` 列表，我们将所有 Target 的扫描结果完整保留到了执行阶段。回归测试验证了即使在多 Target 场景下，首个 Target 的文档哈希更新也能被正确持久化到 `.stitcher/signatures` 目录。

### 目标
1.  将核心逻辑修复、汉化资源和回归测试加入暂存区。
2.  创建一个符合规范的 Git 提交。

### 基本原理
遵循“验证意图而非实现”的原则，回归测试确保了物理存储的最终一致性。通过分离分析 (Phase 1) 和执行 (Phase 2)，我们消除了状态管理的歧义。

### 标签
#intent/fix #flow/done #priority/high #comp/runtime #comp/common #comp/tests #scope/core #scope/i18n #ai/instruct #task/domain/testing #task/object/check-command #task/action/fix #task/state/end

---

### Script

#### Acts 1: 提交修复与测试

我们将修复后的代码和新增的回归测试提交到仓库。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/tests/test_check_regression.py
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/state.json
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(app): ensure auto-reconciliation persistence across all targets

Fixed a critical scoping bug in `StitcherApp.run_check` where the `modules`
variable was overwritten in each target iteration. This caused the
auto-reconciliation phase (Phase 2) to only find and persist hash updates
for files in the last scanned target, silently skipping others.

Changes:
- Introduced `all_modules` list to accumulate `ModuleDef` across targets.
- Updated `Phase 2` lookup to use `all_modules`.
- Localized check state messages in `stitcher-common` for better UX.
- Added `test_check_regression.py` to ensure multi-target persistence.
~~~~~

### 下一步建议
- **代码清理**: 检查是否还有其他类似的循环作用域隐患（例如 `run_hydrate`）。
- **性能优化**: 随着 `all_modules` 包含的对象增多，未来的 Phase 2 查找可以考虑将其转换为字典映射以提高效率。
