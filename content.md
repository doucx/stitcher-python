简要回答
好的，我们现在将 `SemanticGraph`（分析器）和 `SymbolRenamerTransformer`（修改器）结合起来，创建 `RenameSymbolOperation`，这是第一个完整的、端到端的重构算子。

## [WIP] feat: 实现 RenameSymbolOperation

### 用户需求
实现 `RenameSymbolOperation` 类，它封装了“重命名一个符号”的完整逻辑：
1.  接收旧的 FQN 和新的 FQN。
2.  使用 `SemanticGraph` 查找所有引用位置。
3.  对每个受影响的文件应用 `SymbolRenamerTransformer`。
4.  生成一组 `WriteFileOp` 操作，准备提交给 `TransactionManager`。

### 评论
这是“阶段二：核心重命名引擎”的顶点。通过将复杂的分析和转换逻辑封装在一个单一的、声明式的 `Operation` 对象中，我们为上层调用者（如 CLI 或迁移脚本）提供了一个极其简洁的 API。调用者只需说“把 A 重命名为 B”，而无需关心 Griffe 或 LibCST 的内部细节。

### 目标
1.  定义 `operations/base.py` 中的 `AbstractOperation` 和 `engine/context.py` 中的 `RefactorContext`。
2.  在 `operations/rename_symbol.py` 中实现 `RenameSymbolOperation`。
3.  实现 `analyze` 方法，该方法编排了从 Usage 查询到代码转换的全过程。
4.  编写单元测试，通过 Mock `SemanticGraph` 来验证 `RenameSymbolOperation` 的业务逻辑，确保它能正确地为多个文件生成 `WriteFileOp`。

### 基本原理
-   **策略模式**: `RenameSymbolOperation` 是一个具体的策略实现，它定义了如何执行“重命名”这一特定任务。
-   **上下文对象**: `RefactorContext` 作为上下文对象，在操作（Operation）和引擎状态（Graph）之间传递信息，避免了全局状态。
-   **关注点分离**: `Operation` 负责“做什么”（业务逻辑），`Transformer` 负责“怎么改”（AST 操作），`Graph` 负责“在哪里”（语义分析），`TransactionManager` 负责“何时执行”（事务控制）。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #task/domain/refactor #task/object/rename-operation #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建上下文和操作基类
首先定义 `RefactorContext` 和 `AbstractOperation`，它们是所有重构操作的共享基础。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/engine/context.py
~~~~~
~~~~~python
from dataclasses import dataclass
from .graph import SemanticGraph


@dataclass
class RefactorContext:
    graph: SemanticGraph
~~~~~

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python
from abc import ABC, abstractmethod
from typing import List
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp


class AbstractOperation(ABC):
    @abstractmethod
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        """
        Analyzes the codebase and returns a list of file operations
        without applying them.
        """
        pass
~~~~~

#### Acts 2: 实现 RenameSymbolOperation
现在，我们实现核心的重命名操作逻辑。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/rename_symbol.py
~~~~~
~~~~~python
import libcst as cst
from collections import defaultdict
from typing import List, Dict
from pathlib import Path

from .base import AbstractOperation
from .transforms.rename_transformer import SymbolRenamerTransformer
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, WriteFileOp
from stitcher.refactor.engine.graph import UsageLocation


class RenameSymbolOperation(AbstractOperation):
    def __init__(self, old_fqn: str, new_fqn: str):
        self.old_fqn = old_fqn
        self.new_fqn = new_fqn

    def _get_base_name(self, fqn: str) -> str:
        return fqn.split(".")[-1]

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        ops: List[FileOp] = []
        
        old_name = self._get_base_name(self.old_fqn)
        new_name = self._get_base_name(self.new_fqn)
        
        if old_name == new_name:
            return [] # No change needed

        rename_map = {old_name: new_name}
        
        # 1. Find all usages
        usages = ctx.graph.registry.get_usages(self.old_fqn)
        
        # 2. Group usages by file
        usages_by_file: Dict[Path, List[UsageLocation]] = defaultdict(list)
        for usage in usages:
            usages_by_file[usage.file_path].append(usage)
            
        # 3. For each affected file, apply transformation
        for file_path, file_usages in usages_by_file.items():
            try:
                # We assume file_path is absolute from Griffe
                original_source = file_path.read_text(encoding="utf-8")
                
                module = cst.parse_module(original_source)
                wrapper = cst.MetadataWrapper(module)
                
                transformer = SymbolRenamerTransformer(rename_map, file_usages)
                modified_module = wrapper.visit(transformer)

                if modified_module.code != original_source:
                    # The path in WriteFileOp should be relative to the project root
                    relative_path = file_path.relative_to(ctx.graph.root_path)
                    ops.append(WriteFileOp(path=relative_path, content=modified_module.code))

            except Exception:
                # Log error and continue? For now, let it fail fast.
                # In a real CLI, we'd collect these errors.
                raise

        return ops
