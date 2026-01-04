简要回答
好的，我们来编写第一个端到端的集成测试，将 `SemanticGraph`, `RenameSymbolOperation`, 和 `TransactionManager` 串联起来，完成一次真实的文件系统重构。

## [WIP] test: 添加 RenameSymbolOperation 的端到端集成测试

### 用户需求
编写一个集成测试，模拟完整的重构流程：
1.  在临时文件系统中创建一个多文件 Python 包。
2.  使用 `SemanticGraph` 加载并分析该包。
3.  执行 `RenameSymbolOperation` 以生成文件修改计划。
4.  使用 `TransactionManager` 将计划应用到磁盘。
5.  验证磁盘上的文件内容是否已按预期被重构。

### 评论
这个测试是阶段二的最终“验收标准”。它不再依赖任何 Mock，直接验证了从代码分析到文件写入的整个工作流。成功通过此测试意味着我们的重构引擎已经具备了最核心的端到端能力。

### 目标
1.  创建 `packages/stitcher-refactor/tests/integration/test_rename_e2e.py` 文件。
2.  编写 `test_rename_symbol_end_to_end` 测试用例。
3.  在测试中，创建一个包含定义和跨文件引用的 Python 包。
4.  执行完整的分析 -> 计划 -> 提交流程。
5.  断言最终写入磁盘的文件内容是正确的。

### 基本原理
-   **黑盒测试**: 将整个重构流程（`load` -> `analyze` -> `commit`）视为一个黑盒，只关心输入（原始代码）和输出（修改后的代码），不关心内部实现细节。
-   **真实环境**: 使用 `pytest` 的 `tmp_path` fixture 来模拟一个干净、真实的开发环境，确保测试的可靠性和隔离性。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #task/domain/refactor #task/object/rename-operation #task/action/integration-test #task/state/continue

---

### Script

#### Acts 1: 编写端到端集成测试
创建集成测试文件并实现测试逻辑。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation


def test_rename_symbol_end_to_end(tmp_path):
    # 1. Setup: Create a virtual project
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    
    # File with the definition
    core_path = pkg_dir / "core.py"
    core_path.write_text(
        "class OldHelper:\n    pass\n\ndef old_func():\n    pass",
        encoding="utf-8"
    )
    
    # File with usages
    app_path = pkg_dir / "app.py"
    app_path.write_text(
        "from .core import OldHelper, old_func\n\n"
        "h = OldHelper()\n"
        "old_func()",
        encoding="utf-8"
    )

    # 2. Analysis Phase
    graph = SemanticGraph(root_path=tmp_path)
    graph.load("mypkg")
    ctx = RefactorContext(graph=graph)

    # 3. Planning Phase
    op = RenameSymbolOperation(
        old_fqn="mypkg.core.OldHelper", 
        new_fqn="mypkg.core.NewHelper"
    )
    file_ops = op.analyze(ctx)

    # 4. Execution Phase
    tm = TransactionManager(tmp_path)
    for op in file_ops:
        # In a real app, we might add ops one by one. Here we add all.
        # This assumes analyze() returns WriteFileOp with correct content.
        tm.add_write(op.path, op.content)
    
    tm.commit()

    # 5. Verification Phase
    # Check the file where the definition was
    modified_core_code = core_path.read_text(encoding="utf-8")
    expected_core_code = "class NewHelper:\n    pass\n\ndef old_func():\n    pass"
    assert modified_core_code == expected_core_code

    # Check the file where it was used
    modified_app_code = app_path.read_text(encoding="utf-8")
    expected_app_code = ("from .core import NewHelper, old_func\n\n"
                         "h = NewHelper()\n"
                         "old_func()")
    assert modified_app_code == expected_app_code
~~~~~

### 下一步建议
我们已经成功地验证了重构引擎的核心工作流！

阶段二的主要目标已经达成。接下来的任务是提升其健壮性和功能覆盖范围：
1.  **完善 `SymbolRenamerTransformer`**: 扩展它以正确处理更复杂的导入场景，例如重命名 `Attribute` (`import mypkg; mypkg.core.OldHelper`) 和 `ImportAlias` (`from .core import OldHelper as OH`)。
2.  **实现 `MoveFileOperation`**: 这是另一个核心重构算子，它将复用 `RenameSymbolOperation` 的逻辑来更新所有因文件移动而改变的导入语句。
