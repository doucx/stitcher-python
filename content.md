好的，你的分析非常到位。当一个自动化工具未能按预期工作时，第一步就是增加诊断输出来理解其内部决策过程。`stitcher refactor` 命令没有产生任何操作，这强烈暗示在早期的“分析”阶段，它未能找到要重命名的符号或其任何用法。

我将生成一个计划，为 `refactor` 命令添加详细的调试日志，以便我们能精确地看到问题所在。

## [WIP] fix: 为重构命令添加调试日志以进行诊断

### 错误分析
`stitcher refactor apply` 命令报告“未规划任何操作”，这表明 `RenameSymbolOperation` 的 `analyze` 方法返回了一个空列表。根本原因可能有以下几种：
1.  **工作区发现失败**：`Workspace` 类可能没有正确地发现 `stitcher-common` 包，导致其源路径未被添加到搜索路径中。
2.  **语义图谱加载失败**：`SemanticGraph` (Griffe) 在加载 `stitcher` 模块时可能遇到了问题，导致 `MessageBus` 符号未能被正确索引。
3.  **符号用法查找失败**：`UsageRegistry` 未能找到 `stitcher.common.messaging.bus.MessageBus` 的任何定义或引用，这是最直接的原因。

通过添加调试日志，我们可以逐一排查这些可能性。

### 用户需求
用户需要向 `refactor` 命令注入调试日志，以诊断为什么重构操作没有按预期生成文件变更计划。

### 评论
这是一个非常标准的调试流程。为复杂操作提供详细的、可选的（通过 `--verbose` 标志）日志记录是提升工具可维护性和开发者体验（DX）的关键。这次的修改将使我们能够深入了解重构引擎的内部工作状态。

### 目标
1.  修改 `packages/stitcher-cli/src/stitcher/cli/commands/refactor.py` 文件。
2.  在 `refactor_command` 函数内部，添加一系列 `bus.debug` 调用，以记录关键的中间状态：
    *   打印已发现的工作区搜索路径。
    *   打印将要加载到图谱中的所有包名。
    *   在规划之前，显式查询并打印目标 FQN (`stitcher.common.messaging.bus.MessageBus`) 的用法数量。
    *   打印最终生成的计划操作数量。

### 基本原理
我们将使用 `patch_file` 来精确地将 `bus.debug` 调用插入到 `refactor_command` 的逻辑流程中。这些日志消息将使用 `L.debug.log` 语义指针，并只有在用户提供了 `--verbose` (或 `-v`) 标志时才会显示。这使得我们能够在不影响正常用户输出的情况下，获得必要的诊断信息。

### 标签
#intent/fix #flow/ready #priority/high #comp/cli #concept/executor #scope/dx #ai/instruct #task/domain/core-abstractions #task/object/message-bus #task/action/rename #task/state/continue

---

### Script

#### Acts 1: 注入诊断日志
我们将修改 `refactor.py` 文件，在关键位置添加调试日志输出。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~
~~~~~python.old
    try:
        # 1. Bootstrap services
        bus.info(L.refactor.run.loading_graph)
        workspace = Workspace(root_path)
        sidecar_manager = SidecarManager(root_path)
        graph = SemanticGraph(workspace)

        # Load all packages discovered by the workspace
        for pkg_name in workspace.import_to_source_dirs.keys():
            graph.load(pkg_name)

        ctx = RefactorContext(
            workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
        )

        # 2. Load and plan the migration
        bus.info(L.refactor.run.planning)
        loader = MigrationLoader()
        spec = loader.load_from_path(migration_script)

        planner = Planner()
        file_ops = planner.plan(spec, ctx)

        if not file_ops:
            bus.success(L.refactor.run.no_ops)
            return
~~~~~
~~~~~python.new
    try:
        # 1. Bootstrap services
        bus.info(L.refactor.run.loading_graph)
        workspace = Workspace(root_path)
        bus.debug(
            L.debug.log, msg=f"Workspace search paths: {workspace.get_search_paths()}"
        )
        sidecar_manager = SidecarManager(root_path)
        graph = SemanticGraph(workspace)

        # Load all packages discovered by the workspace
        pkg_names = list(workspace.import_to_source_dirs.keys())
        bus.debug(L.debug.log, msg=f"Discovered packages to load: {pkg_names}")
        for pkg_name in pkg_names:
            bus.debug(L.debug.log, msg=f"Loading package '{pkg_name}' into graph...")
            graph.load(pkg_name)

        ctx = RefactorContext(
            workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
        )

        # 2. Load and plan the migration
        bus.info(L.refactor.run.planning)
        loader = MigrationLoader()
        spec = loader.load_from_path(migration_script)

        # --- DEBUG ---
        for op in spec.operations:
            if op.__class__.__name__ == "RenameSymbolOperation":
                target_fqn = op.old_fqn
                usages = graph.registry.get_usages(target_fqn)
                bus.debug(
                    L.debug.log,
                    msg=f"Found {len(usages)} usages for '{target_fqn}'",
                )
        # --- END DEBUG ---

        planner = Planner()
        file_ops = planner.plan(spec, ctx)
        bus.debug(L.debug.log, msg=f"Planner generated {len(file_ops)} file operations.")

        if not file_ops:
            bus.success(L.refactor.run.no_ops)
            return
~~~~~

### 下一步建议
现在，请重新运行之前的 `stitcher refactor apply` 命令，但这次**务必**加上 `--verbose` 或 `-v` 标志。例如：

```bash
stitcher --verbose refactor apply 001_rename_message_bus.py --yes
```

请将新的输出结果提供给我，这些详细的日志将帮助我们定位问题的根源。
