from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType


class NoOpInteractionHandler(InteractionHandler):
    """
    A non-interactive handler that resolves conflicts based on CLI flags.
    This preserves the original behavior for CI/CD environments.
    """

    def __init__(self, force_relink: bool = False, reconcile: bool = False):
        self._force_relink = force_relink
        self._reconcile = reconcile

    def ask_resolution(self, context: InteractionContext) -> ResolutionAction:
        if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
            if self._force_relink:
                return ResolutionAction.RELINK
        elif context.conflict_type == ConflictType.CO_EVOLUTION:
            if self._reconcile:
                return ResolutionAction.RECONCILE
        return ResolutionAction.SKIP