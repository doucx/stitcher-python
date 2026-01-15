我们正在修复由于 `LockSession` 状态污染、`PumpExecutor` 指纹更新逻辑缺失以及 `CheckResolver` 绕过中央 Session 管理导致的集成测试失败。

## [WIP] fix: 修复 LockSession 状态污染与核心逻辑缺陷

### 错误分析

1.  **状态污染 (`test_check_regression`)**: `StitcherApp` 在测试中是重用的。`run_init` 将 Lock 数据加载到内存中。随后的 `run_check` 虽然更新了磁盘，但 `StitcherApp` 在命令结束时调用 `lock_session.commit_to_transaction()` 将内存中的**旧数据**重新刷回了磁盘，覆盖了正确的更新。
2.  **指纹更新缺失 (`test_init_sidecar_idempotency`)**: 在 `init` (即 `pump --reconcile`) 且选择保留现有 YAML 时，系统未将该 YAML 内容记录为新的基线，导致下一次检查时仍被视为冲突。
3.  **持久化不一致 (`auto_reconcile_docs`)**: `CheckResolver` 目前直接读写磁盘文件，绕过了 `LockSession`。这不仅导致了逻辑冗余，更因为命令结束时的 `lock_session.commit()` 会覆盖它的操作。
4.  **测试消息匹配失败 (`test_check_signatures`)**: `run_init` 现在委托给 `run_pump` 执行，因此发出的是 `pump.run.complete` 消息而非旧的 `init.run.complete`。

### 用户需求

修复所有集成测试失败，确保系统在复杂状态切换下的确定性。

### 评论

这次修复的重点是建立严格的生命周期管理。`LockSession` 必须作为一个“工作单元”缓存，在每次命令执行前后保持清晰的边界。

### 目标

1.  在 `LockSession` 中引入 `clear()` 方法，并在 `StitcherApp` 命令入口强制执行。
2.  修正 `PumpExecutor`，确保在任何逻辑同步动作（包括调和）发生时更新指纹。
3.  重构 `CheckResolver` 自动调和逻辑，使其成为 `LockSession` 的参与者而非破坏者。
4.  对齐测试断言与新的命令输出。

### 基本原理

遵循 **SSoT (Single Source of Truth)** 原则。所有的 Lock 操作必须汇聚到 `LockSession`。同时，根据 **原子性原则**，命令执行结束后必须清理临时状态，防止污染。

### 标签

#intent/fix #flow/ready #priority/high #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/runtime #task/object/state-management #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 为 LockSession 添加生命周期管理方法

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/lock_session.py
~~~~~
~~~~~python.old
            except ValueError:
                # Fallback/Safety: Should not happen if pkg_root is inside root_path
                pass
~~~~~
~~~~~python.new
            except ValueError:
                # Fallback/Safety: Should not happen if pkg_root is inside root_path
                pass

    def clear(self):
        """
        Clears the internal buffer. Should be called at the end of a command execution
        to prevent stale state from polluting subsequent runs.
        """
        self._locks.clear()
~~~~~

#### Acts 2: 在 StitcherApp 核心入口实施清理

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        # 8. Commit Lock and Doc changes
        self.lock_session.commit_to_transaction(tm)
        tm.commit()

        # 9. Final Report
        report_success = self.check_runner.report(all_results, arch_violations)
        return report_success and not self.scanner.had_errors

    def run_pump(
        self,
        strip: bool = False,
        force: bool = False,
        reconcile: bool = False,
        dry_run: bool = False,
    ) -> PumpResult:
        self.ensure_index_fresh()
        bus.info(L.pump.run.start)
        configs, _ = self._load_configs()
        tm = TransactionManager(self.root_path, dry_run=dry_run)

        self.scanner.had_errors = False
        global_success = True
        all_redundant: List[Path] = []

        with self.db_manager.session():
            for config in configs:
                modules = self._configure_and_scan(config)
                if not modules:
                    continue

                result = self.pump_runner.run_batch(
                    modules, config, tm, strip, force, reconcile
                )
                if not result.success:
                    global_success = False
                all_redundant.extend(result.redundant_files)

        # Commit all lock changes buffered in the session to the transaction
        self.lock_session.commit_to_transaction(tm)

        if self.scanner.had_errors:
            global_success = False

        tm.commit()
        return PumpResult(success=global_success, redundant_files=all_redundant)
