了解。我们立即开始计划的第二阶段。

现在我们已经定义了稳定的 `CheckSubject` 协议和 `ASTCheckSubjectAdapter`，是时候重构 `CheckAnalyzer`，使其完全依赖于这个新的抽象层。这将是本次重构中逻辑变更最集中的一步，但由于我们有了清晰的契约，风险已经被有效控制。

## [WIP] refactor(check): 重构 CheckAnalyzer 以使用 CheckSubject 协议

### 用户需求

修改 `CheckAnalyzer`，移除其对多个底层服务的直接依赖，使其唯一的输入源是 `CheckSubject` 协议。同时，更新 `CheckRunner` 以协调 `ASTCheckSubjectAdapter` 的创建和传递。

### 评论

这是整个重构任务的核心。通过将 `CheckAnalyzer` 的业务逻辑与数据获取逻辑分离开，我们不仅极大地简化了 `CheckAnalyzer` 本身，使其更容易测试和理解，而且还为未来的“数据库驱动”模式的引入铺平了道路。这个步骤完成后，我们的 `check` 流程将在新的、更健壮的架构上运行，尽管其外部行为不会有任何改变。

### 目标

1.  **扩展协议**：为 `SymbolState` 和 `CheckSubject` 添加 `baseline` 状态和 `is_documentable` 方法，以满足 `CheckAnalyzer` 的全部信息需求。
2.  **更新适配器**：增强 `ASTCheckSubjectAdapter`，使其能够加载并提供这些 `baseline` 状态。
3.  **重写 Analyzer**：彻底重写 `CheckAnalyzer._analyze_file` 方法，使其所有判定逻辑（Missing, Pending, Conflict, Drift 等）都基于从 `CheckSubject` 获取的 `SymbolState`。
4.  **调整 Runner**：修改 `CheckRunner`，使其作为协调者，负责创建 `ASTCheckSubjectAdapter` 实例并将其传递给 `CheckAnalyzer`。

### 基本原理

我们正在将“做什么（What）”和“从哪里获取信息（How）”分离开。`CheckAnalyzer` 现在只关心“做什么”——即应用一组纯粹的业务规则来比较符号状态。而“如何获取信息”的复杂性则被完全封装在 `ASTCheckSubjectAdapter` 中。这种分离使得系统的每一部分都更加内聚、更易于维护。

### 标签

#intent/refine #flow/ready #priority/high #comp/application #task/domain/quality #task/object/check-runner #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 扩展协议以包含 Baseline 状态

`CheckAnalyzer` 需要 `baseline` 数据来进行比较。我们首先在 `protocols.py` 中扩展我们的数据契约。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/protocols.py
~~~~~
~~~~~python.old
@dataclass
class SymbolState:
    """A complete snapshot of a symbol's state from all sources."""

    fqn: str
    is_public: bool

    # --- Source Code State ---
    exists_in_code: bool
    source_doc_content: Optional[str]
    signature_hash: Optional[str]
    signature_text: Optional[str]

    # --- YAML Documentation State ---
    exists_in_yaml: bool
    yaml_doc_ir: Optional[DocstringIR]
    yaml_content_hash: Optional[str]


class CheckSubject(Protocol):
    """The contract for what the CheckAnalyzer can inspect."""

    @property
    def file_path(self) -> str:
        ...

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        """
        Gets the aggregated state of all symbols relevant to this subject.
        This includes symbols defined in code and/or documented in YAML.
        """
        ...
~~~~~
~~~~~python.new
from typing import Protocol, Dict, Optional
from dataclasses import dataclass
from stitcher.spec import DocstringIR


@dataclass
class SymbolState:
    """A complete snapshot of a symbol's state from all sources."""

    fqn: str
    is_public: bool

    # --- Source Code State (Current) ---
    exists_in_code: bool
    source_doc_content: Optional[str]
    signature_hash: Optional[str]
    signature_text: Optional[str]

    # --- YAML Documentation State (Current) ---
    exists_in_yaml: bool
    yaml_doc_ir: Optional[DocstringIR]
    yaml_content_hash: Optional[str]
    
    # --- Baseline State (Stored) ---
    baseline_signature_hash: Optional[str]
    baseline_signature_text: Optional[str]
    baseline_yaml_content_hash: Optional[str]


class CheckSubject(Protocol):
    """The contract for what the CheckAnalyzer can inspect."""

    @property
    def file_path(self) -> str:
        ...
        
    def is_documentable(self) -> bool:
        """Checks if the subject as a whole is worth tracking."""
        ...

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        """
        Gets the aggregated state of all symbols relevant to this subject.
        This includes symbols defined in code and/or documented in YAML.
        """
        ...
