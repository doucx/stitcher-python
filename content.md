太棒了。测试的全面通过标志着我们成功完成了一次深度的架构拨乱反正。通过建立显式的上下文传递契约，我们不仅根除了由于“启发式猜测”导致的逻辑崩溃，更将重构引擎的稳定性提升到了一个新的量级。

我们现在将这些关键的架构修正正式提交。

## [COMMIT] refactor(refactor): establish deterministic contract for sidecar updates

### 用户需求
彻底移除重构引擎中用于推导模块边界的启发式字符串操作，建立一个确定性的、上下文感知的 Sidecar 更新机制。

### 评论
这次重构解决了系统中最深层的歧义来源。通过将“确定模块边界”的职责从低层的 Mixin 提升到拥有全局视野的 Planner，我们确保了符号标识符（SURI 和 Fragment）的计算始终建立在物理事实之上。这不仅修复了嵌套符号重命名时的崩溃，也让整个重构逻辑变得极其清晰和可预测，完美符合 HFEA 的“零启发式”公理。

### 目标
1.  提交对 `SidecarUpdateMixin` 的重构，移除 `_get_module_fqn_from_symbol_fqn`。
2.  提交对 `Planner` 的增强逻辑，使其能根据全局意图计算并传递模块上下文。
3.  提交经过完整重写、能验证 SURI/Fragment 逻辑的单元测试。

### 基本原理
我们确立了以下确定性契约：
- **Planner (决策)**: 利用全局 `MoveFileIntent` 建立模块重命名映射，为每一个 Sidecar 更新意图确定地提供 `old_module_fqn` 和 `new_module_fqn`。
- **Mixin (计算)**: 仅执行物理层面的“减法”操作（`FQN - Module_FQN`），不再对命名空间结构做任何猜测。

### 标签
#intent/refine #flow/ready #priority/critical #comp/engine #concept/refactoring-engine #scope/core #ai/brainstorm #task/domain/refactoring #task/object/sidecar-updates #task/action/architectural-fix #task/state/end

---

### Script

#### Acts 1: 提交架构修正与测试

我们将核心重构逻辑和配套的单元测试添加到 Git 暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(refactor): establish deterministic contract for sidecar updates

Eliminates heuristic string manipulation in the refactoring engine and establishes
an explicit context-passing contract between the Planner and SidecarUpdateMixin.

Key Changes:
1.  Removed '_get_module_fqn_from_symbol_fqn' from SidecarUpdateMixin, eradicating
    illegal heuristic guesses about module boundaries.
2.  Refactored '_update_sidecar_data' to explicitly receive 'old_module_fqn' and
    'new_module_fqn' contexts.
3.  Enhanced Planner to compute the correct module context mapping by pre-processing
    MoveFileIntents, ensuring deterministic fragment calculation for nested symbols.
4.  Completely replaced obsolete unit tests with a new suite validating SURI (JSON)
    and Fragment (YAML) update strategies in isolation.

This fix resolves AssertionErrors in nested method renaming and ensures that
sidecar updates are anchored to the physical reality of the module structure.
~~~~~

### 下一步建议

“大清洗”行动至此已圆满结束。我们已经：
1.  ✅ 清洗并规范化了所有测试数据。
2.  ✅ 重写了 `SidecarAdapter` 以支持物理 SURI 采集。
3.  ✅ 重写了 `Planner` 与 `Mixin`，建立了确定性的 sidecar 更新契约。

**系统已重回稳态。**

接下来的建议方向：
- **模块化迁移**: 正如您之前注意到的，`stitcher-refactor` 目前还在 Mixin 中手动处理逻辑。我们现在可以考虑将这些逻辑正式迁移/集成到 `stitcher-lang-sidecar` 中，使 `Planner` 调用更高级的抽象。
- **性能优化**: 随着 SURI 体系的确立，我们可以优化 `IndexStore` 的查询路径，进一步提升大规模重构时的响应速度。
- **扩展重构类型**: 我们可以利用这套稳固的 SURI 体系，开始实现更复杂的重构，如“跨文件提取类”或“命名空间合并”。

您想先从哪个方向继续？
