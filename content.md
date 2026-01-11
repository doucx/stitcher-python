You are absolutely right to point out the test failure. My previous implementation had a subtle but critical flaw.

## [WIP] fix: Correct error flag handling in `run_check`

### 错误分析

测试 `test_check_fails_gracefully_on_local_import` 仍然失败，是因为我在 `StitcherApp.run_check` 方法中错误地重置了错误状态。

1.  我的修改在 `ensure_index_fresh()` 之后，如果索引构建失败，会正确地设置 `self.scanner.had_errors = True`。
2.  **但是**，在这之后，我又错误地保留了一行 `self.scanner.had_errors = False`，这行代码是旧流程的遗留物，它会立即把我刚刚设置的 `True` 状态覆盖回 `False`。
3.  因此，即使索引阶段失败了，当函数执行到末尾的 `return report_success and not self.scanner.had_errors` 时，`had_errors` 标志也是 `False`，导致整个 `run_check` 意外地返回了 `True`，从而引发了断言失败。

### 用户需求

修复 `StitcherApp.run_check` 中的逻辑，确保在索引构建阶段发生的任何错误都能被正确地记录下来，并最终导致整个 `check` 命令返回失败状态 (`False`)。

### 评论

这是一个典型的状态管理错误。修复方法很简单：将错误状态的重置 (`self.scanner.had_errors = False`) 移动到 `run_check` 方法的最开始，并确保在后续流程中不再有其他的重置操作。这样，任何阶段（无论是索引还是检查）设置的错误状态都会被保留到函数结束。

### 目标

1.  修改 `StitcherApp.run_check`。
2.  将 `self.scanner.had_errors = False` 移到函数的第一行。
3.  确保 `if not self.ensure_index_fresh():` 块能正确地设置此标志，并且该标志不会被再次重置。

### 基本原理

通过在函数入口处统一初始化状态，我们可以确保后续的条件分支只会单向地将状态从“成功”变为“失败”。这种模式比在函数中间重置状态要健壮得多，可以有效防止状态被意外覆盖。

### 标签

#intent/fix #flow/ready #priority/critical
#comp/engine #comp/tests #scope/core
#ai/brainstorm
#task/domain/testing #task/object/zero-io-check #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `run_check` 中的错误状态管理

我将对 `packages/stitcher-application/src/stitcher/app/core.py` 应用一个补丁来修正 `run_check` 方法的逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        if not self.ensure_index_fresh():
            self.scanner.had_errors = True
        
        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []
        all_modules_for_post_processing: List[ModuleDef] = []

        self.scanner.had_errors = False

        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
~~~~~
~~~~~python.new
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        self.scanner.had_errors = False
        if not self.ensure_index_fresh():
            self.scanner.had_errors = True

        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []
        all_modules_for_post_processing: List[ModuleDef] = []

        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
~~~~~

### 下一步建议

这次的修复直接命中了问题的根源。现在，当索引阶段发生错误时，`had_errors` 标志会被正确设置并保持，直到 `run_check` 方法返回。

我建议重新运行测试套件以验证此修复。如果所有测试都通过，我们就可以确认 Zero-IO Check 的所有阶段都已成功完成，并且系统的鲁棒性得到了保证。
