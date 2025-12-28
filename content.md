简要回答：
这是一个极好的 DX 改进。通过将交互式引导模型泛化并应用于 `hydrate` 命令，我们能够显著减少用户在处理文档冲突时的认知负荷和操作步骤。我将按照提案，对 Spec、Service、Application 和 CLI 层进行必要的重构和扩展，以实现这一统一的交互模型。

## [WIP] feat: 泛化交互模型并集成至 hydrate 命令

### 用户需求
目前 `hydrate` 命令在遇到文档内容冲突时（代码中的文档与 YAML 中的文档不一致），会报错并提示用户使用 `--force` 或 `--reconcile` 标志重新运行。用户希望能够在交互式终端中直接通过按键选择解决方案（覆盖或保留），类似于 `check` 命令的交互体验。

### 评论
该计划实现了“一次执行，即时解决”的工作流，符合现代 CLI 工具的最佳实践。通过统一 `check` 和 `hydrate` 的交互模型，我们避免了代码重复，并为未来更多需要用户决策的命令奠定了基础。

### 目标
1.  扩展 `stitcher-spec` 中的冲突类型和解决动作枚举，支持 hydration 场景。
2.  重构 `DocumentManager.hydrate_module` 以支持 `dry_run` 模式和细粒度的冲突解决策略。
3.  升级 `StitcherApp.run_hydrate`，引入“分析-决策-执行”三阶段处理流程。
4.  扩展 `TyperInteractionHandler`，实现针对 `hydrate` 冲突的交互菜单。
5.  确保在非交互模式下（NoOpHandler），CLI 标志（`--force`, `--reconcile`）依然能正确驱动行为。

### 基本原理
我们将交互逻辑从具体的命令中剥离出来，抽象为一个通用的“冲突-解决”循环。
1.  **模型扩展**: 定义新的 `ConflictType.DOC_CONTENT_CONFLICT` 和 `ResolutionAction.HYDRATE_*`，明确表达 hydration 领域的语义。
2.  **服务层增强**: `DocumentManager` 需要能力来“预演”补水过程（dry_run），以便在产生副作用前收集所有冲突；同时需要支持传入一个 `resolution_map`，以便在执行阶段对每个 Key 应用用户的特定决策。
3.  **应用层编排**: `StitcherApp` 负责协调分析（调用 dry_run）、交互（调用 Handler）和执行（调用带 resolution_map 的 hydrate）三个步骤。
4.  **UI 适配**: `TyperInteractionHandler` 根据传入的冲突类型动态渲染不同的菜单，复用底层的输入捕获和循环逻辑。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #comp/runtime #concept/ui #scope/ux #task/domain/cli #task/object/interactive-mode #task/action/integration #task/state/begin

---

### Script

#### Acts 1: 扩展 Spec 模型

首先，我们在 `stitcher-spec` 中定义新的冲突类型和解决动作。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
class ConflictType(str, Enum):
    SIGNATURE_DRIFT = "SIGNATURE_DRIFT"
    CO_EVOLUTION = "CO_EVOLUTION"


class ResolutionAction(str, Enum):
    RELINK = "RELINK"
    RECONCILE = "RECONCILE"
    SKIP = "SKIP"
    ABORT = "ABORT"
~~~~~
~~~~~python.new
class ConflictType(str, Enum):
    SIGNATURE_DRIFT = "SIGNATURE_DRIFT"
    CO_EVOLUTION = "CO_EVOLUTION"
    DOC_CONTENT_CONFLICT = "DOC_CONTENT_CONFLICT"


class ResolutionAction(str, Enum):
    RELINK = "RELINK"
    RECONCILE = "RECONCILE"
    HYDRATE_OVERWRITE = "HYDRATE_OVERWRITE"  # Equivalent to --force (Code wins)
    HYDRATE_KEEP_EXISTING = "HYDRATE_KEEP_EXISTING"  # Equivalent to --reconcile (YAML wins)
    SKIP = "SKIP"
    ABORT = "ABORT"