~~~~~

#### Acts 2: 增强 AST 适配器以提供 Baseline 数据

现在我们更新 `ASTCheckSubjectAdapter`，使其加载并填充这些新的 `baseline` 字段。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load all necessary data from various sources (the old way)
        source_docs = self._doc_manager.flatten_module_docs(self._module)
        yaml_docs = self._doc_manager.load_docs_for_module(self._module)
        public_fqns = self._module.get_public_documentable_fqns()
        
        fingerprints = self._compute_fingerprints()
        yaml_hashes = self._doc_manager.compute_yaml_content_hashes(self._module)
        
        all_fqns = set(source_docs.keys()) | set(yaml_docs.keys())
        states: Dict[str, SymbolState] = {}

        # 2. Iterate and build the state object for each symbol
        for fqn in all_fqns:
            fp = fingerprints.get(fqn, Fingerprint())
            source_ir = source_docs.get(fqn)
            
            states[fqn] = SymbolState(
                fqn=fqn,
                is_public=(fqn in public_fqns),
                exists_in_code=(fqn in source_docs),
                source_doc_content=source_ir.summary if source_ir else None,
                signature_hash=fp.get("current_code_structure_hash"),
                signature_text=fp.get("current_code_signature_text"),
                exists_in_yaml=(fqn in yaml_docs),
                yaml_doc_ir=yaml_docs.get(fqn),
                yaml_content_hash=yaml_hashes.get(fqn),
            )
            
        return states
~~~~~
~~~~~python.new
    def is_documentable(self) -> bool:
        return self._module.is_documentable()

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load all necessary data from various sources (the old way)
        source_docs = self._doc_manager.flatten_module_docs(self._module)
        yaml_docs = self._doc_manager.load_docs_for_module(self._module)
        public_fqns = self._module.get_public_documentable_fqns()

        fingerprints = self._compute_fingerprints()
        yaml_hashes = self._doc_manager.compute_yaml_content_hashes(self._module)
        stored_hashes = self._sig_manager.load_composite_hashes(self.file_path)

        all_fqns = set(source_docs.keys()) | set(yaml_docs.keys()) | set(stored_hashes.keys())
        states: Dict[str, SymbolState] = {}

        # 2. Iterate and build the state object for each symbol
        for fqn in all_fqns:
            fp = fingerprints.get(fqn, Fingerprint())
            source_ir = source_docs.get(fqn)
            stored_fp = stored_hashes.get(fqn, Fingerprint())

            states[fqn] = SymbolState(
                fqn=fqn,
                is_public=(fqn in public_fqns),
                exists_in_code=(fqn in source_docs),
                source_doc_content=source_ir.summary if source_ir else None,
                signature_hash=fp.get("current_code_structure_hash"),
                signature_text=fp.get("current_code_signature_text"),
                exists_in_yaml=(fqn in yaml_docs),
                yaml_doc_ir=yaml_docs.get(fqn),
                yaml_content_hash=yaml_hashes.get(fqn),
                baseline_signature_hash=stored_fp.get("baseline_code_structure_hash"),
                baseline_signature_text=stored_fp.get("baseline_code_signature_text"),
                baseline_yaml_content_hash=stored_fp.get("baseline_yaml_content_hash"),
            )

        return states
~~~~~

#### Acts 3: 重构 Analyzer 以使用新协议

这是核心步骤。我们将 `CheckAnalyzer` 的逻辑完全替换为基于 `CheckSubject` 的新实现。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/check/analyzer.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Tuple

from stitcher.spec import ConflictType
from stitcher.app.services import Differ
from stitcher.app.protocols import InteractionContext
from stitcher.app.types import FileCheckResult
from .protocols import CheckSubject


