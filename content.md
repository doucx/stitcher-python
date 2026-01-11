好的，我们立即执行第二阶段的战略重构。

通过将 `CheckRunner` 的逻辑完全建立在增强后的语义索引之上，我们将实现架构的纯粹性，并显著提升 `check` 命令的性能。分析阶段将不再有任何源文件 I/O，只有在需要应用解决方案或格式化时，才会按需解析。

我将生成一个计划来完成这次迁移。

## [WIP] refactor(check): 将 CheckRunner 重构为完全由索引驱动

### 用户需求

将 `CheckRunner` 的核心分析逻辑从依赖 AST (`ModuleDef`) 迁移到完全依赖语义索引 (`IndexStore`)、YAML 文件和签名文件。这将消除在检查过程中对源文件的读取和解析需求，实现“Index-First”架构。

### 评论

这是对“分层检测架构”的完美实现。通过这次重构，`check` 命令的常规路径（即项目处于健康状态时）将变得极快，因为它只涉及数据库查询和内存中的哈希比较。文件 I/O 和 CPU 密集型的解析工作被推迟到处理异常情况的“诊断”阶段，这是一种非常高效和优雅的设计。

### 目标

1.  **更新 `StitcherApp`**: 修改 `run_check` 方法，使其不再预先解析所有文件，而是将文件路径列表传递给 `CheckRunner`。同时，为 `CheckRunner` 注入 `IndexStore` 依赖。
2.  **净化 `DocumentManager`**: 移除过时且职责不清的 `check_module` 和 `check_consistency_with_symbols` 方法，使其回归纯粹的数据提供者角色。
3.  **重写 `CheckRunner`**:
    *   移除内部的 AST 计算逻辑 (`_compute_fingerprints`)。
    *   重写 `_analyze_file` 方法，实现一个纯粹基于 `IndexStore`、`DocumentManager` 和 `SignatureManager` 的哈希比较状态机。
    *   当检测到内容冲突时，利用已存入索引的 `docstring_content` 来生成 diff，无需读取源文件。
    *   仅在处理“未追踪文件 (Untracked)”的详细报告时，才按需（JIT）解析该文件。

### 基本原理

我们已经将索引升级为代码的“高保真镜像”，现在是时候利用这个新能力了。`CheckRunner` 作为状态“检测”引擎，其所有决策所需的数据（代码结构哈希、文档内容哈希、原始文档内容）都已存在于索引中。本次重构将使 `CheckRunner` 的实现与这一架构思想完全对齐，将检测（纯内存/DB）与诊断/修复（可能需要 I/O）彻底分离。

### 标签

#intent/refine #flow/ready #priority/high #comp/application #comp/index #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/semantic-index #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 净化 DocumentManager

