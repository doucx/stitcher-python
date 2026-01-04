简要回答
好的，开始实施 `SemanticGraph` 原型。

## [WIP] feat: 实现 SemanticGraph 原型

### 用户需求
根据阶段一规划，需要实现 `SemanticGraph` 原型，核心任务是封装 `griffe.load()` 以构建项目的语义快照，并定义用于存储引用关系的 `UsageRegistry` 数据结构。

### 评论
`SemanticGraph` 是重构引擎的“大脑”。在这一步，我们暂时不实现复杂的全程序引用消解算法（这是阶段二的重点），而是专注于**数据的加载与结构化表示**。我们需要证明能够利用 Griffe 将磁盘上的代码转化为内存中的可查询对象图。

### 目标
1.  在 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py` 中实现核心数据结构：
    *   `UsageLocation`: 定义代码引用的物理坐标。
    *   `SemanticGraph`: 封装 Griffe 的加载逻辑。
2.  集成 `griffe` 库，实现对指定目录下 Python 包的加载。
3.  编写集成测试，验证 `SemanticGraph` 能够正确解析项目结构并识别出顶层符号。

### 基本原理
-   **适配器模式**: `SemanticGraph` 充当 Griffe 和 Stitcher 重构引擎之间的适配器，屏蔽 Griffe 的具体 API 细节。
-   **数据驱动**: 核心产物是数据（Graph），后续所有的重构操作（Move, Rename）都将基于这个内存快照进行计算，而不是直接操作文件。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #task/domain/refactor #task/object/semantic-graph #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 实现 SemanticGraph
我们将创建 `graph.py`，定义 `UsageLocation` 和 `SemanticGraph` 类。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Set
import griffe


@dataclass
class UsageLocation:
    """
    Represents a specific usage of a symbol in the codebase.
    """
    file_path: Path
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    # context: str  # e.g., source line content for debugging


@dataclass
class SymbolNode:
    """
    Represents a symbol (function, class, module) in the graph.
    Wraps Griffe's object model.
    """
    fqn: str
    kind: str  # "module", "class", "function", "attribute"
    path: Path
    # Future: dependencies, usages, etc.


class SemanticGraph:
    """
    The brain of the refactoring engine.
    Holds the semantic snapshot of the codebase using Griffe.
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self._griffe_loader = griffe.GriffeLoader(search_paths=[self.root_path])
        self._modules: Dict[str, griffe.Module] = {}
        # In the future, this registry will hold the cross-references
        self._usage_registry: Dict[str, List[UsageLocation]] = {}

    def load(self, package_name: str, submodules: bool = True) -> None:
        """
        Loads a package into the graph using Griffe.
        """
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module

    def get_module(self, package_name: str) -> Optional[griffe.Module]:
        return self._modules.get(package_name)

    def iter_members(self, package_name: str) -> List[SymbolNode]:
        """
        Flattened iterator over all members in a package.
        Useful for building the initial index.
        """
        module = self.get_module(package_name)
        if not module:
            return []

        nodes = []
        # Walk through the module members recursively
        # Griffe's member structure is hierarchical.
        
        # Helper to recursively collect members
        def _collect(obj: griffe.Object):
            path = obj.filepath if obj.filepath else Path("")
            # Griffe kind mapping
            kind = "unknown"
            if obj.is_module: kind = "module"
            elif obj.is_class: kind = "class"
            elif obj.is_function: kind = "function"
            elif obj.is_attribute: kind = "attribute"

            nodes.append(SymbolNode(fqn=obj.path, kind=kind, path=path))

            if hasattr(obj, "members"):
                for member in obj.members.values():
                    # Filter out aliases for now to keep it simple, or handle them?
                    # For a graph, we usually want definitions.
                    if not member.is_alias:
                        _collect(member)

        _collect(module)
        return nodes
~~~~~

#### Acts 2: 编写集成测试
创建一个集成测试，在临时目录中创建一个简单的 Python 包，然后使用 `SemanticGraph` 加载它，验证是否能正确解析出符号。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_semantic_graph.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.refactor.engine.graph import SemanticGraph


def test_semantic_graph_load_package(tmp_path):
    # 1. Setup: Create a dummy python package
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("x = 1", encoding="utf-8")
    
    sub_dir = pkg_dir / "utils"
    sub_dir.mkdir()
    (sub_dir / "__init__.py").write_text("", encoding="utf-8")
    (sub_dir / "math.py").write_text(
        "def add(a, b): return a + b\n\nclass Calculator:\n    def multiply(self, a, b): return a * b", 
        encoding="utf-8"
    )

    # 2. Execute: Load into SemanticGraph
    # Note: We need to add tmp_path to sys.path or let Griffe know where to look.
    # SemanticGraph init takes search_paths.
    graph = SemanticGraph(root_path=tmp_path)
    graph.load("mypkg")

    # 3. Verify: Check if modules are loaded
    module = graph.get_module("mypkg")
    assert module is not None
    assert module.path == "mypkg"

    # 4. Verify: Check flattened members
    members = graph.iter_members("mypkg")
    fqns = {node.fqn for node in members}

    expected_fqns = {
        "mypkg",
        "mypkg.x",
        "mypkg.utils",
        "mypkg.utils.math",
        "mypkg.utils.math.add",
        "mypkg.utils.math.Calculator",
        "mypkg.utils.math.Calculator.multiply",
    }
    
    # Check that all expected FQNs are present
    # Note: Griffe might return more stuff or handle things differently depending on version
    # but these core definitions should be there.
    for expected in expected_fqns:
        assert expected in fqns, f"Missing {expected} in graph"

    # Verify a specific node details
    add_func = next(n for n in members if n.fqn == "mypkg.utils.math.add")
    assert add_func.kind == "function"
    # Path might be absolute or relative depending on Griffe, usually absolute
    assert str(add_func.path).endswith("math.py")
~~~~~

### 下一步建议
`SemanticGraph` 原型通过后，我们的基础设施阶段就算完成了：
1.  包结构 (`stitcher-refactor`) ✅
2.  事务管理 (`TransactionManager`) ✅
3.  图谱加载 (`SemanticGraph`) ✅

接下来的任务属于“阶段二：核心重命名引擎”。第一步是开发 `SymbolRenamerTransformer` (LibCST)，它将利用 `SemanticGraph` 提供的信息（尽管目前还只有定义，没有引用），在文件级别执行精确的 AST 修改。由于我们还没实现引用查找，我们可以先用硬编码的位置或模拟的 `UsageRegistry` 来驱动 Transformer 的开发。