~~~~~
~~~~~python.new
        try:
            # 8. Commit Lock and Doc changes
            self.lock_session.commit_to_transaction(tm)
            tm.commit()

            # 9. Final Report
            report_success = self.check_runner.report(all_results, arch_violations)
            return report_success and not self.scanner.had_errors
        finally:
            self.lock_session.clear()

    def run_pump(
        self,
        strip: bool = False,
        force: bool = False,
        reconcile: bool = False,
        dry_run: bool = False,
    ) -> PumpResult:
        self.ensure_index_fresh()
        bus.info(L.pump.run.start)
        configs, _ = self._load_configs()
        tm = TransactionManager(self.root_path, dry_run=dry_run)

        self.scanner.had_errors = False
        global_success = True
        all_redundant: List[Path] = []

        try:
            with self.db_manager.session():
                for config in configs:
                    modules = self._configure_and_scan(config)
                    if not modules:
                        continue

                    result = self.pump_runner.run_batch(
                        modules, config, tm, strip, force, reconcile
                    )
                    if not result.success:
                        global_success = False
                    all_redundant.extend(result.redundant_files)

            # Commit all lock changes buffered in the session to the transaction
            self.lock_session.commit_to_transaction(tm)

            if self.scanner.had_errors:
                global_success = False

            tm.commit()
            return PumpResult(success=global_success, redundant_files=all_redundant)
        finally:
            self.lock_session.clear()
~~~~~

#### Acts 3: 修正 PumpExecutor 的指纹生成策略

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
~~~~~
~~~~~python.old
            if decision != ResolutionAction.SKIP:
                exec_plan.update_code_fingerprint = True
                if decision == ResolutionAction.HYDRATE_OVERWRITE or (
                    decision is None and has_source_doc
                ):
                    exec_plan.hydrate_yaml = True
                    exec_plan.update_doc_fingerprint = True
                if strip_requested and (
                    decision == ResolutionAction.HYDRATE_OVERWRITE
                    or decision == ResolutionAction.HYDRATE_KEEP_EXISTING
                    or (decision is None and has_source_doc)
                ):
~~~~~
~~~~~python.new
            if decision != ResolutionAction.SKIP:
                exec_plan.update_code_fingerprint = True
                if (
                    decision == ResolutionAction.HYDRATE_OVERWRITE
                    or (decision is None and has_source_doc)
                    or decision == ResolutionAction.HYDRATE_KEEP_EXISTING
                ):
                    # We must update doc fingerprint even if we don't write to YAML (reconcile)
                    exec_plan.update_doc_fingerprint = True

                if (
                    decision == ResolutionAction.HYDRATE_OVERWRITE
                    or (decision is None and has_source_doc)
                ):
                    exec_plan.hydrate_yaml = True

                if strip_requested and (
                    decision == ResolutionAction.HYDRATE_OVERWRITE
                    or decision == ResolutionAction.HYDRATE_KEEP_EXISTING
                    or (decision is None and has_source_doc)
                ):
~~~~~

#### Acts 4: 重构 Check 自动调和逻辑以消除冗余和竞态

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