~~~~~

#### Acts 2: 增强 DocumentManager

我们需要修改 `hydrate_module`，使其支持 `dry_run`（仅分析不写入）以及接收 `resolution_map`（针对特定 Key 的决策）。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
~~~~~
~~~~~python.old
    def hydrate_module(
        self, module: ModuleDef, force: bool = False, reconcile: bool = False
    ) -> Dict[str, Any]:
        source_docs = self.flatten_module_docs(module)
        if not source_docs:
            return {
                "success": True,
                "updated_keys": [],
                "conflicts": [],
                "reconciled_keys": [],
            }
        yaml_docs = self.load_docs_for_module(module)
        updated_keys = []
        conflicts = []
        reconciled_keys = []
        new_yaml_docs = yaml_docs.copy()

        for key, source_content in source_docs.items():
            if key not in yaml_docs:
                new_yaml_docs[key] = source_content
                updated_keys.append(key)
            elif yaml_docs[key] != source_content:
                if reconcile:
                    reconciled_keys.append(key)
                    continue
                elif force:
                    new_yaml_docs[key] = source_content
                    updated_keys.append(key)
                else:
                    conflicts.append(key)

        if conflicts:
            return {
                "success": False,
                "updated_keys": [],
                "conflicts": conflicts,
                "reconciled_keys": [],
            }

        if updated_keys:
            module_path = self.root_path / module.file_path
            output_path = module_path.with_suffix(".stitcher.yaml")
            self.adapter.save(output_path, new_yaml_docs)

        return {
            "success": True,
            "updated_keys": updated_keys,
            "conflicts": [],
            "reconciled_keys": reconciled_keys,
        }
