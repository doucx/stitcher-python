好的，既然集成测试已经通过，证明修复逻辑已成功覆盖了 Pump 和 Init 命令所依赖的写入路径。

我将生成一个 `[COMMIT]` 计划，将修复代码和新增的单元测试一并提交。

## [COMMIT] fix(sidecar): 强制所有 Sidecar 输出路径使用块标量格式

### 用户需求
提交修复代码，确保 Sidecar 文件在任何更新场景下都保持一致的 `|-` 格式。

### 评论
此修复解决了 `SidecarAdapter` 中的一个逻辑漏点。通过在底层 `dump_raw_data_to_string` 方法中增加原地强制转换，我们不仅修复了当前的集成测试失败，还为未来可能的其他写入路径提供了“格式保险”。

### 目标
1.  将 `adapter.py` 和 `test_sidecar_adapter.py` 的更改提交到 Git。

### 基本原理
遵循 `[COMMIT]` 规范，此计划仅包含 Git 操作。我们在提交消息中清晰地描述了修复的原理：即通过原地修改 `ruamel.yaml` 的数据结构来保证在高保真（High-Fidelity）更新模式下的输出一致性。

### 标签
#intent/fix #flow/ready #priority/medium #comp/runtime #comp/tests #concept/state #ai/instruct #task/domain/storage #task/object/sidecar-adapter #task/action/commit #task/state/end

---

### Script

#### Acts 1: 提交变更

我们将修改后的文件添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
packages/stitcher-lang-sidecar/tests/unit/test_sidecar_adapter.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(sidecar): force block scalar format for all docstring outputs

Previously, the 'pump' and 'init' commands (which use dump_raw_data_to_string) could produce sidecar files where single-line docstrings were serialized as plain YAML strings instead of the required literal block scalar ('|-') format.

This happened because dump_raw_data_to_string was dumping the raw data structure (CommentedMap) without ensuring its values were wrapped in LiteralScalarString.

Changes:
- Added `_ensure_block_scalars_inplace` to SidecarAdapter to recursively convert strings to LiteralScalarString while preserving metadata/comments.
- Integrated this check into dump_raw_data_to_string to cover all high-fidelity update paths.
- Added a reproduction unit test in test_sidecar_adapter.py.

This ensures consistent formatting across all sidecar modification paths.
~~~~~

### 下一步建议
- **回归检查**: 既然 Sidecar 的格式化问题已经解决，建议运行完整的集成测试套件，确保没有其他由于 `ruamel.yaml` 严格模式引起的潜在问题。
- **性能评估**: 由于 `_ensure_block_scalars_inplace` 是递归执行的，虽然 Sidecar 文件通常不大，但在处理极端巨大的文件时可能会有微小开销。目前阶段无需优化，但值得在未来关注。