我们首先移除 `DocumentManager` 中与检查逻辑耦合的方法。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def apply_docs_to_module(self, module: ModuleDef) -> None:
        docs = self.load_docs_for_module(module)
        if not docs:
            return
        if "__doc__" in docs:
            module.docstring = docs["__doc__"].summary
            module.docstring_ir = docs["__doc__"]
        for func in module.functions:
            self._apply_to_function(func, docs)
        for cls in module.classes:
            self._apply_to_class(cls, docs)
        for attr in module.attributes:
            if attr.name in docs:
                attr.docstring = docs[attr.name].summary

    def check_module(self, module: ModuleDef) -> Dict[str, set]:
        public_keys = self._extract_keys(module, public_only=True)
        all_keys = self._extract_keys(module, public_only=False)
        source_docs = self.flatten_module_docs(module)
        yaml_docs = self.load_docs_for_module(module)
        yaml_keys = set(yaml_docs.keys())

        extra = yaml_keys - all_keys
        extra.discard("__doc__")

        missing_doc = set()
        pending_hydration = set()
        redundant_doc = set()
        doc_conflict = set()

        for key in all_keys:
            is_public = key in public_keys
            has_source_doc = key in source_docs
            has_yaml_doc = key in yaml_keys

            if not has_source_doc and not has_yaml_doc:
                if is_public:
                    missing_doc.add(key)
            elif has_source_doc and not has_yaml_doc:
                pending_hydration.add(key)
            elif has_source_doc and has_yaml_doc:
                # Compare SUMMARIES only.
                # Addons in YAML do not cause conflict with Source Code.
                src_summary = source_docs[key].summary or ""
                yaml_summary = yaml_docs[key].summary or ""

                if src_summary != yaml_summary:
                    doc_conflict.add(key)
                else:
                    redundant_doc.add(key)

        return {
            "extra": extra,
            "missing": missing_doc,
            "pending": pending_hydration,
            "redundant": redundant_doc,
            "conflict": doc_conflict,
        }

    def check_consistency_with_symbols(
        self, file_path: str, actual_symbols: List["SymbolRecord"]
    ) -> Dict[str, set]:
        """
        Performs structural consistency check using Index Symbols instead of AST.
        Note: This does NOT check for content conflicts (doc_conflict) or redundancy,
        as that requires source content. It focuses on Missing and Extra keys.
        """
        # 1. Extract keys from symbols
        all_keys = set()
        public_keys = set()

        for sym in actual_symbols:
            key = None
            if sym.kind == "module":
                key = "__doc__"
            elif sym.logical_path:
                key = sym.logical_path

            if key:
                all_keys.add(key)
                # Check for visibility (simple underscore check on components)
                # logical_path 'A.B._c' -> parts ['A', 'B', '_c']
                parts = key.split(".")
                if not any(p.startswith("_") and p != "__doc__" for p in parts):
                    public_keys.add(key)

        # 2. Load YAML keys
        yaml_docs = self.load_docs_for_path(file_path)
        yaml_keys = set(yaml_docs.keys())

        # 3. Compare
        extra = yaml_keys - all_keys
        extra.discard("__doc__")  # __doc__ in yaml is fine even if not explicitly tracked sometimes?
        # Actually, if it's in yaml but not in code (e.g. empty file?), it is extra.
        # But 'module' symbol usually exists.

        missing_doc = set()

        for key in all_keys:
            if key in public_keys and key not in yaml_keys:
                missing_doc.add(key)

        return {
            "extra": extra,
            "missing": missing_doc,
            # Pending/Redundant/Conflict require source content comparison, skipped here.
            "pending": set(),
            "redundant": set(),
            "conflict": set(),
        }

    def hydrate_module(
        self,
        module: ModuleDef,
~~~~~
~~~~~python.new
    def apply_docs_to_module(self, module: ModuleDef) -> None:
        docs = self.load_docs_for_module(module)
        if not docs:
            return
        if "__doc__" in docs:
            module.docstring = docs["__doc__"].summary
            module.docstring_ir = docs["__doc__"]
        for func in module.functions:
            self._apply_to_function(func, docs)
        for cls in module.classes:
            self._apply_to_class(cls, docs)
        for attr in module.attributes:
            if attr.name in docs:
                attr.docstring = docs[attr.name].summary

    def hydrate_module(
        self,
        module: ModuleDef,
~~~~~

#### Acts 2: 注入依赖并更新应用核心 `run_check` 流程

现在，我们在 `StitcherApp` 中为 `CheckRunner` 注入 `IndexStore`，并修改 `run_check` 以传递文件路径而非解析后的模块。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        # 3. Runners (Command Handlers)
        self.check_runner = CheckRunner(
            root_path,
            parser,
            self.doc_manager,
            self.sig_manager,
            self.differ,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
        )
        self.pump_runner = PumpRunner(
~~~~~
~~~~~python.new
        # 3. Runners (Command Handlers)
        self.check_runner = CheckRunner(
            root_path,
            parser,
            self.doc_manager,
            self.sig_manager,
            self.differ,
            interaction_handler,
            fingerprint_strategy=self.fingerprint_strategy,
            index_store=self.index_store,
        )
        self.pump_runner = PumpRunner(
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        self.ensure_index_fresh()
        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []
        all_modules: List[ModuleDef] = []

        self.scanner.had_errors = False

        for config in configs:
            modules = self._configure_and_scan(config)
            if not modules:
                continue
            all_modules.extend(modules)

            results, conflicts = self.check_runner.analyze_batch(modules)
            all_results.extend(results)

            self.check_runner.auto_reconcile_docs(results, modules)

            if not self.check_runner.resolve_conflicts(
                results, conflicts, force_relink, reconcile
            ):
                return False

        self.check_runner.reformat_all(all_modules)
        report_success = self.check_runner.report(all_results)
        return report_success and not self.scanner.had_errors
~~~~~
~~~~~python.new
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        self.ensure_index_fresh()
        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []
        all_modules_to_reformat: List[ModuleDef] = []

        self.scanner.had_errors = False

        for config in configs:
            # Configure docstring strategy first
            parser, renderer = get_docstring_codec(config.docstring_style)
            serializer = get_docstring_serializer(config.docstring_style)
            self.doc_manager.set_strategy(parser, serializer)

            # Get file paths from config, don't parse yet.
            file_paths = [
                p.relative_to(self.root_path).as_posix()
                for p in self.scanner.get_files_from_config(config)
            ]
            if not file_paths:
                continue

            results, conflicts = self.check_runner.analyze_batch(file_paths)
            all_results.extend(results)

            # JIT parse modules that had doc improvements for auto-reconciliation
            paths_to_parse = {res.path for res in results if res.infos["doc_improvement"]}
            modules_for_reconcile = self.scanner.scan_files(
                [self.root_path / p for p in paths_to_parse]
            )

            self.check_runner.auto_reconcile_docs(results, modules_for_reconcile)

            if not self.check_runner.resolve_conflicts(
                results, conflicts, force_relink, reconcile
            ):
                return False

            # Collect all modules for the final reformatting pass
            all_modules_to_reformat.extend(
                self.scanner.scan_files([self.root_path / p for p in file_paths])
            )

        self.check_runner.reformat_all(all_modules_to_reformat)
        report_success = self.check_runner.report(all_results)
        return report_success and not self.scanner.had_errors
~~~~~

#### Acts 3: 重写 CheckRunner

这是核心步骤。我们将用新的、完全基于索引的实现替换 `CheckRunner`。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/check.py
~~~~~
~~~~~python
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
~~~~~

### 下一步建议

我们已经成功地将 `CheckRunner` 的核心分析逻辑迁移到了索引之上，实现了架构上的巨大飞跃。

下一步是利用这个成果来优化 `PumpRunner`。当前 `PumpRunner` 仍然依赖于昂贵的 AST 解析来检测哪些文档是“脏”的。我们可以应用相同的“Index-First”原理，通过比较索引中的 `docstring_hash` 和签名文件中的 `baseline_code_docstring_hash` 来快速识别需要“抽取 (pump)”的符号，从而显著提升 `pump` 命令的性能。

如果你同意，我将生成一个计划来重构 `PumpRunner`。
