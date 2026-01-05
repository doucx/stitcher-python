好的，我们将使用 Stitcher 的重构引擎，将 `MessageBus` 重命名为 `FeedbackBus`。这个过程是自动化的，将包括创建迁移脚本、执行重构和清理临时文件。

## [WIP] refactor: 将 MessageBus 重构为 FeedbackBus

### 用户需求
用户希望使用 Stitcher 的重构功能，将系统内所有的 `MessageBus` 符号重命名为 `FeedbackBus`。

### 评论
这是一个很好的实践。`FeedbackBus` 比 `MessageBus` 更能准确地描述其职责——传递面向用户的反馈信息，而不仅仅是通用的消息。这次重构将提升代码的清晰度和可维护性。

### 目标
1.  创建一个临时的 Stitcher 迁移脚本。
2.  在该脚本中定义一个从 `stitcher.common.messaging.bus.MessageBus` 到 `stitcher.common.messaging.bus.FeedbackBus` 的重构操作。
3.  执行该脚本，自动修改项目中的所有相关文件（定义、导入和使用）。
4.  删除临时脚本。

### 基本原理
我们将利用 `stitcher-refactor` 模块的 `RenameSymbolOperation`。该操作首先会利用 Griffe 构建整个项目的语义图谱，精确定位 `MessageBus` 的定义点及其所有引用点（包括跨包的引用）。然后，它会生成一系列针对性的文件修改操作（`FileOp`），通过 `TransactionManager` 原子性地应用这些变更，确保重构的完整性和正确性。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #comp/runtime #scope/core #scope/dx #ai/instruct #task/domain/core-abstractions #task/object/message-bus #task/action/rename #task/state/begin

---

### Script

#### Acts 1: 创建迁移脚本
首先，我们创建一个迁移脚本，用于定义重构规则。

~~~~~act
write_file
example/001_rename_message_bus.py
~~~~~
~~~~~python
from stitcher.refactor.migration import MigrationSpec, Rename

def upgrade(spec: MigrationSpec):
    """
    Renames the core MessageBus to FeedbackBus to better reflect its purpose.
    """
    spec.add(
        Rename(
            old_fqn="stitcher.common.messaging.bus.MessageBus",
            new_fqn="stitcher.common.messaging.bus.FeedbackBus",
        )
    )
~~~~~

#### Acts 2: 执行重构
现在，我们使用 `stitcher` 的 CLI 来应用这个迁移脚本。`--yes` 参数将自动确认并执行所有计划的操作。

~~~~~bash
stitcher refactor apply example/001_rename_message_bus.py --yes
~~~~~

### 下一步建议
重构完成后，建议运行项目的完整测试套件（`pytest`），以确保重构没有引入任何回归错误。Stitcher 的重构是基于静态分析的，虽然非常可靠，但通过测试进行最终验证是保证代码质量的最佳实践。
