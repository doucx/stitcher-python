你的分析非常精准。测试失败暴露了 `SidecarUpdateMixin` 中两个关键的逻辑缺陷：

1.  **过于激进的短名称识别**：目前的逻辑假设任何不以 `module_fqn.` 开头的键都是短名称，并盲目地为其添加前缀。这导致了 `mypkg.other_mod.MyClass` 被错误地识别为短名称，并被转换成了 `mypkg.new_mod.mypkg.other_mod.MyClass`。
2.  **模块重命名时的上下文漂移**：当重命名整个模块时，`module_fqn` 本身也发生了变化。在将 FQN 转换回短名称时，必须使用**新的**模块 FQN 作为基准，否则转换将失败（导致输出完整的 FQN）。

我将修复 `base.py` 中的这些逻辑错误。

## [WIP] fix: 修复 SidecarUpdateMixin 中的短名称识别与上下文转换逻辑

### 错误分析

1.  **短名称判定失效**：在 `test_update_module_rename` 中，当 `module_fqn` 为 `mypkg.old_mod` 时，处理键 `mypkg.other_mod.MyClass`。由于它不以 `mypkg.old_mod.` 开头，逻辑将其误判为短名称并前缀化。
    *   **改进策略**：引入基于项目前缀的启发式检查。如果一个键已经包含了项目的根包名（Project Root Package）但不是当前模块，则应将其视为其他模块的 FQN，而非当前模块的短名称。
2.  **转换基准错误**：在 `test_update_short_name_when_module_is_renamed` 中，模块从 `old_mod` 变更为 `new_mod`。逻辑成功生成了 `mypkg.new_mod.MyClass`，但在尝试还原为短名称时，它仍在使用旧的 `module_fqn` (`mypkg.old_mod`) 进行匹配，导致匹配失败并输出了完整的 FQN。
    *   **改进策略**：在转换回短名称时，检测是否正在进行模块级重命名。如果是，则使用 `new_fqn` 作为新的“有效模块上下文”。

### 用户需求

修复 `SidecarUpdateMixin` 中的 Bug，确保其能够正确处理模块重命名场景，并准确区分短名称与无关的 FQN。

### 评论

这是一个非常微妙的逻辑点。Mixin 必须在缺乏全局语义图谱的情况下，仅凭字符串模式做出正确的决策。通过引入“项目前缀”和“动态上下文”的概念，我们可以显著提高这种启发式判断的准确性。

### 目标

1.  修改 `SidecarUpdateMixin._update_sidecar_data` 方法。
2.  实现更精确的 `is_short_name` 判定逻辑。
3.  在转换回短名称时，使用动态计算的 `effective_new_module` 上下文。

### 基本原理

1.  **项目感知**: 通过 `module_fqn.split('.')[0]` 提取项目根包名。如果键以该包名开头但不属于当前模块，则判定为 FQN。
2.  **动态上下文**: 如果 `old_fqn == module_fqn`（意味着正在重构当前模块本身），则在还原短名称时，逻辑上的“当前模块”已变为 `new_fqn`。

### 标签

#intent/fix #flow/ready #priority/high #comp/runtime #scope/core #ai/instruct #task/domain/refactoring #task/object/sidecar-updater-mixin #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `base.py` 中的 Mixin 逻辑

我们将更新 `SidecarUpdateMixin` 的实现，以修正上述逻辑缺陷。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python.old
    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
    ) -> Dict[str, Any]:
        new_data = {}
        modified = False

        for key, value in data.items():
            key_fqn = key
            is_short_name = False

            if module_fqn:
                if not key.startswith(module_fqn + "."):
                    key_fqn = f"{module_fqn}.{key}"
                    is_short_name = True
                else:
                    is_short_name = False

            new_key = key
            if key_fqn == old_fqn:
                target_fqn = new_fqn
                if is_short_name and module_fqn:
                    if target_fqn.startswith(module_fqn + "."):
                        new_key = target_fqn[len(module_fqn) + 1 :]
                    else:
                        new_key = target_fqn
                else:
                    new_key = target_fqn
                modified = True

            elif key_fqn.startswith(old_fqn + "."):
                suffix = key_fqn[len(old_fqn) :]
                target_fqn = new_fqn + suffix
                if is_short_name and module_fqn:
                    if target_fqn.startswith(module_fqn + "."):
                        new_key = target_fqn[len(module_fqn) + 1 :]
                    else:
                        new_key = target_fqn
                else:
                    new_key = target_fqn
                modified = True

            new_data[new_key] = value

        return new_data if modified else data
~~~~~
~~~~~python.new
    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
    ) -> Dict[str, Any]:
        new_data = {}
        modified = False

        for key, value in data.items():
            key_fqn = key
            is_short_name = False

            if module_fqn:
                if key.startswith(module_fqn + "."):
                    key_fqn = key
                    is_short_name = False
                else:
                    # Heuristic: If it starts with the project's root package but not
                    # the current module, it's likely an FQN from another module.
                    project_prefix = module_fqn.split(".")[0] + "."
                    if key.startswith(project_prefix):
                        key_fqn = key
                        is_short_name = False
                    else:
                        key_fqn = f"{module_fqn}.{key}"
                        is_short_name = True

            # Determine the effective module FQN for short-name restoration.
            # If the module itself is being renamed, the new context is new_fqn.
            effective_new_module = new_fqn if old_fqn == module_fqn else module_fqn

            new_key = key
            if key_fqn == old_fqn:
                target_fqn = new_fqn
                if is_short_name and effective_new_module:
                    if target_fqn.startswith(effective_new_module + "."):
                        new_key = target_fqn[len(effective_new_module) + 1 :]
                    else:
                        new_key = target_fqn
                else:
                    new_key = target_fqn
                modified = True

            elif key_fqn.startswith(old_fqn + "."):
                suffix = key_fqn[len(old_fqn) :]
                target_fqn = new_fqn + suffix
                if is_short_name and effective_new_module:
                    if target_fqn.startswith(effective_new_module + "."):
                        new_key = target_fqn[len(effective_new_module) + 1 :]
                    else:
                        new_key = target_fqn
                else:
                    new_key = target_fqn
                modified = True

            new_data[new_key] = value

        return new_data if modified else data
~~~~~

### 下一步建议

逻辑已修复。请重新运行 `packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py`。这次所有 8 个测试用例（包括之前失败的模块重命名相关用例）都应该能够顺利通过。

如果通过，我们就可以准备最终的 `[COMMIT]` 计划。
