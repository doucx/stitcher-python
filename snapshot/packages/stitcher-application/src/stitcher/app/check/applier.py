import copy
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple

from stitcher.app.services import DocumentManager, SignatureManager
from stitcher.spec import (
    ModuleDef,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
)


class ResolutionApplier:
    """
    Applies resolutions to the filesystem by modifying signature and doc files.
    This service is stateful and performs I/O.
    """

    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
    ):
        self.root_path = root_path
        self.parser = parser
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager

    def apply_resolutions(
        self, resolutions: Dict[str, List[Tuple[str, ResolutionAction]]]
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
            # This is inefficient as it re-parses, but necessary for now
            # The next refactoring will fix this by using the index.
            # We accept this temporary inefficiency as part of the transition.
            full_module_def = self.parser.parse(
                (self.root_path / file_path).read_text("utf-8"), file_path
            )
            # This is a circular dependency smell that will be removed next.
            from stitcher.app.check.analyzer import StateAnalyzer

            # We need a fingerprint strategy to compute fingerprints.
            # This indicates that the applier might still have too much knowledge.
            # For now, we'll instantiate a dummy analyzer to access its method.
            # A better approach would be to pass computed fingerprints in.
            from stitcher.spec import FingerprintStrategyProtocol

            dummy_analyzer = StateAnalyzer(
                self.doc_manager, self.sig_manager, None, None
            )
            # This is a hack. The app needs to provide the strategy.
            # For now, we assume the applier doesn't need a real differ/strategy
            # if we pass the computed data.
            # Let's re-think. The applier needs the *new* state to write.
            # It needs `computed_fingerprints` and `current_yaml_map`.

            # This part is complex to refactor without the index.
            # The current `_apply_resolutions` re-calculates everything.
            # I will replicate this logic for now. The key is isolating it.
            stored_hashes = self.sig_manager.load_composite_hashes(file_path)
            new_hashes = copy.deepcopy(stored_hashes)

            # Re-calculating state.
            from stitcher.adapter.python import PythonFingerprintStrategy

            analyzer = StateAnalyzer(
                self.doc_manager,
                self.sig_manager,
                None,
                PythonFingerprintStrategy(),
            )
            computed_fingerprints = analyzer._compute_fingerprints(full_module_def)
            current_yaml_map = self.doc_manager.compute_yaml_content_hashes(
                full_module_def
            )

            for fqn, action in fqn_actions:
                if fqn in new_hashes:
                    fp = new_hashes[fqn]
                    current_fp = computed_fingerprints.get(fqn, Fingerprint())
                    current_code_hash = current_fp.get("current_code_structure_hash")

                    if action == ResolutionAction.RELINK:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                    elif action == ResolutionAction.RECONCILE:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                        if fqn in current_yaml_map:
                            fp["baseline_yaml_content_hash"] = str(
                                current_yaml_map[fqn]
                            )

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

    def auto_reconcile_doc_improvements(self, module: ModuleDef, result: FileCheckResult):
        if not result.infos["doc_improvement"]:
            return

        stored_hashes = self.sig_manager.load_composite_hashes(module.file_path)
        new_hashes = copy.deepcopy(stored_hashes)
        current_yaml_map = self.doc_manager.compute_yaml_content_hashes(module)

        for fqn in result.infos["doc_improvement"]:
            if fqn in new_hashes:
                new_yaml_hash = current_yaml_map.get(fqn)
                if new_yaml_hash is not None:
                    new_hashes[fqn]["baseline_yaml_content_hash"] = new_yaml_hash
                elif "baseline_yaml_content_hash" in new_hashes[fqn]:
                    del new_hashes[fqn]["baseline_yaml_content_hash"]

        if new_hashes != stored_hashes:
            self.sig_manager.save_composite_hashes(module.file_path, new_hashes)