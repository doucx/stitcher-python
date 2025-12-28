好的，我们正式进入第三阶段，也是最激动人心的部分：将所有设计落地，构建一个流畅、智能的交互式命令行体验。

根据我们之前的讨论，为了实现支持撤销和导航的“问卷式”交互，我们需要先对应用层进行一次精微的重构，使其能够一次性找出所有待处理的冲突，然后再将它们整体交给交互层处理。

这是本次任务的最终计划。

## [WIP] feat: 实现交互式检查CLI与应用层重构

### 用户需求
完成“交互式引导”功能的最后阶段。这要求在 CLI 中实现一个功能完备的交互式“向导”，支持单键输入、撤销和粘性默认值，并对 `StitcherApp` 进行必要的重构以支持这种高级交互模式。

### 评论
这是整个功能的“最后一公里”，是用户体验设计的核心。我们将应用层 (`StitcherApp`) 的职责进一步提纯为“分析”和“执行”，而将所有复杂的交互状态管理（如导航、撤销）完全封装在表现层 (`TyperInteractionHandler`) 中。这种清晰的职责划分是构建健壮、可维护软件的典范。最终，我们将交付一个不仅功能强大，而且使用起来极为高效和人性化的工具。

### 目标
1.  **应用层重构**:
    *   修改 `_analyze_file` 方法，使其**只分析不修改**，返回一个包含所有待处理冲突的分析结果。
    *   修改 `run_check` 方法，使其先收集所有模块的分析结果，然后将所有冲突一次性交给 `InteractionHandler` 处理，最后根据返回的 `ResolutionPlan` 执行变更。
2.  **协议更新**:
    *   更新 `InteractionHandler` 协议，用一个更强大的 `process_interactive_session` 方法取代原有的 `ask_resolution`。
3.  **CLI 实现**:
    *   在 `stitcher-cli` 中创建 `TyperInteractionHandler`。
    *   在其中实现完整的“问卷式”交互循环，处理导航（回车）、撤销（`z`）、选择（`f`, `r`, `s`）和中止（`a`）。
    *   在 `check` 命令中检测 TTY 环境，并在交互模式下注入 `TyperInteractionHandler` 实例。

### 基本原理
我们采用“分析-决策-执行”三步走的模式。`StitcherApp` 负责“分析”并生成问题列表。`TyperInteractionHandler` 负责主持“决策”过程，引导用户填写“问卷”并生成最终的计划。最后，`StitcherApp` 再负责“执行”这个由用户确认过的计划。这个模型将复杂的交互逻辑与核心业务逻辑完美解耦，确保了各层职责的单一性。

### 标签
#intent/build #intent/refine #flow/ready #priority/high #comp/application #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/interactive-check #task/action/implementation #task/state/end

---

### Script

#### Acts 1: 更新应用层协议 (`protocols.py`)

我们将用一个能处理整个会话的方法来更新 `InteractionHandler` 协议。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/protocols.py
~~~~~
~~~~~python.old
class InteractionHandler(Protocol):
    """Protocol for handling user interactions during a check."""

    def ask_resolution(self, context: InteractionContext) -> ResolutionAction:
        """
        Asks the user (or a non-interactive policy) how to resolve a conflict.
        """
        ...
~~~~~
~~~~~python.new
class InteractionHandler(Protocol):
    """Protocol for handling user interactions during a check."""

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        """
        Processes a list of conflicts, returning a list of chosen actions.
        The length of the returned list MUST match the input list.
        """
        ...
~~~~~

#### Acts 2: 更新 `NoOpInteractionHandler`

现在我们更新默认的 Handler 以符合新协议。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/handlers/noop_handler.py
~~~~~
~~~~~python.old
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType


class NoOpInteractionHandler(InteractionHandler):
    """
    A non-interactive handler that resolves conflicts based on CLI flags.
    This preserves the original behavior for CI/CD environments.
    """

    def __init__(self, force_relink: bool = False, reconcile: bool = False):
        self._force_relink = force_relink
        self._reconcile = reconcile

    def ask_resolution(self, context: InteractionContext) -> ResolutionAction:
        if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
            if self._force_relink:
                return ResolutionAction.RELINK
        elif context.conflict_type == ConflictType.CO_EVOLUTION:
            if self._reconcile:
                return ResolutionAction.RECONCILE
        return ResolutionAction.SKIP
