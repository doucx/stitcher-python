好的，我们进入阶段 3。

这是一个重构 `CheckResolver` 以使用 `LockSession` 的计划，同时将 `check` 命令的文件操作纳入事务管理，以提高一致性和健壮性。

我们将重构 `CheckResolver`，移除其内部所有手动的 Lock 文件读写逻辑，并将其替换为对 `LockSession` 的调用。同时，我们将为 `check` 命令引入 `TransactionManager`，以原子方式处理文档和 Lock 文件的更新。

## [WIP] refactor(check): 将 CheckResolver 迁移至 LockSession

### 用户需求
完成 **Check 流程重构 (Phase 3)**，将 `check` 命令中处理冲突解决（Relink, Reconcile, Purge）时对 `stitcher.lock` 的修改，统一委托给 `LockSession`。

### 评论
这次重构是实现架构一致性的关键。`CheckResolver` 的逻辑比 `PumpExecutor` 更复杂，因为它处理多种状态变更意图。将其迁移到 `LockSession` 不仅能消除代码重复，更能保证所有状态变更（无论来自 `pump` 还是 `check`）都遵循相同的、经过测试的持久化路径。此外，将文件操作纳入 `TransactionManager` 修复了一个潜在的原子性问题。

### 目标
1.  **依赖注入**: 将 `LockSession` 实例注入到 `CheckResolver` 中。
2.  **事务化**: 在 `StitcherApp.run_check` 中引入 `TransactionManager`，并将其传递给 `CheckResolver`。
3.  **逻辑迁移**:
    *   重构 `CheckResolver._apply_resolutions` 方法。
    *   移除所有手动的 `lock_manager.load/save` 调用。
    *   根据 `ResolutionAction` 调用对应的 `lock_session` 方法 (`record_relink`, `record_fresh_state`, `record_purge`)。
    *   将 `.stitcher.yaml` 的删除和写入操作从直接 I/O 改为 `tm.add_delete_file` 和 `tm.add_write`。
4.  **编排**: 在 `StitcherApp.run_check` 的末尾，统一提交 `lock_session` 和 `tm`。

### 基本原理
-   **单一职责**: `CheckResolver` 的职责是“解决冲突”，而不是“持久化解决方案”。
-   **原子性**: 所有因 `check` 命令产生的文件系统变更（文档变更 + Lock 变更）现在都处于同一个事务边界内，要么全部成功，要么全部回滚（在 Dry-Run 模式下）。
-   **架构一致性**: `check` 和 `pump` 命令现在以完全相同的方式处理状态持久化，降低了系统的认知复杂度和维护成本。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/lock-session #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新 `StitcherApp` 以驱动事务化 `check`

