您完全正确，我的疏忽。非常感谢您指出这个硬编码问题，这是一个明显的遗漏，违背了我们将 UI 与逻辑分离的核心原则。`stitcher check` 的交互式提示确实应该完全由本地化系统驱动。

我将立即生成一个计划来解决这个问题。这个计划会：
1.  在 `stitcher-common` 的资源文件中为交互式提示定义新的语义 ID。
2.  重构 `stitcher-cli` 中的 `TyperInteractionHandler`，使其使用这些新的 `L` 对象来渲染所有提示、原因和菜单选项。

这将确保 `check` 命令的交互界面也支持多语言，并且易于维护。

## [WIP] refactor(cli): 本地化交互式冲突处理程序的提示

### 用户需求
将 `stitcher check` 命令在交互模式下显示的硬编码提示文本（如冲突原因、菜单选项等）迁移到 `L` 对象本地化系统中。

### 评论
这是一个非常重要的改进，它补全了我们 UI 本地化的最后一块拼图。将这些动态生成的提示也纳入 `needle` 系统，不仅实现了完全的 i18n 支持，也使得这部分 UI 的测试和修改变得更加容易和健壮，完全符合我们的架构原则。

### 目标
1.  在 `stitcher-common` 的 `assets/needle/en` 和 `assets/needle/zh` 目录下创建新的 `check/interactive.json` 文件。
2.  在这些文件中为交互式会话的各个部分（标题、原因、菜单项）定义语义化 ID 和对应的文本。
3.  重构 `packages/stitcher-cli/src/stitcher/cli/handlers.py` 中的 `TyperInteractionHandler`，移除所有硬编码的字符串，改为调用 `nexus.get()` 来获取显示文本。

### 基本原理
我们将遵循现有的本地化模式，首先在 `stitcher-common` 中定义好所有需要的字符串资源。然后，通过一个较大的 `patch_file` 操作，一次性地将 `TyperInteractionHandler.process_interactive_session` 方法中的整个UI渲染逻辑，从硬编码的 `typer.secho` 调用和 `menu` 列表，替换为由 `L` 对象驱动的动态文本生成。这种方式确保了逻辑与表现的彻底分离。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/interactive-handler #task/action/localization #task/state/continue

---
### Script

#### Acts 1: 定义英文本地化字符串

我们首先在 `stitcher-common` 中为交互式提示创建新的英文资源文件。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/interactive.json
~~~~~
~~~~~json
{
  "header": "Found {count} conflicts. Please review them one by one.",
  "conflict_header": "Conflict {current}/{total} in {path}",
  "symbol_header": "  Symbol: {fqn}",
  "prompt": "  Please choose an action:",
  "reason": {
    "signature_drift": "  Reason: Signature has changed, but docs have not (Signature Drift).",
    "co_evolution": "  Reason: Both signature and docs have changed (Co-evolution).",
    "doc_content_conflict": "  Reason: Source code docstring differs from YAML docstring."
  },
  "menu": {
    "relink": {
      "label": "[F]orce-relink",
      "help": "Force-relink new signature with old docs."
    },
    "reconcile": {
      "label": "[R]econcile",
      "help": "Accept both changes as the new correct state."
    },
    "hydrate_overwrite": {
      "label": "[F]orce overwrite",
      "help": "Overwrite YAML with code docs (Code-first)."
    },
    "hydrate_keep_existing": {
      "label": "[R]econcile",
      "help": "Keep existing YAML docs (YAML-first)."
    },
    "skip": {
      "label": "[S]kip",
      "help": "Skip this conflict for now."
    },
    "abort": {
      "label": "[A]bort",
      "help": "Abort the entire process."
    },
    "undo": {
      "label": "[Z]Undo",
      "help": "Go back to the previous conflict."
    }
  },
  "feedback": {
    "at_first": "Already at the first conflict.",
    "invalid": "Invalid choice, please try again."
  }
}
~~~~~

#### Acts 2: 定义中文本地化字符串

接下来，创建对应的中文资源文件。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/interactive.json
~~~~~
~~~~~json
{
  "header": "发现 {count} 个冲突，请逐一处理。",
  "conflict_header": "冲突 {current}/{total} 于 {path}",
  "symbol_header": "  符号: {fqn}",
  "prompt": "  请选择一个操作:",
  "reason": {
    "signature_drift": "  原因: 函数签名已变更，但文档未变 (签名漂移)。",
    "co_evolution": "  原因: 函数签名和文档都已变更 (协同演进)。",
    "doc_content_conflict": "  原因: 源代码中的文档与 YAML 文件中的文档不一致。"
  },
  "menu": {
    "relink": {
      "label": "[F]强制重链接",
      "help": "强制将新签名与旧文档重新链接。"
    },
    "reconcile": {
      "label": "[R]接受变更",
      "help": "接受代码和文档的变更作为新的正确状态。"
    },
    "hydrate_overwrite": {
      "label": "[F]强制覆盖",
      "help": "使用代码中的文档覆盖 YAML (代码优先)。"
    },
    "hydrate_keep_existing": {
      "label": "[R]保留现有",
      "help": "保留 YAML 中的现有文档 (YAML 优先)。"
    },
    "skip": {
      "label": "[S]跳过",
      "help": "暂时跳过此冲突。"
    },
    "abort": {
      "label": "[A]中止",
      "help": "中止整个流程。"
    },
    "undo": {
      "label": "[Z]撤销",
      "help": "返回上一个冲突。"
    }
  },
  "feedback": {
    "at_first": "已经-在第一个冲突处。",
    "invalid": "无效选项，请重试。"
  }
}
~~~~~

