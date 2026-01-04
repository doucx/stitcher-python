简要回答
好的，进入阶段二。我们将首先实现基于 LibCST 的 `SymbolRenamerTransformer`，这是实现代码重构的核心“手术刀”。

## [WIP] feat: 实现 SymbolRenamerTransformer 原型

### 用户需求
根据阶段二规划，需要开发一个 LibCST Transformer，它能够接受 `UsageRegistry`（即一组精确的代码位置）和重命名映射，对 Python 源代码进行精确的、“定位打击”式的修改。

### 评论
这是实现“无魔法”重构的关键。通过将“分析（Analysis）”和“修改（Transformation）”解耦——Griffe 负责找到位置，LibCST 负责修改位置——我们避免了在 Transformer 内部进行脆弱的语义猜测。

### 目标
1.  创建 `packages/stitcher-refactor/src/stitcher/refactor/operations/transforms` 目录。
2.  实现 `SymbolRenamerTransformer` 类：
    *   依赖 `libcst.metadata.PositionProvider` 获取节点位置。
    *   接收一组目标 `UsageLocation`。
    *   仅当节点位置与目标位置匹配时，才应用重命名。
3.  编写单元测试，验证其能够根据位置信息重命名变量，而不误伤同名变量。

### 基本原理
-   **位置驱动 (Location-Driven)**: Transformer 不关心“这个变量是不是叫 `foo`”，它只关心“这个节点是不是在第 10 行第 5 列”。这使得重构的准确性完全由上游的语义分析（Griffe）保证。
-   **LibCST Metadata**: 使用 `MetadataWrapper` 注入位置信息，这是进行精确代码定位的标准做法。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #task/domain/refactor #task/object/rename-transformer #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建目录结构
创建存放 LibCST 转换器的目录。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-refactor/src/stitcher/refactor/operations/transforms
touch packages/stitcher-refactor/src/stitcher/refactor/operations/__init__.py
touch packages/stitcher-refactor/src/stitcher/refactor/operations/transforms/__init__.py
~~~~~

#### Acts 2: 实现 SymbolRenamerTransformer
实现转换器逻辑。为了 MVP，我们目前主要处理 `Name` 节点（变量、函数调用）的重命名。`Attribute` 和 `Import` 的处理逻辑将在后续迭代中完善。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/transforms/rename_transformer.py
~~~~~
~~~~~python
import libcst as cst
from libcst.metadata import PositionProvider, CodeRange
from typing import Dict, List, Tuple, Optional
from stitcher.refactor.engine.graph import UsageLocation


class SymbolRenamerTransformer(cst.CSTTransformer):
    """
    A LibCST transformer that renames symbols at specific locations.
    It does NOT perform semantic analysis; it blindly trusts the provided locations.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, rename_map: Dict[str, str], target_locations: List[UsageLocation]):
        """
        Args:
            rename_map: Mapping from old_name to new_name.
                        Note: For simple Name nodes, this is just the identifier.
            target_locations: List of locations that MUST be renamed.
        """
        self.rename_map = rename_map
        self._location_index = self._build_location_index(target_locations)

    def _build_location_index(self, locations: List[UsageLocation]) -> Dict[Tuple[int, int], UsageLocation]:
        """
        Builds a lookup index (start_line, start_col) -> UsageLocation for O(1) access.
        """
        index = {}
        for loc in locations:
            # Griffe locations are usually 1-based for lines.
            # LibCST CodeRange is also 1-based for lines, 0-based for columns.
            # We assume UsageLocation stores data compatible with the parser we used (Griffe).
            # We'll use (start_line, start_col) as a unique key for "Name" nodes.
            key = (loc.lineno, loc.col_offset)
            index[key] = loc
        return index

    def _is_target(self, node: cst.CSTNode) -> Optional[str]:
        """
        Checks if the current node matches a target location.
        Returns the new name if it should be renamed, else None.
        """
        pos = self.get_metadata(PositionProvider, node)
        # pos is a CodeRange object: start=(line, col), end=(line, col)
        
        # Check exact match on start position
        # Note: We might need more fuzzy matching depending on how Griffe reports positions 
        # vs LibCST. For now, we assume exact match on start.
        key = (pos.start.line, pos.start.column)
        
        if key in self._location_index:
            # Found a match! Now we need to determine the new name.
            # In a real scenario, the UsageLocation might carry the specific transformation.
            # For this MVP, we look up the node's current value in the map.
            # But wait, rename_map is old->new. 
            
            # If the node is a Name, its value is the name.
            if isinstance(node, cst.Name):
                old_name = node.value
                return self.rename_map.get(old_name)
            
        return None

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        new_name = self._is_target(original_node)
        if new_name:
            return updated_node.with_changes(value=new_name)
        return updated_node

    # TODO: Add leave_Attribute, leave_ImportFrom, etc. in future iterations.
~~~~~

#### Acts 3: 编写单元测试
验证转换器是否能精确重命名指定位置的变量，而忽略其他同名变量。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/test_rename_transformer.py
~~~~~
~~~~~python
import libcst as cst
from pathlib import Path
from stitcher.refactor.engine.graph import UsageLocation
from stitcher.refactor.operations.transforms.rename_transformer import SymbolRenamerTransformer


def test_rename_specific_occurrence():
    # Source code with two 'foo' variables in different scopes/lines
    source = """
def func1():
    foo = 1  # Target to rename
    return foo

def func2():
    foo = 2  # Should NOT rename
    return foo
"""
    
    # Define locations. 
    # LibCST positions:
    # Line 3: "    foo = 1" -> foo starts at line 3, col 4
    # Line 4: "    return foo" -> foo starts at line 4, col 11
    
    locations = [
        UsageLocation(Path(""), lineno=3, col_offset=4, end_lineno=3, end_col_offset=7),
        UsageLocation(Path(""), lineno=4, col_offset=11, end_lineno=4, end_col_offset=14),
    ]
    
    rename_map = {"foo": "bar"}
    
    # Parse and Transform
    module = cst.parse_module(source)
    wrapper = cst.MetadataWrapper(module)
    transformer = SymbolRenamerTransformer(rename_map, locations)
    
    modified_module = wrapper.visit(transformer)
    modified_code = modified_module.code

    expected_code = """
def func1():
    bar = 1  # Target to rename
    return bar

def func2():
    foo = 2  # Should NOT rename
    return foo
"""
    
    assert modified_code == expected_code
~~~~~

### 下一步建议
实现并验证了 `SymbolRenamerTransformer` 后，我们将拥有修改代码的能力。
接下来的步骤是：
1.  **实现 `UsageRegistry` 和 Griffe 到 `UsageLocation` 的转换**：我们需要一个真实的方式从 Griffe 的分析结果中提取出 `UsageLocation` 列表，而不仅仅是手动构造它们。这将涉及到遍历 Griffe 的 AST 引用（Griffe 最近的版本开始支持引用解析，或者我们需要自己遍历 AST）。
    *   *修正*: 考虑到 Griffe 的引用解析可能还在实验阶段，阶段二的路线图提到“构建 SemanticGraph... 建立 UsageRegistry”。我们可能需要自己写一个简单的 AST Visitor (使用 `ast` 或 `libcst`) 来扫描文件并构建这个 Registry，作为 `SemanticGraph` 的一部分。
2.  **集成 `RenameSymbolOperation`**: 将 Graph 分析、Registry 查找和 Transformer 修改封装成一个完整的 Operation 类。
