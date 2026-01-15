from stitcher.refactor.migration import MigrationSpec, Rename


def upgrade(spec: MigrationSpec):
    """
    Updates all project references from the old bus location in common
    to the new dedicated bus package.
    """
    # This will update all 'from stitcher.common import bus'
    # to 'from stitcher.bus import bus' throughout the workspace.
    spec.add(Rename("stitcher.common.bus", "stitcher.bus.bus"))

    # Also update the operator if used directly
    spec.add(
        Rename("stitcher.common.stitcher_operator", "stitcher.bus.stitcher_operator")
    )
