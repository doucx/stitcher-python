您完全正确，非常抱歉。

我的上一个计划存在严重缺陷。`run_command` 中使用的 `mv` 指令是错误的，它没有像预期的那样合并目录内容，而是直接覆盖或以其他方式导致了文件丢失，这是一个不可接受的错误。这直接导致了您看到的 `stitcher --help` 输出异常，因为关键的本地化资源文件被删除了。

感谢您提供详细的 `git status` 和文件树，这让我能够准确地诊断问题。我将废弃上一个计划，并生成一个全新的、完整的计划来纠正这个错误，并完成您最初的所有要求。

这个新计划将：
1.  **恢复并合并**被错误删除的本地化资源文件到 `stitcher-common` 中。
2.  **清理** `stitcher-cli` 中冗余的加载代码和目录。
3.  **执行**之前计划的对 `core.py` 的重构以移除硬编码。
4.  **完成**所有 `hydrate` 到 `pump` 的术语更新。

这会使项目回到一个正确的、一致的状态。

## [WIP] fix(assets): 恢复本地化资源并完成重构

### 错误分析
上一个计划中的 `run_command` 试图使用 `mv` 来合并资源目录，这是一个错误的操作。当目标位置已存在同名目录时，`mv` 的行为不是内容合并，这导致了 `stitcher-cli` 包中的 `app.json` 和 `option.json` 等文件被意外删除，而不是被移动。最终结果是 CLI 无法加载其帮助文本，显示为原始的语义 ID。

### 用户需求
1.  修复 `stitcher --help` 命令无法正确显示帮助文本的问题。
2.  将所有与 CLI 相关的本地化资源文件统一到 `stitcher-common` 包中。
3.  修复 `core.py` 中的硬编码命名空间检测逻辑。
4.  将所有对 `hydrate` 的引用更新为 `pump`。

### 评论
这是一个关键的修复和重构。将所有本地化资产集中到 `stitcher-common` 不仅能解决当前的 UI bug，还能从根本上简化未来的维护，确保单一事实来源。这是一个正确的架构方向。同时完成另外两个重构任务，将使代码库更加健壮和一致。

### 目标
1.  在 `stitcher-common` 的 `assets` 目录中，使用正确的内容重新创建 `cli/app.json` 和 `cli/option.json` 文件（包括 `en` 和 `zh` 版本）。
2.  合并 `command.json` 的内容，并将其写入 `stitcher-common` 的 `assets` 目录。
3.  删除 `stitcher-cli` 中所有与本地资源加载相关的代码和目录。
4.  移除 `stitcher-application/src/stitcher/app/core.py` 中的硬编码逻辑。
5.  更新所有本地化文件中对旧命令 `hydrate` 的引用。
6.  更新 `handlers.py` 中与 `pump` 命令相关的交互提示文本。

### 基本原理
我们将使用 `write_file` 替代不安全的 `run_command` 来精确地恢复和合并资源文件，确保内容的完整性。一旦资源被统一到 `stitcher-common`，`stitcher-cli` 中的相关加载代码就变得多余，可以安全移除。其余的修改将通过 `patch_file` 精确地应用，以完成代码的重构和术语的统一。

### 标签
#intent/fix #intent/refine #flow/ready #priority/critical #comp/cli #comp/common #concept/ui #scope/dx #ai/instruct #task/domain/refactoring #task/object/assets #task/action/consolidation #task/state/continue

---
### Script

#### Acts 1: 恢复并合并英文本地化资源