~~~~~
~~~~~python.new
from typing import List
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType


class NoOpInteractionHandler(InteractionHandler):
    """
    A non-interactive handler that resolves conflicts based on CLI flags.
    This preserves the original behavior for CI/CD environments.
    """

    def __init__(self, force_relink: bool = False, reconcile: bool = False):
        self._force_relink = force_relink
        self._reconcile = reconcile

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        actions: List[ResolutionAction] = []
        for context in contexts:
            action = ResolutionAction.SKIP
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                if self._force_relink:
                    action = ResolutionAction.RELINK
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
                if self._reconcile:
                    action = ResolutionAction.RECONCILE
            actions.append(action)
        return actions
~~~~~

#### Acts 3: 重构 `StitcherApp` 核心逻辑 (`core.py`)

这是本次重构的核心，我们将 `_analyze_file` 和 `run_check` 改为新的工作模式。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def _analyze_file(
        self, module: ModuleDef, handler: InteractionHandler
    ) -> FileCheckResult:
        result = FileCheckResult(path=module.file_path)

        # 1. Content Checks
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            if doc_issues["missing"]:
                result.warnings["missing"].extend(doc_issues["missing"])
            if doc_issues["redundant"]:
                result.warnings["redundant"].extend(doc_issues["redundant"])
            if doc_issues["pending"]:
                result.errors["pending"].extend(doc_issues["pending"])
            if doc_issues["conflict"]:
                result.errors["conflict"].extend(doc_issues["conflict"])
            if doc_issues["extra"]:
                result.errors["extra"].extend(doc_issues["extra"])

        # 2. State Machine Checks
        doc_path = (self.root_path / module.file_path).with_suffix(".stitcher.yaml")
        is_tracked = doc_path.exists()

        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(
            module
        )
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = copy.deepcopy(stored_hashes_map)

        all_fqns = set(current_code_structure_map.keys()) | set(
            stored_hashes_map.keys()
        )

        for fqn in sorted(list(all_fqns)):
            current_code_structure_hash = current_code_structure_map.get(fqn)
            current_yaml_content_hash = current_yaml_content_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            baseline_code_structure_hash = stored.get("baseline_code_structure_hash")
            baseline_yaml_content_hash = stored.get("baseline_yaml_content_hash")

            if not current_code_structure_hash and baseline_code_structure_hash:
                if fqn in new_hashes_map:
                    new_hashes_map.pop(fqn, None)
                continue

            if current_code_structure_hash and not baseline_code_structure_hash:
                if is_tracked:
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                continue

            code_structure_matches = (
                current_code_structure_hash == baseline_code_structure_hash
            )
            yaml_content_matches = (
                current_yaml_content_hash == baseline_yaml_content_hash
            )

            if code_structure_matches and yaml_content_matches:
                pass
            elif code_structure_matches and not yaml_content_matches:
                result.infos["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["baseline_yaml_content_hash"] = (
                        current_yaml_content_hash
                    )
                result.auto_reconciled_count += 1
            elif not code_structure_matches and yaml_content_matches:
                context = InteractionContext(
                    file_path=module.file_path,
                    fqn=fqn,
                    conflict_type=ConflictType.SIGNATURE_DRIFT,
                )
                action = handler.ask_resolution(context)
                if action == ResolutionAction.RELINK:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["baseline_code_structure_hash"] = (
                            current_code_structure_hash
                        )
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not code_structure_matches and not yaml_content_matches:
                context = InteractionContext(
                    file_path=module.file_path,
                    fqn=fqn,
                    conflict_type=ConflictType.CO_EVOLUTION,
                )
                action = handler.ask_resolution(context)
                if action == ResolutionAction.RECONCILE:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                else:
                    result.errors["co_evolution"].append(fqn)

        if not is_tracked and module.is_documentable():
            undocumented = module.get_undocumented_public_keys()
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        if new_hashes_map != stored_hashes_map:
            self.sig_manager.save_composite_hashes(module, new_hashes_map)

        return result

    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        handler = self.interaction_handler or NoOpInteractionHandler(
            force_relink=force_relink, reconcile=reconcile
        )

        configs, _ = load_config_from_path(self.root_path)
        global_failed_files = 0
        global_warnings_files = 0
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            for module in modules:
                res = self._analyze_file(module, handler)
                if res.is_clean:
                    if res.auto_reconciled_count > 0:
                        bus.info(
                            L.check.state.auto_reconciled,
                            count=res.auto_reconciled_count,
                            path=res.path,
                        )
                    for key in sorted(res.infos["doc_improvement"]):
                        bus.info(L.check.state.doc_updated, key=key)
                    continue

                if res.reconciled_count > 0:
                    for key in res.reconciled.get("force_relink", []):
                        bus.success(L.check.state.relinked, key=key, path=res.path)
                    for key in res.reconciled.get("reconcile", []):
                        bus.success(L.check.state.reconciled, key=key, path=res.path)
                if res.auto_reconciled_count > 0:
                    bus.info(
                        L.check.state.auto_reconciled,
                        count=res.auto_reconciled_count,
                        path=res.path,
                    )

                if res.error_count > 0:
                    global_failed_files += 1
                    bus.error(L.check.file.fail, path=res.path, count=res.error_count)
                elif res.warning_count > 0:
                    global_warnings_files += 1
                    bus.warning(
                        L.check.file.warn, path=res.path, count=res.warning_count
                    )

                # Report Specific Issues
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

                for key in sorted(res.infos["doc_improvement"]):
                    bus.info(L.check.state.doc_updated, key=key)

                if "untracked_detailed" in res.warnings:
                    keys = res.warnings["untracked_detailed"]
                    bus.warning(
                        L.check.file.untracked_with_details,
                        path=res.path,
                        count=len(keys),
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
~~~~~python.new
    def _analyze_file(self, module: ModuleDef) -> tuple[FileCheckResult, list[InteractionContext]]:
        result = FileCheckResult(path=module.file_path)
        unresolved_conflicts: list[InteractionContext] = []

        # Content checks (unchanged)
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            result.warnings["missing"].extend(doc_issues["missing"])
            result.warnings["redundant"].extend(doc_issues["redundant"])
            result.errors["pending"].extend(doc_issues["pending"])
            result.errors["conflict"].extend(doc_issues["conflict"])
            result.errors["extra"].extend(doc_issues["extra"])

        # State machine analysis
        is_tracked = (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists()
        current_code_map = self.sig_manager.compute_code_structure_hashes(module)
        current_yaml_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)

        all_fqns = set(current_code_map.keys()) | set(stored_hashes_map.keys())

        for fqn in sorted(list(all_fqns)):
            code_hash = current_code_map.get(fqn)
            yaml_hash = current_yaml_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            baseline_code_hash = stored.get("baseline_code_structure_hash")
            baseline_yaml_hash = stored.get("baseline_yaml_content_hash")

            if not code_hash and baseline_code_hash: # Extra
                continue
            if code_hash and not baseline_code_hash: # New
                continue
                
            code_matches = code_hash == baseline_code_hash
            yaml_matches = yaml_hash == baseline_yaml_hash

            if code_matches and not yaml_matches: # Doc improvement
                result.infos["doc_improvement"].append(fqn)
            elif not code_matches and yaml_matches: # Signature Drift
                unresolved_conflicts.append(
                    InteractionContext(module.file_path, fqn, ConflictType.SIGNATURE_DRIFT)
                )
            elif not code_matches and not yaml_matches: # Co-evolution
                unresolved_conflicts.append(
                    InteractionContext(module.file_path, fqn, ConflictType.CO_EVOLUTION)
                )
        
        # Untracked file check
        if not is_tracked and module.is_documentable():
            undocumented = module.get_undocumented_public_keys()
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        return result, unresolved_conflicts

    def _apply_resolutions(self, resolutions: dict[str, list[tuple[str, ResolutionAction]]]):
        # This is the execution phase. We now write to files.
        for file_path, fqn_actions in resolutions.items():
            module_def = ModuleDef(file_path=file_path) # Minimal def for path logic
            stored_hashes = self.sig_manager.load_composite_hashes(module_def)
            new_hashes = copy.deepcopy(stored_hashes)
            
            # We need the current hashes again to apply changes
            full_module_def = parse_source_code((self.root_path / file_path).read_text("utf-8"), file_path)
            current_code_map = self.sig_manager.compute_code_structure_hashes(full_module_def)
            current_yaml_map = self.doc_manager.compute_yaml_content_hashes(full_module_def)

            for fqn, action in fqn_actions:
                if action == ResolutionAction.RELINK:
                    if fqn in new_hashes:
                        new_hashes[fqn]["baseline_code_structure_hash"] = current_code_map.get(fqn)
                elif action == ResolutionAction.RECONCILE:
                    if fqn in new_hashes:
                        new_hashes[fqn]["baseline_code_structure_hash"] = current_code_map.get(fqn)
                        new_hashes[fqn]["baseline_yaml_content_hash"] = current_yaml_map.get(fqn)

            if new_hashes != stored_hashes:
                self.sig_manager.save_composite_hashes(module_def, new_hashes)

    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        configs, _ = load_config_from_path(self.root_path)
        
        all_results: list[FileCheckResult] = []
        all_conflicts: list[InteractionContext] = []

        # 1. Analysis Phase
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            for module in modules:
                result, conflicts = self._analyze_file(module)
                all_results.append(result)
                all_conflicts.extend(conflicts)

        # 2. Interactive Resolution Phase
        if all_conflicts and self.interaction_handler:
            chosen_actions = self.interaction_handler.process_interactive_session(all_conflicts)
            
            resolutions_by_file = defaultdict(list)
            reconciled_results = defaultdict(lambda: defaultdict(list))

            for i, context in enumerate(all_conflicts):
                action = chosen_actions[i]
                if action == ResolutionAction.RELINK:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["force_relink"].append(context.fqn)
                elif action == ResolutionAction.RECONCILE:
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path]["reconcile"].append(context.fqn)
                elif action == ResolutionAction.SKIP:
                    # Find the corresponding result and add the error
                    for res in all_results:
                        if res.path == context.file_path:
                            error_key = "signature_drift" if context.conflict_type == ConflictType.SIGNATURE_DRIFT else "co_evolution"
                            res.errors[error_key].append(context.fqn)
                            break
                elif action == ResolutionAction.ABORT:
                    bus.warning(L.strip.run.aborted) # Re-use abort message for now
                    return False
            
            # 3. Execution Phase
            self._apply_resolutions(dict(resolutions_by_file))
            
            # Update results with reconciled items for reporting
            for res in all_results:
                if res.path in reconciled_results:
                    res.reconciled["force_relink"] = reconciled_results[res.path]["force_relink"]
                    res.reconciled["reconcile"] = reconciled_results[res.path]["reconcile"]
        else: # Non-interactive mode
            handler = NoOpInteractionHandler(force_relink, reconcile)
            chosen_actions = handler.process_interactive_session(all_conflicts)
            # Logic is similar to above, can be refactored later
            resolutions_by_file = defaultdict(list)
            reconciled_results = defaultdict(lambda: defaultdict(list))
            for i, context in enumerate(all_conflicts):
                action = chosen_actions[i]
                if action != ResolutionAction.SKIP:
                    key = "force_relink" if action == ResolutionAction.RELINK else "reconcile"
                    resolutions_by_file[context.file_path].append((context.fqn, action))
                    reconciled_results[context.file_path][key].append(context.fqn)
                else:
                     for res in all_results:
                        if res.path == context.file_path:
                            error_key = "signature_drift" if context.conflict_type == ConflictType.SIGNATURE_DRIFT else "co_evolution"
                            res.errors[error_key].append(context.fqn)
            self._apply_resolutions(dict(resolutions_by_file))
            for res in all_results:
                if res.path in reconciled_results:
                    res.reconciled["force_relink"] = reconciled_results[res.path]["force_relink"]
                    res.reconciled["reconcile"] = reconciled_results[res.path]["reconcile"]

        # 4. Reporting Phase
        global_failed_files = 0
        global_warnings_files = 0
        for res in all_results:
            if res.is_clean:
                continue

            if res.reconciled_count > 0:
                for key in res.reconciled.get("force_relink", []):
                    bus.success(L.check.state.relinked, key=key, path=res.path)
                for key in res.reconciled.get("reconcile", []):
                    bus.success(L.check.state.reconciled, key=key, path=res.path)

            if res.error_count > 0:
                global_failed_files += 1
                bus.error(L.check.file.fail, path=res.path, count=res.error_count)
            elif res.warning_count > 0:
                global_warnings_files += 1
                bus.warning(L.check.file.warn, path=res.path, count=res.warning_count)

            # Report Specific Issues (same as before)
            for key in sorted(res.errors["extra"]): bus.error(L.check.issue.extra, key=key)
            for key in sorted(res.errors["signature_drift"]): bus.error(L.check.state.signature_drift, key=key)
            for key in sorted(res.errors["co_evolution"]): bus.error(L.check.state.co_evolution, key=key)
            for key in sorted(res.errors["conflict"]): bus.error(L.check.issue.conflict, key=key)
            for key in sorted(res.errors["pending"]): bus.error(L.check.issue.pending, key=key)
            for key in sorted(res.warnings["missing"]): bus.warning(L.check.issue.missing, key=key)
            for key in sorted(res.warnings["redundant"]): bus.warning(L.check.issue.redundant, key=key)
            for key in sorted(res.warnings["untracked_key"]): bus.warning(L.check.state.untracked_code, key=key)
            if "untracked_detailed" in res.warnings:
                keys = res.warnings["untracked_detailed"]
                bus.warning(L.check.file.untracked_with_details, path=res.path, count=len(keys))
                for key in sorted(keys): bus.warning(L.check.issue.untracked_missing_key, key=key)
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

