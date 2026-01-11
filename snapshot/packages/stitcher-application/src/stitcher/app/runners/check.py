import copy
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict

from stitcher.common import bus
from needle.pointer import L
from stitcher.spec import (
    ModuleDef,
    ConflictType,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
)
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    Differ,
)
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.app.handlers.noop_handler import NoOpInteractionHandler
from stitcher.app.types import FileCheckResult
from stitcher.index.store import IndexStore


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
        index_store: IndexStore,
    ):
        self.root_path = root_path
        self.parser = parser
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.differ = differ
        self.interaction_handler = interaction_handler
        self.fingerprint_strategy = fingerprint_strategy
        self.index_store = index_store

    def _analyze_file(
        self, file_path: str
    ) -> Tuple[FileCheckResult, List[InteractionContext]]:
        result = FileCheckResult(path=file_path)
        unresolved_conflicts: List[InteractionContext] = []

        # 1. Load all state from persisted sources
        actual_symbols_list = self.index_store.get_symbols_by_file_path(file_path)
        actual_symbols = {
            s.logical_path: s for s in actual_symbols_list if s.logical_path
        }
        doc_irs = self.doc_manager.load_docs_for_path(file_path)
        baseline_fps = self.sig_manager.load_composite_hashes(file_path)

        all_fqns = set(actual_symbols.keys()) | set(doc_irs.keys())

        # 2. State Machine Analysis per FQN
        for fqn in sorted(list(all_fqns)):
            actual = actual_symbols.get(fqn)
            doc_ir = doc_irs.get(fqn)
            baseline_fp = baseline_fps.get(fqn)

            # States
            has_code = actual is not None
            has_doc = doc_ir is not None
            is_tracked = baseline_fp is not None

            if not has_code and has_doc:
                unresolved_conflicts.append(
                    InteractionContext(file_path, fqn, ConflictType.DANGLING_DOC)
                )
                continue

            if not has_code:
                continue

            # From here, we know `actual` exists.
            actual_code_hash = actual.signature_hash
            actual_doc_hash = actual.docstring_hash
            actual_sig_text = actual.signature_text
            actual_doc_content = actual.docstring_content or ""
            is_public = not any(p.startswith("_") for p in fqn.split("."))

            if has_doc and actual_doc_hash:
                yaml_summary = doc_ir.summary or ""
                if yaml_summary.strip() == actual_doc_content.strip():
                    result.warnings["redundant"].append(fqn)
                else:
                    doc_diff = self.differ.generate_text_diff(
                        yaml_summary, actual_doc_content, "yaml", "code"
                    )
                    unresolved_conflicts.append(
                        InteractionContext(
                            file_path, fqn, ConflictType.DOC_CONTENT_CONFLICT, doc_diff
                        )
                    )

            if not is_tracked:
                if actual_doc_hash and not has_doc:
                    result.errors["pending"].append(fqn)
                elif not actual_doc_hash and not has_doc and is_public:
                    result.warnings["missing"].append(fqn)
                continue

            # From here, we know the symbol is tracked.
            baseline_code_hash = baseline_fp.get("baseline_code_structure_hash")
            baseline_yaml_hash = baseline_fp.get("baseline_yaml_content_hash")
            baseline_sig_text = baseline_fp.get("baseline_code_signature_text")
            yaml_hash = (
                self.doc_manager.compute_yaml_content_hash(
                    self.doc_manager._serialize_ir(doc_ir)
                )
                if doc_ir
                else None
            )

            code_changed = actual_code_hash != baseline_code_hash
            doc_changed = yaml_hash != baseline_yaml_hash

            if not code_changed and doc_changed:
                result.infos["doc_improvement"].append(fqn)
            elif code_changed:
                sig_diff = self.differ.generate_text_diff(
                    baseline_sig_text or "", actual_sig_text or "", "baseline", "current"
                )
                conflict_type = (
                    ConflictType.CO_EVOLUTION
                    if doc_changed
                    else ConflictType.SIGNATURE_DRIFT
                )
                unresolved_conflicts.append(
                    InteractionContext(
                        file_path, fqn, conflict_type, signature_diff=sig_diff
                    )
                )

        # 3. Handle Untracked files (JIT Parse)
        doc_path = (self.root_path / file_path).with_suffix(".stitcher.yaml")
        if not doc_path.exists():
            try:
                content = (self.root_path / file_path).read_text("utf-8")
                module_def = self.parser.parse(content, file_path=file_path)
                if module_def.is_documentable():
                    undocumented = module_def.get_undocumented_public_keys()
                    if undocumented:
                        result.warnings["untracked_detailed"].extend(undocumented)
                    else:
                        result.warnings["untracked"].append("all")
            except Exception:
                result.warnings["untracked"].append("all")

        return result, unresolved_conflicts

    def analyze_batch(
        self, file_paths: List[str]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        results = []
        conflicts = []
        for path in file_paths:
            res, conf = self._analyze_file(path)
            results.append(res)
            conflicts.extend(conf)
        return results, conflicts

    def _apply_resolutions(
        self, resolutions: dict[str, list[tuple[str, ResolutionAction]]]
    ):
        sig_updates_by_file = defaultdict(list)
        purges_by_file = defaultdict(list)

        for file_path, fqn_actions in resolutions.items():
            for fqn, action in fqn_actions:
                if action in [ResolutionAction.RELINK, ResolutionAction.RECONCILE]:
                    sig_updates_by_file[file_path].append((fqn, action))
                elif action == ResolutionAction.PURGE_DOC:
                    purges_by_file[file_path].append(fqn)

        # Apply signature updates
        for file_path, fqn_actions in sig_updates_by_file.items():
            stored_hashes = self.sig_manager.load_composite_hashes(file_path)
            new_hashes = copy.deepcopy(stored_hashes)

            # JIT load current state from index for resolution
            actual_symbols = {
                s.logical_path: s
                for s in self.index_store.get_symbols_by_file_path(file_path)
                if s.logical_path
            }
            doc_irs = self.doc_manager.load_docs_for_path(file_path)

            for fqn, action in fqn_actions:
                if fqn in new_hashes and fqn in actual_symbols:
                    fp = new_hashes[fqn]
                    actual = actual_symbols[fqn]

                    if action == ResolutionAction.RELINK:
                        if actual.signature_hash:
                            fp["baseline_code_structure_hash"] = str(actual.signature_hash)
                    elif action == ResolutionAction.RECONCILE:
                        if actual.signature_hash:
                            fp["baseline_code_structure_hash"] = str(actual.signature_hash)
                        if fqn in doc_irs:
                            doc_ir = doc_irs[fqn]
                            yaml_hash = self.doc_manager.compute_yaml_content_hash(
                                self.doc_manager._serialize_ir(doc_ir)
                            )
                            fp["baseline_yaml_content_hash"] = str(yaml_hash)

            if new_hashes != stored_hashes:
                self.sig_manager.save_composite_hashes(file_path, new_hashes)

        # Apply doc purges
        for file_path, fqns_to_purge in purges_by_file.items():
            module_def = ModuleDef(file_path=file_path)
            docs = self.doc_manager.load_docs_for_module(module_def)
            original_len = len(docs)

            for fqn in fqns_to_purge:
                if fqn in docs:
                    del docs[fqn]

            if len(docs) < original_len:
                doc_path = (self.root_path / file_path).with_suffix(".stitcher.yaml")
                if not docs:
                    if doc_path.exists():
                        doc_path.unlink()
                else:
                    final_data = {
                        k: self.doc_manager._serialize_ir(v) for k, v in docs.items()
                    }
                    self.doc_manager.adapter.save(doc_path, final_data)

    def auto_reconcile_docs(
        self, results: List[FileCheckResult], modules: List[ModuleDef]
    ):
        for res in results:
            if res.infos["doc_improvement"]:
                module_def = next((m for m in modules if m.file_path == res.path), None)
                if not module_def:
                    continue

                stored_hashes = self.sig_manager.load_composite_hashes(
                    module_def.file_path
                )
                new_hashes = copy.deepcopy(stored_hashes)
                current_yaml_map = self.doc_manager.compute_yaml_content_hashes(
                    module_def
                )

                for fqn in res.infos["doc_improvement"]:
                    if fqn in new_hashes:
                        new_yaml_hash = current_yaml_map.get(fqn)
                        if new_yaml_hash is not None:
                            new_hashes[fqn]["baseline_yaml_content_hash"] = (
                                new_yaml_hash
                            )
                        elif "baseline_yaml_content_hash" in new_hashes[fqn]:
                            del new_hashes[fqn]["baseline_yaml_content_hash"]

                if new_hashes != stored_hashes:
                    self.sig_manager.save_composite_hashes(
                        module_def.file_path, new_hashes
                    )

    def resolve_conflicts(
        self,
        results: List[FileCheckResult],
        conflicts: List[InteractionContext],
        force_relink: bool = False,
        reconcile: bool = False,
    ) -> bool:
        if not conflicts:
            return True

        if self.interaction_handler:
            chosen_actions = self.interaction_handler.process_interactive_session(
                conflicts
            )
            resolutions_by_file = defaultdict(list)
            reconciled_results = defaultdict(lambda: defaultdict(list))

            for i, context in enumerate(conflicts):
                action = chosen_actions[i]
                if action == ResolutionAction.RELINK:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["force_relink"].append(
                        context.fqn
                    )
                elif action == ResolutionAction.RECONCILE:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["reconcile"].append(
                        context.fqn
                    )
                elif action == ResolutionAction.PURGE_DOC:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["purged"].append(context.fqn)
                elif action == ResolutionAction.SKIP:
                    for res in results:
                        if res.path == context.file_path:
                            error_key = {
                                ConflictType.SIGNATURE_DRIFT: "signature_drift",
                                ConflictType.CO_EVOLUTION: "co_evolution",
                                ConflictType.DANGLING_DOC: "extra",
                                ConflictType.DOC_CONTENT_CONFLICT: "conflict",
                            }.get(context.conflict_type, "unknown")
                            res.errors[error_key].append(context.fqn)
                            break
                elif action == ResolutionAction.ABORT:
                    bus.warning(L.strip.run.aborted)
                    return False

            self._apply_resolutions(dict(resolutions_by_file))

            for res in results:
                if res.path in reconciled_results:
                    res.reconciled["force_relink"] = reconciled_results[res.path][
                        "force_relink"
                    ]
                    res.reconciled["reconcile"] = reconciled_results[res.path][
                        "reconcile"
                    ]
                    res.reconciled["purged"] = reconciled_results[res.path].get(
                        "purged", []
                    )
        else:
            handler = NoOpInteractionHandler(force_relink, reconcile)
            chosen_actions = handler.process_interactive_session(conflicts)
            resolutions_by_file = defaultdict(list)
            reconciled_results = defaultdict(lambda: defaultdict(list))
            for i, context in enumerate(conflicts):
                action = chosen_actions[i]
                if action != ResolutionAction.SKIP:
                    key = (
                        "force_relink"
                        if action == ResolutionAction.RELINK
                        else "reconcile"
                    )
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path][key].append(context.fqn)
                else:
                    for res in results:
                        if res.path == context.file_path:
                            error_key = {
                                ConflictType.SIGNATURE_DRIFT: "signature_drift",
                                ConflictType.CO_EVOLUTION: "co_evolution",
                                ConflictType.DANGLING_DOC: "extra",
                                ConflictType.DOC_CONTENT_CONFLICT: "conflict",
                            }.get(context.conflict_type, "unknown")
                            res.errors[error_key].append(context.fqn)

            self._apply_resolutions(dict(resolutions_by_file))
            for res in results:
                if res.path in reconciled_results:
                    res.reconciled["force_relink"] = reconciled_results[res.path][
                        "force_relink"
                    ]
                    res.reconciled["reconcile"] = reconciled_results[res.path][
                        "reconcile"
                    ]
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
            for key in sorted(res.infos["doc_improvement"]):
                bus.info(L.check.state.doc_updated, key=key)
            if res.is_clean:
                continue
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
            if "untracked_detailed" in res.warnings:
                keys = res.warnings["untracked_detailed"]
                bus.warning(
                    L.check.file.untracked_with_details, path=res.path, count=len(keys)
                )
                for key in sorted(keys):
                    bus.warning(L.check.issue.untracked_missing_key, key=key)
            elif "untracked" in res.warnings:
                bus.warning(L.check.file.untracked, path=res.path)

        if global_failed_files > 0:
            bus.error(L.check.run.fail, count=global_failed_files)
            return False
        if global_warnings_files > 0:
            bus.success(L.check.run.success_with_warnings, count=global_warnings_files)
        else:
            bus.success(L.check.run.success)
        return True