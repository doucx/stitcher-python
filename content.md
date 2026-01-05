简要回答
确实，之前的测试使用了 `MoveFileOperation`，这会导致 `old_fqn == module_fqn`，从而掩盖了 Bug。Bug 出现在当重命名的是模块的**父包**（即 `MoveDirectoryOperation` 场景）时，`effective_new_module` 计算错误，导致无法正确还原短名称。

我将更新测试用例，改用 `MoveDirectoryOperation` 来移动一个包含文件的目录，以此触发父包重命名逻辑，从而让测试变红。

## [WIP] test: 使用目录移动复现 Sidecar FQN 格式问题

### 用户需求
复现 `stitcher` 在移动目录时，子文件的 Sidecar YAML 键名被错误地展开为 FQN 的问题。

### 评论
必须构建一个嵌套结构（例如 `mypkg.sub.module`），并移动父目录（`mypkg.sub` -> `mypkg.moved`），使得 `SidecarUpdateMixin` 处理的 `old_fqn`（重命名对象）是 `module_fqn` 的前缀，而非完全相等。这将暴露 `effective_new_module` 计算中的逻辑缺陷。

### 目标
更新 `packages/stitcher-refactor/src/stitcher/refactor/tests/integration/test_repro_sidecar_fqn.py`，使用 `MoveDirectoryOperation` 进行测试。

### 基本原理
当 `old_fqn`（如 `mypkg.sub`）是 `module_fqn`（如 `mypkg.sub.module`）的父级时，当前的 `effective_new_module` 逻辑会错误地保留旧的模块名，导致新生成的 FQN（如 `mypkg.moved.module.Class`）无法与旧模块名匹配，从而无法还原为短名称。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #concept/state #scope/core #ai/instruct #task/domain/refactor #task/object/sidecar-updater #task/action/repro-bug #task/state/continue

---

### Script

#### Acts 1: 更新复现测试

我们将重写测试文件，模拟目录移动场景。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/tests/integration/test_repro_sidecar_fqn.py
~~~~~
~~~~~python
import yaml
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    DeleteDirectoryOp,
    WriteFileOp,
)
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_repro_sidecar_keys_should_remain_short_names_after_directory_move(tmp_path):
    """
    Reproduction test for the bug where moving a DIRECTORY causes Sidecar keys
    in child files to be expanded to FQNs instead of remaining as Short Names.
    
    Scenario:
      Structure: mypkg/section/core.py
      Sidecar:   mypkg/section/core.stitcher.yaml (Key: "MyClass")
      Action:    Move dir 'mypkg/section' -> 'mypkg/moved_section'
      
    Technical Cause Analysis (Hypothesis):
      When moving a directory, the RenameIntent is for 'mypkg.section'.
      The module is 'mypkg.section.core'.
      The 'effective_new_module' logic likely fails to account for prefix renames,
      leaving the effective module as the OLD one, which fails to match the NEW FQN
      of the class, thus preventing short-name restoration.
    """
    # 1. ARRANGE
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/section/__init__.py", "")
        .with_source("mypkg/section/core.py", "class MyClass:\n    pass")
        .with_docs(
            "mypkg/section/core.stitcher.yaml",
            {
                "MyClass": "Class doc"
            },
        )
        .build()
    )

    src_dir = project_root / "mypkg/section"
    dest_dir = project_root / "mypkg/moved_section"

    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # Load top level to ensure graph coverage
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveDirectoryOperation(src_dir, dest_dir)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # The file should now be at mypkg/moved_section/core.stitcher.yaml
    new_yaml_path = dest_dir / "core.stitcher.yaml"
    assert new_yaml_path.exists(), "Sidecar file was not moved correctly!"
    
    data = yaml.safe_load(new_yaml_path.read_text())
    
    print(f"\n[DEBUG] Keys in new sidecar: {list(data.keys())}")
    
    # Assert Short Name retention
    # This assertion is expected to FAIL if the bug is present.
    # It will likely contain "mypkg.moved_section.core.MyClass" instead.
    assert "MyClass" in data, (
        f"Short name 'MyClass' missing. Found keys: {list(data.keys())}"
    )
~~~~~

### 下一步建议
执行测试。现在它应该因为 keys 包含 FQN 而失败。之后，我将根据分析修复 `SidecarUpdateMixin` 中的 `effective_new_module` 计算逻辑。
