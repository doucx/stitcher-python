from stitcher.cli.handlers import TyperInteractionHandler
from stitcher.app.protocols import InteractionContext
from stitcher.spec import ResolutionAction, ConflictType
import click

def test_handler_single_key_and_sticky_default(monkeypatch):
    handler = TyperInteractionHandler()
    contexts = [
        InteractionContext("f1.py", "a", ConflictType.SIGNATURE_DRIFT),
        InteractionContext("f1.py", "b", ConflictType.SIGNATURE_DRIFT),
    ]
    
    # Simulating: 
    # 1. User presses 'f' for the first conflict
    # 2. User presses 'Enter' (\r) for the second conflict (should use 'f' as sticky default)
    input_sequence = iter(['f', '\r'])
    monkeypatch.setattr(click, "getchar", lambda: next(input_sequence))
    
    actions = handler.process_interactive_session(contexts)
    
    assert actions[0] == ResolutionAction.RELINK
    assert actions[1] == ResolutionAction.RELINK

def test_handler_undo_logic(monkeypatch):
    handler = TyperInteractionHandler()
    contexts = [
        InteractionContext("f1.py", "a", ConflictType.SIGNATURE_DRIFT),
        InteractionContext("f1.py", "b", ConflictType.SIGNATURE_DRIFT),
    ]
    
    # Simulating:
    # 1. User presses 'f' (Relink) for first
    # 2. User presses 'z' (Undo) to go back
    # 3. User presses 's' (Skip) to overwrite the first decision
    # 4. User presses 'r' (Reconcile - though not valid for drift, but handler will handle it or we test flow)
    # Actually, let's keep it simple: f -> z -> s -> s
    input_sequence = iter(['f', 'z', 's', 's'])
    monkeypatch.setattr(click, "getchar", lambda: next(input_sequence))
    
    actions = handler.process_interactive_session(contexts)
    
    assert actions[0] == ResolutionAction.SKIP
    assert actions[1] == ResolutionAction.SKIP