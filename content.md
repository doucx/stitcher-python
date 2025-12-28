好的，我将执行您要求的两项任务：修复硬编码问题，并更新与 `stitcher pump` 命令相关的本地化文件。

这是一个增量改进计划，旨在提高代码的健壮性和用户体验的一致性。

## [WIP] refactor(app): 移除硬编码逻辑并更新 pump 命令本地化

### 用户需求
1.  修复在 `stitcher-application` 的 `core.py` 中存在的硬编码命名空间检测逻辑。
2.  将所有面向用户的文本（尤其是在本地化文件中）提及的旧命令 `stitcher hydrate` 更新为新命令 `stitcher pump`。

### 评论
这个计划解决了两个重要问题。首先，移除硬编码的命名空间逻辑使 `stitcher` 的行为更通用、更可预测，降低了未来维护的难度。其次，统一 `pump` 命令的术语，确保了命令行界面、日志输出和交互式提示之间的一致性，避免了用户混淆。

### 目标
1.  重构 `_scaffold_stub_package` 方法，移除其中针对 `pyneedle` 和 `stitcher` 的硬编码 `elif` 分支。
2.  修改英文和中文的 `check/issue.json` 本地化文件，将 `stitcher hydrate` 替换为 `stitcher pump`。
3.  更新 `TyperInteractionHandler` 中的交互式提示文本，将 "Force-hydrate" 更改为更清晰的 "Force overwrite"。

### 基本原理
在 `core.py` 中，命名空间推断逻辑中存在一个冗余且包含硬编码规则的 `elif` 块。前面的 `if` 块已经能正确处理类似 `src/namespace` 的路径，而对于其他情况，现有的基于目标名称的 `fallback` 逻辑是更通用且正确的选择。因此，我将安全地移除这个 `elif` 块，从而消除硬编码。

对于本地化更新，这是一个直接的查找和替换操作，以确保术语在整个应用中的一致性。

### 标签
#intent/refine #intent/tune #flow/ready #priority/high #comp/cli #comp/application #scope/dx #scope/ux #ai/instruct #task/domain/refactoring #task/object/hardcoding #task/action/fix #task/state/begin

---
### Script

#### Acts 1: 移除 `core.py` 中的硬编码逻辑

我将修改 `_scaffold_stub_package` 方法，移除其中冗余且硬编码的 `elif` 块。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        package_namespace: str = ""
        for path_str in config.scan_paths:
            path_parts = Path(path_str).parts
            if path_parts and path_parts[-1] != "src":
                package_namespace = path_parts[-1]
                break
            elif len(path_parts) >= 2 and path_parts[-2] == "src":
                if "pyneedle" in stub_base_name:
                    package_namespace = "needle"
                elif "stitcher" in stub_base_name:
                    package_namespace = "stitcher"
                break
        if not package_namespace:
            package_namespace = stub_base_name.split("-")[0]
~~~~~
~~~~~python.new
        package_namespace: str = ""
        for path_str in config.scan_paths:
            path_parts = Path(path_str).parts
            if path_parts and path_parts[-1] != "src":
                # This handles cases like 'src/my_app' where 'my_app' is the namespace.
                package_namespace = path_parts[-1]
                break

        if not package_namespace:
            # Fallback for when all scan_paths end in 'src'.
            # Derives namespace from the target name (e.g., 'stitcher-cli' -> 'stitcher').
            package_namespace = stub_base_name.split("-")[0]
~~~~~

#### Acts 2: 更新本地化文件和交互提示

我将更新英文和中文的本地化文件，并将交互式处理器中的旧术语 "hydrate" 替换掉。
