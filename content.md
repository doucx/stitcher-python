好的，我们立即开始执行“大清洗”的第二阶段：重写 `SidecarAdapter` 以拥抱新的 SURI 本体论。

我将生成一个计划，该计划会修改 `SidecarAdapter` 及其相关组件，使其在解析文档文件 (`.stitcher.yaml`) 时，不再依赖脆弱的 FQN，而是直接计算并生成指向物理代码的、确定性的 SURI 引用。

## [WIP] refactor(sidecar): Rewrite SidecarAdapter for SURI-based doc references

### 用户需求

根据新的标识符架构，重写 `SidecarAdapter`。当解析 `.stitcher.yaml` 文档文件时，适配器必须：
1.  停止生成 `kind="yaml_fqn"` 的引用。
2.  根据 YAML 文件的物理路径，推断出其对应的 Python 源文件路径。
3.  将 YAML 文件中的键（现在是 Fragment/短名）与源文件路径结合，实时计算出每个符号的 SURI。
4.  生成一个强类型的、基于 SURI 的引用（`target_id`），彻底消除对 FQN 解析的依赖。

### 评论

这是实现“本体论正确性”的关键一步。通过修改 `SidecarAdapter`，我们将文档 (`.yaml`) 从一个依赖于逻辑命名空间的抽象概念，转变为一个直接锚定于物理代码工件（通过 SURI）的实体。这不仅极大地增强了重构操作（特别是文件移动）的鲁棒性，也使得整个系统的引用体系更加统一和清晰。此举完美践行了 `d3-principle-arch-stable-identifiers` 和 `HFEA` 的核心思想。

### 目标

1.  **更新引用类型定义**: 在 `ReferenceType` 枚举中，用代表 SURI 引用的新类型替换掉陈旧的 `yaml_fqn`。
2.  **增强 `SidecarAdapter`**: 为其添加 `__init__` 以接收项目根路径，并重写 `parse` 方法的核心逻辑，使其能够从 YAML 的 Fragment 键和文件路径计算出 SURI。
3.  **调整解析器**: 更新 `parse_doc_references` 函数的文档，明确其返回的是 Fragment 而非 FQN，并移除一个易产生混淆的别名。

### 基本原理

新的工作流将如下所示：
1.  `SidecarAdapter` 在 `parse` 方法中接收到 `.stitcher.yaml` 的路径。
2.  它利用一个路径解析器（`AssetPathResolver`）将文档路径（如 `src/pkg/mod.stitcher.yaml`）反向解析为其对应的源文件路径（`src/pkg/mod.py`）。
3.  然后，它调用 `parse_doc_references` 从 YAML 内容中提取出所有的键（现在是 `Fragments`，如 `MyClass`）。
4.  对于每一个 `Fragment`，它使用 `SURIGenerator`，结合源文件的相对路径和 `Fragment`，生成一个全局唯一的 SURI（如 `py://src/pkg/mod.py#MyClass`）。
5.  最后，它创建一个 `ReferenceRecord`，将此 SURI 直接填入 `target_id` 字段，并将 `kind` 设置为新的类型 `yaml_suri`。这个引用是一个确定性的、不需要后续链接的强引用，从而在索引阶段就完成了文档与代码的物理绑定。

### 标签

#intent/refine #flow/ready #priority/critical #comp/engine #comp/interfaces #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/identifier-ontology #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新引用类型定义

我们将 `ReferenceType` 枚举中的 `SIDECAR_NAME` (`yaml_fqn`) 替换为 `SIDECAR_DOC_ID` (`yaml_suri`)，以反映新的引用类型。

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/models.py
~~~~~
~~~~~python.old
class ReferenceType(Enum):
    SYMBOL = "symbol"
    IMPORT_PATH = "import_path"
    SIDECAR_ID = "json_suri"      # Reference in Signature (.json) via SURI
    SIDECAR_NAME = "yaml_fqn"     # Reference in Doc (.yaml) via FQN
~~~~~
~~~~~python.new
class ReferenceType(Enum):
    SYMBOL = "symbol"
    IMPORT_PATH = "import_path"
    SIDECAR_ID = "json_suri"  # Reference in Signature (.json) via SURI
    SIDECAR_DOC_ID = "yaml_suri"  # Reference in Doc (.yaml) via SURI (computed)
~~~~~

#### Acts 2: 调整 Sidecar 解析器

更新 `parse_doc_references` 的文档字符串，明确它返回的是符号的短名（Fragment），并移除废弃的 `parse_sidecar_references` 别名。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/parser.py
~~~~~
~~~~~python.old
def parse_doc_references(content: str) -> List[Tuple[str, int, int]]:
    """
    Parses a Stitcher YAML Doc file and returns a list of (fqn, lineno, col_offset)
    for all top-level keys.
    """
    yaml = YAML()
    try:
        data = yaml.load(content)
    except YAMLError:
        return []

    references = []

    if not isinstance(data, dict):
        return references

    for key in data.keys():
        lc = getattr(data, "lc", None)
        if lc and hasattr(lc, "item"):
            # lc.item(key) returns [line, col, pre_key_comment_line, key_comment_line]
            # line is 0-based.
            pos = lc.item(key)
            if pos:
                lineno = pos[0] + 1  # Convert to 1-based
                col_offset = pos[1]
                references.append((str(key), lineno, col_offset))
        else:
            # Fallback if no line info
            # For robustness, we could search the string, but ruamel usually works.
            references.append((str(key), 0, 0))

    return references


