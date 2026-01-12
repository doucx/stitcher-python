简要回答
好的，我将执行架构重构的阶段四（部分）和阶段五，定义重构策略协议并创建 `stitcher-lang-sidecar` 包。

## [WIP] feat: 引入重构策略协议与 Sidecar 语言包

### 用户需求
1.  **协议定义**: 在 `stitcher-spec` 中定义通用的 `RefactoringStrategyProtocol`，以解耦重构引擎与具体语言实现。
2.  **Sidecar 标准化**: 创建 `stitcher-lang-sidecar` 包，将 `.stitcher.yaml` 文件提升为标准语言资源，使其参与索引和重构流程。

### 评论
这是架构演进的关键一步。通过将 Sidecar 视为一种“语言”，我们可以利用现有的索引和引用查找机制来统一处理重构，彻底消除 `stitcher-refactor` 中针对 Sidecar 的硬编码逻辑 (`SidecarUpdateMixin`)。引入 `ruamel.yaml` 是为了在解析和修改 YAML 时保留注释和格式，这对于重构工具至关重要。

### 目标
1.  在 `stitcher-spec` 中建立 `RefactoringStrategyProtocol` 和 `RefactorUsage`。
2.  初始化 `packages/stitcher-lang-sidecar` 包结构。
3.  实现 `SidecarAdapter`，利用 `ruamel.yaml` 解析 YAML 键作为对 Python 符号的引用 (`ReferenceRecord`)。

### 基本原理
*   **泛化重构**: 引擎只应编排“查找引用”和“调用策略”，而不应知道“如何修改 Python 代码”或“如何修改 YAML”。
*   **统一引用模型**: 将 YAML 中的 Key `my_pkg.MyClass` 建模为对符号 `my_pkg.MyClass` 的引用 (`kind="sidecar_key"`)，使得重命名 `MyClass` 时，Sidecar 文件会自动出现在“受影响文件列表”中。

### 标签
#intent/architect #intent/build #flow/ready #priority/high
#comp/spec #comp/lang-sidecar #concept/refactor
#task/domain/refactor #task/object/sidecar-adapter #task/action/create #task/state/begin

---

### Script

#### Acts 1: 定义重构协议 (stitcher-spec)

首先，我们在 `stitcher-spec` 中定义重构策略的接口和数据结构。

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/refactor.py
~~~~~
~~~~~python
from dataclasses import dataclass
from typing import Protocol, List

from .models import SourceLocation


@dataclass
class RefactorUsage:
    """Represents a specific usage of a symbol to be refactored."""
    location: SourceLocation
    # Optional text matching for verification (e.g. ensure we are replacing the right thing)
    match_text: str = ""


class RefactoringStrategyProtocol(Protocol):
    """
    Defines how a specific language handles refactoring operations.
    """

    def rename_symbol(
        self,
        source_code: str,
        usages: List[RefactorUsage],
        new_name: str
    ) -> str:
        """
        Apply a rename operation to the source code.

        Args:
            source_code: The original content of the file.
            usages: A list of locations in this file that refer to the symbol being renamed.
            new_name: The new fully qualified name (FQN) or short name.
                      The strategy is responsible for determining whether to use
                      the short name or FQN based on the context of each usage.

        Returns:
            The modified source code.
        """
        ...
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
    "ResolutionPlan",
    "FunctionExecutionPlan",
]
~~~~~
~~~~~python.new
    "ResolutionPlan",
    "FunctionExecutionPlan",
    # Refactor
    "RefactorUsage",
    "RefactoringStrategyProtocol",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
from .models import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
    SourceLocation,
    ConflictType,
    ResolutionAction,
    Resolution,
    ResolutionPlan,
    FunctionExecutionPlan,
)
~~~~~
~~~~~python.new
from .models import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
    SourceLocation,
    ConflictType,
    ResolutionAction,
    Resolution,
    ResolutionPlan,
    FunctionExecutionPlan,
)
from .refactor import RefactorUsage, RefactoringStrategyProtocol
~~~~~

#### Acts 2: 创建 stitcher-lang-sidecar 包结构

初始化新包 `stitcher-lang-sidecar`。我们将引入 `ruamel.yaml` 以支持高保真的 YAML 处理。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar
~~~~~