#### Acts 4: 实现 `TyperInteractionHandler`

现在我们在 CLI 包中创建交互逻辑。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/handlers.py
~~~~~
~~~~~python
import sys
from typing import List, Optional
import click
import typer

from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType

class TyperInteractionHandler(InteractionHandler):
    """An interactive handler using Typer/Click for user prompts."""

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        if not sys.stdin.isatty():
            # Should not happen if logic is correct, but as a safeguard
            return [ResolutionAction.SKIP] * len(contexts)

        typer.echo(
            f"Found {len(contexts)} conflicts. Please review them one by one."
        )
        
        resolutions: List[Optional[ResolutionAction]] = [None] * len(contexts)
        current_index = 0
        last_choice: Optional[ResolutionAction] = None

        while current_index < len(contexts):
            context = contexts[current_index]
            
            # Determine default choice
            recorded_choice = resolutions[current_index]
            default_choice = recorded_choice or last_choice or ResolutionAction.ABORT

            # --- Display Conflict ---
            typer.echo("\n" + ("-" * 20))
            typer.secho(
                f"Conflict {current_index + 1}/{len(contexts)} in {context.file_path}",
                fg=typer.colors.CYAN,
            )
            typer.secho(f"  Symbol: {context.fqn}", bold=True)
            
            # --- Build and Display Menu ---
            menu = []
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                typer.secho("  Reason: Signature has changed, but docs have not (Signature Drift).")
                menu.append(("[F]orce-relink", ResolutionAction.RELINK, "Force-relink new signature with old docs."))
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
                typer.secho("  Reason: Both signature and docs have changed (Co-evolution).")
                menu.append(("[R]econcile", ResolutionAction.RECONCILE, "Accept both changes as the new correct state."))
            
            menu.append(("[S]kip", ResolutionAction.SKIP, "Skip this conflict for now."))
            menu.append(("[A]bort", ResolutionAction.ABORT, "Abort the entire check process."))
            menu.append(("[Z]Undo", "UNDO", "Go back to the previous conflict."))
            
            typer.echo("  Please choose an action:")
            for option, action, desc in menu:
                is_default = action == default_choice
                prefix = "> " if is_default else "  "
                typer.secho(f"  {prefix}{option:<15} - {desc}", bold=is_default)
            
            # --- Get Input ---
            char = click.getchar().lower()

            # --- Process Input ---
            if char == '\r' or char == '\n': # Enter
                action = default_choice
            elif char == 'f' and any(a == ResolutionAction.RELINK for _, a, _ in menu):
                action = ResolutionAction.RELINK
            elif char == 'r' and any(a == ResolutionAction.RECONCILE for _, a, _ in menu):
                action = ResolutionAction.RECONCILE
            elif char == 's':
                action = ResolutionAction.SKIP
            elif char == 'a':
                action = ResolutionAction.ABORT
            elif char == 'z':
                if current_index > 0:
                    current_index -= 1
                else:
                    typer.secho("Already at the first conflict.", fg=typer.colors.YELLOW)
                continue # loop to re-display previous conflict
            else:
                typer.secho("Invalid choice, please try again.", fg=typer.colors.RED)
                continue

            resolutions[current_index] = action
            if action != ResolutionAction.ABORT:
                last_choice = action # Update sticky default
            
            if action == ResolutionAction.ABORT:
                # Fill remaining with ABORT to signal cancellation
                for i in range(len(resolutions)):
                    if resolutions[i] is None:
                        resolutions[i] = ResolutionAction.ABORT
                break

            current_index += 1

        # Fill any remaining unvisited with SKIP
        final_actions = [res or ResolutionAction.SKIP for res in resolutions]
        
        # Final confirmation could be added here later
        
        return final_actions
