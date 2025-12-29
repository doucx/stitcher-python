## [WIP] fix(cli): 适配 Operator 架构，修复 stitcher_nexus 引用

### 摘要头
## [WIP] fix(cli): 适配 Operator 架构，简化 CLI 中的资源访问

### 用户需求
1.  **修复 API 断裂**: 之前的重构移除了 `stitcher_nexus` 属性，导致 CLI 启动失败。
2.  **适配 Operator 调用**: 将 `nexus.get(L...)` 迁移为函数调用形式 `nexus(L...)`，符合 `OperatorProtocol`。
3.  **暴露 `stitcher_operator`**: `stitcher.common` 需要公开一个可调用的接口（`stitcher_operator`），供下游直接获取原始字符串（如 Help Text、TUI 提示等）。

### 评论
CLI 中的多个模块 (`main.py`, `pump.py`, `factories.py`) 仍然依赖已废弃的 `stitcher_nexus` 及其 `.get()` 方法。虽然 `MessageBus` 已经成功封装了这些调用，但 CLI 在构建 Help Text 和 Interactive Menu 时，仍需直接访问资源。我们不能简单地将 `stitcher_nexus` 加回来（那是倒退），而是应该让 CLI 依赖新的 `stitcher_operator`，并根据 Operator 协议 (`__call__`) 更新所有调用点。

### 目标
1.  修改 `stitcher-cli/src/stitcher/cli/main.py`: 导入 `stitcher_operator` 并替换所有 `nexus.get(...)` 为 `operator(...)`。
2.  修改 `stitcher-cli/src/stitcher/cli/commands/pump.py`: 同上。
3.  修改 `stitcher-cli/src/stitcher/cli/factories.py`: 传递 `stitcher_operator` 给交互式渲染器。
4.  修改 `stitcher-cli/src/stitcher/cli/interactive.py`: 适配 Operator 调用方式。
5.  修改 `stitcher-common/src/stitcher/common/__init__.py`: 移除残留的 YAML 文档引用（`stitcher_nexus`）。

### 基本原理
我们正在完成从“对象+方法”模式 (`obj.get(key)`) 到“函数式算子”模式 (`func(key)`) 的迁移。
新的 `stitcher_operator` 已经是一个符合 `OperatorProtocol` 的可调用对象（通过 `get_current_renderer` 动态获取管道），它是获取本地化字符串的唯一正确入口。

### 标签
#intent/fix #flow/ready #priority/high #comp/cli #concept/config #scope/core #ai/instruct #task/domain/refactor #task/object/operator #task/action/integrate #task/state/end

---

### Script

#### Acts 1: CLI Main 适配

修正入口文件，使用 `stitcher_operator` 替换 `stitcher_nexus`。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python
import typer

from stitcher.common import bus, stitcher_nexus as nexus
from needle.pointer import L
from .rendering import CliRenderer
~~~~~
~~~~~python
import typer

from stitcher.common import bus, stitcher_operator as nexus
from needle.pointer import L
from .rendering import CliRenderer
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python
app = typer.Typer(
    name="stitcher",
    help=nexus.get(L.cli.app.description),
    no_args_is_help=True,
)


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help=nexus.get(L.cli.option.verbose.help)
    ),
):
    # The CLI is the composition root. It decides *which* renderer to use.
    # We configure it here to capture the global verbose flag.
    cli_renderer = CliRenderer(verbose=verbose)
    bus.set_renderer(cli_renderer)


# Register commands
app.command(name="check", help=nexus.get(L.cli.command.check.help))(check_command)
app.command(name="pump", help=nexus.get(L.cli.command.pump.help))(pump_command)
app.command(name="generate", help=nexus.get(L.cli.command.generate.help))(
    generate_command
)
app.command(name="init", help=nexus.get(L.cli.command.init.help))(init_command)
app.command(name="strip", help=nexus.get(L.cli.command.strip.help))(strip_command)
app.command(name="inject", help=nexus.get(L.cli.command.inject.help))(inject_command)
~~~~~
~~~~~python
app = typer.Typer(
    name="stitcher",
    help=nexus(L.cli.app.description),
    no_args_is_help=True,
)


@app.callback()
def main(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help=nexus(L.cli.option.verbose.help)
    ),
):
    # The CLI is the composition root. It decides *which* renderer to use.
    # We configure it here to capture the global verbose flag.
    cli_renderer = CliRenderer(verbose=verbose)
    bus.set_renderer(cli_renderer)