~~~~~act
write_file
packages/stitcher-lang-sidecar/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "stitcher-lang-sidecar"
version = "0.1.0"
description = "Sidecar (.stitcher.yaml) language support for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "ruamel.yaml>=0.17.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/__init__.py
~~~~~
~~~~~python
# This allows this package to coexist with other distribution packages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .adapter import SidecarAdapter

__all__ = ["SidecarAdapter"]
~~~~~

#### Acts 3: 实现 Sidecar 解析器与适配器

实现 `SidecarParser` (封装 `ruamel.yaml` 逻辑) 和 `SidecarAdapter` (实现 `LanguageAdapter` 接口)。

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/parser.py
~~~~~
~~~~~python
from typing import List, Tuple
from io import StringIO
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

def parse_sidecar_references(content: str) -> List[Tuple[str, int, int]]:
    """
    Parses a Stitcher YAML file and returns a list of (fqn, lineno, col_offset)
    for all top-level keys.

    Note: ruamel.yaml uses 0-based indexing for lines and columns internally,
    but Stitcher (and most editors) expect 1-based lines and 0-based columns.
    Wait, most AST parsers (Python's ast, LibCST) use 1-based lines.
    We will normalize to 1-based lines here.
    """
    yaml = YAML()
    try:
        data = yaml.load(content)
    except YAMLError:
        return []

    references = []
    
    if not isinstance(data, dict):
        return references

    # ruamel.yaml attaches metadata to the loaded dict/objects
    # We can inspect this metadata to find line numbers.
    
    for key in data.keys():
        # The key itself usually corresponds to a Python FQN (e.g. "my_pkg.mod.func")
        # We treat this as a reference to that Python symbol.
        
        # Accessing line info for keys is tricky in ruamel.yaml.
        # It is stored in data.lc.data (for dicts).
        # data.lc.data is a dict-like structure or list where keys are indices?
        # Actually, for CommentedMap, .lc.item(key) returns (lineno, colno, ...)
        
        if hasattr(data, "lc") and hasattr(data.lc, "item"):
            # lc.item(key) returns [line, col, pre_key_comment_line, key_comment_line]
            # line is 0-based.
            pos = data.lc.item(key)
            if pos:
                lineno = pos[0] + 1  # Convert to 1-based
                col_offset = pos[1]
                references.append((str(key), lineno, col_offset))
        else:
            # Fallback if no line info (shouldn't happen with round-trip loader)
            pass

    return references
~~~~~

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Tuple

from stitcher.spec.registry import LanguageAdapter
from stitcher.spec.index import SymbolRecord, ReferenceRecord
from stitcher.lang.sidecar.parser import parse_sidecar_references
from stitcher.lang.python.uri import SURIGenerator

class SidecarAdapter(LanguageAdapter):
    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]:
        symbols: List[SymbolRecord] = []
        references: List[ReferenceRecord] = []

        # 1. Define the module symbol for the sidecar file itself
        # This allows the sidecar file to be tracked in the index.
        # rel_path = file_path.as_posix() # Assuming file_path passed in is relative or we handle it
        # Actually LanguageAdapter.parse receives file_path which might be absolute or relative 
        # depending on caller. The caller (FileIndexer) usually passes absolute path 
        # but expects records to contain info relevant for storage.
        # Usually SURIGenerator needs a relative path.
        # Let's assume the caller handles SURI generation or we create a specific SURI for sidecar?
        # For now, we only care about references.
        
        # 2. Extract references (keys)
        refs = parse_sidecar_references(content)
        for ref_fqn, line, col in refs:
             # We treat each top-level key as a reference to a Python symbol.
             # Kind is 'sidecar_key' so we can distinguish it later if needed.
             references.append(ReferenceRecord(
                 target_fqn=ref_fqn,
                 kind="sidecar_key",
                 lineno=line,
                 col_offset=col,
                 end_lineno=line, 
                 end_col_offset=col + len(ref_fqn) 
             ))
             
        return symbols, references
~~~~~

### 下一步建议

下一步应是 **步骤 3: 改造 `stitcher-lang-python`**，在其内部实现 `PythonRefactoringStrategy`，封装现有的 CST 转换逻辑，并对外暴露符合新定义的 `RefactoringStrategyProtocol` 的接口。这将为彻底解耦 `stitcher-refactor` 做好准备。
