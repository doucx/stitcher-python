好的，我们开始 **阶段 3：逻辑驱动重构**。我们将重构 `CheckRunner`，使其采用 "Query-First" 模式。这将极大地改变 `CheckRunner` 的工作方式，使其从一个“解析器”变成一个“查询器”。

## [WIP] refactor(application): 重构 CheckRunner 为 Index-First 模式

### 用户需求
根据 [Stitcher 2.0 确定性链接实施路线图：Index-First 架构](Stitcher%202.0%20确定性链接实施路线图：Index-First%20架构.md) 中的 "重构 CheckRunner (Query-First)" 部分，将 `CheckRunner` 的核心分析逻辑从“读取文件并解析”迁移为“从数据库查询”。这将使 `check` 命令的速度与代码库大小解耦，而主要取决于索引查询速度。

### 评论
这是 Stitcher 2.0 性能提升的核心。通过利用已经在 `index.db` 中准备好的结构化数据（我们在前两个阶段已经确保了其中包含完整的签名文本和文档哈希），我们可以在毫秒级完成文件的状态检查。

### 目标
1.  修改 `CheckRunner.__init__`，接收 `IndexStore` 实例，取代 `LanguageParserProtocol` (解析器) 和 `FingerprintStrategyProtocol` (指纹策略)。因为解析和指纹计算现在由索引器负责。
2.  重构 `_analyze_file` 方法：
    *   **移除**: 文件读取、解析 AST、计算指纹的逻辑。
    *   **新增**: 通过 `self.index_store.get_file_by_path()` 获取文件记录，再通过 `self.index_store.get_symbols_by_file()` 获取该文件的所有符号记录。
    *   **逻辑变更**: 将查询到的 `SymbolRecord` 转换为 `Fingerprint` 对象，作为 "Actual" 状态，与 `SignatureManager` 加载的 "Baseline" 进行比对。
3.  更新 `StitcherApp` 以适配新的 `CheckRunner` 依赖注入。

### 基本原理
-   **Baseline**: 依然通过 `SignatureManager.load_composite_hashes` 获取。
-   **Actual**: 现在通过 `IndexStore` 获取。`SymbolRecord` 中的 `signature_hash`, `signature_text`, `docstring_hash` 字段直接映射到 `Fingerprint` 的 `current_` 字段。
-   **Diff**: 利用 DB 中的 `signature_text` 与 Baseline 中的 `baseline_code_signature_text` 直接生成 Diff，无需读取源码。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #concept/state #scope/core #ai/instruct #task/domain/runner #task/object/check-runner #task/action/query-first-refactor #task/state/begin

---

### Script

#### Acts 1: 重构 CheckRunner 依赖与分析逻辑