def parse_signature_references(content: str) -> List[Tuple[str, int, int]]:
    """
    Parses a Stitcher JSON Signature file and returns a list of (suri, lineno, col_offset)
    for all top-level keys.

    Since Signature files are machine-generated with standard formatting,
    we use regex scanning for performance and simplicity to extract keys and line numbers.
    """
    references = []
    
    # Matches keys that look like SURIs at the start of a line (standard formatting)
    # e.g. "py://path/to/file.py#symbol":
    pattern = re.compile(r'^\s*"(py://[^"]+)":')
    
    lines = content.splitlines()
    for i, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            suri = match.group(1)
            # Find the actual start column of the key quote
            col = line.find('"' + suri + '"')
            if col == -1: 
                col = 0
            references.append((suri, i + 1, col))
            
    return references

# Alias for backward compatibility if needed, though we should update callers.
parse_sidecar_references = parse_doc_references
~~~~~
~~~~~python.new
def parse_doc_references(content: str) -> List[Tuple[str, int, int]]:
    """
    Parses a Stitcher YAML Doc file and returns a list of (fragment, lineno, col_offset)
    for all top-level keys, which are expected to be short symbol names (fragments).
    """
    yaml = YAML()
    try:
        data = yaml.load(content)
    except YAMLError:
        return []

    references = []

    if not isinstance(data, dict):
        return references

    for key in data.keys():
        lc = getattr(data, "lc", None)
        if lc and hasattr(lc, "item"):
            # lc.item(key) returns [line, col, pre_key_comment_line, key_comment_line]
            # line is 0-based.
            pos = lc.item(key)
            if pos:
                lineno = pos[0] + 1  # Convert to 1-based
                col_offset = pos[1]
                references.append((str(key), lineno, col_offset))
        else:
            # Fallback if no line info
            # For robustness, we could search the string, but ruamel usually works.
            references.append((str(key), 0, 0))

    return references


def parse_signature_references(content: str) -> List[Tuple[str, int, int]]:
    """
    Parses a Stitcher JSON Signature file and returns a list of (suri, lineno, col_offset)
    for all top-level keys.

    Since Signature files are machine-generated with standard formatting,
    we use regex scanning for performance and simplicity to extract keys and line numbers.
    """
    references = []
    
    # Matches keys that look like SURIs at the start of a line (standard formatting)
    # e.g. "py://path/to/file.py#symbol":
    pattern = re.compile(r'^\s*"(py://[^"]+)":')
    
    lines = content.splitlines()
    for i, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            suri = match.group(1)
            # Find the actual start column of the key quote
            col = line.find('"' + suri + '"')
            if col == -1: 
                col = 0
            references.append((suri, i + 1, col))
            
    return references
~~~~~

#### Acts 3: 重写 `SidecarAdapter`

这是本次计划的核心。我们将完全重写 `SidecarAdapter`，使其具备计算 SURI 的能力，并生成正确的、基于 SURI 的 `ReferenceRecord`。

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Tuple

from stitcher.spec.registry import LanguageAdapter
from stitcher.spec.index import SymbolRecord, ReferenceRecord
from stitcher.lang.sidecar.parser import (
    parse_doc_references,
    parse_signature_references,
)
from stitcher.common.services import AssetPathResolver
from stitcher.lang.python.uri import SURIGenerator
from stitcher.lang.python.analysis.models import ReferenceType


class SidecarAdapter(LanguageAdapter):
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.resolver = AssetPathResolver(root_path)

    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]:
        symbols: List[SymbolRecord] = []
        references: List[ReferenceRecord] = []

        if file_path.suffix == ".json":
            # --- Handle Signature File (.json) ---
            # Keys are SURIs (Identity References)
            refs = parse_signature_references(content)
            for suri, line, col in refs:
                references.append(
                    ReferenceRecord(
                        target_fqn=None,  # Pure ID reference
                        target_id=suri,  # The key IS the ID
                        kind=ReferenceType.SIDECAR_ID.value,
                        lineno=line,
                        col_offset=col,
                        end_lineno=line,
                        end_col_offset=col + len(suri),
                    )
                )

        elif file_path.suffix in (".yaml", ".yml"):
            # --- Handle Doc File (.yaml) ---
            # Keys are Fragments, which we resolve to SURIs
            try:
                # 1. Resolve corresponding python file
                py_path = self.resolver.get_source_path_from_doc(file_path)
                rel_py_path = py_path.relative_to(self.root_path).as_posix()

                # 2. Parse fragments from YAML
                refs = parse_doc_references(content)
                for fragment, line, col in refs:
                    # 3. Compute SURI
                    suri = SURIGenerator.for_symbol(rel_py_path, fragment)

                    # 4. Create ReferenceRecord
                    references.append(
                        ReferenceRecord(
                            target_fqn=None,  # No longer used for linking
                            target_id=suri,  # Direct, strong reference
                            kind=ReferenceType.SIDECAR_DOC_ID.value,
                            lineno=line,
                            col_offset=col,
                            end_lineno=line,
                            end_col_offset=col + len(fragment),
                        )
                    )
            except (ValueError, FileNotFoundError):
                # If we can't find the source file, we can't generate SURIs.
                # In a real app, we might log a warning here.
                pass

        return symbols, references
~~~~~

### 下一步建议

我们已经成功地重写了 `SidecarAdapter`，使其完全符合新的 SURI 本体论。现在，数据采集层（Adapter）和数据模型（`ReferenceType`）都已对齐。

下一个合乎逻辑的步骤是**第三步：重写 Planner**。`Planner` 中的 sidecar 更新逻辑目前仍然基于 FQN。我们需要对其进行改造，使其能够理解和处理基于 SURI 的重构意图，并正确地更新 `.stitcher.yaml` (Fragments) 和 `.json` (SURIs) 文件。

如果您同意，我将开始制定重构 `Planner` 的计划。
