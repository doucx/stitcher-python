from pathlib import Path

from stitcher.common import bus
from needle.pointer import L

from stitcher.refactor.engine import (
    SemanticGraph,
    RefactorContext,
    Planner,
    TransactionManager,
)
from stitcher.refactor.migration import MigrationLoader, MigrationError
from stitcher.refactor.workspace import Workspace
from stitcher.refactor.sidecar.manager import SidecarManager


class RefactorRunner:
    def __init__(
        self,
        workspace: Workspace,
        sidecar_manager: SidecarManager,
        graph: SemanticGraph,
        loader: MigrationLoader,
        planner: Planner,
        tm: TransactionManager,
    ):
        self.workspace = workspace
        self.sidecar_manager = sidecar_manager
        self.graph = graph
        self.loader = loader
        self.planner = planner
        self.tm = tm

    def run(self, migration_script: Path) -> TransactionManager:
        bus.info(L.refactor.run.loading_graph)
        pkg_names = list(self.workspace.import_to_source_dirs.keys())
        for pkg_name in pkg_names:
            self.graph.load(pkg_name)

        ctx = RefactorContext(
            workspace=self.workspace,
            graph=self.graph,
            sidecar_manager=self.sidecar_manager,
        )

        bus.info(L.refactor.run.planning)
        spec = self.loader.load_from_path(migration_script)
        file_ops = self.planner.plan(spec, ctx)

        if not file_ops:
            bus.success(L.refactor.run.no_ops)
            return self.tm

        for op in file_ops:
            if op.__class__.__name__ == "WriteFileOp":
                self.tm.add_write(op.path, op.content)
            elif op.__class__.__name__ == "MoveFileOp":
                self.tm.add_move(op.path, op.dest)
            elif op.__class__.__name__ == "DeleteFileOp":
                self.tm.add_delete_file(op.path)
            elif op.__class__.__name__ == "DeleteDirectoryOp":
                self.tm.add_delete_dir(op.path)

        return self.tm