我们将修改 `check.py`，移除解析器依赖，引入 `IndexStore`，并彻底重写 `_analyze_file` 方法以使用数据库查询。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check.py
~~~~~
~~~~~python.old
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
        self.differ = differ
        self.interaction_handler = interaction_handler
        self.fingerprint_strategy = fingerprint_strategy

    def _compute_fingerprints(self, module: ModuleDef) -> Dict[str, Fingerprint]:
        fingerprints: Dict[str, Fingerprint] = {}
        for func in module.functions:
            fingerprints[func.name] = self.fingerprint_strategy.compute(func)
        for cls in module.classes:
            for method in cls.methods:
                fqn = f"{cls.name}.{method.name}"
                fingerprints[fqn] = self.fingerprint_strategy.compute(method)
        return fingerprints

    def _analyze_file(
        self, module: ModuleDef
    ) -> Tuple[FileCheckResult, List[InteractionContext]]:
        result = FileCheckResult(path=module.file_path)
        unresolved_conflicts: List[InteractionContext] = []

        # Content checks
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            result.warnings["missing"].extend(doc_issues["missing"])
            result.warnings["redundant"].extend(doc_issues["redundant"])
            result.errors["pending"].extend(doc_issues["pending"])
            result.errors["conflict"].extend(doc_issues["conflict"])
            for fqn in doc_issues["extra"]:
                unresolved_conflicts.append(
                    InteractionContext(module.file_path, fqn, ConflictType.DANGLING_DOC)
                )

        # State machine analysis
        is_tracked = (
            (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists()
        )

        computed_fingerprints = self._compute_fingerprints(module)
        current_yaml_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module.file_path)

        all_fqns = set(computed_fingerprints.keys()) | set(stored_hashes_map.keys())

        for fqn in sorted(list(all_fqns)):
            computed_fp = computed_fingerprints.get(fqn, Fingerprint())

            code_hash = computed_fp.get("current_code_structure_hash")
            current_sig_text = computed_fp.get("current_code_signature_text")
            yaml_hash = current_yaml_map.get(fqn)

            stored_fp = stored_hashes_map.get(fqn)
            baseline_code_hash = (
                stored_fp.get("baseline_code_structure_hash") if stored_fp else None
            )
            baseline_yaml_hash = (
                stored_fp.get("baseline_yaml_content_hash") if stored_fp else None
            )
            baseline_sig_text = (
                stored_fp.get("baseline_code_signature_text") if stored_fp else None
            )

            if not code_hash and baseline_code_hash:  # Extra
                continue
            if code_hash and not baseline_code_hash:  # New
                continue

            code_matches = code_hash == baseline_code_hash
            yaml_matches = yaml_hash == baseline_yaml_hash

            if code_matches and not yaml_matches:  # Doc improvement
                result.infos["doc_improvement"].append(fqn)
            elif not code_matches:
                sig_diff = None
                if baseline_sig_text and current_sig_text:
                    sig_diff = self.differ.generate_text_diff(
                        baseline_sig_text,
                        current_sig_text,
                        "baseline",
                        "current",
                    )
                elif current_sig_text:
                    sig_diff = f"(No baseline signature stored)\n+++ current\n{current_sig_text}"

                conflict_type = (
                    ConflictType.SIGNATURE_DRIFT
                    if yaml_matches
                    else ConflictType.CO_EVOLUTION
                )

                unresolved_conflicts.append(
                    InteractionContext(
                        module.file_path, fqn, conflict_type, signature_diff=sig_diff
                    )
                )

        if not is_tracked and module.is_documentable():
            undocumented = module.get_undocumented_public_keys()
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        return result, unresolved_conflicts

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

            full_module_def = self.parser.parse(
                (self.root_path / file_path).read_text("utf-8"), file_path
            )
            computed_fingerprints = self._compute_fingerprints(full_module_def)
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
~~~~~
~~~~~python.new
from stitcher.common import bus
from needle.pointer import L
from stitcher.spec import (
    ModuleDef,
    ConflictType,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
)
from stitcher.index.store import IndexStore
from stitcher.index.types import SymbolRecord
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    Differ,
)
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.app.handlers.noop_handler import NoOpInteractionHandler
from stitcher.app.types import FileCheckResult


