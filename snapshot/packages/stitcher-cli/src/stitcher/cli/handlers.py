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

        # Fill any remaining unvisited with SKIP
        final_actions = [res or ResolutionAction.SKIP for res in resolutions]

        # Final confirmation could be added here later

        return final_actions
