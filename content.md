好的，我们已经成功完成了 **任务 1.1**（项目初始化与 CLI 框架）以及解耦消息总线系统的引入。整个项目的核心链路现已完全连通，且测试策略已升级为基于“意图”的验证模式。

现在我将生成一个 `[COMMIT]` 计划，将这些关键的架构进展固化到 Git 仓库中。

## [COMMIT] feat: 实现解耦消息总线并完成 CLI 与应用层的缝合

### 用户需求
将已实现的 `stitcher-common` 消息系统、`stitcher-cli` 入口点以及经过测试重构的应用层代码提交到 Git 仓库。

### 评论
这次提交标志着 `stitcher-python` 从一个逻辑库正式演变为一个具有生产级架构的工具。通过引入参考 Cascade 经验的消息总线，我们在 MVP 阶段就实现了 UI 逻辑与业务逻辑的彻底分离。同时，对测试套件的重构确保了未来功能扩展（如插件发现）时，测试依然能保持极高的稳定性。

### 目标
1.  将所有新创建的包（`common`, `cli`）和重构后的代码添加到暂存区。
2.  创建一个详尽的提交记录，涵盖消息总线的设计和应用层的缝合。

### 基本原理
遵循 `quipu-plan` 协议，在完成架构级重构和功能整合后建立稳定的检查点。这为接下来开发复杂的插件发现机制（任务 1.4）提供了一个整洁、解耦且经过充分测试验证的起点。

### 标签
#intent/build #flow/ready #priority/high
#comp/cli #comp/common #comp/app #comp/tests #concept/ui #scope/dx
#task/domain/infra #task/object/cli-messaging #task/action/commit
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更
我们将添加所有新文件并创建一个包含架构变更说明的提交。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat: implement decoupled messaging and wire up CLI to Application layer

Significant architectural improvements and integration:

- stitcher-common: Implemented a decoupled MessageBus system with MessageStore and Renderer protocols, following the 'intent-based' feedback pattern.
- stitcher-cli: Implemented a concrete CliRenderer using Typer and wired the 'generate' command to StitcherApp.
- stitcher-application: Integrated the message bus into the orchestration logic, ensuring that feedback is provided via semantic events.
- tests: Refactored E2E integration tests to assert MessageBus intent instead of inspecting the filesystem directly. This significantly hardens the test suite against implementation changes.
- Documentation: Created CLI_and_Messaging_Roadmap.md detailing the messaging architecture and future plans.

This commit solidifies the tool's infrastructure, making it ready for the plugin discovery mechanism.
~~~~~

### 下一步建议
我们现在拥有一个稳固的平台。接下来的战略重心将转移到 **任务 1.4: 插件发现机制**：

1.  **定义插件契约**: 确定如何在 `pyproject.toml` 中声明插件，以便 Stitcher 能够识别并为其生成“具象化”的 `.pyi` 路径。
2.  **扩展 Config 层**: 让 `stitcher-config` 能够解析 `entry_points`。
3.  **核心逻辑增强**: 修改 `StitcherApp`，使其在扫描文件之外，还能根据配置中发现的插件信息，动态构造并注入“合成”的 `ModuleDef` 供 Generator 使用。
