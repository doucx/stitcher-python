好的，我明白了。我将检查整个代码库，找出所有硬编码的、面向用户的字符串（特别是在 `bus` 调用和 Typer 命令的 `help` 文本中），并将它们迁移到 `needle` 的 `L` 指针系统中。

这是一个重要的重构，它将提高代码的可维护性、一致性，并为未来的国际化做好准备。

## [WIP] refactor: 将硬编码的 CLI 消息和帮助文本迁移到 L 指针

### 用户需求

用户要求检查代码库，将所有面向用户的硬编码字符串（尤其是在 `bus` 的消息和 Typer 命令的 `help` 文本中）替换为 `needle` 的 `L` 语义指针。

### 评论

这是一个关键的代码质量改进。当前在多个 CLI 命令中存在硬编码的错误消息和帮助文本，这违反了“UI 与逻辑分离”的核心原则。将这些字符串集中到 `needle` 资源文件中，可以带来以下好处：
1.  **中心化管理**：所有文案都在 `assets` 目录中，易于查找和修改。
2.  **国际化**：为未来支持多语言（如中文）奠定了基础。
3.  **一致性**：重复的字符串（如 `--non-interactive` 的帮助文本）可以复用同一个 `L` 指针，确保文案统一。
4.  **健壮的测试**：测试可以断言正确的“意图”（如 `L.error.cli.conflicting_options`），而不是脆弱的、可能会改变的英文字符串。

### 目标

1.  在 `needle` 的 JSON 资源文件中为所有新发现的硬编码字符串创建对应的 `L` 指针。
2.  修改 `packages/stitcher-cli` 中的 `check.py`, `pump.py`, 和 `refactor.py` 文件。
3.  将 `typer.Option` 和 `typer.Argument` 中的 `help="..."` 硬编码字符串替换为 `help=nexus(L.cli.option.*)` 的形式。
4.  将 `bus.error(...)` 中的硬编码错误消息替换为 `bus.error(L.error.cli.*)` 的形式。

### 基本原理

我将首先扩展 `needle` 的资源文件，为所有需要迁移的字符串定义新的、语义化的键。我将把 CLI 相关的错误信息放在一个新的 `error/cli.json` 文件中，以保持组织清晰。然后，我将使用 `patch_file` 操作，精确地替换 Python 源代码中所有硬编码的字符串为对新创建的 `L` 指针的调用。这将确保所有面向用户的文本都通过 `needle` 系统进行管理，从而完成本次重构。

### 标签

#intent/refine #flow/ready #priority/medium #comp/cli #concept/ui #scope/dx #ai/instruct #task/domain/cli #task/object/localization #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 扩展 Needle 资源文件

我将首先创建新的 `L` 指针并更新现有的资源文件，以包含所有之前硬编码的文本。

首先，为 CLI 相关的错误创建一个新的资源文件。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/error/cli.json
~~~~~
~~~~~json
{
  "conflicting_options": "❌ Cannot use --{opt1} and --{opt2} simultaneously."
}
~~~~~

然后创建对应的中文版本。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/error/cli.json
~~~~~
~~~~~json
{
  "conflicting_options": "❌ 不能同时使用 --{opt1} 和 --{opt2}。"
}
~~~~~

接下来，将所有新的 `help` 文本添加到 `option.json` 文件中。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/option.json
~~~~~
~~~~~json.old
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
  "verbose": {
    "help": "Enable debug logging."
  }
}
~~~~~
~~~~~json.new
{
  "force": {
    "help": "Code-first: Overwrite YAML content if it differs from source code."
  },
  "force_relink": {
    "help": "[Non-interactive] For 'Signature Drift' errors, forces relinking."
  },
  "non_interactive": {
    "help": "Force non-interactive mode, failing on unresolved conflicts."
  },
  "reconcile": {
    "help": "YAML-first: Ignore source docstrings if they conflict with existing YAML."
  },
  "reconcile_co_evolution": {
    "help": "[Non-interactive] For 'Co-evolution' errors, accepts both changes."
  },
  "refactor_dry_run": {
    "help": "Show planned changes without applying them."
  },
  "refactor_script_path": {
    "help": "Path to the Python migration script."
  },
  "refactor_yes": {
    "help": "Automatically confirm and apply changes."
  },
  "strip": {
    "help": "Remove docstrings from source code after pumping."
  },
  "verbose": {
    "help": "Enable debug logging."
  }
}
~~~~~

