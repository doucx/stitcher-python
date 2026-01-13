好的，收到了 `rg SignatureManagerProtocol` 的结果。这表明虽然我在代码中删除了 `SignatureManager` 的实现类，但 `SignatureManagerProtocol` 仍然存在于 `stitcher-spec` 中，并且被大量测试和部分尚未迁移的业务代码（Check子系统）引用。

我必须先完成业务代码的迁移，然后再去清理协议定义和测试。如果现在就删除协议，所有的引用都会报错，导致无法继续进行“手术式替换”。

**策略调整**:
我们将继续执行原计划的 Check 子系统重写。在重写的过程中，我们会自然地将 `SignatureManagerProtocol` 替换为 `LockManagerProtocol`。只有当所有的业务代码都迁移完毕后，我们才会最后去删除 `SignatureManagerProtocol` 的定义并修复测试。

## [WIP] feat: 迁移 Check 子系统至 LockFileManager

### 用户需求
1.  **重写 `SubjectAdapter`**: 修改 `IndexCheckSubjectAdapter` 和 `ASTCheckSubjectAdapter`，使其不再依赖 `SignatureManager`，而是通过 `LockFileManager` 加载数据，并通过 `URIGenerator` 生成 SURI 进行查找。
2.  **重写 `CheckResolver`**: 修改冲突解决逻辑，从更新分散的签名文件变为更新集中的 Lock 数据。
3.  **重写 `CheckRunner`**: 更新其构造函数和调用链，注入新的管理器。

### 评论
Check 子系统是系统中逻辑最复杂的部分，因为它不仅要读取数据，还要进行多维度的比对（Code vs Doc vs Baseline）。这里的关键是将“读取 Baseline”的操作从 `load_composite_hashes(file_path)` 转换为 `lock_manager.load(pkg_root).get(suri)`。这需要 `SubjectAdapter` 能够计算出正确的 SURI。

### 目标
1.  重写 `stitcher-application/src/stitcher/app/runners/check/subject.py`。
2.  重写 `stitcher-application/src/stitcher/app/runners/check/resolver.py`。
3.  重写 `stitcher-application/src/stitcher/app/runners/check/runner.py`。

### 基本原理
-   **SURI 是连接点**: 在 Check 过程中，每一个被检查的符号（无论是来自 AST 还是 Index）都必须先被转换为全局唯一的 SURI。这个 SURI 是从 Lock 文件中检索 Baseline 指纹的唯一 Key。
-   **Lock 上下文**: `SubjectAdapter` 需要知道当前文件属于哪个包（Package Root），以便从正确的 `stitcher.lock` 中获取数据。这需要注入 `Workspace`。

### 标签
#intent/refactor #flow/ready #priority/critical #comp/application #comp/check #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/suri-lockfile #task/action/check-subsystem-migration #task/state/continue

---

### Script

#### Acts 1: 重写 `SubjectAdapter` (`stitcher-application`)

这是 Check 逻辑的数据源适配器。我们需要将它对 `SignatureManager` 的依赖替换为对 `LockManager`, `URIGenerator` 和 `Workspace` 的依赖。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
from typing import Dict, Optional
from pathlib import Path
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec.index import SymbolRecord
from stitcher.analysis.schema import SymbolState
from stitcher.analysis.protocols import AnalysisSubject as CheckSubject


class IndexCheckSubjectAdapter(CheckSubject):
    def __init__(
        self,
        file_path: str,
        index_store: IndexStoreProtocol,
        doc_manager: DocumentManagerProtocol,
        sig_manager: SignatureManagerProtocol,
        root_path: Path,
    ):
        self._file_path = file_path
        self._index_store = index_store
        self._doc_manager = doc_manager
        self._sig_manager = sig_manager
        self._root_path = root_path

    @property
    def file_path(self) -> str:
~~~~~
~~~~~python.new
from typing import Dict, Optional
from pathlib import Path
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol
from stitcher.spec.index import SymbolRecord
from stitcher.analysis.schema import SymbolState
from stitcher.analysis.protocols import AnalysisSubject as CheckSubject
from stitcher.workspace import Workspace


