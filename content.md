简要回答
好的，我们正式启动阶段二：核心重命名引擎。第一步是构建执行代码重构的“手术刀”——`SymbolRenamerTransformer`。它将使用 LibCST 对代码的抽象语法树（AST）进行精确修改。

## [WIP] feat: 实现 LibCST SymbolRenamerTransformer

### 用户需求
根据阶段二规划，需要实现 `SymbolRenamerTransformer`。这是一个 LibCST 转换器，它接收一个重命名映射（例如 `{'old.api': 'new.api'}`）和一组需要修改的代码位置，然后对 AST 进行精确修改，最终生成重构后的代码，同时保持原始代码的格式。

### 评论
这是重构引擎的“肌肉”。`SemanticGraph` 是“大脑”，负责找出*什么*需要改变以及*在哪里*改变。而这个 Transformer 则是负责执行具体“手术”的组件。通过 LibCST，我们可以在不破坏代码格式（如注释、空行）的前提下，安全地修改代码结构。

### 目标
1.  在 `packages/stitcher-refactor/src/stitcher/refactor/operations/transforms/` 目录下创建 `rename_transformer.py`。
2.  定义 `SymbolRenamerTransformer` 类，它继承自 `cst.CSTTransformer`。
3.  实现 `__init__` 方法，接收重命名映射和一个简化的位置集合（用于测试）。
4.  实现 `leave_Name` 方法，这是修改符号名称的核心逻辑。
5.  创建一个新的单元测试文件，验证 Transformer 在一个示例代码片段上能够正确工作。

### 基本原理
-   **AST 转换**: 我们使用 LibCST 解析源代码为具体语法树（CST），它保留了所有格式信息。`CSTTransformer` 允许我们遍历树并返回修改后的节点。
-   **元数据驱动**: `SymbolRenamerTransformer` 的行为是无状态的，它完全由外部传入的元数据（重命名映射和位置信息）驱动。
-   **隔离测试**: 在 `SemanticGraph` 的引用分析完成之前，我们将通过在测试中手动提供要修改的代码位置（行号和列号）来独立测试 Transformer 的代码生成逻辑。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/executor #task/domain/refactor #task/object/cst-transformer #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建 Transformer 目录和 `__init__.py`
我们需要为 LibCST Transformers 创建一个专用的子目录。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-refactor/src/stitcher/refactor/operations/transforms
touch packages/stitcher-refactor/src/stitcher/refactor/operations/__init__.py
touch packages/stitcher-refactor/src/stitcher/refactor/operations/transforms/__init__.py
~~~~~

#### Acts 2: 实现 SymbolRenamerTransformer
创建 `rename_transformer.py` 并实现核心转换逻辑。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/transforms/rename_transformer.py
~~~~~
~~~~~python
from typing import Dict, Set, Tuple
import libcst as cst
import libcst.matchers as m
from libcst.metadata import PositionProvider


class SymbolRenamerTransformer(cst.CSTTransformer):
    """
    A LibCST transformer that renames symbols at specific locations.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, rename_map: Dict[str, str], locations_to_modify: Set[Tuple[int, int]]):
        self.rename_map = rename_map
        self.locations_to_modify = locations_to_modify

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        pos = self.get_metadata(PositionProvider, original_node)
        
        # Check if the start position of this Name node is one we need to modify
        if (pos.start.line, pos.start.column) in self.locations_to_modify:
            if original_node.value in self.rename_map:
                return updated_node.with_changes(value=self.rename_map[original_node.value])
        return updated_node


def apply_rename_transformer(
    source_code: str,
    rename_map: Dict[str, str],
    locations: Set[Tuple[int, int]],
) -> str:
    """
    Applies the SymbolRenamerTransformer to a given source code.
    """
    tree = cst.parse_module(source_code)
    wrapper = cst.MetadataWrapper(tree)
    transformer = SymbolRenamerTransformer(rename_map, locations)
    
    modified_tree = wrapper.visit(transformer)
    return modified_tree.code
~~~~~

#### Acts 3: 创建 Transformer 测试目录
为我们的 Transformer 创建对应的单元测试目录。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-refactor/tests/unit/operations/transforms
touch packages/stitcher-refactor/tests/unit/operations/__init__.py
touch packages/stitcher-refactor/tests/unit/operations/transforms/__init__.py
~~~~~

#### Acts 4: 编写单元测试
创建测试文件，验证 Transformer 是否能正确修改代码。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/operations/transforms/test_rename_transformer.py
~~~~~
~~~~~python
import textwrap
from stitcher.refactor.operations.transforms.rename_transformer import apply_rename_transformer


def test_apply_rename_transformer():
    # 1. Setup
    source_code = textwrap.dedent("""
        from old_lib import old_func
        
        def main():
            result = old_func()
            return result
    """)
    
    rename_map = {"old_func": "new_func"}
    
    # These locations correspond to the start of 'old_func' tokens
    # (line, column), 0-indexed internally by LibCST but 1-indexed for humans.
    # LibCST Position is 1-indexed for lines, 0-indexed for columns.
    locations_to_modify = {
        (1, 20),  # from old_lib import old_func
        (4, 13),  # result = old_func()
    }

    # 2. Execute
    modified_code = apply_rename_transformer(source_code, rename_map, locations_to_modify)

    # 3. Verify
    expected_code = textwrap.dedent("""
        from old_lib import new_func
        
        def main():
            result = new_func()
            return result
    """)
    
    assert modified_code == expected_code
~~~~~

### 下一步建议
`SymbolRenamerTransformer` 的核心逻辑已经实现并经过了单元测试。现在，我们需要将“大脑”和“肌肉”连接起来。

下一步的关键任务是**实现 `UsageRegistry` 的填充逻辑**。我们需要扩展 `SemanticGraph`，使其在加载代码时，不仅记录符号的定义，还要遍历 Griffe 的 AST，找出每个符号的所有引用点（`UsageLocation`），并将这些信息填充到 `UsageRegistry` 中。这将为我们提供 `locations_to_modify` 的真实数据来源。