最后，更新中文版的 `option.json`。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/option.json
~~~~~
~~~~~json.old
{
  "force": {
    "help": "代码优先：如果内容不一致，使用代码中的文档覆盖 YAML 内容。"
  },
  "non_interactive": {
    "help": "强制使用非交互模式，在遇到无法解决的冲突时将直接失败。"
  },
  "reconcile": {
    "help": "YAML 优先：当与现有 YAML 冲突时，保留 YAML 的文档内容。"
  },
  "strip": {
    "help": "在抽取文档后立即从源代码中移除它们。"
  },
  "verbose": {
    "help": "启用调试级别的日志输出。"
  }
}
~~~~~
~~~~~json.new
{
  "force": {
    "help": "代码优先：如果内容不一致，使用代码中的文档覆盖 YAML 内容。"
  },
  "force_relink": {
    "help": "[非交互] 针对“签名漂移”错误，强制重新链接。"
  },
  "non_interactive": {
    "help": "强制使用非交互模式，在遇到无法解决的冲突时将直接失败。"
  },
  "reconcile": {
    "help": "YAML 优先：当与现有 YAML 冲突时，保留 YAML 的文档内容。"
  },
  "reconcile_co_evolution": {
    "help": "[非交互] 针对“协同演进”错误，接受双方的变更。"
  },
  "refactor_dry_run": {
    "help": "仅显示计划中的变更，不实际应用。"
  },
  "refactor_script_path": {
    "help": "指向 Python 迁移脚本的路径。"
  },
  "refactor_yes": {
    "help": "自动确认并应用变更。"
  },
  "strip": {
    "help": "在抽取文档后立即从源代码中移除它们。"
  },
  "verbose": {
    "help": "启用调试级别的日志输出。"
  }
}
~~~~~

#### Acts 2: 更新 CLI 命令实现

现在，我将修改 Python 代码以使用新创建的 `L` 指针。

首先是 `check` 命令。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/check.py
~~~~~
~~~~~python.old
import typer
from stitcher.common import bus
from stitcher.cli.factories import make_app, make_interaction_handler


def check_command(
    force_relink: bool = typer.Option(
        False,
        "--force-relink",
        help="[Non-interactive] For 'Signature Drift' errors, forces relinking.",
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help="[Non-interactive] For 'Co-evolution' errors, accepts both changes.",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Force non-interactive mode, failing on unresolved conflicts.",
    ),
):
    if force_relink and reconcile:
        bus.error("Cannot use --force-relink and --reconcile simultaneously.")
        raise typer.Exit(code=1)

    # Use factory to decide if we need an interaction handler
~~~~~
~~~~~python.new
import typer
from stitcher.common import bus, stitcher_operator as nexus
from needle.pointer import L
from stitcher.cli.factories import make_app, make_interaction_handler


def check_command(
    force_relink: bool = typer.Option(
        False,
        "--force-relink",
        help=nexus(L.cli.option.force_relink.help),
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help=nexus(L.cli.option.reconcile_co_evolution.help),
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help=nexus(L.cli.option.non_interactive.help),
    ),
):
    if force_relink and reconcile:
        bus.error(
            L.error.cli.conflicting_options, opt1="force-relink", opt2="reconcile"
        )
        raise typer.Exit(code=1)

    # Use factory to decide if we need an interaction handler
~~~~~

接着是 `pump` 命令。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/pump.py
~~~~~
~~~~~python.old
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Force non-interactive mode, failing on unresolved conflicts.",
    ),
):
    if force and reconcile:
        bus.error("Cannot use --force and --reconcile simultaneously.")
        raise typer.Exit(code=1)

    # Use factory logic
~~~~~
~~~~~python.new
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help=nexus(L.cli.option.non_interactive.help),
    ),
):
    if force and reconcile:
        bus.error(L.error.cli.conflicting_options, opt1="force", opt2="reconcile")
        raise typer.Exit(code=1)

    # Use factory logic
~~~~~

最后是 `refactor` 命令。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~
~~~~~python.old
def refactor_command(
    migration_script: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the Python migration script.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show planned changes without applying them.",
    ),
    yes: bool = typer.Option(
        False,
        "-y",
        "--yes",
        help="Automatically confirm and apply changes.",
    ),
):
    root_path = Path.cwd()
~~~~~
~~~~~python.new
def refactor_command(
    migration_script: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help=nexus(L.cli.option.refactor_script_path.help),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help=nexus(L.cli.option.refactor_dry_run.help),
    ),
    yes: bool = typer.Option(
        False,
        "-y",
        "--yes",
        help=nexus(L.cli.option.refactor_yes.help),
    ),
):
    root_path = Path.cwd()
~~~~~

### 下一步建议

变更完成后，建议运行完整的测试套件 (`pytest`) 以确保没有引入任何回归问题。此外，可以手动运行 `stitcher {check,pump,refactor} --help` 命令，验证新的帮助文本是否正确显示。