我们在 `run_check` 方法中创建 `TransactionManager`，将其传递给 `check_runner`，并在最后提交所有变更。同时，在 `__init__` 中将 `lock_session` 注入 `CheckResolver`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        # 5. Runners (Command Handlers)
        check_resolver = CheckResolver(
            root_path,
            self.workspace,
            parser,
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            interaction_handler,
            self.fingerprint_strategy,
        )
        check_reporter = CheckReporter()
        self.check_runner = CheckRunner(
~~~~~
~~~~~python.new
        # 5. Runners (Command Handlers)
        check_resolver = CheckResolver(
            root_path,
            self.workspace,
            parser,
            self.doc_manager,
            self.lock_manager,
            self.uri_generator,
            interaction_handler,
            self.fingerprint_strategy,
            self.lock_session,
        )
        check_reporter = CheckReporter()
        self.check_runner = CheckRunner(
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        self.scanner.had_errors = False
        index_stats = self.ensure_index_fresh()
        if not index_stats["success"]:
            self.scanner.had_errors = True

        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []

        # We wrap the entire multi-target check process in a single DB session
        with self.db_manager.session():
            for config in configs:
                if config.name != "default":
                    bus.info(L.generate.target.processing, name=config.name)

                # 1. Config Strategy
                parser, renderer = get_docstring_codec(config.docstring_style)
                serializer = get_docstring_serializer(config.docstring_style)
                self.doc_manager.set_strategy(parser, serializer)

                # 2. Get Files (Physical) - Zero-IO Path
                files = self.scanner.get_files_from_config(config)
                rel_paths = [f.relative_to(self.root_path).as_posix() for f in files]

                # 3. Get Plugins (Virtual) - AST Path
                plugin_modules = self.scanner.process_plugins(config.plugins)

                if not rel_paths and not plugin_modules:
                    continue

                # 4. Analyze
                batch_results: List[FileCheckResult] = []
                batch_conflicts: List[InteractionContext] = []

                if rel_paths:
                    f_res, f_conflicts = self.check_runner.analyze_paths(rel_paths)
                    batch_results.extend(f_res)
                    batch_conflicts.extend(f_conflicts)

                if plugin_modules:
                    p_res, p_conflicts = self.check_runner.analyze_batch(plugin_modules)
                    batch_results.extend(p_res)
                    batch_conflicts.extend(p_conflicts)

                all_results.extend(batch_results)

                # 5. Prepare lightweight ModuleDefs for post-processing
                file_module_stubs = [ModuleDef(file_path=p) for p in rel_paths]
                batch_modules = file_module_stubs + plugin_modules

                # 6. Auto-Reconcile Docs (e.g., when only docs are updated)
                self.check_runner.auto_reconcile_docs(batch_results, batch_modules)

                # 7. Resolve interactive/manual conflicts
                if not self.check_runner.resolve_conflicts(
                    batch_results, batch_conflicts, force_relink, reconcile
                ):
                    return False

            # --- Phase B: Architecture Check (Global) ---
            arch_violations = self.architecture_engine.analyze(self.index_store)

        # 9. Final Report
        report_success = self.check_runner.report(all_results, arch_violations)
        return report_success and not self.scanner.had_errors
~~~~~
~~~~~python.new
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        self.scanner.had_errors = False
        index_stats = self.ensure_index_fresh()
        if not index_stats["success"]:
            self.scanner.had_errors = True

        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []
        # Create a single transaction for the entire check run
        tm = TransactionManager(self.root_path)

        # We wrap the entire multi-target check process in a single DB session
        with self.db_manager.session():
            for config in configs:
                if config.name != "default":
                    bus.info(L.generate.target.processing, name=config.name)

                # 1. Config Strategy
                parser, renderer = get_docstring_codec(config.docstring_style)
                serializer = get_docstring_serializer(config.docstring_style)
                self.doc_manager.set_strategy(parser, serializer)

                # 2. Get Files (Physical) - Zero-IO Path
                files = self.scanner.get_files_from_config(config)
                rel_paths = [f.relative_to(self.root_path).as_posix() for f in files]

                # 3. Get Plugins (Virtual) - AST Path
                plugin_modules = self.scanner.process_plugins(config.plugins)

                if not rel_paths and not plugin_modules:
                    continue

                # 4. Analyze
                batch_results: List[FileCheckResult] = []
                batch_conflicts: List[InteractionContext] = []

                if rel_paths:
                    f_res, f_conflicts = self.check_runner.analyze_paths(rel_paths)
                    batch_results.extend(f_res)
                    batch_conflicts.extend(f_conflicts)

                if plugin_modules:
                    p_res, p_conflicts = self.check_runner.analyze_batch(plugin_modules)
                    batch_results.extend(p_res)
                    batch_conflicts.extend(p_conflicts)

                all_results.extend(batch_results)

                # 5. Prepare lightweight ModuleDefs for post-processing
                file_module_stubs = [ModuleDef(file_path=p) for p in rel_paths]
                batch_modules = file_module_stubs + plugin_modules

                # 6. Auto-Reconcile Docs (e.g., when only docs are updated)
                self.check_runner.auto_reconcile_docs(batch_results, batch_modules)

                # 7. Resolve interactive/manual conflicts
                if not self.check_runner.resolve_conflicts(
                    batch_results, batch_conflicts, tm, force_relink, reconcile
                ):
                    return False

            # --- Phase B: Architecture Check (Global) ---
            arch_violations = self.architecture_engine.analyze(self.index_store)

        # 8. Commit Lock and Doc changes
        self.lock_session.commit_to_transaction(tm)
        tm.commit()

        # 9. Final Report
        report_success = self.check_runner.report(all_results, arch_violations)
        return report_success and not self.scanner.had_errors
~~~~~

#### Acts 2: 更新 `CheckRunner` 以传递 `TransactionManager`

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
    def resolve_conflicts(
        self,
        results: List[AnalysisFileCheckResult],
        conflicts: List[InteractionContext],
        force_relink: bool = False,
        reconcile: bool = False,
    ) -> bool:
        return self.resolver.resolve_conflicts(
            results, conflicts, force_relink, reconcile
        )
~~~~~
~~~~~python.new
    def resolve_conflicts(
        self,
        results: List[AnalysisFileCheckResult],
        conflicts: List[InteractionContext],
        tm: "TransactionManager",
        force_relink: bool = False,
        reconcile: bool = False,
    ) -> bool:
        return self.resolver.resolve_conflicts(
            results, conflicts, tm, force_relink, reconcile
        )
~~~~~

#### Acts 3: 更新 `CheckResolver` 以注入 `LockSession` 和 `TransactionManager`

首先，更新 `__init__` 和 `resolve_conflicts` 的签名。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
from stitcher.spec.managers import DocumentManagerProtocol
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.app.handlers.noop_handler import NoOpInteractionHandler
from stitcher.analysis.schema import FileCheckResult
from stitcher.workspace import Workspace


class CheckResolver:
    def __init__(
        self,
        root_path: Path,
        workspace: Workspace,
        parser: LanguageParserProtocol,
        doc_manager: DocumentManagerProtocol,
        lock_manager: LockManagerProtocol,
        uri_generator: URIGeneratorProtocol,
        interaction_handler: InteractionHandler | None,
        fingerprint_strategy: FingerprintStrategyProtocol,
    ):
        self.root_path = root_path
        self.workspace = workspace
        self.parser = parser
        self.doc_manager = doc_manager
        self.lock_manager = lock_manager
        self.uri_generator = uri_generator
        self.interaction_handler = interaction_handler
        self.fingerprint_strategy = fingerprint_strategy
~~~~~
~~~~~python.new
from stitcher.spec.managers import DocumentManagerProtocol
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.app.handlers.noop_handler import NoOpInteractionHandler
from stitcher.app.services.lock_session import LockSession
from stitcher.analysis.schema import FileCheckResult
from stitcher.workspace import Workspace
from stitcher.common.transaction import TransactionManager


class CheckResolver:
    def __init__(
        self,
        root_path: Path,
        workspace: Workspace,
        parser: LanguageParserProtocol,
        doc_manager: DocumentManagerProtocol,
        lock_manager: LockManagerProtocol,
        uri_generator: URIGeneratorProtocol,
        interaction_handler: InteractionHandler | None,
        fingerprint_strategy: FingerprintStrategyProtocol,
        lock_session: LockSession,
    ):
        self.root_path = root_path
        self.workspace = workspace
        self.parser = parser
        self.doc_manager = doc_manager
        self.lock_manager = lock_manager
        self.uri_generator = uri_generator
        self.interaction_handler = interaction_handler
        self.fingerprint_strategy = fingerprint_strategy
        self.lock_session = lock_session
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
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
            return self._resolve_interactive(results, conflicts)
        else:
            return self._resolve_noop(results, conflicts, force_relink, reconcile)

    def _resolve_interactive(
        self, results: List[FileCheckResult], conflicts: List[InteractionContext]
    ) -> bool:
        assert self.interaction_handler is not None

        chosen_actions = self.interaction_handler.process_interactive_session(conflicts)
        resolutions_by_file = defaultdict(list)
        unresolved_contexts: List[InteractionContext] = []

        for i, context in enumerate(conflicts):
            action = chosen_actions[i]
            if action in (
                ResolutionAction.RELINK,
                ResolutionAction.RECONCILE,
                ResolutionAction.HYDRATE_OVERWRITE,
                ResolutionAction.HYDRATE_KEEP_EXISTING,
                ResolutionAction.PURGE_DOC,
            ):
                resolutions_by_file[context.file_path].append((context, action))
            elif action == ResolutionAction.SKIP:
                unresolved_contexts.append(context)
            elif action == ResolutionAction.ABORT:
                bus.warning(L.strip.run.aborted)
                return False

        self._apply_resolutions(dict(resolutions_by_file))
        self._update_results(results, dict(resolutions_by_file))

        # Unresolved conflicts are kept in the violations list, so no action needed.
        return True

    def _resolve_noop(
        self,
        results: List[FileCheckResult],
        conflicts: List[InteractionContext],
        force_relink: bool,
        reconcile: bool,
    ) -> bool:
        handler = NoOpInteractionHandler(force_relink, reconcile)
        chosen_actions = handler.process_interactive_session(conflicts)
        resolutions_by_file = defaultdict(list)

        for i, context in enumerate(conflicts):
            action = chosen_actions[i]
            if action != ResolutionAction.SKIP:
                resolutions_by_file[context.file_path].append((context, action))

        self._apply_resolutions(dict(resolutions_by_file))
        self._update_results(results, dict(resolutions_by_file))
        return True
~~~~~
~~~~~python.new
    def resolve_conflicts(
        self,
        results: List[FileCheckResult],
        conflicts: List[InteractionContext],
        tm: TransactionManager,
        force_relink: bool = False,
        reconcile: bool = False,
    ) -> bool:
        if not conflicts:
            return True

        if self.interaction_handler:
            return self._resolve_interactive(results, conflicts, tm)
        else:
            return self._resolve_noop(results, conflicts, tm, force_relink, reconcile)

    def _resolve_interactive(
        self,
        results: List[FileCheckResult],
        conflicts: List[InteractionContext],
        tm: TransactionManager,
    ) -> bool:
        assert self.interaction_handler is not None

        chosen_actions = self.interaction_handler.process_interactive_session(conflicts)
        resolutions_by_file = defaultdict(list)
        unresolved_contexts: List[InteractionContext] = []

        for i, context in enumerate(conflicts):
            action = chosen_actions[i]
            if action in (
                ResolutionAction.RELINK,
                ResolutionAction.RECONCILE,
                ResolutionAction.HYDRATE_OVERWRITE,
                ResolutionAction.HYDRATE_KEEP_EXISTING,
                ResolutionAction.PURGE_DOC,
            ):
                resolutions_by_file[context.file_path].append((context, action))
            elif action == ResolutionAction.SKIP:
                unresolved_contexts.append(context)
            elif action == ResolutionAction.ABORT:
                bus.warning(L.strip.run.aborted)
                return False

        self._apply_resolutions(dict(resolutions_by_file), tm)
        self._update_results(results, dict(resolutions_by_file))

        # Unresolved conflicts are kept in the violations list, so no action needed.
        return True

    def _resolve_noop(
        self,
        results: List[FileCheckResult],
        conflicts: List[InteractionContext],
        tm: TransactionManager,
        force_relink: bool,
        reconcile: bool,
    ) -> bool:
        handler = NoOpInteractionHandler(force_relink, reconcile)
        chosen_actions = handler.process_interactive_session(conflicts)
        resolutions_by_file = defaultdict(list)

        for i, context in enumerate(conflicts):
            action = chosen_actions[i]
            if action != ResolutionAction.SKIP:
                resolutions_by_file[context.file_path].append((context, action))

        self._apply_resolutions(dict(resolutions_by_file), tm)
        self._update_results(results, dict(resolutions_by_file))
        return True
~~~~~

#### Acts 4: 重构 `_apply_resolutions` 核心逻辑

这是本次重构的核心，我们将完全替换此方法的实现。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
    def _apply_resolutions(
        self, resolutions: dict[str, list[tuple[InteractionContext, ResolutionAction]]]
    ):
        # 1. Group resolutions by Package Root (Lock Boundary)
        updates_by_pkg: Dict[Path, Dict[str, Fingerprint]] = defaultdict(dict)
        actions_by_file = defaultdict(list)

        # Pre-process actions to group by file first for efficient parsing
        for file_path, context_actions in resolutions.items():
            abs_path = self.root_path / file_path
            pkg_root = self.workspace.find_owning_package(abs_path)

            if pkg_root not in updates_by_pkg:
                updates_by_pkg[pkg_root] = self.lock_manager.load(pkg_root)

            actions_by_file[file_path].extend(context_actions)

        # 2. Process file-by-file logic
        purges_by_file = defaultdict(list)

        for file_path, context_actions in actions_by_file.items():
            abs_path = self.root_path / file_path
            pkg_root = self.workspace.find_owning_package(abs_path)
            ws_rel_path = self.workspace.to_workspace_relative(abs_path)

            lock_data = updates_by_pkg[pkg_root]

            # Need to parse code to get current state for Relink/Reconcile
            has_sig_updates = any(
                a in [ResolutionAction.RELINK, ResolutionAction.RECONCILE]
                for _, a in context_actions
            )

            computed_fingerprints = {}
            current_yaml_map = {}

            if has_sig_updates:
                full_module_def = self.parser.parse(
                    abs_path.read_text("utf-8"), file_path
                )
                computed_fingerprints = self._compute_fingerprints(full_module_def)
                current_yaml_map = self.doc_manager.compute_yaml_content_hashes(
                    full_module_def
                )

            for context, action in context_actions:
                fqn = context.fqn

                if action == ResolutionAction.PURGE_DOC:
                    purges_by_file[file_path].append(fqn)
                    continue

                suri = self.uri_generator.generate_symbol_uri(ws_rel_path, fqn)
                if suri in lock_data:
                    fp = lock_data[suri]
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

        # 3. Save Lock Files
        for pkg_root, lock_data in updates_by_pkg.items():
            self.lock_manager.save(pkg_root, lock_data)

        # 4. Apply doc purges (Sidecar operations)
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
                        k: self.doc_manager.serialize_ir(v) for k, v in docs.items()
                    }
                    content = self.doc_manager.dump_data(final_data)
                    doc_path.write_text(content, encoding="utf-8")

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
                        k: self.doc_manager.serialize_ir(v) for k, v in docs.items()
                    }
                    content = self.doc_manager.dump_data(final_data)
                    doc_path.write_text(content, encoding="utf-8")