class IndexCheckSubjectAdapter(CheckSubject):
    def __init__(
        self,
        file_path: str,
        index_store: IndexStoreProtocol,
        doc_manager: DocumentManagerProtocol,
        lock_manager: LockManagerProtocol,
        uri_generator: URIGeneratorProtocol,
        workspace: Workspace,
        root_path: Path,
    ):
        self._file_path = file_path
        self._index_store = index_store
        self._doc_manager = doc_manager
        self._lock_manager = lock_manager
        self._uri_generator = uri_generator
        self._workspace = workspace
        self._root_path = root_path

    @property
    def file_path(self) -> str:
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load data from all sources
        symbols_from_db = self._index_store.get_symbols_by_file_path(self.file_path)
        yaml_docs = self._doc_manager.load_docs_for_path(self.file_path)
        stored_hashes = self._sig_manager.load_composite_hashes(self.file_path)

        yaml_content_hashes = {
            fqn: self._doc_manager.compute_ir_hash(ir) for fqn, ir in yaml_docs.items()
        }
~~~~~
~~~~~python.new
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load data from all sources
        symbols_from_db = self._index_store.get_symbols_by_file_path(self.file_path)
        yaml_docs = self._doc_manager.load_docs_for_path(self.file_path)
        
        # Load Lock Data
        abs_path = self._root_path / self.file_path
        pkg_root = self._workspace.find_owning_package(abs_path)
        lock_data = self._lock_manager.load(pkg_root)
        
        # Prepare coordinates
        ws_rel_path = self._workspace.to_workspace_relative(abs_path)

        yaml_content_hashes = {
            fqn: self._doc_manager.compute_ir_hash(ir) for fqn, ir in yaml_docs.items()
        }
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
        # 3. Aggregate all unique FQNs
        all_fqns = (
            set(symbol_map.keys()) | set(yaml_docs.keys()) | set(stored_hashes.keys())
        )
        if module_symbol:
            all_fqns.add("__doc__")

        states: Dict[str, SymbolState] = {}

        # 4. Build state for each FQN
        for fqn in all_fqns:
            symbol_rec: Optional[SymbolRecord] = None
            if fqn == "__doc__":
                symbol_rec = module_symbol
            else:
                symbol_rec = symbol_map.get(fqn)

            stored_fp = stored_hashes.get(fqn, Fingerprint())

            states[fqn] = SymbolState(
~~~~~
~~~~~python.new
        # 3. Aggregate all unique FQNs
        # Note: We can't easily get FQNs from lock_data without iterating all keys,
        # but for a single file check, we rely on symbols and yaml as primary sources.
        # Lock is a lookup source.
        all_fqns = set(symbol_map.keys()) | set(yaml_docs.keys())
        if module_symbol:
            all_fqns.add("__doc__")

        states: Dict[str, SymbolState] = {}

        # 4. Build state for each FQN
        for fqn in all_fqns:
            symbol_rec: Optional[SymbolRecord] = None
            if fqn == "__doc__":
                symbol_rec = module_symbol
            else:
                symbol_rec = symbol_map.get(fqn)

            # Lookup Baseline in Lock
            suri = self._uri_generator.generate_symbol_uri(ws_rel_path, fqn)
            stored_fp = lock_data.get(suri) or Fingerprint()

            states[fqn] = SymbolState(
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
class ASTCheckSubjectAdapter(CheckSubject):
    def __init__(
        self,
        module_def: ModuleDef,
        doc_manager: DocumentManagerProtocol,
        sig_manager: SignatureManagerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        root_path: Path,
    ):
        self._module = module_def
        self._doc_manager = doc_manager
        self._sig_manager = sig_manager
        self._fingerprint_strategy = fingerprint_strategy
        self._root_path = root_path
~~~~~
~~~~~python.new
class ASTCheckSubjectAdapter(CheckSubject):
    def __init__(
        self,
        module_def: ModuleDef,
        doc_manager: DocumentManagerProtocol,
        lock_manager: LockManagerProtocol,
        uri_generator: URIGeneratorProtocol,
        workspace: Workspace,
        fingerprint_strategy: FingerprintStrategyProtocol,
        root_path: Path,
    ):
        self._module = module_def
        self._doc_manager = doc_manager
        self._lock_manager = lock_manager
        self._uri_generator = uri_generator
        self._workspace = workspace
        self._fingerprint_strategy = fingerprint_strategy
        self._root_path = root_path
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load all necessary data from various sources
        source_docs = self._doc_manager.flatten_module_docs(self._module)
        yaml_docs = self._doc_manager.load_docs_for_module(self._module)
        public_fqns = self._module.get_public_documentable_fqns()
        code_fqns = set(self._module.get_all_fqns())
        # The module docstring key is always valid/present in code context,
        # even if the source file has no docstring.
        code_fqns.add("__doc__")

        fingerprints = self._compute_fingerprints()
        yaml_hashes = self._doc_manager.compute_yaml_content_hashes(self._module)
        stored_hashes = self._sig_manager.load_composite_hashes(self.file_path)

        all_fqns = code_fqns | set(yaml_docs.keys()) | set(stored_hashes.keys())
        states: Dict[str, SymbolState] = {}

        # 2. Iterate and build the state object for each symbol
        for fqn in all_fqns:
            fp = fingerprints.get(fqn, Fingerprint())
            source_ir = source_docs.get(fqn)
            stored_fp = stored_hashes.get(fqn, Fingerprint())

            states[fqn] = SymbolState(
~~~~~
~~~~~python.new
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load all necessary data from various sources
        source_docs = self._doc_manager.flatten_module_docs(self._module)
        yaml_docs = self._doc_manager.load_docs_for_module(self._module)
        public_fqns = self._module.get_public_documentable_fqns()
        code_fqns = set(self._module.get_all_fqns())
        # The module docstring key is always valid/present in code context,
        # even if the source file has no docstring.
        code_fqns.add("__doc__")

        fingerprints = self._compute_fingerprints()
        yaml_hashes = self._doc_manager.compute_yaml_content_hashes(self._module)
        
        # Load Lock Data
        lock_data = {}
        ws_rel_path = ""
        
        if self._module.file_path:
            abs_path = self._root_path / self.file_path
            pkg_root = self._workspace.find_owning_package(abs_path)
            lock_data = self._lock_manager.load(pkg_root)
            ws_rel_path = self._workspace.to_workspace_relative(abs_path)

        # Note: We rely on code and yaml to drive the loop. Stored hashes are looked up.
        # This differs slightly from old behavior where stored_hashes keys were also iterated.
        # But logically, if it's in Lock but not in Code and not in YAML, it's effectively invisible/deleted?
        # Or should we flag it? For now, we stick to Code | YAML driven check.
        all_fqns = code_fqns | set(yaml_docs.keys())
        states: Dict[str, SymbolState] = {}

        # 2. Iterate and build the state object for each symbol
        for fqn in all_fqns:
            fp = fingerprints.get(fqn, Fingerprint())
            source_ir = source_docs.get(fqn)
            
            stored_fp = Fingerprint()
            if ws_rel_path:
                suri = self._uri_generator.generate_symbol_uri(ws_rel_path, fqn)
                stored_fp = lock_data.get(suri) or Fingerprint()

            states[fqn] = SymbolState(
~~~~~

#### Acts 2: 重写 `CheckResolver` (`stitcher-application`)

适配解决冲突和自动调和的逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.app.handlers.noop_handler import NoOpInteractionHandler
from stitcher.analysis.schema import FileCheckResult


class CheckResolver:
    def __init__(
        self,
        root_path: Path,
        parser: LanguageParserProtocol,
        doc_manager: DocumentManagerProtocol,
        sig_manager: SignatureManagerProtocol,
        interaction_handler: InteractionHandler | None,
        fingerprint_strategy: FingerprintStrategyProtocol,
    ):
        self.root_path = root_path
        self.parser = parser
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.interaction_handler = interaction_handler
        self.fingerprint_strategy = fingerprint_strategy
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
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

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
    def auto_reconcile_docs(
        self, results: List[FileCheckResult], modules: List[ModuleDef]
    ):
        for res in results:
            # Find all "doc_updated" violations and update baselines
            doc_update_violations = [
                v for v in res.info_violations if v.kind == L.check.state.doc_updated
            ]
            if not doc_update_violations:
                continue

            module_def = next((m for m in modules if m.file_path == res.path), None)
            if not module_def:
                continue

            stored_hashes = self.sig_manager.load_composite_hashes(module_def.file_path)
            new_hashes = copy.deepcopy(stored_hashes)
            current_yaml_map = self.doc_manager.compute_yaml_content_hashes(module_def)

            for violation in doc_update_violations:
                fqn = violation.fqn
                if fqn in new_hashes:
                    new_yaml_hash = current_yaml_map.get(fqn)
                    if new_yaml_hash is not None:
                        new_hashes[fqn]["baseline_yaml_content_hash"] = new_yaml_hash
                    elif "baseline_yaml_content_hash" in new_hashes[fqn]:
                        del new_hashes[fqn]["baseline_yaml_content_hash"]

            if new_hashes != stored_hashes:
                self.sig_manager.save_composite_hashes(module_def.file_path, new_hashes)
~~~~~
~~~~~python.new
    def auto_reconcile_docs(
        self, results: List[FileCheckResult], modules: List[ModuleDef]
    ):
        # Group by package to batch lock updates
        updates_by_pkg: Dict[Path, Dict[str, Fingerprint]] = defaultdict(dict)
        
        # Pre-load needed lock data? Or load on demand.
        # Since this is auto-reconcile, we iterate results.
        
        for res in results:
            doc_update_violations = [
                v for v in res.info_violations if v.kind == L.check.state.doc_updated
            ]
            if not doc_update_violations:
                continue

            module_def = next((m for m in modules if m.file_path == res.path), None)
            if not module_def:
                continue
                
            abs_path = self.root_path / module_def.file_path
            pkg_root = self.workspace.find_owning_package(abs_path)
            ws_rel_path = self.workspace.to_workspace_relative(abs_path)
            
            # Load lock only if not already loaded for this batch? 
            # For simplicity, we load fresh, update in memory, then save later.
            # But here we need cumulative updates.
            if pkg_root not in updates_by_pkg:
                updates_by_pkg[pkg_root] = self.lock_manager.load(pkg_root)
            
            lock_data = updates_by_pkg[pkg_root]
            current_yaml_map = self.doc_manager.compute_yaml_content_hashes(module_def)

            for violation in doc_update_violations:
                fqn = violation.fqn
                suri = self.uri_generator.generate_symbol_uri(ws_rel_path, fqn)
                
                if suri in lock_data:
                    fp = lock_data[suri]
                    new_yaml_hash = current_yaml_map.get(fqn)
                    
                    if new_yaml_hash is not None:
                        fp["baseline_yaml_content_hash"] = new_yaml_hash
                    elif "baseline_yaml_content_hash" in fp:
                        del fp["baseline_yaml_content_hash"]
                        
        # Save all updated locks
        for pkg_root, lock_data in updates_by_pkg.items():
            self.lock_manager.save(pkg_root, lock_data)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
    def _apply_resolutions(
        self, resolutions: dict[str, list[tuple[InteractionContext, ResolutionAction]]]
    ):
        sig_updates_by_file = defaultdict(list)
        purges_by_file = defaultdict(list)

        for file_path, context_actions in resolutions.items():
            for context, action in context_actions:
                if action in [ResolutionAction.RELINK, ResolutionAction.RECONCILE]:
                    sig_updates_by_file[file_path].append((context.fqn, action))
                elif action == ResolutionAction.PURGE_DOC:
                    purges_by_file[file_path].append(context.fqn)

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
~~~~~
~~~~~python.new
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
            has_sig_updates = any(a in [ResolutionAction.RELINK, ResolutionAction.RECONCILE] for _, a in context_actions)
            
            computed_fingerprints = {}
            current_yaml_map = {}
            
            if has_sig_updates:
                full_module_def = self.parser.parse(
                    abs_path.read_text("utf-8"), file_path
                )
                computed_fingerprints = self._compute_fingerprints(full_module_def)
                current_yaml_map = self.doc_manager.compute_yaml_content_hashes(full_module_def)

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
                            fp["baseline_yaml_content_hash"] = str(current_yaml_map[fqn])

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
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
    def reformat_all(self, modules: List[ModuleDef]):
        bus.info(L.check.run.reformatting)
        for module in modules:
            self.doc_manager.reformat_docs_for_module(module)
            self.sig_manager.reformat_hashes_for_file(module.file_path)
~~~~~
~~~~~python.new
    def reformat_all(self, modules: List[ModuleDef]):
        bus.info(L.check.run.reformatting)
        # Reformatting only applies to docs now. Lock file is auto-formatted on save.
        for module in modules:
            self.doc_manager.reformat_docs_for_module(module)
~~~~~

#### Acts 3: 重写 `CheckRunner` (`stitcher-application`)

更新 Runner 入口。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    DifferProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
from stitcher.spec.interaction import InteractionContext
from stitcher.analysis.schema import FileCheckResult as AnalysisFileCheckResult

from stitcher.app.runners.check.resolver import CheckResolver
from stitcher.app.runners.check.reporter import CheckReporter
from .subject import IndexCheckSubjectAdapter, ASTCheckSubjectAdapter
from stitcher.analysis.engines.consistency.engine import create_consistency_engine


class CheckRunner:
    def __init__(
        self,
        doc_manager: DocumentManagerProtocol,
        sig_manager: SignatureManagerProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        index_store: IndexStoreProtocol,
        differ: DifferProtocol,
        resolver: CheckResolver,
        reporter: CheckReporter,
        root_path: Path,
    ):
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.fingerprint_strategy = fingerprint_strategy
        self.index_store = index_store
        self.root_path = root_path

        self.engine = create_consistency_engine(differ=differ)
        self.resolver = resolver
        self.reporter = reporter
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
    DifferProtocol,
    LockManagerProtocol,
    URIGeneratorProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol
from stitcher.spec.interaction import InteractionContext
from stitcher.analysis.schema import FileCheckResult as AnalysisFileCheckResult

from stitcher.app.runners.check.resolver import CheckResolver
from stitcher.app.runners.check.reporter import CheckReporter
from .subject import IndexCheckSubjectAdapter, ASTCheckSubjectAdapter
from stitcher.analysis.engines.consistency.engine import create_consistency_engine
from stitcher.workspace import Workspace


class CheckRunner:
    def __init__(
        self,
        doc_manager: DocumentManagerProtocol,
        lock_manager: LockManagerProtocol,
        uri_generator: URIGeneratorProtocol,
        fingerprint_strategy: FingerprintStrategyProtocol,
        index_store: IndexStoreProtocol,
        workspace: Workspace,
        differ: DifferProtocol,
        resolver: CheckResolver,
        reporter: CheckReporter,
        root_path: Path,
    ):
        self.doc_manager = doc_manager
        self.lock_manager = lock_manager
        self.uri_generator = uri_generator
        self.fingerprint_strategy = fingerprint_strategy
        self.index_store = index_store
        self.workspace = workspace
        self.root_path = root_path

        self.engine = create_consistency_engine(differ=differ)
        self.resolver = resolver
        self.reporter = reporter
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
        for file_path in file_paths:
            subject = IndexCheckSubjectAdapter(
                file_path,
                self.index_store,
                self.doc_manager,
                self.sig_manager,
                self.root_path,
            )
            analysis_result = self.engine.analyze(subject)
~~~~~
~~~~~python.new
        for file_path in file_paths:
            subject = IndexCheckSubjectAdapter(
                file_path,
                self.index_store,
                self.doc_manager,
                self.lock_manager,
                self.uri_generator,
                self.workspace,
                self.root_path,
            )
            analysis_result = self.engine.analyze(subject)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
        for module in modules:
            subject = ASTCheckSubjectAdapter(
                module,
                self.doc_manager,
                self.sig_manager,
                self.fingerprint_strategy,
                self.root_path,
            )
            analysis_result = self.engine.analyze(subject)
~~~~~
~~~~~python.new
        for module in modules:
            subject = ASTCheckSubjectAdapter(
                module,
                self.doc_manager,
                self.lock_manager,
                self.uri_generator,
                self.workspace,
                self.fingerprint_strategy,
                self.root_path,
            )
            analysis_result = self.engine.analyze(subject)
~~~~~

### 下一步建议
我们已经完成了应用层的代码重写。现在所有的 Runner 应该都能基于新的 LockFileManager 工作。

接下来的步骤是 **阶段 4: 重构引擎简化 (Refactor Engine Lobotomy)**。我们需要去 `stitcher-refactor` 包中，把那些复杂的、针对旧签名文件的移动/重命名逻辑砍掉，换成简单的 Lock 更新逻辑。完成那一步之后，我们就可以进行全面的清理和测试修复了。
