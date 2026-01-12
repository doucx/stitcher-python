这是一个基于 `pyneedle` 的、高度语义化的分析层构建计划。

我们将把 `SemanticPointer` 作为分析结果的一等公民，彻底摒弃硬编码字符串。

## [WIP] feat(analysis): Define Needle-based analysis contracts

### 用户需求

实施 Phase 1.2：定义分析契约。
关键变更：采用基于 `pyneedle` 的 `Violation` 结构替代传统的字典结构。分析引擎将产生包含 `SemanticPointer` 的 `Violation` 对象，从而实现“语义化错误码”。

### 评论

这个设计非常优雅。它不仅解决了“魔术字符串”的问题，还让 `stitcher-analysis` 与 `FeedbackBus` 实现了完美的协同。分析引擎只负责产生语义（指针），而展示层（Bus/Reporter）负责解释语义（模板渲染），这完全符合单一职责原则。

### 目标

1.  更新 `stitcher-analysis` 的依赖，引入 `pyneedle-pointer`。
2.  定义核心 Schema：
    *   `SymbolState`: 保持原设计，描述符号的三态。
    *   `Violation`: **新核心**，使用 `SemanticPointer` 描述问题类型。
    *   `FileCheckResult`: 更新为包含 `List[Violation]` 的容器。
3.  定义核心 Protocol：
    *   `AnalysisSubject`: 定义分析引擎的输入接口。

### 基本原理

1.  **依赖注入**: 首先需要在 `pyproject.toml` 中声明对 `pyneedle-pointer` 的依赖，这是实现语义指针的基础。
2.  **Schema 定义**:
    *   `symbol_state.py`: 承载数据状态。
    *   `violation.py`: 引入 `SemanticPointer`，作为分析结果的最小单元。
    *   `results.py`: 聚合 `Violation`，移除旧的字典分类逻辑，使结构扁平化。
3.  **Protocol 定义**: 明确引擎与数据的边界。

### 标签

#intent/architect #intent/build #flow/ready #priority/high #comp/interfaces #scope/core #ai/instruct #task/domain/architecture #task/object/analysis-engine #task/action/define-contracts #task/state/continue

---

### Script

#### Acts 1: 添加 `pyneedle-pointer` 依赖

我们需要 `pyneedle-pointer` 包来使用 `SemanticPointer` 类。

~~~~~act
patch_file
packages/stitcher-analysis/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-index",
    "stitcher-config",
]

[tool.hatch.build.targets.wheel]
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-index",
    "stitcher-config",
    "pyneedle-pointer",
]

[tool.hatch.build.targets.wheel]
~~~~~

~~~~~act
patch_file
packages/stitcher-analysis/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-config = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
stitcher-config = { workspace = true }
pyneedle-pointer = { workspace = true }
~~~~~

#### Acts 2: 定义 `SymbolState` Schema

定义符号的三态数据结构。

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

#### Acts 3: 定义 `Violation` Schema

这是实现“语义指针即错误码”的核心类。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/schema/violation.py
~~~~~
~~~~~python
from dataclasses import dataclass, field
from typing import Dict, Any
from needle.pointer import SemanticPointer


@dataclass
class Violation:
    """
    Represents a specific finding or issue identified by the analysis engine.
    Instead of using string keys, it uses SemanticPointers to strictly type the issue kind.
    """

    # The semantic type of the violation (e.g., L.issue.signature_drift)
    kind: SemanticPointer

    # The fully qualified name of the symbol where the violation occurred
    fqn: str

    # Contextual data required to render the message (e.g., diffs, counts)
    context: Dict[str, Any] = field(default_factory=dict)
~~~~~

#### Acts 4: 定义 `FileCheckResult` Schema

更新后的结果容器，使用扁平化的 `Violation` 列表。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/schema/results.py
~~~~~
~~~~~python
from dataclasses import dataclass, field
from typing import List

from .violation import Violation


@dataclass
class FileCheckResult:
    """
    Aggregates all analysis results for a single file.
    Uses a flat list of Violations instead of categorizing by severity/type,
    delegating interpretation to the consumer/reporter.
    """

    path: str
    
    # All findings (errors, warnings, infos)
    violations: List[Violation] = field(default_factory=list)
    
    # Records of actions taken during auto-reconciliation
    # Reconciled items are also fundamentally Violations that were resolved.
    reconciled: List[Violation] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """
        A file is clean if there are no active violations.
        Reconciled items do not count against cleanliness as they are resolved.
        """
        return len(self.violations) == 0
~~~~~

#### Acts 5: 暴露 Schema

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/schema/__init__.py
~~~~~
~~~~~python
from .symbol_state import SymbolState
from .violation import Violation
from .results import FileCheckResult

__all__ = ["SymbolState", "Violation", "FileCheckResult"]
~~~~~

#### Acts 6: 定义 `AnalysisSubject` Protocol

定义分析引擎的输入接口。

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/protocols/subject.py
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

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/protocols/__init__.py
~~~~~
~~~~~python
from .subject import AnalysisSubject

__all__ = ["AnalysisSubject"]
~~~~~

### 下一步建议

契约层定义完毕。现在我们有了基于 `SemanticPointer` 的数据结构。

接下来的步骤 (**Phase 1.3**) 是开始提取具体的 Check 规则。我们将利用新的 `Violation` 结构来编写规则。

建议首先定义规则的基类 `Rule` 接口，然后实现第一个具体的规则类（例如 `SignatureRule`），展示如何通过分析 `SymbolState` 并返回 `List[Violation]`。这将验证我们的新架构是否顺畅。