from stitcher.common import bus
from needle.pointer import L, SemanticPointer
from stitcher.spec import (
    ModuleDef,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
    DocstringIR,
)
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

    def _compute_fingerprints(self, module: ModuleDef) -> Dict[str, Fingerprint]:
        fingerprints: Dict[str, Fingerprint] = {}
        for func in module.functions:
            fingerprints[func.name] = self.fingerprint_strategy.compute(func)
        for cls in module.classes:
            for method in cls.methods:
                fqn = f"{cls.name}.{method.name}"
                fingerprints[fqn] = self.fingerprint_strategy.compute(method)
        return fingerprints

    def auto_reconcile_docs(
        self, results: List[FileCheckResult], modules: List[ModuleDef]
    ):
        """
        Automatically reconciles documentation improvements by updating the lock session.
        This handles cases where the doc IR changed in YAML but is considered an 'improvement'
        rather than a conflict (e.g., when YAML is newer but code has no doc).
        """
        for res in results:
            doc_update_violations = [
                v for v in res.info_violations if v.kind == L.check.state.doc_updated
            ]
            if not doc_update_violations:
                continue

            module_def = next((m for m in modules if m.file_path == res.path), None)
            if not module_def:
                continue

            # Load current IRs from sidecar to get the new baseline for the lock
            current_docs = self.doc_manager.load_docs_for_module(module_def)

            for violation in doc_update_violations:
                fqn = violation.fqn
                if fqn in current_docs:
                    # Update lock session with new Doc baseline
                    self.lock_session.record_fresh_state(
                        module_def, fqn, doc_ir=current_docs[fqn]
                    )

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

    def _update_results(
        self,
        results: List[FileCheckResult],
        resolutions: Dict[str, List[tuple[InteractionContext, ResolutionAction]]],
    ):
        for res in results:
            if res.path not in resolutions:
                continue

            resolved_fqns_by_kind: Dict[SemanticPointer, set] = defaultdict(set)
            for context, _ in resolutions[res.path]:
                resolved_fqns_by_kind[context.violation_type].add(context.fqn)

            remaining_violations = []
            for violation in res.violations:
                resolved_fqns = resolved_fqns_by_kind.get(violation.kind, set())
                if violation.fqn in resolved_fqns:
                    res.reconciled.append(violation)
                else:
                    remaining_violations.append(violation)
            res.violations = remaining_violations

    def _apply_resolutions(
        self,
        resolutions: dict[str, list[tuple[InteractionContext, ResolutionAction]]],
        tm: TransactionManager,
    ):
        for file_path, context_actions in resolutions.items():
            abs_path = self.root_path / file_path

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

            full_module_def: ModuleDef | None = None
            computed_fingerprints: dict[str, Fingerprint] = {}
            current_doc_irs: dict[str, "DocstringIR"] = {}

            if needs_parsing:
                full_module_def = self.parser.parse(
                    abs_path.read_text("utf-8"), file_path
                )
                computed_fingerprints = self._compute_fingerprints(full_module_def)
                current_doc_irs = self.doc_manager.load_docs_for_module(full_module_def)

            fqns_to_purge_from_doc: list[str] = []
            for context, action in context_actions:
                fqn = context.fqn
                module_stub = full_module_def or ModuleDef(file_path=file_path)

                if action == ResolutionAction.RELINK:
                    code_fp = computed_fingerprints.get(fqn)
                    if code_fp:
                        self.lock_session.record_relink(module_stub, fqn, code_fp)

                elif (
                    action
                    in [
                        ResolutionAction.RECONCILE,
                        ResolutionAction.HYDRATE_OVERWRITE,
                        ResolutionAction.HYDRATE_KEEP_EXISTING,
                    ]
                ):
                    self.lock_session.record_fresh_state(
                        module_stub,
                        fqn,
                        doc_ir=current_doc_irs.get(fqn),
                        code_fingerprint=computed_fingerprints.get(fqn),
                    )

                elif action == ResolutionAction.PURGE_DOC:
                    fqns_to_purge_from_doc.append(fqn)
                    self.lock_session.record_purge(module_stub, fqn)

            if fqns_to_purge_from_doc:
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

    def reformat_all(self, modules: List[ModuleDef]):
        bus.info(L.check.run.reformatting)
        for module in modules:
            self.doc_manager.reformat_docs_for_module(module)
~~~~~

#### Acts 5: 对齐测试断言

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_signatures.py
~~~~~
~~~~~python.old
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    _assert_no_errors(spy_bus)
    spy_bus.assert_id_called(L.init.run.complete, level="success")
~~~~~
~~~~~python.new
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    _assert_no_errors(spy_bus)
    # run_init is an alias for pump --reconcile, so it emits pump messages
    spy_bus.assert_id_called(L.pump.run.complete, level="success")
~~~~~

### 下一步建议

执行测试以验证修复结果。如果所有测试通过，则此修复方案已成功将状态管理带回正确轨道。建议下一步审查 `CoverageRunner` 是否也需要类似的 Session 生命周期保护。
