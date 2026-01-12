好的，我们来执行协议文件的结构化重构。`refactor` 包已卸载，相关操作将跳过。

## [WIP] refactor(spec): 将服务协议按领域划分到独立文件

### 用户需求
根据路线图的要求，将 `stitcher-spec/src/stitcher/spec/protocols.py` 中定义的 `DocumentManagerProtocol` 和 `SignatureManagerProtocol` 移动到新的 `managers.py` 文件中，以改善代码组织结构。

### 评论
随着协议数量的增加，将所有协议都放在一个 `protocols.py` 文件中会变得难以维护。按照领域（如 `storage`, `managers`）将它们分拆到不同的文件中，可以使 `stitcher-spec` 包的内部结构更清晰、更符合逻辑，便于开发者快速定位特定领域的接口定义。

### 目标
1.  在 `stitcher-spec` 中创建 `src/stitcher/spec/managers.py` 文件。
2.  将 `DocumentManagerProtocol` 和 `SignatureManagerProtocol` 从 `protocols.py` 移动到 `managers.py`。
3.  更新 `stitcher-spec/__init__.py` 的导入路径。
4.  更新 `stitcher-application` 中所有引用这些协议的 Runner 和子组件的导入路径。

### 基本原理
此操作是一次纯粹的代码组织重构。通过将相关的协议组合在一起，我们提高了代码的内聚性，并遵循了“关注点分离”的设计原则。这使得 `stitcher-spec` 包本身更易于理解和扩展。

### 标签
#intent/refine #flow/ready #priority/low
#comp/interfaces
#scope/dx
#ai/instruct
#task/domain/architecture #task/object/code-organization #task/action/refactor
#task/state/continue

---

### Script

#### Acts 1: 创建 managers.py 并移动协议

首先，我们创建 `managers.py` 并将 `DocumentManagerProtocol` 和 `SignatureManagerProtocol` 的定义剪切/粘贴到新文件中。

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/managers.py
~~~~~
~~~~~python
from typing import Protocol, Dict, Union, Optional, Any, List
from pathlib import Path

from .docstring import DocstringIR
from .fingerprint import Fingerprint
from .models import ModuleDef


class DocumentManagerProtocol(Protocol):
    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def load_docs_for_path(self, file_path: str) -> Dict[str, DocstringIR]: ...

    def save_docs_for_module(self, module: ModuleDef) -> Path: ...

    def flatten_module_docs(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]: ...

    def compute_yaml_content_hash(self, content: Union[str, Dict[str, Any]]) -> str: ...

    def hydrate_module(
        self,
        module: ModuleDef,
        force: bool = False,
        reconcile: bool = False,
        resolution_map: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        source_docs_override: Optional[Dict[str, DocstringIR]] = None,
    ) -> Dict[str, Any]: ...

    def reformat_docs_for_module(self, module: ModuleDef) -> bool: ...

    # Helper method used by PumpRunner to serialize for hash computation
    def _serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...

    # Accessor for the underlying adapter, used for raw dumps in PumpRunner
    @property
    def adapter(self) -> Any: ...


class SignatureManagerProtocol(Protocol):
    def load_composite_hashes(self, file_path: str) -> Dict[str, Fingerprint]: ...

    def save_composite_hashes(
        self, file_path: str, hashes: Dict[str, Fingerprint]
    ) -> None: ...

    def reformat_hashes_for_file(self, file_path: str) -> bool: ...

    # Used by PumpRunner for centralized serialization
    def serialize_hashes(self, file_path: str, hashes: Dict[str, Fingerprint]) -> str: ...

    # Internal helper used by PumpRunner to delete files
    def _get_sig_path(self, file_path: str) -> Path: ...
~~~~~

#### Acts 2: 从 protocols.py 中移除已移动的协议

现在清理旧的 `protocols.py` 文件。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python.old
from typing import Protocol, Dict, Union, Optional, List, Any
from pathlib import Path
from .models import ModuleDef, FunctionDef, ClassDef
from .fingerprint import Fingerprint
from .docstring import DocstringIR


class LanguageParserProtocol(Protocol):
    def parse(self, source_code: str, file_path: str = "") -> ModuleDef: ...


class LanguageTransformerProtocol(Protocol):
    def strip(self, source_code: str, whitelist: Optional[List[str]] = None) -> str: ...

    def inject(self, source_code: str, docs: Dict[str, str]) -> str: ...


class FingerprintStrategyProtocol(Protocol):
    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint: ...


class DifferProtocol(Protocol):
    def generate_text_diff(
        self, a: str, b: str, label_a: str = "old", label_b: str = "new"
    ) -> str: ...


class DocstringMergerProtocol(Protocol):
    def merge(self, base: Optional[DocstringIR], incoming: DocstringIR) -> DocstringIR: ...


