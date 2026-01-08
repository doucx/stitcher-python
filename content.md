好的，我将为相关的 `stitcher-cli` 子命令添加 `--dry-run` 开关，并将该值传递给 `StitcherApp` 以便在执行前预览文件系统变更。

此计划将分两步执行：
1.  **修改 `pump` 命令**：为其添加 `--dry-run` 选项。
2.  **修改 `basics` 命令**：为 `generate`、`strip` 和 `inject` 命令添加 `--dry-run` 选项。

## [WIP] feat(cli): 为多个子命令添加 --dry-run 选项

### 用户需求

需要在 `stitcher-cli` 中为 `generate`, `pump`, `strip`, `inject` 等会修改文件系统的命令添加一个 `--dry-run` 标志。当此标志被激活时，程序应显示计划执行的文件操作，而不是实际执行它们。

### 评论

这是一个非常重要的功能，它提升了 CLI 工具的安全性和用户体验。用户可以在执行可能具有破坏性的操作（如 `strip`）之前，清楚地了解将要发生的变更，从而避免意外修改。这也使得 Stitcher 在自动化脚本中的使用更加安全可控。

### 目标

1.  为 `pump` 命令的 Typer 定义添加 `--dry-run` 选项。
2.  将 `dry_run` 参数传递给 `app_instance.run_pump()` 和 `app_instance.run_strip()`。
3.  为 `generate`, `strip`, `inject` 命令的 Typer 定义添加 `--dry-run` 选项。
4.  将 `dry_run` 参数传递给它们各自调用的 `StitcherApp` 方法。
5.  在 `strip` 和 `inject` 命令中，如果 `dry_run` 为 `True`，则跳过危险操作的确认提示。

### 基本原理

`StitcherApp` 中的相关方法（如 `run_pump`, `run_from_config` 等）已经通过 `TransactionManager` 支持了 `dry_run` 模式。我们只需在 CLI 层（`stitcher-cli`）暴露这个功能即可。

我们将通过 `typer.Option` 为每个相关命令添加 `--dry-run` 标志，并将其值向下传递。为了保持一致性，我们将复用 `refactor` 命令中已有的 `L.cli.option.refactor_dry_run.help` 文本。对于会修改源文件的 `strip` 和 `inject` 命令，我们将增加逻辑，在 `dry_run` 模式下跳过交互式确认，以改善用户体验。

### 标签

#intent/build #flow/ready #priority/high #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/dry-run-feature #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 为 `pump` 命令添加 `--dry-run` 选项

我们将修改 `pump_command` 函数，添加 `--dry-run` 选项，并将其传递给底层的 `run_pump` 和 `run_strip` 调用。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/pump.py
~~~~~
~~~~~python.old
def pump_command(
    strip: bool = typer.Option(False, "--strip", help=nexus(L.cli.option.strip.help)),
    force: bool = typer.Option(
        False,
        "--force",
        help=nexus(L.cli.option.force.help),
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help=nexus(L.cli.option.reconcile.help),
    ),
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
    handler = make_interaction_handler(
        non_interactive=non_interactive,
        auto_resolve_mode=(force or reconcile),
    )

    app_instance = make_app(handler)

    # 1. Run Pump
    result = app_instance.run_pump(strip=strip, force=force, reconcile=reconcile)
    if not result.success:
        raise typer.Exit(code=1)

    # 2. Interactive Strip Confirmation
    # Check if we have a handler (implies interactive mode) and redundant files exist
    if handler and result.redundant_files and not strip:
        typer.echo("")
        typer.secho(
            f"Found {len(result.redundant_files)} file(s) with redundant docstrings in source code.",
            fg=typer.colors.YELLOW,
        )
        if typer.confirm("Do you want to strip them now?", default=True):
            app_instance.run_strip(files=result.redundant_files)
~~~~~
~~~~~python.new
def pump_command(
    strip: bool = typer.Option(False, "--strip", help=nexus(L.cli.option.strip.help)),
    force: bool = typer.Option(
        False,
        "--force",
        help=nexus(L.cli.option.force.help),
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help=nexus(L.cli.option.reconcile.help),
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help=nexus(L.cli.option.non_interactive.help),
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help=nexus(L.cli.option.refactor_dry_run.help)
    ),
):
    if force and reconcile:
        bus.error(L.error.cli.conflicting_options, opt1="force", opt2="reconcile")
        raise typer.Exit(code=1)

    # Use factory logic
    handler = make_interaction_handler(
        non_interactive=non_interactive,
        auto_resolve_mode=(force or reconcile),
    )

    app_instance = make_app(handler)

    # 1. Run Pump
    result = app_instance.run_pump(
        strip=strip, force=force, reconcile=reconcile, dry_run=dry_run
    )
    if not result.success:
        raise typer.Exit(code=1)

    # 2. Interactive Strip Confirmation
    # Check if we have a handler (implies interactive mode) and redundant files exist
    if handler and result.redundant_files and not strip:
        typer.echo("")
        typer.secho(
            f"Found {len(result.redundant_files)} file(s) with redundant docstrings in source code.",
            fg=typer.colors.YELLOW,
        )
        if typer.confirm("Do you want to strip them now?", default=True):
            app_instance.run_strip(files=result.redundant_files, dry_run=dry_run)
~~~~~

#### Acts 2: 为 `generate`, `strip`, 和 `inject` 命令添加 `--dry-run` 选项

由于这些命令位于同一个文件中，并且修改幅度较大，我将使用 `write_file` 一次性更新 `basics.py` 文件。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/commands/basics.py
~~~~~
~~~~~python
import typer
from needle.pointer import L
from stitcher.common import bus, stitcher_operator as nexus
from stitcher.cli.factories import make_app


def generate_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", help=nexus(L.cli.option.refactor_dry_run.help)
    ),
):
    app_instance = make_app()
    app_instance.run_from_config(dry_run=dry_run)


def init_command():
    app_instance = make_app()
    app_instance.run_init()


def strip_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", help=nexus(L.cli.option.refactor_dry_run.help)
    ),
):
    if not dry_run and not typer.confirm(bus.render_to_string(L.strip.run.confirm)):
        bus.warning(L.strip.run.aborted)
        raise typer.Abort()

    app_instance = make_app()
    app_instance.run_strip(dry_run=dry_run)


def inject_command(
    dry_run: bool = typer.Option(
        False, "--dry-run", help=nexus(L.cli.option.refactor_dry_run.help)
    ),
):
    if not dry_run and not typer.confirm(bus.render_to_string(L.inject.run.confirm)):
        bus.warning(L.inject.run.aborted)
        raise typer.Abort()

    app_instance = make_app()
    app_instance.run_inject(dry_run=dry_run)
~~~~~

### 下一步建议

我们已经完成了 CLI 层的功能添加。现在，我建议创建一个 `[COMMIT]` 计划来将这些变更提交到版本控制中。如果你同意，我将生成包含 `git add` 和 `git commit` 指令的计划。