~~~~~
~~~~~python.new
    def hydrate_module(
        self,
        module: ModuleDef,
        force: bool = False,
        reconcile: bool = False,
        resolution_map: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        # resolution_map: Dict[fqn, ResolutionAction]
        resolution_map = resolution_map or {}
        
        source_docs = self.flatten_module_docs(module)
        if not source_docs:
            return {
                "success": True,
                "updated_keys": [],
                "conflicts": [],
                "reconciled_keys": [],
            }
        yaml_docs = self.load_docs_for_module(module)
        updated_keys = []
        conflicts = []
        reconciled_keys = []
        new_yaml_docs = yaml_docs.copy()

        for key, source_content in source_docs.items():
            if key not in yaml_docs:
                new_yaml_docs[key] = source_content
                updated_keys.append(key)
            elif yaml_docs[key] != source_content:
                # Check for specific resolution first
                action = resolution_map.get(key)
                
                # Determine strategy
                should_force = force or (action == "HYDRATE_OVERWRITE")
                should_reconcile = reconcile or (action == "HYDRATE_KEEP_EXISTING")
                
                if should_reconcile:
                    reconciled_keys.append(key)
                    continue
                elif should_force:
                    new_yaml_docs[key] = source_content
                    updated_keys.append(key)
                else:
                    conflicts.append(key)

        if conflicts:
            return {
                "success": False,
                "updated_keys": [],
                "conflicts": conflicts,
                "reconciled_keys": [],
            }

        if updated_keys and not dry_run:
            module_path = self.root_path / module.file_path
            output_path = module_path.with_suffix(".stitcher.yaml")
            self.adapter.save(output_path, new_yaml_docs)

        return {
            "success": True,
            "updated_keys": updated_keys,
            "conflicts": [],
            "reconciled_keys": reconciled_keys,
        }
~~~~~

#### Acts 3: 更新 NoOpHandler

更新 `NoOpInteractionHandler` 以支持 hydrate 相关的逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/handlers/noop_handler.py
~~~~~
~~~~~python.old
class NoOpInteractionHandler(InteractionHandler):

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
~~~~~python.new
class NoOpInteractionHandler(InteractionHandler):

    def __init__(
        self,
        force_relink: bool = False,
        reconcile: bool = False,
        hydrate_force: bool = False,
        hydrate_reconcile: bool = False,
    ):
        self._force_relink = force_relink
        self._reconcile = reconcile  # For Check
        self._hydrate_force = hydrate_force
        self._hydrate_reconcile = hydrate_reconcile

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
            elif context.conflict_type == ConflictType.DOC_CONTENT_CONFLICT:
                if self._hydrate_force:
                    action = ResolutionAction.HYDRATE_OVERWRITE
                elif self._hydrate_reconcile:
                    action = ResolutionAction.HYDRATE_KEEP_EXISTING
            actions.append(action)
        return actions
~~~~~

#### Acts 4: 重构 StitcherApp.run_hydrate

实现“分析-决策-执行”三阶段。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_hydrate(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> bool:
        bus.info(L.hydrate.run.start)
        configs, _ = load_config_from_path(self.root_path)
        total_updated = 0
        total_conflicts = 0
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            files_to_strip = []
            for module in modules:
                result = self.doc_manager.hydrate_module(
                    module, force=force, reconcile=reconcile
                )
                if not result["success"]:
                    total_conflicts += 1
                    for conflict_key in result["conflicts"]:
                        bus.error(
                            L.hydrate.error.conflict,
                            path=module.file_path,
                            key=conflict_key,
                        )
                    continue
                if result["reconciled_keys"]:
                    bus.info(
                        L.hydrate.info.reconciled,
                        path=module.file_path,
                        count=len(result["reconciled_keys"]),
                    )
                if result["updated_keys"]:
                    total_updated += 1
                    bus.success(
                        L.hydrate.file.success,
                        path=module.file_path,
                        count=len(result["updated_keys"]),
                    )
                code_hashes = self.sig_manager.compute_code_structure_hashes(module)
                yaml_hashes = self.doc_manager.compute_yaml_content_hashes(module)
                all_fqns = set(code_hashes.keys()) | set(yaml_hashes.keys())
                combined = {
                    fqn: {
                        "code_structure_hash": code_hashes.get(fqn),
                        "yaml_content_hash": yaml_hashes.get(fqn),
                    }
                    for fqn in all_fqns
                }
                self.sig_manager.save_composite_hashes(module, combined)
                files_to_strip.append(module)
            if strip and files_to_strip:
                stripped_count = 0
                for module in files_to_strip:
                    source_path = self.root_path / module.file_path
                    try:
                        original_content = source_path.read_text(encoding="utf-8")
                        stripped_content = strip_docstrings(original_content)
                        if original_content != stripped_content:
                            source_path.write_text(stripped_content, encoding="utf-8")
                            stripped_count += 1
                            relative_path = source_path.relative_to(self.root_path)
                            bus.success(L.strip.file.success, path=relative_path)
                    except Exception as e:
                        bus.error(L.error.generic, error=e)
                if stripped_count > 0:
                    bus.success(L.strip.run.complete, count=stripped_count)
        if total_conflicts > 0:
            bus.error(L.hydrate.run.conflict, count=total_conflicts)
            return False
        if total_updated == 0:
            bus.info(L.hydrate.run.no_changes)
        else:
            bus.success(L.hydrate.run.complete, count=total_updated)
        return True
~~~~~
~~~~~python.new
    def run_hydrate(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> bool:
        bus.info(L.hydrate.run.start)
        configs, _ = load_config_from_path(self.root_path)
        
        all_modules: List[ModuleDef] = []
        all_conflicts: List[InteractionContext] = []
        
        # 1. Analysis Phase (Dry Run)
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            all_modules.extend(modules)
            
            for module in modules:
                # Dry run to detect conflicts
                res = self.doc_manager.hydrate_module(
                    module, force=force, reconcile=reconcile, dry_run=True
                )
                if not res["success"]:
                    for key in res["conflicts"]:
                        all_conflicts.append(
                            InteractionContext(
                                module.file_path, key, ConflictType.DOC_CONTENT_CONFLICT
                            )
                        )

        # 2. Decision Phase
        resolutions_by_file: Dict[str, Dict[str, ResolutionAction]] = defaultdict(dict)
        
        if all_conflicts:
            if self.interaction_handler:
                chosen_actions = self.interaction_handler.process_interactive_session(all_conflicts)
            else:
                handler = NoOpInteractionHandler(hydrate_force=force, hydrate_reconcile=reconcile)
                chosen_actions = handler.process_interactive_session(all_conflicts)
            
            for i, context in enumerate(all_conflicts):
                action = chosen_actions[i]
                if action == ResolutionAction.ABORT:
                    bus.warning(L.hydrate.run.conflict, count=len(all_conflicts)) # Reuse conflict msg as abort indicator?
                    bus.error("Hydration aborted by user.")
                    return False
                resolutions_by_file[context.file_path][context.fqn] = action

        # 3. Execution Phase
        total_updated = 0
        total_conflicts_remaining = 0
        files_to_strip = []
        
        for module in all_modules:
            resolution_map = resolutions_by_file.get(module.file_path, {})
            
            # Execute hydration with resolutions
            result = self.doc_manager.hydrate_module(
                module, force=force, reconcile=reconcile, resolution_map=resolution_map, dry_run=False
            )
            
            if not result["success"]:
                # If conflicts persist (e.g. user chose SKIP), verify failure
                total_conflicts_remaining += len(result["conflicts"])
                for conflict_key in result["conflicts"]:
                    bus.error(
                        L.hydrate.error.conflict,
                        path=module.file_path,
                        key=conflict_key,
                    )
                continue
            
            if result["reconciled_keys"]:
                bus.info(
                    L.hydrate.info.reconciled,
                    path=module.file_path,
                    count=len(result["reconciled_keys"]),
                )
            if result["updated_keys"]:
                total_updated += 1
                bus.success(
                    L.hydrate.file.success,
                    path=module.file_path,
                    count=len(result["updated_keys"]),
                )
            
            # Update signatures if successful
            code_hashes = self.sig_manager.compute_code_structure_hashes(module)
            yaml_hashes = self.doc_manager.compute_yaml_content_hashes(module)
            all_fqns = set(code_hashes.keys()) | set(yaml_hashes.keys())
            combined = {
                fqn: {
                    "baseline_code_structure_hash": code_hashes.get(fqn),
                    "baseline_yaml_content_hash": yaml_hashes.get(fqn),
                }
                for fqn in all_fqns
            }
            self.sig_manager.save_composite_hashes(module, combined)
            files_to_strip.append(module)

        # 4. Strip Phase (Optional)
        if strip and files_to_strip:
            stripped_count = 0
            for module in files_to_strip:
                source_path = self.root_path / module.file_path
                try:
                    original_content = source_path.read_text(encoding="utf-8")
                    stripped_content = strip_docstrings(original_content)
                    if original_content != stripped_content:
                        source_path.write_text(stripped_content, encoding="utf-8")
                        stripped_count += 1
                        relative_path = source_path.relative_to(self.root_path)
                        bus.success(L.strip.file.success, path=relative_path)
                except Exception as e:
                    bus.error(L.error.generic, error=e)
            if stripped_count > 0:
                bus.success(L.strip.run.complete, count=stripped_count)

        if total_conflicts_remaining > 0:
            bus.error(L.hydrate.run.conflict, count=total_conflicts_remaining)
            return False
            
        if total_updated == 0:
            bus.info(L.hydrate.run.no_changes)
        else:
            bus.success(L.hydrate.run.complete, count=total_updated)
            
        return True
~~~~~

#### Acts 5: 更新 TyperInteractionHandler

实现新的菜单分支。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/handlers.py
~~~~~
~~~~~python.old
            # --- Build and Display Menu ---
            menu = []
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                typer.secho("  Reason: Signature has changed, but docs have not (Signature Drift).")
                menu.append(("[F]orce-relink", ResolutionAction.RELINK, "Force-relink new signature with old docs."))
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
                typer.secho("  Reason: Both signature and docs have changed (Co-evolution).")
                menu.append(("[R]econcile", ResolutionAction.RECONCILE, "Accept both changes as the new correct state."))
            
            menu.append(("[S]kip", ResolutionAction.SKIP, "Skip this conflict for now."))
~~~~~
~~~~~python.new
            # --- Build and Display Menu ---
            menu = []
            if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
                typer.secho("  Reason: Signature has changed, but docs have not (Signature Drift).")
                menu.append(("[F]orce-relink", ResolutionAction.RELINK, "Force-relink new signature with old docs."))
            elif context.conflict_type == ConflictType.CO_EVOLUTION:
                typer.secho("  Reason: Both signature and docs have changed (Co-evolution).")
                menu.append(("[R]econcile", ResolutionAction.RECONCILE, "Accept both changes as the new correct state."))
            elif context.conflict_type == ConflictType.DOC_CONTENT_CONFLICT:
                typer.secho("  Reason: Source code docstring differs from YAML docstring.")
                menu.append(("[F]orce-hydrate", ResolutionAction.HYDRATE_OVERWRITE, "Overwrite YAML with code docs (Code-first)."))
                menu.append(("[R]econcile", ResolutionAction.HYDRATE_KEEP_EXISTING, "Keep existing YAML docs (YAML-first)."))

            menu.append(("[S]kip", ResolutionAction.SKIP, "Skip this conflict for now."))
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/handlers.py
~~~~~
~~~~~python.old
            # --- Process Input ---
            if char == '\r' or char == '\n': # Enter
                action = default_choice
            elif char == 'f' and any(a == ResolutionAction.RELINK for _, a, _ in menu):
                action = ResolutionAction.RELINK
            elif char == 'r' and any(a == ResolutionAction.RECONCILE for _, a, _ in menu):
                action = ResolutionAction.RECONCILE
            elif char == 's':
~~~~~
~~~~~python.new
            # --- Process Input ---
            if char == '\r' or char == '\n': # Enter
                action = default_choice
            elif char == 'f':
                 if any(a == ResolutionAction.RELINK for _, a, _ in menu):
                    action = ResolutionAction.RELINK
                 elif any(a == ResolutionAction.HYDRATE_OVERWRITE for _, a, _ in menu):
                    action = ResolutionAction.HYDRATE_OVERWRITE
            elif char == 'r':
                 if any(a == ResolutionAction.RECONCILE for _, a, _ in menu):
                    action = ResolutionAction.RECONCILE
                 elif any(a == ResolutionAction.HYDRATE_KEEP_EXISTING for _, a, _ in menu):
                    action = ResolutionAction.HYDRATE_KEEP_EXISTING
            elif char == 's':
~~~~~

#### Acts 6: 在 main.py 中启用 Hydrate 交互

将 Handler 注入到 `hydrate` 命令。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help=nexus.get(L.cli.option.reconcile.help),
    ),
):
    if force and reconcile:
        bus.error("Cannot use --force and --reconcile simultaneously.")
        raise typer.Exit(code=1)

    project_root = Path.cwd()
    app_instance = StitcherApp(root_path=project_root)
    success = app_instance.run_hydrate(strip=strip, force=force, reconcile=reconcile)
    if not success:
        raise typer.Exit(code=1)
~~~~~
~~~~~python.new
    reconcile: bool = typer.Option(
        False,
        "--reconcile",
        help=nexus.get(L.cli.option.reconcile.help),
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Force non-interactive mode, failing on unresolved conflicts.",
    ),
):
    if force and reconcile:
        bus.error("Cannot use --force and --reconcile simultaneously.")
        raise typer.Exit(code=1)

    project_root = Path.cwd()
    
    handler = None
    if sys.stdin.isatty() and not non_interactive and not force and not reconcile:
        handler = TyperInteractionHandler()

    app_instance = StitcherApp(root_path=project_root, interaction_handler=handler)
    success = app_instance.run_hydrate(strip=strip, force=force, reconcile=reconcile)
    if not success:
        raise typer.Exit(code=1)
~~~~~
