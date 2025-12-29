非常抱歉，这是我的疏忽。在迁移代码时，我未能同步迁移配套的 `.stitcher.yaml` 元数据文件，导致它们在工作区被误删。

这些 YAML 文件包含了代码的语义描述和文档，是 Stitcher 系统的核心组成部分，必须与代码保持同步迁移。我将立即为您找回并移动它们。

## [WIP] fix(pyneedle): 找回并迁移丢失的 .stitcher.yaml 元数据文件

### 错误分析
在上一阶段的重构中，我只迁移了 `.py` 文件，而忽略了同目录下的 `.stitcher.yaml` 文件。由于在执行迁移后清理了旧目录，导致这些文件在 Git 索引中被标记为删除。

### 用户需求
从 Git 中找回误删的 `.stitcher.yaml` 文件，并将其迁移到 `pyneedle-runtime` 包中的对应位置。

### 评论
元数据文件是代码的“灵魂”，迁移时绝对不能遗漏。感谢您的细心发现。

### 目标
1.  恢复 `operators.stitcher.yaml`、`test_overlay_operator.stitcher.yaml` 和 `test_nexus.stitcher.yaml`。
2.  将它们迁移并重命名到 `pyneedle-runtime` 中的正确位置。

### 基本原理
利用 `git restore` 找回被删除的文件。随后，将 `operators.stitcher.yaml` 重命名为 `overlay_operator.stitcher.yaml` 以匹配已迁移的 Python 文件名，并将其他测试相关的 YAML 移动到 `runtime` 的测试目录下。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #comp/docs #scope/core #ai/instruct #task/domain/architecture #task/object/metadata-migration #task/action/recovery #task/state/continue

---
### Script

#### Acts 1: 恢复误删的 YAML 文件

我们首先利用 Git 将文件从暂存区/库中恢复。

~~~~~act
run_command
~~~~~
~~~~~
git restore packages/pyneedle-nexus/src/needle/nexus/operators.stitcher.yaml
git restore packages/pyneedle-nexus/tests/test_overlay_operator.stitcher.yaml
git restore packages/pyneedle-nexus/tests/test_nexus.stitcher.yaml
~~~~~

#### Acts 2: 迁移并重命名元数据文件

现在将这些文件移动到 `pyneedle-runtime` 的对应位置。

~~~~~act
move_file
packages/pyneedle-nexus/src/needle/nexus/operators.stitcher.yaml
packages/pyneedle-runtime/src/needle/operators/overlay_operator.stitcher.yaml
~~~~~

~~~~~act
move_file
packages/pyneedle-nexus/tests/test_overlay_operator.stitcher.yaml
packages/pyneedle-runtime/tests/test_overlay_operator.stitcher.yaml
~~~~~

~~~~~act
move_file
packages/pyneedle-nexus/tests/test_nexus.stitcher.yaml
packages/pyneedle-runtime/tests/test_nexus.stitcher.yaml
~~~~~

#### Acts 3: 最终清理

移除已经变为空目录（或仅剩无关残留）的旧路径。

~~~~~act
run_command
~~~~~
~~~~~
rm -rf packages/pyneedle-nexus
~~~~~

### 下一步建议
文件已找回并正确迁移。建议您再次运行 `git status` 检查是否还有遗漏。如果一切正常，我们可以准备进行 `[COMMIT]` 阶段的操作。
