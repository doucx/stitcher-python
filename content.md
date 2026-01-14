好的，收到指令。我们将立即执行修复计划，以恢复配置加载逻辑的正确性并让测试套件通过。

## [WIP] fix: Correct config loading logic for rootless workspaces

### 错误分析

在将 `_find_pyproject_toml` 统一为 `find_workspace_root` 的重构中，`load_config_from_path` 函数的逻辑被错误地简化了。新的实现将插件发现和配置加载强行绑定在同一个 `try` 块中。这导致在测试环境（通常是一个没有 `.git` 的临时目录）中，`find_workspace_root` 抛出 `WorkspaceNotFoundError`，使得整个配置加载过程（包括插件发现）被跳过，最终返回一个空的默认配置。这与旧行为不一致，并引发了大规模的集成测试失败。

### 用户需求

修复 `load_config_from_path` 函数，使其能够正确处理找不到工作区根目录（例如，在测试环境中）的场景，确保插件发现逻辑总能被执行，并且在 `pyproject.toml` 不存在时能够优雅地回退。

### 评论

这是一个典型的回归错误，源于对重构影响范围的分析不够全面。修复此问题的核心是恢复逻辑的鲁棒性，确保函数的行为在所有边界条件下都与之前保持一致。此修复将严格遵循原始函数的意图，同时保留我们已经完成的架构改进（即统一使用 `find_workspace_root`）。

### 目标

1.  重构 `load_config_from_path` 函数。
2.  将插件发现 (`_find_plugins`) 的调用移出主 `try...except` 块，确保它总是被执行。
3.  确保在 `find_workspace_root` 失败时，函数能够返回一个包含已发现插件的默认 `StitcherConfig` 对象。

### 基本原理

我们将通过一次精确的 `patch_file` 操作来重写 `load_config_from_path` 函数。新的实现将遵循以下逻辑：
1.  首先，无条件地调用 `_find_plugins(search_path)`。这将恢复旧的行为，确保插件总能被发现。
2.  其次，在一个 `try...except` 块中，尝试调用 `find_workspace_root` 并加载 `pyproject.toml` 中的具体配置。
3.  如果 `try` 块成功，则将加载的配置与已发现的插件合并。
4.  如果 `try` 块失败，则返回一个仅包含已发现插件的默认配置。
这个结构完美地复制了原始的功能意图，同时保持了代码的清晰和健壮。

### 标签

#intent/fix #flow/ready #priority/critical #comp/workspace #scope/core #scope/dx #ai/instruct #task/domain/architecture #task/object/package-merge #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 修复 `load_config_from_path` 逻辑

我们将用一个功能上正确的新版本替换 `config.py` 中的 `load_config_from_path` 函数。

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/config.py
~~~~~
~~~~~python.old
def load_config_from_path(
    search_path: Path,
) -> Tuple[List[StitcherConfig], Optional[str]]:
    project_name: Optional[str] = None
    stitcher_data: Dict[str, Any] = {}

    try:
        workspace_root = find_workspace_root(search_path)
        plugins = _find_plugins(workspace_root)
        config_path = workspace_root / "pyproject.toml"

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        project_name = data.get("project", {}).get("name")
        stitcher_data = data.get("tool", {}).get("stitcher", {})

    except (FileNotFoundError, WorkspaceNotFoundError):
        # In case of no root, we can't reliably find plugins.
        # This behavior is now more correct. We return an empty plugin dict.
        return [StitcherConfig(plugins={})], None

    configs: List[StitcherConfig] = []
    targets = stitcher_data.get("targets", {})

    if targets:
        # Multi-target mode
        for target_name, target_data in targets.items():
            configs.append(
                StitcherConfig(
                    name=target_name,
                    scan_paths=target_data.get("scan_paths", []),
                    plugins=plugins,
                    stub_path=target_data.get("stub_path"),
                    stub_package=target_data.get("stub_package"),
                    docstring_style=target_data.get("docstring_style", "raw"),
                    peripheral_paths=target_data.get("peripheral_paths", []),
                )
            )
    else:
        # Single-target (Legacy/Simple) mode
        configs.append(
            StitcherConfig(
                scan_paths=stitcher_data.get("scan_paths", []),
                plugins=plugins,
                stub_path=stitcher_data.get("stub_path"),
                stub_package=stitcher_data.get("stub_package"),
                docstring_style=stitcher_data.get("docstring_style", "raw"),
                peripheral_paths=stitcher_data.get("peripheral_paths", []),
            )
        )

    return configs, project_name
~~~~~
~~~~~python.new
def load_config_from_path(
    search_path: Path,
) -> Tuple[List[StitcherConfig], Optional[str]]:
    # Plugin discovery should run from the search_path, regardless of whether a
    # formal workspace root is found. This matches original behavior and supports
    # testing scenarios.
    plugins = _find_plugins(search_path)
    project_name: Optional[str] = None
    stitcher_data: Dict[str, Any] = {}

    try:
        workspace_root = find_workspace_root(search_path)
        config_path = workspace_root / "pyproject.toml"

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        project_name = data.get("project", {}).get("name")
        stitcher_data = data.get("tool", {}).get("stitcher", {})

    except (FileNotFoundError, WorkspaceNotFoundError):
        # If no root config file, return default config with discovered plugins.
        return [StitcherConfig(plugins=plugins)], None

    configs: List[StitcherConfig] = []
    targets = stitcher_data.get("targets", {})

    if targets:
        # Multi-target mode
        for target_name, target_data in targets.items():
            configs.append(
                StitcherConfig(
                    name=target_name,
                    scan_paths=target_data.get("scan_paths", []),
                    plugins=plugins,
                    stub_path=target_data.get("stub_path"),
                    stub_package=target_data.get("stub_package"),
                    docstring_style=target_data.get("docstring_style", "raw"),
                    peripheral_paths=target_data.get("peripheral_paths", []),
                )
            )
    else:
        # Single-target (Legacy/Simple) mode
        configs.append(
            StitcherConfig(
                scan_paths=stitcher_data.get("scan_paths", []),
                plugins=plugins,
                stub_path=stitcher_data.get("stub_path"),
                stub_package=stitcher_data.get("stub_package"),
                docstring_style=stitcher_data.get("docstring_style", "raw"),
                peripheral_paths=stitcher_data.get("peripheral_paths", []),
            )
        )

    return configs, project_name
~~~~~

### 下一步建议

我们已经应用了针对回归错误的修复。现在必须通过运行完整的测试套件来验证此修复的有效性。

请运行 `pytest`。如果所有测试都通过，我们将可以自信地将 `config` 与 `workspace` 的合并视为一个已完成且稳定的工作单元，并可以创建一个 `[COMMIT]` 计划来正式结束这个宏观任务。
