测试通过。SURI 路径更新问题的修复确保了重构操作后系统内部状态的绝对一致性。现在我们将这些更改正式提交。

## [COMMIT] fix(refactor): Update SURI keys in sidecar files during moves

### 用户需求
当文件被移动时，其对应的签名文件（`.json`）中的 SURI 键（格式为 `py://<file_path>#<symbol>`）必须同步更新，以反映文件在工作区中的新位置。

### 评论
这是一个至关重要的修复。SURI 是 Stitcher 标识代码实体的唯一“坐标”，如果文件移动后 SURI 保持不变，则会导致现有的签名数据失效。此修复完善了重构引擎的“整体性”原则，确保了元数据与代码的同步演进。

### 目标
1.  在 `SidecarUpdateIntent` 中增加对原始文件路径和目标文件路径的支持。
2.  在 `MoveFileOperation` 和 `MoveDirectoryOperation` 中捕获并传递这些路径信息。
3.  增强 `SidecarUpdateMixin` 的转换逻辑，使其能够识别并重写 SURI 格式的键。

### 基本原理
通过修改 `SidecarUpdateIntent` 这一核心通信对象，我们将路径变更信息从操作层（Operations）传递到了执行层（Planner）。在最终执行数据转换的 `SidecarUpdateMixin` 中，我们增加了对 `py://` 前缀的识别逻辑。如果检测到 SURI 中的路径部分与移动前的路径匹配，则将其替换为新路径，从而实现了对签名文件内容的精准重构。

### 标签
#intent/fix #flow/ready #priority/high #comp/refactor #concept/suri #scope/core #ai/instruct #task/domain/refactor #task/object/suri-integrity #task/action/fix-implementation #task/state/end

---

### Script

#### Acts 1: 提交 SURI 更新修复

我们将暂存所有涉及的架构文件，包括意图定义、操作逻辑和执行器计划。

~~~~~act
git_add
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(refactor): update SURI keys in sidecar files during moves

Ensures that SURI keys (py://<path>#<fragment>) in signature files are
correctly updated when a file or directory is moved.

Previously, while the sidecar files themselves were moved, their content
remained stale, with keys still pointing to the old file path. This broke
the link between the moved code and its stored metadata.

Changes:
- Added 'old_file_path' and 'new_file_path' to SidecarUpdateIntent.
- Updated MoveFile and MoveDirectory operations to propagate path info.
- Enhanced SidecarUpdateMixin to detect and rewrite SURI-formatted keys.
- Added an integration test to verify SURI integrity after a move.
~~~~~

### 下一步建议
- **回归测试**: 建议运行全量集成测试 `pytest tests/integration`，确保此次对 `SidecarUpdateMixin` 的修改没有影响到正常的 FQN 重命名逻辑。
- **清理测试文件**: 如果不再需要，可以删除新创建的测试文件，或者将其保留作为永久的回归测试套件。
- **继续重构**: 现在基础设施已经稳固，你可以继续执行 `migrations/001_phase_1_sinking.py` 脚本了。
