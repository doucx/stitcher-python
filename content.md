## [WIP] feat(analysis): Define core analysis contracts and schemas

### 用户需求

实现 Phase 1 的第 2 步：定义分析契约。这意味着在 `stitcher-analysis` 包中建立核心数据结构和接口协议，为后续的逻辑迁移打下基础。具体包括 `SymbolState`、`FileCheckResult` 的迁移重定义，以及 `AnalysisSubject` 协议的定义。

### 评论

这是解耦过程中的关键一步。我们通过在 `stitcher-analysis` 中建立这些“标准”定义，实际上是在定义 `stitcher-application`（作为调用者）和 `stitcher-analysis`（作为执行者）之间的通信语言。在这一步，我们先进行“加法”，即在通过新包中创建这些结构，暂不修改旧包，以确保迁移的安全性。

### 目标

1.  在 `stitcher-analysis` 中创建 `schema` 子包，并在其中定义 `SymbolState` 和 `FileCheckResult`。
2.  在 `stitcher-analysis` 中创建 `protocols` 模块，并定义 `AnalysisSubject` 协议（它是原 `CheckSubject` 的泛化）。

### 基本原理

我们将严格按照 XML 上下文中现有的定义来重建这些类，确保与现有逻辑兼容。
- `SymbolState`: 这是一个核心的数据载体，用于描述一个符号在代码、YAML 和基线（History）中的三态。
- `FileCheckResult`: 这是分析结果的标准容器。
- `AnalysisSubject`: 这是分析引擎对输入对象的抽象，使得引擎可以不关心具体的 AST 或 Index 实现细节。

### 标签

#intent/architect #intent/build #flow/ready #priority/high #comp/interfaces #scope/core #ai/instruct #task/domain/architecture #task/object/analysis-engine #task/action/define-contracts #task/state/continue

---

### Script

#### Acts 1: 创建 Schema 和 Protocol 目录

首先创建存放契约定义的目录。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-analysis/src/stitcher/analysis/schema
mkdir -p packages/stitcher-analysis/src/stitcher/analysis/protocols
touch packages/stitcher-analysis/src/stitcher/analysis/schema/__init__.py
touch packages/stitcher-analysis/src/stitcher/analysis/protocols/__init__.py
~~~~~

#### Acts 2: 定义 `SymbolState` Schema

这是分析逻辑中最基础的数据单元，描述了符号的多维状态。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/schema/symbol_state.py
~~~~~
~~~~~python
from dataclasses import dataclass
from typing import Optional

from stitcher.spec import DocstringIR


@dataclass
class SymbolState:
    """
    Represents the state of a symbol across three dimensions:
    1. Source Code (Current Reality)
    2. YAML Documentation (Stored Documentation)
    3. Baseline/Signature History (Last Known State)
    """

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
~~~~~

#### Acts 3: 定义 `FileCheckResult` Schema

这是分析结果的载体，用于向调用者报告发现的问题。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/schema/results.py
~~~~~
~~~~~python
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, List


@dataclass
class FileCheckResult:
    """
    Aggregates all analysis results (errors, warnings, infos) for a single file.
    """

    path: str
    errors: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    warnings: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    infos: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    # Used for tracking auto-reconciliation actions performed during analysis
    reconciled: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    auto_reconciled_count: int = 0

    @property
    def error_count(self) -> int:
        return sum(len(keys) for keys in self.errors.values())

    @property
    def warning_count(self) -> int:
        return sum(len(keys) for keys in self.warnings.values())

    @property
    def reconciled_count(self) -> int:
        return sum(len(keys) for keys in self.reconciled.values())

    @property
    def is_clean(self) -> bool:
        return (
            self.error_count == 0
            and self.warning_count == 0
            and self.reconciled_count == 0
            # Auto-reconciled (infos) do not affect cleanliness
        )
~~~~~

#### Acts 4: 暴露 Schema

更新 `schema/__init__.py` 以方便导入。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/schema/__init__.py
~~~~~
~~~~~python
from .symbol_state import SymbolState
from .results import FileCheckResult

__all__ = ["SymbolState", "FileCheckResult"]
~~~~~

#### Acts 5: 定义 `AnalysisSubject` 协议

定义引擎对输入对象的预期接口。这个协议解耦了引擎与具体的数据来源（如 Index 或 AST）。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/protocols/__init__.py
~~~~~
~~~~~python
from typing import Protocol, Dict

from stitcher.analysis.schema import SymbolState


class AnalysisSubject(Protocol):
    """
    A protocol defining the interface for any subject (file/module)
    that can be analyzed by the consistency engine.
    """

    @property
    def file_path(self) -> str:
        """The relative path of the file being analyzed."""
        ...

    def is_documentable(self) -> bool:
        """Whether this subject contains any documentable entities."""
        ...

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        """
        Retrieves the complete state map for all symbols in this subject,
        aggregating data from code, yaml, and history.
        """
        ...
~~~~~

### 下一步建议

契约层已定义完成。下一步，我们将进入核心逻辑的提取阶段 (**Phase 1.3**)。

建议开始提取 Check 规则。我们将把原 `CheckAnalyzer` 中庞大的 `analyze_subject` 方法拆解为多个独立的、单一职责的规则类（如 `DocstringContentRule`, `SignatureRule` 等）。我们将从创建规则基类 `Rule` 开始。如果你同意，我将生成该计划。
