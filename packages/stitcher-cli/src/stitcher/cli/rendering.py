import typer
from stitcher.common.messaging import MessageStore, protocols

class CliRenderer(protocols.Renderer):
    """
    Renders messages to the command line using Typer for colored output.
    """
    def __init__(self, store: MessageStore):
        self._store = store

    def render(self, msg_id: str, level: str, **kwargs):
        message = self._store.get(msg_id, **kwargs)
        
        color = None
        if level == "success":
            color = typer.colors.GREEN
        elif level == "warning":
            color = typer.colors.YELLOW
        elif level == "error":
            color = typer.colors.RED
            
        typer.secho(message, fg=color)