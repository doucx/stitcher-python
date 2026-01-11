from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict

from stitcher.common import bus
from needle.pointer import L
from stitcher.spec import (
    ModuleDef,
    ConflictType,
    ResolutionAction,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
)
from stitcher.app.services import DocumentManager, SignatureManager, Differ
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.app.handlers.noop_handler import NoOpInteractionHandler
from stitcher.app.types import FileCheckResult
from stitcher.app.check.analyzer import StateAnalyzer
from stitcher.app.check.applier import ResolutionApplier


class CheckRunner:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
        differ: Differ,
        interaction_handler: InteractionHandler | None,
        fingerprint_strategy: FingerprintStrategyProtocol,
    ):
        self.root_path = root_path
        self.parser = parser
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.interaction_handler = interaction_handler
        self.analyzer = StateAnalyzer(
            doc_manager, sig_manager, differ, fingerprint_strategy
        )
        self.applier = ResolutionApplier(root_path, parser, doc_manager, sig_manager)

    def analyze_batch(
        self, modules: List[ModuleDef]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        results = []
        conflicts = []
        for module in modules:
            is_tracked = (
                (self.root_path / module.file_path)
                .with_suffix(".stitcher.yaml")
                .exists()
            )
            res, conf = self.analyzer.analyze_file(module, is_tracked)
            results.append(res)
            conflicts.extend(conf)
        return results, conflicts

    def auto_reconcile_docs(self, results: List[FileCheckResult], modules: List[ModuleDef]):
        for i, module in enumerate(modules):
            self.applier.auto_reconcile_doc_improvements(module, results[i])

    def resolve_conflicts(
        self,
        results: List[FileCheckResult],
        conflicts: List[InteractionContext],
        force_relink: bool = False,
        reconcile: bool = False,
    ) -> bool:
        if not conflicts:
            return True

        handler = self.interaction_handler or NoOpInteractionHandler(
            force_relink, reconcile
        )
        chosen_actions = handler.process_interactive_session(conflicts)
        resolutions_by_file = defaultdict(list)
        reconciled_results = defaultdict(lambda: defaultdict(list))

        for i, context in enumerate(conflicts):
            action = chosen_actions[i]
            if action == ResolutionAction.ABORT:
                bus.warning(L.strip.run.aborted)
                return False

            if action != ResolutionAction.SKIP:
                resolutions_by_file[context.file_path].append((context.fqn, action))

                # Update result DTO for reporting
                result_key = {
                    ResolutionAction.RELINK: "force_relink",
                    ResolutionAction.RECONCILE: "reconcile",
                    ResolutionAction.PURGE_DOC: "purged",
                }.get(action)

                if result_key:
                    reconciled_results[context.file_path][result_key].append(context.fqn)
            else:
                # Mark skipped conflicts as errors
                for res in results:
                    if res.path == context.file_path:
                        error_key = {
                            ConflictType.SIGNATURE_DRIFT: "signature_drift",
                            ConflictType.CO_EVOLUTION: "co_evolution",
                            ConflictType.DANGLING_DOC: "extra",
                        }.get(context.conflict_type, "unknown")
                        res.errors[error_key].append(context.fqn)
                        break

        self.applier.apply_resolutions(dict(resolutions_by_file))

        for res in results:
            if res.path in reconciled_results:
                for key, fqns in reconciled_results[res.path].items():
                    res.reconciled[key] = fqns
        return True

    def reformat_all(self, modules: List[ModuleDef]):
        bus.info(L.check.run.reformatting)
        for module in modules:
            self.doc_manager.reformat_docs_for_module(module)
            self.sig_manager.reformat_hashes_for_file(module.file_path)

    def report(self, results: List[FileCheckResult]) -> bool:
        global_failed_files = 0
        global_warnings_files = 0
        for res in results:
            if res.is_clean:
                continue

            for key in sorted(res.infos["doc_improvement"]):
                bus.info(L.check.state.doc_updated, key=key)

            if res.reconciled_count > 0:
                for key in res.reconciled.get("force_relink", []):
                    bus.success(L.check.state.relinked, key=key, path=res.path)
                for key in res.reconciled.get("reconcile", []):
                    bus.success(L.check.state.reconciled, key=key, path=res.path)
                for key in res.reconciled.get("purged", []):
                    bus.success(L.check.state.purged, key=key, path=res.path)

            if res.error_count > 0:
                global_failed_files += 1
                bus.error(L.check.file.fail, path=res.path, count=res.error_count)
            elif res.warning_count > 0:
                global_warnings_files += 1
                bus.warning(L.check.file.warn, path=res.path, count=res.warning_count)

            # Detailed issue reporting
            for key in sorted(res.errors["extra"]):
                bus.error(L.check.issue.extra, key=key)
            for key in sorted(res.errors["signature_drift"]):
                bus.error(L.check.state.signature_drift, key=key)
            for key in sorted(res.errors["co_evolution"]):
                bus.error(L.check.state.co_evolution, key=key)
            for key in sorted(res.errors["conflict"]):
                bus.error(L.check.issue.conflict, key=key)
            for key in sorted(res.errors["pending"]):
                bus.error(L.check.issue.pending, key=key)
            for key in sorted(res.warnings["missing"]):
                bus.warning(L.check.issue.missing, key=key)
            for key in sorted(res.warnings["redundant"]):
                bus.warning(L.check.issue.redundant, key=key)
            for key in sorted(res.warnings["untracked_key"]):
                bus.warning(L.check.state.untracked_code, key=key)
            if res.warnings.get("untracked_detailed"):
                keys = res.warnings["untracked_detailed"]
                bus.warning(
                    L.check.file.untracked_with_details, path=res.path, count=len(keys)
                )
                for key in sorted(keys):
                    bus.warning(L.check.issue.untracked_missing_key, key=key)
            elif res.warnings.get("untracked"):
                bus.warning(L.check.file.untracked, path=res.path)

        if global_failed_files > 0:
            bus.error(L.check.run.fail, count=global_failed_files)
            return False
        if global_warnings_files > 0:
            bus.success(L.check.run.success_with_warnings, count=global_warnings_files)
        else:
            bus.success(L.check.run.success)
        return True