好的，逻辑已通过测试验证。现在我们将这些更改作为一个完整的逻辑单元提交。

我们已经在 `SidecarUpdateMixin` 中建立了一个鲁棒的 SURI 解析和更新机制，解决了重命名符号时签名文件（Signature Files）中键失效的问题。

## [COMMIT] fix(refactor): 增强 SidecarUpdateMixin 以支持 SURI 片段重命名

### 用户需求
在重命名符号（如类或函数）时，自动更新对应的 `.json` 签名文件中的 SURI 键（格式为 `py://path#fragment`），以确保重构后的指纹数据仍然有效。

### 评论
通过引入基于 `SURIGenerator` 的显式解析逻辑，我们彻底摆脱了之前脆弱的字符串前缀匹配。这不仅修复了现有的 Bug，还为未来支持更复杂的 SURI 结构奠定了基础，且无需立即进行大规模的架构分拆。

### 目标
1.  将 `SidecarUpdateMixin` 的 `_update_sidecar_data` 逻辑升级为感知 SURI 结构的模式。
2.  增加针对顶层符号和嵌套符号重命名的集成测试。

### 基本原理
逻辑核心在于：当操作发生在一个模块内部时，我们能够准确计算出该符号在 SURI 中对应的 `fragment`（即 `#` 之后的部分）。通过解析现有的 SURI，我们可以安全地仅替换 `fragment` 而不破坏 `path`，或者在文件移动时同时更新两者。

### 标签
#intent/fix #flow/ready #priority/high 
#comp/refactor #concept/state #scope/core 
#ai/instruct 
#task/domain/refactoring #task/object/sidecar-mixin #task/action/enhance-logic
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交重构代码与测试

我们将更改添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
packages/stitcher-refactor/tests/integration/test_rename_suri_update.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(refactor): enhance SidecarUpdateMixin to support SURI fragment renaming

Improved the SidecarUpdateMixin to correctly handle symbol renames within
signature files (.json). Previously, only the path part of the SURI was
updated during file moves, leaving SURI keys broken when symbols were renamed.

Changes:
- Reimplemented `_update_sidecar_data` to use `SURIGenerator` for parsing.
- Added logic to compute and update the #fragment part of SURIs during in-file renames.
- Supports both top-level and nested symbol (class method) renaming.
- Added integration tests covering various SURI update scenarios.

This fix ensures that documentation and fingerprint data remain linked to
the correct symbols after refactoring operations.
~~~~~

### 下一步建议
- **架构审计**: 虽然目前 "Fix in place" 效果很好，但长期来看，将 `SidecarRefactoringStrategy` 从 `refactor` 核心中剥离到独立的语言包中（如之前的规划）仍然是达成“泛化引擎”目标的必经之路。
- **扩展支持**: 可以检查是否还有其他类型的 Sidecar（如自定义插件生成的元数据文件）也需要类似的 SURI 更新逻辑。