# Register commands
app.command(name="check", help=nexus(L.cli.command.check.help))(check_command)
app.command(name="pump", help=nexus(L.cli.command.pump.help))(pump_command)
app.command(name="generate", help=nexus(L.cli.command.generate.help))(
    generate_command
)
app.command(name="init", help=nexus(L.cli.command.init.help))(init_command)
app.command(name="strip", help=nexus(L.cli.command.strip.help))(strip_command)
app.command(name="inject", help=nexus(L.cli.command.inject.help))(inject_command)
~~~~~

#### Acts 2: Pump Command 适配

修正 `pump` 命令中的帮助文本获取方式。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/pump.py
~~~~~
~~~~~python
import typer
from needle.pointer import L
from stitcher.common import bus, stitcher_nexus as nexus
from stitcher.cli.factories import make_app, make_interaction_handler


def pump_command(
    strip: bool = typer.Option(
        False, "--strip", help=nexus.get(L.cli.option.strip.help)
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help=nexus.get(L.cli.option.force.help),
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help=nexus.get(L.cli.option.reconcile.help),
    ),
~~~~~
~~~~~python
import typer
from needle.pointer import L
from stitcher.common import bus, stitcher_operator as nexus
from stitcher.cli.factories import make_app, make_interaction_handler


def pump_command(
    strip: bool = typer.Option(
        False, "--strip", help=nexus(L.cli.option.strip.help)
    ),
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
~~~~~

#### Acts 3: Factories 适配

替换工厂中的导入，将 `stitcher_operator` 传递给下游。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/factories.py
~~~~~
~~~~~python
from stitcher.app import StitcherApp
from stitcher.app.protocols import InteractionHandler
from stitcher.common import stitcher_nexus as nexus
from stitcher.adapter.python import (
    PythonParser,
~~~~~
~~~~~python
from stitcher.app import StitcherApp
from stitcher.app.protocols import InteractionHandler
from stitcher.common import stitcher_operator as nexus
from stitcher.adapter.python import (
    PythonParser,
~~~~~

#### Acts 4: Interactive Renderer 适配

由于 `TyperInteractiveRenderer` 接收的是 `nexus` (现在是 operator)，需要修改其内部的 `.get()` 调用为直接调用 `{}`。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/interactive.py
~~~~~
~~~~~python
class TyperInteractiveRenderer:
    def __init__(self, nexus):
        self.nexus = nexus

    def show_summary(self, count: int) -> None:
        msg = self.nexus.get(L.interactive.summary).format(count=count)
        typer.echo(msg)

    def show_message(self, msg_id: SemanticPointer, color=None, **kwargs) -> None:
        msg = self.nexus.get(msg_id).format(**kwargs)
        typer.secho(msg, fg=color)

    def prompt(
        self,
        context: InteractionContext,
        current_idx: int,
        total: int,
        options: List[SemanticMenuOption],
        default_action: Any,
    ) -> Any:
        # Header
        header_fmt = self.nexus.get(L.interactive.header.title)
        typer.echo("\n" + ("-" * 20))
        typer.secho(
            header_fmt.format(
                current=current_idx + 1, total=total, path=context.file_path
            ),
            fg=typer.colors.CYAN,
        )

        symbol_fmt = self.nexus.get(L.interactive.header.symbol)
        typer.secho("  " + symbol_fmt.format(fqn=context.fqn), bold=True)

        # Reason
        reason_map = {
            ConflictType.SIGNATURE_DRIFT: L.interactive.reason.signature_drift,
            ConflictType.CO_EVOLUTION: L.interactive.reason.co_evolution,
            ConflictType.DOC_CONTENT_CONFLICT: L.interactive.reason.doc_content_conflict,
        }
        reason_l = reason_map.get(context.conflict_type)
        if reason_l:
            typer.secho("  " + self.nexus.get(reason_l), fg=typer.colors.YELLOW)

        # View Diff
        if context.signature_diff:
            typer.echo("")
            typer.secho("  [ SIGNATURE DIFF ]", bold=True)
            for line in context.signature_diff.splitlines():
                color = None
                if line.startswith("+"):
                    color = typer.colors.GREEN
                elif line.startswith("-"):
                    color = typer.colors.RED
                typer.secho(f"  {line}", fg=color)

        if context.doc_diff:
            typer.echo("")
            typer.secho("  [ DOCSTRING DIFF ]", bold=True)
            for line in context.doc_diff.splitlines():
                color = None
                if line.startswith("+"):
                    color = typer.colors.GREEN
                elif line.startswith("-"):
                    color = typer.colors.RED
                typer.secho(f"  {line}", fg=color)

        # Prompt
        typer.echo("\n  " + self.nexus.get(L.interactive.prompt))

        # Options
        for opt in options:
            label = self.nexus.get(opt.label_id)
            desc = self.nexus.get(opt.desc_id)
            is_default = opt.action == default_action
            prefix = "> " if is_default else "  "
            # Label format assumes "[K]Label" style roughly
            typer.secho(f"  {prefix}{label:<25} - {desc}", bold=is_default)
~~~~~
~~~~~python
class TyperInteractiveRenderer:
    def __init__(self, operator):
        self.operator = operator

    def show_summary(self, count: int) -> None:
        msg = self.operator(L.interactive.summary).format(count=count)
        typer.echo(msg)

    def show_message(self, msg_id: SemanticPointer, color=None, **kwargs) -> None:
        msg = self.operator(msg_id).format(**kwargs)
        typer.secho(msg, fg=color)

    def prompt(
        self,
        context: InteractionContext,
        current_idx: int,
        total: int,
        options: List[SemanticMenuOption],
        default_action: Any,
    ) -> Any:
        # Header
        header_fmt = self.operator(L.interactive.header.title)
        typer.echo("\n" + ("-" * 20))
        typer.secho(
            header_fmt.format(
                current=current_idx + 1, total=total, path=context.file_path
            ),
            fg=typer.colors.CYAN,
        )

        symbol_fmt = self.operator(L.interactive.header.symbol)
        typer.secho("  " + symbol_fmt.format(fqn=context.fqn), bold=True)

        # Reason
        reason_map = {
            ConflictType.SIGNATURE_DRIFT: L.interactive.reason.signature_drift,
            ConflictType.CO_EVOLUTION: L.interactive.reason.co_evolution,
            ConflictType.DOC_CONTENT_CONFLICT: L.interactive.reason.doc_content_conflict,
        }
        reason_l = reason_map.get(context.conflict_type)
        if reason_l:
            typer.secho("  " + self.operator(reason_l), fg=typer.colors.YELLOW)

        # View Diff
        if context.signature_diff:
            typer.echo("")
            typer.secho("  [ SIGNATURE DIFF ]", bold=True)
            for line in context.signature_diff.splitlines():
                color = None
                if line.startswith("+"):
                    color = typer.colors.GREEN
                elif line.startswith("-"):
                    color = typer.colors.RED
                typer.secho(f"  {line}", fg=color)

        if context.doc_diff:
            typer.echo("")
            typer.secho("  [ DOCSTRING DIFF ]", bold=True)
            for line in context.doc_diff.splitlines():
                color = None
                if line.startswith("+"):
                    color = typer.colors.GREEN
                elif line.startswith("-"):
                    color = typer.colors.RED
                typer.secho(f"  {line}", fg=color)

        # Prompt
        typer.echo("\n  " + self.operator(L.interactive.prompt))

        # Options
        for opt in options:
            label = self.operator(opt.label_id)
            desc = self.operator(opt.desc_id)
            is_default = opt.action == default_action
            prefix = "> " if is_default else "  "
            # Label format assumes "[K]Label" style roughly
            typer.secho(f"  {prefix}{label:<25} - {desc}", bold=is_default)
~~~~~

#### Acts 5: 清理 Common 文档

最后，移除 `stitcher-common` 中关于 `stitcher_nexus` 的文档注释，保持文档一致性。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/__init__.stitcher.yaml
~~~~~
~~~~~yaml
"bus": |-
  The global singleton MessageBus instance.
"stitcher_loader": |-
  The global singleton FileSystemLoader instance for Stitcher assets.
"stitcher_nexus": |-
  The global singleton OverlayNexus instance for Stitcher.
~~~~~
~~~~~yaml
"bus": |-
  The global singleton MessageBus instance.
"stitcher_operator": |-
  The global singleton callable OverlayOperator instance for Stitcher.
~~~~~

### 下一步建议
现在 CLI 的所有组件都已适配新的可调用 Operator 模式。请再次尝试运行 `stitcher --help` 和 `check` 相关的测试。如果一切顺利，我们不仅修复了错误，还成功完成了一次优雅的架构降维。