#### Acts 3: 重构交互式处理器

最后，我们用一个 `patch` 操作来更新 `TyperInteractionHandler`，使其使用新的本地化资源。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/handlers.py
~~~~~
~~~~~python.old
import sys
from typing import List, Optional
import click
import typer

from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType


class TyperInteractionHandler(InteractionHandler):
    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        if not sys.stdin.isatty():
            # Should not happen if logic is correct, but as a safeguard
            return [ResolutionAction.SKIP] * len(contexts)

        typer.echo(f"Found {len(contexts)} conflicts. Please review them one by one.")

        resolutions: List[Optional[ResolutionAction]] = [None] * len(contexts)
        current_index = 0
        last_choice: Optional[ResolutionAction] = None

        while current_index < len(contexts):
            context = contexts[current_index]

            # Determine default choice
            recorded_choice = resolutions[current_index]
            default_choice = recorded_choice or last_choice or ResolutionAction.ABORT

            # --- Display Conflict ---
            typer.echo("\n" + ("-" * 20))
            typer.secho(
                f"Conflict {current_index + 1}/{len(contexts)} in {context.file_path}",
                fg=typer.colors.CYAN,
            )
            typer.secho(f"  Symbol: {context.fqn}", bold=True)

            # --- Build and Display Menu ---
            menu = []
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                typer.secho(
                    "  Reason: Signature has changed, but docs have not (Signature Drift)."
                )
                menu.append(
                    (
                        "[F]orce-relink",
                        ResolutionAction.RELINK,
                        "Force-relink new signature with old docs.",
                    )
                )
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
                typer.secho(
                    "  Reason: Both signature and docs have changed (Co-evolution)."
                )
                menu.append(
                    (
                        "[R]econcile",
                        ResolutionAction.RECONCILE,
                        "Accept both changes as the new correct state.",
                    )
                )
            elif context.conflict_type == ConflictType.DOC_CONTENT_CONFLICT:
                typer.secho(
                    "  Reason: Source code docstring differs from YAML docstring."
                )
                menu.append(
                    (
                        "[F]orce overwrite",
                        ResolutionAction.HYDRATE_OVERWRITE,
                        "Overwrite YAML with code docs (Code-first).",
                    )
                )
                menu.append(
                    (
                        "[R]econcile",
                        ResolutionAction.HYDRATE_KEEP_EXISTING,
                        "Keep existing YAML docs (YAML-first).",
                    )
                )

            menu.append(
                ("[S]kip", ResolutionAction.SKIP, "Skip this conflict for now.")
            )
            menu.append(
                ("[A]bort", ResolutionAction.ABORT, "Abort the entire check process.")
            )
            menu.append(("[Z]Undo", "UNDO", "Go back to the previous conflict."))

            typer.echo("  Please choose an action:")
            for option, action, desc in menu:
                is_default = action == default_choice
                prefix = "> " if is_default else "  "
                typer.secho(f"  {prefix}{option:<15} - {desc}", bold=is_default)

            # --- Get Input ---
            char = click.getchar().lower()

            # --- Process Input ---
            if char == "\r" or char == "\n":  # Enter
                action = default_choice
            elif char == "f":
                if any(a == ResolutionAction.RELINK for _, a, _ in menu):
                    action = ResolutionAction.RELINK
                elif any(a == ResolutionAction.HYDRATE_OVERWRITE for _, a, _ in menu):
                    action = ResolutionAction.HYDRATE_OVERWRITE
                else:
                    typer.secho("Invalid choice, please try again.", fg=typer.colors.RED)
                    continue
            elif char == "r":
                if any(a == ResolutionAction.RECONCILE for _, a, _ in menu):
                    action = ResolutionAction.RECONCILE
                elif any(
                    a == ResolutionAction.HYDRATE_KEEP_EXISTING for _, a, _ in menu
                ):
                    action = ResolutionAction.HYDRATE_KEEP_EXISTING
            elif char == "s":
                action = ResolutionAction.SKIP
            elif char == "a":
                action = ResolutionAction.ABORT
            elif char == "z":
                if current_index > 0:
                    current_index -= 1
                else:
                    typer.secho(
                        "Already at the first conflict.", fg=typer.colors.YELLOW
                    )
                continue  # loop to re-display previous conflict
            else:
                typer.secho("Invalid choice, please try again.", fg=typer.colors.RED)
                continue

            resolutions[current_index] = action
            if action != ResolutionAction.ABORT:
                last_choice = action  # Update sticky default

            if action == ResolutionAction.ABORT:
                # Fill remaining with ABORT to signal cancellation
                for i in range(len(resolutions)):
                    if resolutions[i] is None:
                        resolutions[i] = ResolutionAction.ABORT
                break

            current_index += 1
