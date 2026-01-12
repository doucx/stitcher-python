## [WIP] fix(check): 在转换分析结果时对错误条目进行去重以防止报告重复

### 摘要头
Fix: 在 CheckRunner 中对错误条目进行去重。

### 错误分析
测试 `test_ghost_keys_trigger_extra_error` 失败，显示 `FileCheckResult` 中的错误列表包含了重复的条目（例如 `['_ghost_private', '_ghost_private', 'ghost_func', 'ghost_func']`）。这表明在分析或结果转换阶段，同一个违例被处理或添加了多次。虽然根本原因可能涉及复杂的数据流，但在结果汇总层（`_translate_results`）进行防御性去重是确保报告准确性和系统健壮性的必要且有效的手段。

### 用户需求
修复 `test_ghost_keys_trigger_extra_error` 测试失败，确保 `check` 命令报告的错误列表不包含重复项。

### 评论
这是一个低风险的防御性修复。无论上游分析引擎是否产生重复（理论上不应该，但防御性编程总是有益的），结果转换层都应该保证输出的整洁。

### 目标
1.  修改 `packages/stitcher-application/src/stitcher/app/runners/check/runner.py`。
2.  在 `_translate_results` 方法中，在将违例 FQN 添加到结果列表之前，检查其是否已存在。

### 基本原理
通过在 `append` 之前添加 `if violation.fqn not in target_dict[key]:` 检查，我们可以简单有效地消除重复项，确保每个实体的每种错误类型只被报告一次。

### 标签
#intent/fix #flow/ready #priority/high #comp/application #scope/core #ai/instruct #task/domain/cli #task/object/check-runner #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 在 `_translate_results` 中实施去重

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
                if violation.kind == L.check.file.untracked_with_details:
                    keys = violation.context.get("keys", [])
                    target_dict[key].extend(keys)
                else:
                    target_dict[key].append(violation.fqn)

            if violation.kind in INTERACTIVE_VIOLATIONS:
~~~~~
~~~~~python.new
                if violation.kind == L.check.file.untracked_with_details:
                    keys = violation.context.get("keys", [])
                    # Deduplicate while extending
                    for k in keys:
                        if k not in target_dict[key]:
                            target_dict[key].append(k)
                else:
                    # Deduplicate single items
                    if violation.fqn not in target_dict[key]:
                        target_dict[key].append(violation.fqn)

            if violation.kind in INTERACTIVE_VIOLATIONS:
~~~~~

### 下一步建议
运行测试 `pytest packages/stitcher-application/tests/integration/test_check_policy.py` 验证修复是否生效。如果通过，建议运行所有 Check 相关的集成测试以确保没有回归。