~~~~~
~~~~~python.new
    def _apply_resolutions(
        self,
        resolutions: dict[str, list[tuple[InteractionContext, ResolutionAction]]],
        tm: TransactionManager,
    ):
        # Process file-by-file, as each might need parsing.
        # LockSession will handle aggregation by package root internally.
        for file_path, context_actions in resolutions.items():
            abs_path = self.root_path / file_path

            # Determine if we need to parse the file to get current state
            needs_parsing = any(
                action
                in [
                    ResolutionAction.RELINK,
                    ResolutionAction.RECONCILE,
                    ResolutionAction.HYDRATE_OVERWRITE,
                    ResolutionAction.HYDRATE_KEEP_EXISTING,
                ]
                for _, action in context_actions
            )

            # --- Data Loading (on demand) ---
            full_module_def: ModuleDef | None = None
            computed_fingerprints: dict[str, Fingerprint] = {}
            current_doc_irs: dict[str, "DocstringIR"] = {}

            if needs_parsing:
                full_module_def = self.parser.parse(
                    abs_path.read_text("utf-8"), file_path
                )
                computed_fingerprints = self._compute_fingerprints(full_module_def)
                current_doc_irs = self.doc_manager.load_docs_for_module(
                    full_module_def
                )

            # --- Action Execution ---
            fqns_to_purge_from_doc: list[str] = []
            for context, action in context_actions:
                fqn = context.fqn
                # Use a lightweight stub for purge actions if we didn't parse
                module_stub = full_module_def or ModuleDef(file_path=file_path)

                if action == ResolutionAction.RELINK:
                    code_fp = computed_fingerprints.get(fqn)
                    if code_fp:
                        self.lock_session.record_relink(module_stub, fqn, code_fp)

                elif action in [
                    ResolutionAction.RECONCILE,
                    ResolutionAction.HYDRATE_OVERWRITE,
                    ResolutionAction.HYDRATE_KEEP_EXISTING, # In check, this is a reconcile
                ]:
                    self.lock_session.record_fresh_state(
                        module_stub,
                        fqn,
                        doc_ir=current_doc_irs.get(fqn),
                        code_fingerprint=computed_fingerprints.get(fqn),
                    )

                elif action == ResolutionAction.PURGE_DOC:
                    fqns_to_purge_from_doc.append(fqn)
                    self.lock_session.record_purge(module_stub, fqn)

            # --- Sidecar Doc File Updates (Transactional) ---
            if fqns_to_purge_from_doc:
                # Create a stub ModuleDef to pass to the doc manager
                module_def_stub = ModuleDef(file_path=file_path)
                docs = self.doc_manager.load_docs_for_module(module_def_stub)
                original_len = len(docs)

                for fqn in fqns_to_purge_from_doc:
                    if fqn in docs:
                        del docs[fqn]

                if len(docs) < original_len:
                    doc_path = abs_path.with_suffix(".stitcher.yaml")
                    rel_doc_path = doc_path.relative_to(self.root_path)
                    if not docs:
                        if doc_path.exists():
                            tm.add_delete_file(str(rel_doc_path))
                    else:
                        final_data = {
                            k: self.doc_manager.serialize_ir_for_view(v)
                            for k, v in docs.items()
                        }
                        content = self.doc_manager.dump_data(final_data)
                        tm.add_write(str(rel_doc_path), content)
~~~~~

### 下一步建议
我们已经完成了对 `Check` 流程的重构。现在，`pump` 和 `check` 两个核心命令都通过 `LockSession` 以统一和事务化的方式管理状态。下一步是运行完整的测试套件，验证我们的重构是否引入了回归问题，并修复因新架构而暴露出的任何测试逻辑缺陷。