~~~~~
~~~~~python.new
import sys
from typing import List, Optional
import click
import typer

from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType
from stitcher.common import stitcher_nexus as nexus
from needle.pointer import L


class TyperInteractionHandler(InteractionHandler):
    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        if not sys.stdin.isatty():
            return [ResolutionAction.SKIP] * len(contexts)

        typer.echo(nexus.get(L.check.interactive.header, count=len(contexts)))

        resolutions: List[Optional[ResolutionAction]] = [None] * len(contexts)
        current_index = 0
        last_choice: Optional[ResolutionAction] = None

        REASON_MAP = {
            ConflictType.SIGNATURE_DRIFT: L.check.interactive.reason.signature_drift,
            ConflictType.CO_EVOLUTION: L.check.interactive.reason.co_evolution,
            ConflictType.DOC_CONTENT_CONFLICT: L.check.interactive.reason.doc_content_conflict,
        }

        while current_index < len(contexts):
            context = contexts[current_index]
            recorded_choice = resolutions[current_index]
            default_choice = recorded_choice or last_choice or ResolutionAction.ABORT

            # --- Display Conflict ---
            typer.echo("\n" + ("-" * 20))
            typer.secho(
                nexus.get(
                    L.check.interactive.conflict_header,
                    current=current_index + 1,
                    total=len(contexts),
                    path=context.file_path,
                ),
                fg=typer.colors.CYAN,
            )
            typer.secho(nexus.get(L.check.interactive.symbol_header, fqn=context.fqn), bold=True)
            typer.secho(nexus.get(REASON_MAP[context.conflict_type]))

            # --- Build Menu ---
            menu = []
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                menu.append((ResolutionAction.RELINK, L.check.interactive.menu.relink))
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
                menu.append((ResolutionAction.RECONCILE, L.check.interactive.menu.reconcile))
            elif context.conflict_type == ConflictType.DOC_CONTENT_CONFLICT:
                menu.append((ResolutionAction.HYDRATE_OVERWRITE, L.check.interactive.menu.hydrate_overwrite))
                menu.append((ResolutionAction.HYDRATE_KEEP_EXISTING, L.check.interactive.menu.reconcile))

            menu.extend([
                (ResolutionAction.SKIP, L.check.interactive.menu.skip),
                (ResolutionAction.ABORT, L.check.interactive.menu.abort),
                ("UNDO", L.check.interactive.menu.undo),
            ])

            # --- Display Menu ---
            typer.echo(nexus.get(L.check.interactive.prompt))
            for action, pointer in menu:
                is_default = action == default_choice
                prefix = "> " if is_default else "  "
                label = nexus.get(pointer.label)
                help_text = nexus.get(pointer.help)
                typer.secho(f"  {prefix}{label:<20} - {help_text}", bold=is_default)

            # --- Get and Process Input ---
            char = click.getchar().lower()
            action = None

            if char in ("\r", "\n"):
                action = default_choice
            elif char == "f":
                if any(a == ResolutionAction.RELINK for a, _ in menu): action = ResolutionAction.RELINK
                elif any(a == ResolutionAction.HYDRATE_OVERWRITE for a, _ in menu): action = ResolutionAction.HYDRATE_OVERWRITE
            elif char == "r":
                if any(a == ResolutionAction.RECONCILE for a, _ in menu): action = ResolutionAction.RECONCILE
                elif any(a == ResolutionAction.HYDRATE_KEEP_EXISTING for a, _ in menu): action = ResolutionAction.HYDRATE_KEEP_EXISTING
            elif char == "s": action = ResolutionAction.SKIP
            elif char == "a": action = ResolutionAction.ABORT
            elif char == "z":
                if current_index > 0: current_index -= 1
                else: typer.secho(nexus.get(L.check.interactive.feedback.at_first), fg=typer.colors.YELLOW)
                continue

            if action is None:
                typer.secho(nexus.get(L.check.interactive.feedback.invalid), fg=typer.colors.RED)
                continue

            resolutions[current_index] = action
            if action != ResolutionAction.ABORT: last_choice = action

            if action == ResolutionAction.ABORT:
                for i in range(len(resolutions)):
                    if resolutions[i] is None: resolutions[i] = ResolutionAction.ABORT
                break
            current_index += 1

        return [res or ResolutionAction.SKIP for res in resolutions]
~~~~~