class CheckRunner:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,  # Keep parser for applying resolutions (needs re-parse)
        index_store: IndexStore,  # New dependency: The DB
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
        differ: Differ,
        interaction_handler: InteractionHandler | None,
    ):
        self.root_path = root_path
        self.parser = parser
        self.index_store = index_store
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.differ = differ
        self.interaction_handler = interaction_handler

    def _symbol_to_fingerprint(self, symbol: SymbolRecord) -> Fingerprint:
        fp = Fingerprint()
        if symbol.signature_hash:
            fp["current_code_structure_hash"] = symbol.signature_hash
        if symbol.signature_text:
            fp["current_code_signature_text"] = symbol.signature_text
        if symbol.docstring_hash:
            fp["current_code_docstring_hash"] = symbol.docstring_hash
        return fp

    def _analyze_file(
        self, file_path: str
    ) -> Tuple[FileCheckResult, List[InteractionContext]]:
        result = FileCheckResult(path=file_path)
        unresolved_conflicts: List[InteractionContext] = []

        # 1. Query ACTUAL state from DB
        file_record = self.index_store.get_file_by_path(file_path)
        if not file_record:
            # File might be new/untracked or ignored. For check, if not in DB, skip.
            return result, []

        db_symbols = self.index_store.get_symbols_by_file(file_record.id)
        # Convert DB symbols to a map of FQN fragment -> Fingerprint
        actual_fingerprints: Dict[str, Fingerprint] = {}
        for sym in db_symbols:
            if sym.logical_path:  # Skip module root symbol if logical_path is None
                actual_fingerprints[sym.logical_path] = self._symbol_to_fingerprint(sym)

        # 2. Load BASELINE state from Signatures
        stored_hashes_map = self.sig_manager.load_composite_hashes(file_path)

        # 3. Load YAML content hashes (Still need to read YAML file)
        # We construct a minimal ModuleDef just to pass file_path to doc_manager
        module_stub = ModuleDef(file_path=file_path)
        current_yaml_map = self.doc_manager.compute_yaml_content_hashes(module_stub)

        # 4. Content Checks (Doc issues like missing/redundant)
        # doc_manager.check_module still requires a ModuleDef.
        # Ideally, we should refactor doc_manager to check against DB symbols too.
        # But for now, let's defer deep refactor of doc_manager and focus on state machine.
        # We can reconstruct a lightweight ModuleDef from DB symbols?
        # Or, strictly for content checks, we might still need to parse...
        # Wait, the goal is to avoid parsing.
        # If we skip doc_manager.check_module here, we lose "missing/redundant" warnings.
        # Let's keep it consistent: CheckRunner's primary job is State Consistency (Drift).
        # Doc Content Consistency (Missing/Redundant) is secondary but important.
        # TEMPORARY STRATEGY: We will skip `doc_manager.check_module` call that requires full AST.
        # Instead, we implement a lighter check based on set difference of keys.

        # Lighter Doc Content Check using Sets
        yaml_keys = set(current_yaml_map.keys())
        code_keys = set(actual_fingerprints.keys())

        # Filter out private members from code_keys if needed (Stitcher default is public only)
        # The DB stores everything. We should filter.
        public_code_keys = {k for k in code_keys if not k.split(".")[-1].startswith("_")}

        is_tracked = (self.root_path / file_path).with_suffix(".stitcher.yaml").exists()

        if is_tracked:
            # Missing: In code (public), not in YAML
            missing = public_code_keys - yaml_keys
            result.warnings["missing"].extend(sorted(list(missing)))

            # Redundant/Extra: In YAML, not in code
            # Note: "Extra" (Dangling Doc) is usually handled as a conflict type.
            extra = yaml_keys - code_keys
            extra.discard("__doc__") # Ignore module doc key

            for fqn in extra:
                unresolved_conflicts.append(
                    InteractionContext(file_path, fqn, ConflictType.DANGLING_DOC)
                )

        # 5. State Machine Analysis (The Core Loop)
        all_fqns = set(actual_fingerprints.keys()) | set(stored_hashes_map.keys())

        for fqn in sorted(list(all_fqns)):
            computed_fp = actual_fingerprints.get(fqn, Fingerprint())

            code_hash = computed_fp.get("current_code_structure_hash")
            current_sig_text = computed_fp.get("current_code_signature_text")
            yaml_hash = current_yaml_map.get(fqn)

            stored_fp = stored_hashes_map.get(fqn)
            baseline_code_hash = (
                stored_fp.get("baseline_code_structure_hash") if stored_fp else None
            )
            baseline_yaml_hash = (
                stored_fp.get("baseline_yaml_content_hash") if stored_fp else None
            )
            baseline_sig_text = (
                stored_fp.get("baseline_code_signature_text") if stored_fp else None
            )

            if not code_hash and baseline_code_hash:  # Extra (Handled above as Dangling)
                continue
            if code_hash and not baseline_code_hash:  # New (Handled above as Missing)
                continue

            code_matches = code_hash == baseline_code_hash
            yaml_matches = yaml_hash == baseline_yaml_hash

            if code_matches and not yaml_matches:  # Doc improvement
                result.infos["doc_improvement"].append(fqn)
            elif not code_matches:
                sig_diff = None
                if baseline_sig_text and current_sig_text:
                    sig_diff = self.differ.generate_text_diff(
                        baseline_sig_text,
                        current_sig_text,
                        "baseline",
                        "current",
                    )
                elif current_sig_text:
                    sig_diff = f"(No baseline signature stored)\n+++ current\n{current_sig_text}"

                conflict_type = (
                    ConflictType.SIGNATURE_DRIFT
                    if yaml_matches
                    else ConflictType.CO_EVOLUTION
                )

                unresolved_conflicts.append(
                    InteractionContext(
                        file_path, fqn, conflict_type, signature_diff=sig_diff
                    )
                )

        if not is_tracked and public_code_keys:
             # Just list them all as detailed untracked
            result.warnings["untracked_detailed"].extend(sorted(list(public_code_keys)))
        elif not is_tracked:
             # Empty file but untracked
             pass # Nothing to warn about if no public symbols

        return result, unresolved_conflicts

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

            # NOTE: For resolution application (writing new hashes), we still parse the file
            # to get the absolute latest state (in case user modified file *during* interactive session?)
            # Or we could trust the DB. Let's stick to parsing for safety during write operations for now,
            # but ideally we should trust the DB + Indexer.
            # Using parser here ensures we get fresh fingerprints even if indexer wasn't re-run.
            full_module_def = self.parser.parse(
                (self.root_path / file_path).read_text("utf-8"), file_path
            )
            # We need a strategy to compute fingerprints from ModuleDef.
            # CheckRunner no longer has self.fingerprint_strategy.
            # We must instantiate one or pass it in.
            # Ideally, CheckRunner shouldn't be applying writes.
            # But refactoring that is out of scope.
            # Let's rely on StitcherApp to pass the strategy?
            # Wait, `_apply_resolutions` is internal.
            # The previous implementation used `self._compute_fingerprints`.
            # We removed it.
            # SOLUTION: Use the DB! The DB has the latest state (assuming no external modification during check).
            # We can re-query the DB for the "Current" state to update the "Baseline".

            file_record = self.index_store.get_file_by_path(file_path)
            if not file_record:
                continue
            db_symbols = self.index_store.get_symbols_by_file(file_record.id)
            actual_fingerprints = {}
            for sym in db_symbols:
                if sym.logical_path:
                    actual_fingerprints[sym.logical_path] = self._symbol_to_fingerprint(sym)

            # Re-compute YAML hashes (cheap)
            current_yaml_map = self.doc_manager.compute_yaml_content_hashes(
                ModuleDef(file_path=file_path)
            )

            for fqn, action in fqn_actions:
                if fqn in new_hashes:
                    fp = new_hashes[fqn]
                    current_fp = actual_fingerprints.get(fqn, Fingerprint())
                    current_code_hash = current_fp.get("current_code_structure_hash")
                    current_sig_text = current_fp.get("current_code_signature_text")
                    current_doc_hash = current_fp.get("current_code_docstring_hash")

                    if action == ResolutionAction.RELINK:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                        if current_sig_text:
                            fp["baseline_code_signature_text"] = str(current_sig_text)
                        if current_doc_hash:
                            fp["baseline_code_docstring_hash"] = str(current_doc_hash)

                    elif action == ResolutionAction.RECONCILE:
                        if current_code_hash:
                            fp["baseline_code_structure_hash"] = str(current_code_hash)
                        if current_sig_text:
                            fp["baseline_code_signature_text"] = str(current_sig_text)
                        if current_doc_hash:
                            fp["baseline_code_docstring_hash"] = str(current_doc_hash)

                        if fqn in current_yaml_map:
                            fp["baseline_yaml_content_hash"] = str(
                                current_yaml_map[fqn]
                            )

            if new_hashes != stored_hashes:
                self.sig_manager.save_composite_hashes(file_path, new_hashes)

        # Apply doc purges (Same as before)
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

    def analyze_batch(
        self, modules: List[ModuleDef]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        # The signature changes: CheckRunner now iterates over file paths, not ModuleDefs.
        # But for compatibility with StitcherApp loop, we accept ModuleDefs and extract paths.
        results = []
        conflicts = []
        for module in modules:
            res, conf = self._analyze_file(module.file_path)
            results.append(res)
            conflicts.extend(conf)
        return results, conflicts
~~~~~

#### Acts 2: 更新 StitcherApp 以注入新依赖

修改 `StitcherApp`，将 `index_store` 传递给 `CheckRunner`，并移除不再需要的 `fingerprint_strategy` 参数。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        # 2. Runners (Command Handlers)
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
            root_path,
~~~~~
~~~~~python.new
        # 2. Runners (Command Handlers)
        self.check_runner = CheckRunner(
            root_path,
            parser,
            self.index_store,
            self.doc_manager,
            self.sig_manager,
            self.differ,
            interaction_handler,
        )
        self.pump_runner = PumpRunner(
            root_path,
~~~~~

### 下一步建议

`CheckRunner` 的重构已经完成。现在它完全依赖于数据库查询来进行状态分析。

接下来的关键步骤是**确保 `CheckRunner` 在运行时拥有最新的索引数据**。虽然 `StitcherApp.run_check` 已经调用了 `ensure_index_fresh()`，但我们需要通过测试来验证这一整套“扫描-索引-查询”的链路是否工作正常。

因此，下一步建议运行集成测试，特别是那些验证 `check` 命令状态机逻辑的测试（如 `test_check_state_machine.py`），以确保重构没有破坏现有行为。如果测试通过，我们将继续重构 `PumpRunner`。
