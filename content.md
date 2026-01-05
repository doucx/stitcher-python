你的分析完全正确。这是一个典型的重构工具缺陷：它成功地修改了符号的*使用点*（`stitcher.common.__init__.py` 中的 `import` 和实例化），但完全忽略了符号的*定义点*（`stitcher.common.messaging.bus.py` 中的 `class MessageBus:` 声明）。

这导致 `__init__.py` 尝试从 `bus.py` 导入一个不存在的名称 `FeedbackBus`，从而在测试收集阶段就引发了 `ImportError`。

为了防止此类问题再次发生并指导后续的修复，我将遵循测试驱动开发（TDD）的最佳实践，首先创建一个专门用于捕获此“不完整重构”错误的集成测试。这个测试会精确地复现你遇到的问题，并且在当前代码库下会失败。

## [WIP] test: 添加捕获重命名定义缺失错误的集成测试

### 错误分析
`RenameSymbolOperation` 的当前实现存在严重缺陷。它能够通过语义图谱找到一个符号的所有引用（usages），并正确地对引用了该符号的文件进行转换。然而，它未能将符号的原始声明或定义（definition）本身也视为一个必须修改的目标。

因此，当执行 `Rename("A", "B")` 时，所有 `import A` 和使用 `A` 的地方都被改成了 `B`，但 `class A: ...` 却被遗漏了，导致代码库处于一个不一致的、损坏的状态。

### 用户需求
用户需要修复这个重构漏洞。根据 TDD 原则，第一步是创建一个新的、隔离的集成测试，该测试能够稳定地复现这个“仅修改引用而未修改定义”的失败场景。

### 评论
这是一个高优先级的核心功能缺陷。一个可靠的重构引擎是 `stitcher-refactor` 包的基石，而一个不完整的重命名操作会严重破坏开发者信任。添加一个明确的回归测试是修复此问题的正确第一步，它将确保未来的解决方案是完整且健壮的。

### 目标
1.  创建一个新的测试文件 `packages/stitcher-refactor/tests/integration/test_rename_incomplete_refactor.py`。
2.  在该文件中，编写一个测试用例，使用 `WorkspaceFactory` 构建一个包含类定义（`core.py`）和类使用（`app.py`）的微型项目。
3.  在测试中执行 `RenameSymbolOperation`。
4.  断言**使用**该类的文件 `app.py` 已被正确修改。
5.  断言**定义**该类的文件 `core.py` **未被**正确修改，从而精确地锁定并验证当前 bug 的存在。

### 基本原理
我们将通过直接断言重构操作后文件系统上的代码内容来验证 bug。这种方法比尝试捕获 `ImportError` 更直接、更稳定，因为它直接测试了重构操作本身的输出，而不是其连锁副作用。测试将明确证明 `RenameSymbolOperation` 的输出文件内容是不正确的。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/engine #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/refactor-engine #task/action/bug-reproduction #task/state/begin

---

### Script

#### Acts 1: 创建复现错误的集成测试

我将创建一个新的测试文件，其中包含一个会失败的测试用例，该用例专门用于验证重构操作是否遗漏了对符号定义的修改。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_rename_incomplete_refactor.py
~~~~~
~~~~~python
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_rename_operation_fails_to_rename_symbol_definition(tmp_path):
    """
    This test reproduces a critical bug where RenameSymbolOperation renames
    all usages of a symbol but fails to rename the class definition itself.
    """
    # 1. ARRANGE: Create a project with a definition and a usage.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldName: pass")
        .with_source("mypkg/app.py", "from mypkg.core import OldName\n\ninstance = OldName()")
    ).build()

    definition_file = project_root / "mypkg/core.py"
    usage_file = project_root / "mypkg/app.py"

    # 2. ACT: Run the refactoring operation.
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    op = RenameSymbolOperation("mypkg.core.OldName", "mypkg.core.NewName")
    file_ops = op.analyze(ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT: Verify the incomplete refactoring.
    # Assert that the usage file was correctly updated.
    updated_usage_code = usage_file.read_text()
    assert "from mypkg.core import NewName" in updated_usage_code
    assert "instance = NewName()" in updated_usage_code

    # Assert that the definition file was NOT updated (THIS IS THE BUG).
    definition_code = definition_file.read_text()
    assert "class OldName: pass" in definition_code
    assert "class NewName: pass" not in definition_code, \
        "The bug appears to be fixed. This test should now fail and be updated."
~~~~~

### 下一步建议

我们已经成功地用一个可失败的测试用例捕获了 bug。现在，当你运行 `pytest` 时，这个新测试将会失败，因为它明确断言了错误的行为。

下一步是修复 `stitcher.refactor.operations.rename_symbol.RenameSymbolOperation` 的 `analyze` 方法。你需要修改其逻辑，使其不仅查找符号的用法，还要找到并修改符号的定义位置。修复完成后，此测试就应该能成功通过。
