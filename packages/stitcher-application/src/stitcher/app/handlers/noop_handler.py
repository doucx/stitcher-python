from typing import List
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType


class NoOpInteractionHandler(InteractionHandler):

    def __init__(self, force_relink: bool = False, reconcile: bool = False):
        self._force_relink = force_relink
        self._reconcile = reconcile

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        actions: List[ResolutionAction] = []
        for context in contexts:
            action = ResolutionAction.SKIP
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                if self._force_relink:
                    action = ResolutionAction.RELINK
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
                if self._reconcile:
                    action = ResolutionAction.RECONCILE
            actions.append(action)
        return actions