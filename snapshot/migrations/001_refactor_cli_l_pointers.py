from pathlib import Path
from stitcher.refactor.migration import MigrationSpec, Move


def upgrade(spec: MigrationSpec):
    """
    Refactors L.cli.* pointers to L.cli.commands.*.

    This is achieved by moving the underlying JSON asset files. The
    Stitcher refactor engine will automatically update all Python code
    references.
    """
    base_path = Path("packages/stitcher-common/src/stitcher/common/assets/needle/en/cli")
    target_dir = base_path / "commands"

    # List of files to move.
    files_to_move = ["app.json", "command.json", "option.json"]

    for filename in files_to_move:
        src_path = base_path / filename
        dest_path = target_dir / filename

        spec.add(Move(src=src_path, dest=dest_path))