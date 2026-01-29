好的，我们已经成功完成了 Stitcher 的“心脏移植”手术。现在我们将这一系列激进但必要的重构操作打包为一个完整的提交。

## [COMMIT] refactor(bus): 迁移 stitcher-bus 到 pyneedle-bus

### 用户需求
将 Stitcher 现有的总线实现彻底迁移到通用的 `pyneedle-bus` 底座上，并完成清理工作。

### 评论
这次重构消除了一个冗余的内部包（`stitcher-bus`），并将 Stitcher 正式接入了 PyNeedle 生态系统。通过将 I18n 资产移动到 `stitcher-common` 并配置多源加载，我们为未来的插件化和跨项目协作打下了坚实的基础。

### 目标
1.  提交所有文件变更。
2.  记录本次重构的核心动作。

### 基本原理
我们通过 `git add .` 捕获了包括：
- 资产搬迁（Moves）
- 包删除（Deletions）
- 依赖和源码映射更新（pyproject.toml）
- 全局路径替换（Python imports）
- 协议适配（Renderer 签名）
在内的所有变更。

### 标签
#intent/refine #flow/ready #priority/high 
#comp/common #comp/cli #comp/bus #scope/core 
#ai/instruct
#task/domain/bus #task/object/refactoring #task/action/cleanup #task/state/end

---

### Script

#### Acts 1: 提交变更

我们将所有改动添加到暂存区，并创建一个描述详尽的提交。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(bus): migrate stitcher-bus functionality to pyneedle-bus

This commit completes the "Heart Transplant" phase of the radical bus refactoring:

1.  Eliminated the redundant 'stitcher-bus' package.
2.  Relocated I18n JSON assets to 'stitcher-common/src/stitcher/common/assets'.
3.  Established a new, flattened entrypoint in 'stitcher.common.bus' that integrates with 'pyneedle-bus'.
4.  Updated all internal references (application logic, CLI commands, and test utilities) to use the new common bus singleton.
5.  Adapted 'CliRenderer' and 'SpyRenderer' to conform to the pyneedle 'RendererProtocol' by supporting keyword argument passthrough.
6.  Configured 'uv' sources in the workspace root to point to local 'Needle' repository packages for concurrent development.

The system now relies on the universal PyNeedle ecosystem for feedback and I18n, making it ready for the introduction of Event-Driven analysis in the next phase.
~~~~~

### 下一步建议
**阶段一：功能平移** 已正式结项。

现在的架构已经是：`Stitcher (业务) -> pyneedle-bus (基础设施) -> assets (本地资源)`。

**下一步：阶段二 - 引入 EventBus (流式分析)**
我建议接下来的任务焦点转到 `stitcher-analysis` 包。我们将：
1.  在 `AnalysisEngine` 中埋入 `EventBus.publish` 逻辑。
2.  在 `CheckRunner` 中配置 `LogBridge`。
3.  实现即使在大规模项目检查时，用户也能在控制台实时看到发现的每一个违规项，而不是等待所有文件扫描结束。

如果你准备好了，我们可以开始设计 `ViolationDetected` 事件的结构。