~~~~~

#### Acts 3: 编写单元测试
我们通过 Mock `RefactorContext` 和 `SemanticGraph` 来独立测试 `RenameSymbolOperation` 的编排逻辑。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python
from unittest.mock import Mock
from pathlib import Path
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph, UsageRegistry, UsageLocation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.engine.transaction import WriteFileOp


def test_rename_symbol_analyze_orchestration():
    # 1. Setup Mocks
    mock_registry = Mock(spec=UsageRegistry)
    mock_graph = Mock(spec=SemanticGraph)
    mock_graph.registry = mock_registry
    
    # Let's use a real tmp_path for reading files to simplify mocking Path.read_text
    # We will create fake files that the operation can read.
    tmp_path = Path("/tmp/fake_project") # conceptual
    mock_graph.root_path = tmp_path

    ctx = RefactorContext(graph=mock_graph)
    
    # 2. Define Test Data
    old_fqn = "mypkg.core.OldHelper"
    new_fqn = "mypkg.core.NewHelper"
    
    file_a_path = tmp_path / "mypkg" / "a.py"
    file_b_path = tmp_path / "mypkg" / "b.py"

    source_a = "from mypkg.core import OldHelper\n\nobj = OldHelper()"
    source_b = "def func():\n    from mypkg.core import OldHelper\n    return OldHelper"

    locations = [
        # Locations in a.py
        UsageLocation(file_a_path, 1, 23, 1, 32), # from mypkg.core import OldHelper
        UsageLocation(file_a_path, 3, 6, 3, 15),  # obj = OldHelper()
        # Locations in b.py
        UsageLocation(file_b_path, 2, 27, 2, 36), # from mypkg.core import OldHelper
        UsageLocation(file_b_path, 3, 11, 3, 20), # return OldHelper
    ]
    
    mock_registry.get_usages.return_value = locations
    
    # Mock file system reads
    def mock_read_text(path, *args, **kwargs):
        if path == file_a_path:
            return source_a
        if path == file_b_path:
            return source_b
        raise FileNotFoundError(f"Mock read_text: {path}")

    # Use monkeypatch to control Path.read_text
    # This is slightly more integration-y but tests the real interaction with LibCST better.
    from unittest.mock import patch
    with patch.object(Path, "read_text", side_effect=mock_read_text):
        # 3. Execute
        op = RenameSymbolOperation(old_fqn, new_fqn)
        file_ops = op.analyze(ctx)

    # 4. Verify
    mock_registry.get_usages.assert_called_once_with(old_fqn)
    
    assert len(file_ops) == 2
    assert all(isinstance(op, WriteFileOp) for op in file_ops)
    
    op_a = next(op for op in file_ops if op.path == file_a_path.relative_to(tmp_path))
    op_b = next(op for op in file_ops if op.path == file_b_path.relative_to(tmp_path))
    
    expected_code_a = "from mypkg.core import NewHelper\n\nobj = NewHelper()"
    expected_code_b = "def func():\n    from mypkg.core import NewHelper\n    return NewHelper"
    
    assert op_a.content == expected_code_a
    assert op_b.content == expected_code_b
~~~~~

### 下一步建议
我们已经完成了 `RenameSymbolOperation` 的核心实现和单元测试。现在，阶段二的主要技术组件已经就绪。

接下来的步骤是：
1.  **实战演练**: 编写一个**集成测试**，不再 mock `SemanticGraph`，而是使用它来加载一个真实的多文件项目，然后调用 `RenameSymbolOperation`，最后用 `TransactionManager` 提交变更并验证磁盘上的结果。这将是整个重构引擎的第一个端到端测试。
2.  **完善 Transformer**: 当前的 `SymbolRenamerTransformer` 只处理 `Name` 节点。我们需要扩展它以正确处理 `Attribute`（如 `import pkg.core; pkg.core.OldHelper`）和 `ImportFrom` 别名 (`from . import core as c; c.OldHelper`)。