class CheckAnalyzer:
    def __init__(self, root_path: Path, differ: Differ):
        self.root_path = root_path
        self.differ = differ

    def analyze_subject(
        self, subject: CheckSubject
    ) -> Tuple[FileCheckResult, List[InteractionContext]]:
        result = FileCheckResult(path=subject.file_path)
        unresolved_conflicts: List[InteractionContext] = []

        is_tracked = (self.root_path / subject.file_path).with_suffix(".stitcher.yaml").exists()

        for fqn, state in subject.get_all_symbol_states().items():
            # --- State Machine Logic ---
            
            # 1. Content Checks
            if state.exists_in_code and state.exists_in_yaml:
                if state.source_doc_content and state.yaml_doc_ir:
                    if state.source_doc_content == state.yaml_doc_ir.summary:
                        result.warnings["redundant"].append(fqn)
                    else:
                        result.errors["conflict"].append(fqn)

            elif state.is_public and state.exists_in_code and not state.exists_in_yaml:
                if state.source_doc_content:
                    result.errors["pending"].append(fqn)
                else:
                    result.warnings["missing"].append(fqn)

            elif not state.exists_in_code and state.exists_in_yaml:
                unresolved_conflicts.append(
                    InteractionContext(subject.file_path, fqn, ConflictType.DANGLING_DOC)
                )

            # 2. Signature Checks
            code_hash = state.signature_hash
            baseline_code_hash = state.baseline_signature_hash
            
            if code_hash and not baseline_code_hash: # New symbol, skip
                continue
            if not code_hash and baseline_code_hash: # Deleted symbol, handled by DANGLING_DOC
                continue
            
            code_matches = code_hash == baseline_code_hash
            yaml_matches = state.yaml_content_hash == state.baseline_yaml_content_hash

            if code_matches and not yaml_matches:
                result.infos["doc_improvement"].append(fqn)
            elif not code_matches:
                sig_diff = self.differ.generate_text_diff(
                    state.baseline_signature_text or "",
                    state.signature_text or "",
                    "baseline",
                    "current",
                )
                
                conflict_type = (
                    ConflictType.SIGNATURE_DRIFT
                    if yaml_matches
                    else ConflictType.CO_EVOLUTION
                )
                unresolved_conflicts.append(
                    InteractionContext(
                        subject.file_path, fqn, conflict_type, signature_diff=sig_diff
                    )
                )

        # 3. Untracked File Check
        if not is_tracked and subject.is_documentable():
            # Check for any public symbols that would be documented
            undocumented = [
                s.fqn
                for s in subject.get_all_symbol_states().values()
                if s.is_public and not s.source_doc_content and not s.exists_in_yaml
            ]
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        return result, unresolved_conflicts
~~~~~

#### Acts 4: 调整 Runner 以协调适配器和分析器

最后，我们更新 `CheckRunner`，让它负责创建 `ASTCheckSubjectAdapter` 并将其传递给新的 `CheckAnalyzer`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
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
        self.analyzer = CheckAnalyzer(
            root_path, doc_manager, sig_manager, differ, fingerprint_strategy
        )
        self.resolver = CheckResolver(
            root_path,
            parser,
            doc_manager,
            sig_manager,
            interaction_handler,
            fingerprint_strategy,
        )
        self.reporter = CheckReporter()

    def analyze_batch(
        self, modules: List[ModuleDef]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        return self.analyzer.analyze_batch(modules)
~~~~~
~~~~~python.new
from .subject import ASTCheckSubjectAdapter


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
        # Keep services needed by both adapter and resolver
        self.root_path = root_path
        self.parser = parser
        self.doc_manager = doc_manager
        self.sig_manager = sig_manager
        self.fingerprint_strategy = fingerprint_strategy

        # Inject dependencies into sub-components
        self.analyzer = CheckAnalyzer(root_path, differ)
        self.resolver = CheckResolver(
            root_path,
            parser,
            doc_manager,
            sig_manager,
            interaction_handler,
            fingerprint_strategy,
        )
        self.reporter = CheckReporter()

    def analyze_batch(
        self, modules: List[ModuleDef]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        all_results: List[FileCheckResult] = []
        all_conflicts: List[InteractionContext] = []

        for module in modules:
            # Create the adapter (subject) for each module
            subject = ASTCheckSubjectAdapter(
                module,
                self.doc_manager,
                self.sig_manager,
                self._fingerprint_strategy,
            )
            
            # Analyze using the subject
            result, conflicts = self.analyzer.analyze_subject(subject)
            all_results.append(result)
            all_conflicts.extend(conflicts)
            
        return all_results, all_conflicts
~~~~~

### 下一步建议

我们已经成功地将 `CheckAnalyzer` 重构为使用 `CheckSubject` 协议。现在，整个 `check` 流程的逻辑和之前完全一样，但是内部结构已经为下一步的切换做好了准备。

建议下一步：

1.  **全面测试**：运行完整的测试套件，确保这次重大的内部重构没有引入任何回归问题。
2.  **创建 `IndexCheckSubjectAdapter`**：一旦测试通过，我们就可以开始实现新的、基于数据库的适配器。
3.  **切换**：在 `StitcherApp` 中，将 `CheckRunner` 的数据源从 `ModuleDef` 扫描切换为直接从 `IndexStore` 获取文件列表，并实例化 `IndexCheckSubjectAdapter`。

请先运行测试，确认一切正常后，我们可以继续。