class DocumentManagerProtocol(Protocol):
    def load_docs_for_module(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def load_docs_for_path(self, file_path: str) -> Dict[str, DocstringIR]: ...

    def save_docs_for_module(self, module: ModuleDef) -> Path: ...

    def flatten_module_docs(self, module: ModuleDef) -> Dict[str, DocstringIR]: ...

    def compute_yaml_content_hashes(self, module: ModuleDef) -> Dict[str, str]: ...

    def compute_yaml_content_hash(self, content: Union[str, Dict[str, Any]]) -> str: ...

    def hydrate_module(
        self,
        module: ModuleDef,
        force: bool = False,
        reconcile: bool = False,
        resolution_map: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        source_docs_override: Optional[Dict[str, DocstringIR]] = None,
    ) -> Dict[str, Any]: ...

    def reformat_docs_for_module(self, module: ModuleDef) -> bool: ...

    # Helper method used by PumpRunner to serialize for hash computation
    def _serialize_ir(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...

    # Accessor for the underlying adapter, used for raw dumps in PumpRunner
    @property
    def adapter(self) -> Any: ...


class SignatureManagerProtocol(Protocol):
    def load_composite_hashes(self, file_path: str) -> Dict[str, Fingerprint]: ...

    def save_composite_hashes(
        self, file_path: str, hashes: Dict[str, Fingerprint]
    ) -> None: ...

    def reformat_hashes_for_file(self, file_path: str) -> bool: ...

    # Used by PumpRunner for centralized serialization
    def serialize_hashes(self, file_path: str, hashes: Dict[str, Fingerprint]) -> str: ...

    # Internal helper used by PumpRunner to delete files
    def _get_sig_path(self, file_path: str) -> Path: ...
~~~~~
~~~~~python.new
from typing import Protocol, Dict, Union, Optional, List, Any
from .models import ModuleDef, FunctionDef, ClassDef
from .fingerprint import Fingerprint
from .docstring import DocstringIR


class LanguageParserProtocol(Protocol):
    def parse(self, source_code: str, file_path: str = "") -> ModuleDef: ...


class LanguageTransformerProtocol(Protocol):
    def strip(self, source_code: str, whitelist: Optional[List[str]] = None) -> str: ...

    def inject(self, source_code: str, docs: Dict[str, str]) -> str: ...


class FingerprintStrategyProtocol(Protocol):
    def compute(self, entity: Union[FunctionDef, ClassDef]) -> Fingerprint: ...


class DifferProtocol(Protocol):
    def generate_text_diff(
        self, a: str, b: str, label_a: str = "old", label_b: str = "new"
    ) -> str: ...


class DocstringMergerProtocol(Protocol):
    def merge(self, base: Optional[DocstringIR], incoming: DocstringIR) -> DocstringIR: ...
~~~~~

#### Acts 3: 更新 `stitcher-spec` 的 `__init__.py`

我们更新 `__init__.py` 以从新的 `managers.py` 文件导入协议。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
    StubGeneratorProtocol,
    DocstringParserProtocol,
    DocstringRendererProtocol,
    DocstringSerializerProtocol,
    DocumentManagerProtocol,
    SignatureManagerProtocol,
    DifferProtocol,
    DocstringMergerProtocol,
)
from .storage import IndexStoreProtocol

__all__ = [
~~~~~
~~~~~python.new
    StubGeneratorProtocol,
    DocstringParserProtocol,
    DocstringRendererProtocol,
    DocstringSerializerProtocol,
    DifferProtocol,
    DocstringMergerProtocol,
)
from .storage import IndexStoreProtocol
from .managers import DocumentManagerProtocol, SignatureManagerProtocol

__all__ = [
~~~~~

#### Acts 4: 更新 `stitcher-application` 中的导入路径

最后，我们修复所有因协议文件位置变更而损坏的导入语句。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
    DocumentManagerProtocol,
    SignatureManagerProtocol,
    DifferProtocol,
    IndexStoreProtocol,
)
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
    DifferProtocol,
    IndexStoreProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/resolver.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    ConflictType,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
    DocumentManagerProtocol,
    SignatureManagerProtocol,
)
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    ConflictType,
    ResolutionAction,
    Fingerprint,
    LanguageParserProtocol,
    FingerprintStrategyProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    FingerprintStrategyProtocol,
    DocumentManagerProtocol,
    SignatureManagerProtocol,
    IndexStoreProtocol,
)
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    Fingerprint,
    FingerprintStrategyProtocol,
    IndexStoreProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    ModuleDef,
    ConflictType,
    ResolutionAction,
    Fingerprint,
    FunctionExecutionPlan,
    LanguageTransformerProtocol,
    FingerprintStrategyProtocol,
    DocstringIR,
    DocumentManagerProtocol,
    SignatureManagerProtocol,
    DifferProtocol,
    DocstringMergerProtocol,
    IndexStoreProtocol,
)
~~~~~
~~~~~python.new
from stitcher.spec import (
    ModuleDef,
    ConflictType,
    ResolutionAction,
    Fingerprint,
    FunctionExecutionPlan,
    LanguageTransformerProtocol,
    FingerprintStrategyProtocol,
    DocstringIR,
    DifferProtocol,
    DocstringMergerProtocol,
    IndexStoreProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/init.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    Fingerprint,
    ModuleDef,
    FingerprintStrategyProtocol,
    DocumentManagerProtocol,
    SignatureManagerProtocol,
)
~~~~~
~~~~~python.new
from stitcher.spec import (
    Fingerprint,
    ModuleDef,
    FingerprintStrategyProtocol,
)
from stitcher.spec.managers import DocumentManagerProtocol, SignatureManagerProtocol
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/transform.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    LanguageTransformerProtocol,
    ModuleDef,
    DocumentManagerProtocol,
)
~~~~~
~~~~~python.new
from stitcher.spec import (
    LanguageTransformerProtocol,
    ModuleDef,
)
from stitcher.spec.managers import DocumentManagerProtocol
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/coverage.py
~~~~~
~~~~~python.old
from stitcher.spec import DocumentManagerProtocol, IndexStoreProtocol
~~~~~
~~~~~python.new
from stitcher.spec import IndexStoreProtocol
from stitcher.spec.managers import DocumentManagerProtocol
~~~~~

### 下一步建议
我们已经成功地将协议文件结构化。建议运行 `pyright` 确认所有导入路径都已正确更新。如果通过，我们可以创建一个 `[COMMIT]` 计划，将 **3.1 索引存储协议化** 和 **协议文件结构化** 这两个步骤合并为一个逻辑提交，从而完成阶段三的大部分工作。