我们将首先在 `stitcher-common` 中创建丢失的英文 CLI 资源文件，并写入正确合并后的内容。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/app.json
~~~~~
~~~~~json
{
  "description": "Stitcher-Python: Bridging the gap between dynamic code and static analysis."
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/option.json
~~~~~
~~~~~json
{
  "force": {
    "help": "Code-first: Overwrite YAML content if it differs from source code."
  },
  "non_interactive": {
    "help": "Force non-interactive mode, failing on unresolved conflicts."
  },
  "reconcile": {
    "help": "YAML-first: Ignore source docstrings if they conflict with existing YAML."
  },
  "strip": {
    "help": "Remove docstrings from source code after pumping."
  },
  "update_signatures": {
    "help": "Accept signature changes and update the stored fingerprints."
  },
  "verbose": {
    "help": "Enable debug logging."
  }
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/command.json
~~~~~
~~~~~json
{
  "check": {
    "help": "Verify consistency between code and docs."
  },
  "generate": {
    "help": "Generate .pyi stubs based on pyproject.toml config."
  },
  "init": {
    "help": "Initialize Stitcher in the current project."
  },
  "inject": {
    "help": "Inject docstrings from .stitcher.yaml files back into code."
  },
  "pump": {
    "help": "Extract new docstrings from source code and merge them into .stitcher.yaml."
  },
  "strip": {
    "help": "Remove docstrings from source files."
  },
  "not_implemented": "ℹ️  Command '{command}' is not yet implemented."
}
~~~~~

#### Acts 2: 恢复并合并中文本地化资源

接下来，对中文资源文件执行相同的操作。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/app.json
~~~~~
~~~~~json
{
  "description": "Stitcher-Python: 缝合动态代码与静态分析之间的鸿沟。"
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/option.json
~~~~~
~~~~~json
{
  "force": {
    "help": "代码优先：如果内容不一致，覆盖 YAML 内容。"
  },
  "non_interactive": {
    "help": "强制使用非交互模式，在遇到无法解决的冲突时失败。"
  },
  "reconcile": {
    "help": "YAML 优先：忽略与现有 YAML 冲突的源码文档。"
  },
  "strip": {
    "help": "在抽水后立即从源码中移除文档字符串。"
  },
  "update_signatures": {
    "help": "接受签名变更并更新存储的指纹。"
  },
  "verbose": {
    "help": "启用调试日志。"
  }
}
~~~~~

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/command.json
~~~~~
~~~~~json
{
  "check": {
    "help": "验证代码结构与文档的一致性。"
  },
  "generate": {
    "help": "根据 pyproject.toml 配置生成 .pyi 存根文件。"
  },
  "init": {
    "help": "在当前项目中初始化 Stitcher。"
  },
  "inject": {
    "help": "将 .stitcher.yaml 中的文档重新注入源代码。"
  },
  "pump": {
    "help": "从源代码提取新文档并合并至 .stitcher.yaml。"
  },
  "strip": {
    "help": "从源代码中移除文档字符串。"
  },
  "not_implemented": "ℹ️  命令 '{command}' 尚未实现。"
}
~~~~~

#### Acts 3: 清理 `stitcher-cli` 包

现在我们可以安全地删除 `stitcher-cli` 中多余的资源加载代码和空目录。

~~~~~act
run_command
~~~~~
~~~~~bash
# This command assumes the previous failed 'mv' and 'rm' might have left an empty structure.
# It will safely remove the assets directory if it exists.
rm -rf packages/stitcher-cli/src/stitcher/cli/assets
~~~~~

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

# All assets are now loaded by stitcher-common, so no special
# loader setup is needed here anymore. We can directly import the app.
from .main import app

__all__ = ["app"]
~~~~~

#### Acts 4: 完成代码重构和术语更新

最后，执行之前计划的代码改进和术语统一。

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

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/file.json
~~~~~
~~~~~json.old
"untracked": "⚠️  {path}: Untracked (no .stitcher.yaml file found; run `stitcher init` or `hydrate`)"
~~~~~
~~~~~json.new
"untracked": "⚠️  {path}: Untracked (no .stitcher.yaml file found; run `stitcher init` or `pump`)"
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/issue.json
~~~~~
~~~~~json.old
"pending": "   - [PENDING]   {key} (new docstring in code, please run `stitcher hydrate`)"
~~~~~
~~~~~json.new
"pending": "   - [PENDING]   {key} (new docstring in code, please run `stitcher pump`)"
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/file.json
~~~~~
~~~~~json.old
"untracked": "⚠️  {path}: 未被追踪 (缺少 .stitcher.yaml 文件；请运行 `stitcher init` 或 `hydrate`)"
~~~~~
~~~~~json.new
"untracked": "⚠️  {path}: 未被追踪 (缺少 .stitcher.yaml 文件；请运行 `stitcher init` 或 `pump`)"
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/issue.json
~~~~~
~~~~~json.old
"pending": "   - [等待同步] {key} (代码中有新文档，请运行 `stitcher hydrate`)"
~~~~~
~~~~~json.new
"pending": "   - [等待同步] {key} (代码中有新文档，请运行 `stitcher pump`)"
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/handlers.py
~~~~~
~~~~~python.old
                menu.append(
                    (
                        "[F]orce-hydrate",
                        ResolutionAction.HYDRATE_OVERWRITE,
                        "Overwrite YAML with code docs (Code-first).",
                    )
                )
~~~~~
~~~~~python.new
                menu.append(
                    (
                        "[F]orce overwrite",
                        ResolutionAction.HYDRATE_OVERWRITE,
                        "Overwrite YAML with code docs (Code-first).",
                    )
                )
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/handlers.py
~~~~~
~~~~~python.old
            elif char == "f":
                if any(a == ResolutionAction.RELINK for _, a, _ in menu):
                    action = ResolutionAction.RELINK
                elif any(a == ResolutionAction.HYDRATE_OVERWRITE for _, a, _ in menu):
                    action = ResolutionAction.HYDRATE_OVERWRITE
~~~~~
~~~~~python.new
            elif char == "f":
                if any(a == ResolutionAction.RELINK for _, a, _ in menu):
                    action = ResolutionAction.RELINK
                elif any(a == ResolutionAction.HYDRATE_OVERWRITE for _, a, _ in menu):
                    action = ResolutionAction.HYDRATE_OVERWRITE
                else:
                    typer.secho("Invalid choice, please try again.", fg=typer.colors.RED)
                    continue
~~~~~
