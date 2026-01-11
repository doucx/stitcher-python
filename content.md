这是一个非常敏锐的发现。测试失败揭示了我们在定义 `__doc__` 的“存在性”时引入的语义偏差。

我们在 `ASTCheckSubjectAdapter` 中强制将 `__doc__` 标记为 `exists_in_code=True`，这成功解决了“YAML 有文档而代码无文档”被误判为 `DANGLING_DOC` 的问题。

然而，这也导致了副作用：在“YAML 无文档且代码无文档”的情况下，`CheckAnalyzer` 看到一个 `is_public=True` 且 `exists_in_code=True` 的 `__doc__`，判定其为 `MISSING`（缺少文档）。

**旧系统的行为逻辑是**：`__doc__` 是可选的。如果代码没写 docstring，就不强制要求 YAML 有。
**新系统的行为逻辑变成了**：`__doc__` 是必须的。如果代码没写，就报错说你缺文档。

这种策略变更导致了大量的测试回归。

我们不应该回退 `subject.py` 的修改，因为那对于解决 Dangling 问题是必要的。相反，我们应该在 `CheckAnalyzer` 层面显式地恢复“`__doc__` 是可选的”这一策略。

具体操作是：
1.  在判定 **Missing** (有代码无 YAML) 时，如果 FQN 是 `__doc__` 且源码内容为空，则**豁免**之。
2.  在判定 **Untracked** 时，同样从 `undocumented` 列表中排除 `__doc__`。

这能让我们同时满足“不报悬空”和“不报缺失”的双重需求。

## [WIP] fix(check): 在 CheckAnalyzer 中恢复对 __doc__ 的豁免逻辑

### 用户需求

解决因强制将 `__doc__` 视为存在而导致的广泛测试失败（主要是误报 `MISSING` 和 `UNTRACKED`）。恢复旧系统“默认不强制要求模块文档”的行为。

### 评论

这是一个策略调整。我们在数据层（Subject）统一了视图（`__doc__` 总是存在），而在业务层（Analyzer）应用了宽松的规则（`__doc__` 如果没写就算了）。这种分层处理比在数据层搞复杂的条件判断要清晰得多。

### 目标

修改 `packages/stitcher-application/src/stitcher/app/runners/check/analyzer.py`：
1.  在 `missing` 警告的判定分支中，增加对 `__doc__` 的过滤。
2.  在 `untracked` 警告的列表生成中，显式排除 `__doc__`。

### 基本原理

保持向后兼容性，不改变用户现有的文档策略（即不强制要求每个文件都有模块文档），同时保留之前修复的 Dangling Doc 误报问题。

### 标签

#intent/fix #flow/ready #priority/critical #comp/application #task/domain/quality #task/object/check-runner #task/action/bug-fix #task/state/end

---

### Script

#### Acts 1: 在 Analyzer 中应用豁免规则

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/analyzer.py
~~~~~
~~~~~python.old
            elif state.is_public and state.exists_in_code and not state.exists_in_yaml:
                if state.source_doc_content:
                    result.errors["pending"].append(fqn)
                else:
                    result.warnings["missing"].append(fqn)

            elif not state.exists_in_code and state.exists_in_yaml:
~~~~~
~~~~~python.new
            elif state.is_public and state.exists_in_code and not state.exists_in_yaml:
                if state.source_doc_content:
                    result.errors["pending"].append(fqn)
                else:
                    # Legacy Behavior: __doc__ is optional.
                    # If it's missing in both source and YAML, don't report it as missing.
                    if fqn != "__doc__":
                        result.warnings["missing"].append(fqn)

            elif not state.exists_in_code and state.exists_in_yaml:
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/analyzer.py
~~~~~
~~~~~python.old
            # Check for any public symbols that would be documented
            undocumented = [
                s.fqn
                for s in subject.get_all_symbol_states().values()
                if s.is_public and not s.source_doc_content and not s.exists_in_yaml
            ]
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
~~~~~
~~~~~python.new
            # Check for any public symbols that would be documented
            undocumented = [
                s.fqn
                for s in subject.get_all_symbol_states().values()
                if s.is_public
                and s.fqn != "__doc__"
                and not s.source_doc_content
                and not s.exists_in_yaml
            ]
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
~~~~~

### 下一步建议

请重新运行测试。这次修复应该能精准地覆盖所有回归场景，让我们的测试全绿。

一旦测试通过，我们就可以将这一系列重构作为一个整体进行 Commit，然后开始我们真正的目标：实现 `IndexCheckSubjectAdapter`。这将变得非常简单，因为最难的逻辑对齐工作已经在 AST 这一侧完成了。