~~~~~

#### Acts 5: 注入 Handler 到 CLI (`main.py`)

最后一步，我们将所有东西连接起来。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
from pathlib import Path
import typer

from stitcher.app import StitcherApp
from stitcher.common import bus, stitcher_nexus as nexus
from needle.pointer import L
from .rendering import CliRenderer
~~~~~
~~~~~python.new
import sys
from pathlib import Path
import typer

from stitcher.app import StitcherApp
from stitcher.common import bus, stitcher_nexus as nexus
from needle.pointer import L
from .rendering import CliRenderer
from .handlers import TyperInteractionHandler
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
@app.command(help=nexus.get(L.cli.command.check.help))
def check(
    force_relink: bool = typer.Option(
        False,
        "--force-relink",
        help="For 'Signature Drift' errors, forces the new signature to be linked with the existing, unchanged documentation.",
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help="For 'Co-evolution' errors, accepts both signature and documentation changes as the new correct state.",
    ),
):
    if force_relink and reconcile:
        bus.error("Cannot use --force-relink and --reconcile simultaneously.")
        raise typer.Exit(code=1)

    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    success = app_instance.run_check(force_relink=force_relink, reconcile=reconcile)
    if not success:
        raise typer.Exit(code=1)
~~~~~
~~~~~python.new
@app.command(help=nexus.get(L.cli.command.check.help))
def check(
    force_relink: bool = typer.Option(
        False,
        "--force-relink",
        help="[Non-interactive] For 'Signature Drift' errors, forces relinking.",
    ),
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help="[Non-interactive] For 'Co-evolution' errors, accepts both changes.",
    ),
):
    if force_relink and reconcile:
        bus.error("Cannot use --force-relink and --reconcile simultaneously.")
        raise typer.Exit(code=1)

    project_root = Path.cwd()
    
    handler = None
    if sys.stdin.isatty() and not force_relink and not reconcile:
        handler = TyperInteractionHandler()

    app_instance = StitcherApp(root_path=project_root, interaction_handler=handler)
    success = app_instance.run_check(force_relink=force_relink, reconcile=reconcile)
    if not success:
        raise typer.Exit(code=1)
~~~~~
