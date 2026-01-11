好的，我将开始实施 Zero-IO Check 路线图的第一阶段。

此阶段的核心是创建一个新的 `IndexCheckSubjectAdapter`，它将作为 `CheckAnalyzer` 的数据源，但其数据完全来自预先构建的 SQLite 索引，而不是通过实时解析 Python 文件的 AST。这将为后续阶段消除 I/O 瓶颈奠定基础。

我将修改 `packages/stitcher-application/src/stitcher/app/runners/check/subject.py` 文件，在现有的 `ASTCheckSubjectAdapter` 旁边添加新的 `IndexCheckSubjectAdapter` 实现。

## [WIP] feat: 实现基于索引的 IndexCheckSubjectAdapter

### 用户需求

根据 Zero-IO Check 路线图的第一阶段，需要创建一个名为 `IndexCheckSubjectAdapter` 的新类，该类实现 `CheckSubject` 协议，但其数据完全来源于 SQLite 索引 (`IndexStore`)，而不是通过解析 AST。

### 评论

这是实现 Zero-IO Check 的关键一步。通过创建一个与 `ASTCheckSubjectAdapter` 接口兼容但数据源不同的适配器，我们可以无缝地将 `CheckRunner` 的底层数据提供者切换到数据库，而无需修改核心的检查逻辑 (`CheckAnalyzer`)。这体现了良好的分层设计和依赖倒置原则。

### 目标

1.  在 `stitcher.app.runners.check.subject` 模块中创建 `IndexCheckSubjectAdapter` 类。
2.  实现该类，使其通过 `IndexStore`, `DocumentManager`, 和 `SignatureManager` 获取所有必要的数据。
3.  确保 `get_all_symbol_states` 方法能正确地将 `SymbolRecord` 映射为 `SymbolState`，并正确处理模块文档 (`__doc__`) 和符号可见性。
4.  实现 `is_documentable` 方法，使其行为与 AST 版本保持一致。

### 基本原理

新的 `IndexCheckSubjectAdapter` 将遵循 `CheckSubject` 协议，使其可以被 `CheckAnalyzer` 透明地使用。

-   **数据源**：它将从三个地方聚合信息：
    1.  `IndexStore`：获取所有符号的定义、签名哈希、文档内容等代码侧信息。
    2.  `DocumentManager`：加载 `.stitcher.yaml` 文件以获取文档侧信息。
    3.  `SignatureManager`：加载 `.stitcher/signatures/` 文件以获取基线哈希。
-   **核心逻辑**：`get_all_symbol_states` 方法是核心。它会整合来自上述三个数据源的所有 FQN，然后为每个 FQN 构建一个完整的 `SymbolState` 快照，描述其在代码、YAML 和基线中的完整状态。
-   **性能**：此适配器执行的所有操作（DB 查询、YAML 读取、JSON 读取）都比解析 Python AST 快几个数量级，从而为后续的性能提升奠定了基础。

### 标签

#intent/build #flow/ready #priority/high
#comp/engine #concept/state #scope/core
#ai/instruct
#task/domain/testing #task/object/zero-io-check #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 实现 IndexCheckSubjectAdapter

我将向 `subject.py` 文件中添加新的 `IndexCheckSubjectAdapter` 类及其完整实现。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
from typing import Dict
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    FingerprintStrategyProtocol,
)
from stitcher.app.services import DocumentManager, SignatureManager
from .protocols import SymbolState, CheckSubject


class ASTCheckSubjectAdapter(CheckSubject):
~~~~~
~~~~~python.new
from typing import Dict, Optional
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    FingerprintStrategyProtocol,
)
from stitcher.app.services import DocumentManager, SignatureManager
from stitcher.index.store import IndexStore
from stitcher.index.types import SymbolRecord
from .protocols import SymbolState, CheckSubject


class IndexCheckSubjectAdapter(CheckSubject):
    def __init__(
        self,
        file_path: str,
        index_store: IndexStore,
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
    ):
        self._file_path = file_path
        self._index_store = index_store
        self._doc_manager = doc_manager
        self._sig_manager = sig_manager

    @property
    def file_path(self) -> str:
        return self._file_path

    def _is_public(self, fqn: str) -> bool:
        # Replicate public visibility logic from AST-based approach
        parts = fqn.split(".")
        return not any(p.startswith("_") and p != "__doc__" for p in parts)

    def is_documentable(self) -> bool:
        symbols = self._index_store.get_symbols_by_file_path(self.file_path)
        if not symbols:
            return False

        for sym in symbols:
            if sym.kind == "module" and sym.docstring_content:
                return True
            if sym.logical_path and self._is_public(sym.logical_path):
                return True
        return False

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load data from all sources
        symbols_from_db = self._index_store.get_symbols_by_file_path(self.file_path)
        yaml_docs = self._doc_manager.load_docs_for_path(self.file_path)
        stored_hashes = self._sig_manager.load_composite_hashes(self.file_path)

        yaml_content_hashes = {
            fqn: self._doc_manager.compute_yaml_content_hash(
                self._doc_manager._serialize_ir(ir)
            )
            for fqn, ir in yaml_docs.items()
        }

        # 2. Map symbols for easy lookup
        symbol_map: Dict[str, SymbolRecord] = {}
        module_symbol: Optional[SymbolRecord] = None
        for sym in symbols_from_db:
            if sym.kind == "module":
                module_symbol = sym
            elif sym.logical_path:
                symbol_map[sym.logical_path] = sym

        # 3. Aggregate all unique FQNs
        all_fqns = (
            set(symbol_map.keys())
            | set(yaml_docs.keys())
            | set(stored_hashes.keys())
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
                fqn=fqn,
                is_public=self._is_public(fqn),
                # Source Code State (from Index)
                exists_in_code=(symbol_rec is not None),
                source_doc_content=symbol_rec.docstring_content if symbol_rec else None,
                signature_hash=symbol_rec.signature_hash if symbol_rec else None,
                signature_text=symbol_rec.signature_text if symbol_rec else None,
                # YAML State
                exists_in_yaml=(fqn in yaml_docs),
                yaml_doc_ir=yaml_docs.get(fqn),
                yaml_content_hash=yaml_content_hashes.get(fqn),
                # Baseline State
                baseline_signature_hash=stored_fp.get("baseline_code_structure_hash"),
                baseline_signature_text=stored_fp.get("baseline_code_signature_text"),
                baseline_yaml_content_hash=stored_fp.get("baseline_yaml_content_hash"),
            )

        return states


class ASTCheckSubjectAdapter(CheckSubject):
~~~~~

### 下一步建议

我们已经成功实现了第一阶段。`IndexCheckSubjectAdapter` 现在已经可用，它为 `CheckAnalyzer` 提供了一个完全基于数据库的数据视图。

下一步是实施路线图的**第二阶段：重构 `CheckRunner` 的驱动模式**。我将修改 `CheckRunner`，为其增加一个新的 `analyze_paths` 方法，该方法接收文件路径列表并使用我们刚刚创建的 `IndexCheckSubjectAdapter` 来执行分析，从而摆脱对 `ModuleDef` 对象的直接依赖。

如果你同意，我将立即开始制定第二阶段的计划。
