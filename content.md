好的，我来分析并解决这个问题。

测试 `test_move_file_flat_layout` 失败，断言错误为：
`AssertionError: assert 'mypkg.new.A' in 'mypkg.old.A: Doc\n'`

这表明，在执行 `MoveFileOperation` 将 `mypkg/old.py` 移动到 `mypkg/new.py` 后：
1.  对应的 YAML 边车文件 `mypkg/old.stitcher.yaml` 也被成功移动到了 `mypkg/new.stitcher.yaml`。
2.  但是，新的 `mypkg/new.stitcher.yaml` 文件中的**内容没有被更新**。它仍然包含旧的完全限定名称 (FQN) `mypkg.old.A`，而不是预期的 `mypkg.new.A`。

根本原因在于 `MoveFileOperation` 的职责划分不明确。它依赖于为每个成员符号触发的 `RenameSymbolOperation` 的副作用来更新被移动文件的边车内容。然而，这个过程似乎失败了，导致边车文件仅被移动，其内部的 FQN 键没有与文件移动同步。

我将通过重构 `MoveFileOperation` 来修复此问题，使其职责更清晰、行为更健壮。`MoveFileOperation` 自身应该显式地负责更新其所移动文件的边车内容，而不是依赖其他操作的隐式副作用。

具体步骤如下：
1.  修改 `MoveFileOperation.analyze` 方法。
2.  在生成文件移动指令之前，增加一个专门的步骤来处理边车文件的**内容转换**。
3.  该步骤将：
    *   加载与源文件 (`old.py`) 关联的 `.stitcher.yaml` 和 `.json` 边车文件。
    *   遍历文件中的所有 FQN 键。
    *   将与旧模块路径 (`mypkg.old`) 匹配的前缀替换为新模块路径 (`mypkg.new`)。
    *   生成 `WriteFileOp` 指令，用更新后的内容**覆盖原始的边车文件**。
4.  这样，当后续的 `MoveFileOp` 执行时，它移动的将是已经更新好内容的边车文件，从而保证了最终状态的正确性。

我将生成一个计划来执行此修改。

我已分析清楚问题，现在为您生成修复计划。

## [WIP] fix: 修复 MoveFileOperation 未更新边车文件内容的问题

### 错误分析

`test_move_file_flat_layout` 测试失败，原因是 `MoveFileOperation` 在移动 Python 模块及其关联的 `.stitcher.yaml` 边车文件时，虽然正确地移动了文件，但未能更新 YAML 文件内部的完全限定名称 (FQN) 键。这导致断言失败，因为移动后的 `new.stitcher.yaml` 文件仍然包含旧的 FQN (`mypkg.old.A`)。

根本原因在于 `MoveFileOperation` 的职责划分不清，它错误地依赖于 `RenameSymbolOperation` 的副作用来处理其移动文件的边车内容更新，而这一过程并未按预期工作。

### 用户需求

修复 `MoveFileOperation` 的逻辑，确保在移动文件的同时，其关联的边车文件（YAML 和 JSON）内部的所有相关 FQN 键也能被正确更新。

### 评论

这是一个关键的修复。自动化重构引擎的核心价值在于保证代码、文档和元数据（指纹）的原子化同步演进。此 Bug 破坏了这一保证。通过让 `MoveFileOperation` 显式地承担起更新其所移动文件边车内容的职责，我们可以使代码逻辑更健壮、更易于理解和维护。

### 目标

1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py`。
2.  在 `MoveFileOperation.analyze` 方法中，增加显式逻辑，用于在移动边车文件**之前**，更新其内容的 FQN 键。
3.  确保此修改能让 `test_move_file_flat_layout` 测试通过。

### 基本原理

我将修改 `MoveFileOperation` 的 `analyze` 方法。在现有的 `rename_ops`（用于更新外部引用）和 `move_ops`（用于移动文件）之间，我将注入一个新的逻辑块 `content_update_ops`。

这个新的逻辑块会：
1.  定位与被移动的源文件关联的 `.stitcher.yaml` 和 `.json` 文件。
2.  如果这些文件存在，则加载它们。
3.  遍历文件内容中的所有键，将旧的模块 FQN 前缀（如 `mypkg.old`）安全地替换为新的模块 FQN 前缀（如 `mypkg.new`）。
4.  为内容已更改的边车文件生成 `WriteFileOp` 操作。

最终返回的操作序列将是 `content_update_ops + rename_ops + move_ops`，确保在移动任何文件之前，所有内容修改都已规划完毕。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/refactor-engine #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 更新 `move_file.py` 以处理边车内容

我将向 `MoveFileOperation` 添加核心逻辑，使其能够主动更新被移动文件的边车内容的 FQN 键。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
from pathlib import Path
from typing import List, Optional
import libcst as cst

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation


class MoveFileOperation(AbstractOperation):
~~~~~
~~~~~python.new
from pathlib import Path
from typing import List, Optional
import libcst as cst

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, WriteFileOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.updater import DocUpdater, SigUpdater


class MoveFileOperation(AbstractOperation):
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        rename_ops: List[FileOp] = []
        move_ops: List[FileOp] = []
        
        # 1. Symbol Renaming (Must happen BEFORE moves to modify existing files)
        # Why? Because RenameSymbolOperation modifies files in place (including Sidecars).
        # If we move Sidecars first, RenameOp will recreate them at old location or fail.
        # By modifying first, we update content at old location, THEN move to new location.
        
        old_module_fqn = self._path_to_fqn(self.src_path, ctx.graph.root_path)
        new_module_fqn = self._path_to_fqn(self.dest_path, ctx.graph.root_path)
        
        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # Rename the module itself (handles "import old_mod")
            rename_mod_op = RenameSymbolOperation(old_module_fqn, new_module_fqn)
            rename_ops.extend(rename_mod_op.analyze(ctx))
            
            # Rename all members (handles "from old_mod import X")
            members = ctx.graph.iter_members(old_module_fqn)
            
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn):]
                    target_new_fqn = new_module_fqn + suffix
                    
                    sub_op = RenameSymbolOperation(member.fqn, target_new_fqn)
                    rename_ops.extend(sub_op.analyze(ctx))

        # 2. Physical Move
        rel_src = self.src_path.relative_to(ctx.graph.root_path)
        rel_dest = self.dest_path.relative_to(ctx.graph.root_path)
        
        move_ops.append(MoveFileOp(rel_src, rel_dest))
        
        # 3. Sidecar Moves
        # YAML
        yaml_src = self.src_path.with_suffix(".stitcher.yaml")
        yaml_dest = self.dest_path.with_suffix(".stitcher.yaml")
        if yaml_src.exists():
            rel_yaml_src = yaml_src.relative_to(ctx.graph.root_path)
            rel_yaml_dest = yaml_dest.relative_to(ctx.graph.root_path)
            move_ops.append(MoveFileOp(rel_yaml_src, rel_yaml_dest))
            
        # Signatures
        sig_root = ctx.graph.root_path / ".stitcher/signatures"
        sig_src = sig_root / rel_src.with_suffix(".json")
        sig_dest = sig_root / rel_dest.with_suffix(".json")
        if sig_src.exists():
             rel_sig_src = sig_src.relative_to(ctx.graph.root_path)
             rel_sig_dest = sig_dest.relative_to(ctx.graph.root_path)
             move_ops.append(MoveFileOp(rel_sig_src, rel_sig_dest))
        
        # Return combined ops: FIRST modify content, THEN move files
        return rename_ops + move_ops
~~~~~
~~~~~python.new
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        rename_ops: List[FileOp] = []
        move_ops: List[FileOp] = []
        content_update_ops: List[FileOp] = []

        old_module_fqn = self._path_to_fqn(self.src_path, ctx.graph.root_path)
        new_module_fqn = self._path_to_fqn(self.dest_path, ctx.graph.root_path)

        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # 1. Update external references to the moved symbols
            # Rename the module itself (handles "import old_mod")
            rename_mod_op = RenameSymbolOperation(old_module_fqn, new_module_fqn)
            rename_ops.extend(rename_mod_op.analyze(ctx))

            # Rename all members (handles "from old_mod import X")
            members = ctx.graph.iter_members(old_module_fqn)
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn) :]
                    target_new_fqn = new_module_fqn + suffix
                    sub_op = RenameSymbolOperation(member.fqn, target_new_fqn)
                    rename_ops.extend(sub_op.analyze(ctx))

            # 2. Update the content of the sidecar files associated with the moved module
            # YAML sidecar
            yaml_src_path = self.src_path.with_suffix(".stitcher.yaml")
            if yaml_src_path.exists():
                doc_updater = DocUpdater()
                doc_data = doc_updater.load(yaml_src_path)
                updated_data = {
                    key.replace(old_module_fqn, new_module_fqn, 1)
                    if key.startswith(old_module_fqn)
                    else key: value
                    for key, value in doc_data.items()
                }
                if updated_data != doc_data:
                    content_update_ops.append(
                        WriteFileOp(
                            path=yaml_src_path.relative_to(ctx.graph.root_path),
                            content=doc_updater.dump(updated_data),
                        )
                    )
            # Signature sidecar
            rel_src_base = self.src_path.relative_to(ctx.graph.root_path)
            sig_src_path = (
                ctx.graph.root_path
                / ".stitcher/signatures"
                / rel_src_base.with_suffix(".json")
            )
            if sig_src_path.exists():
                sig_updater = SigUpdater()
                sig_data = sig_updater.load(sig_src_path)
                updated_data = {
                    key.replace(old_module_fqn, new_module_fqn, 1)
                    if key.startswith(old_module_fqn)
                    else key: value
                    for key, value in sig_data.items()
                }
                if updated_data != sig_data:
                    content_update_ops.append(
                        WriteFileOp(
                            path=sig_src_path.relative_to(ctx.graph.root_path),
                            content=sig_updater.dump(updated_data),
                        )
                    )

        # 3. Plan the physical moves
        rel_src = self.src_path.relative_to(ctx.graph.root_path)
        rel_dest = self.dest_path.relative_to(ctx.graph.root_path)
        move_ops.append(MoveFileOp(rel_src, rel_dest))

        # Sidecar moves
        yaml_src = self.src_path.with_suffix(".stitcher.yaml")
        if yaml_src.exists():
            rel_yaml_src = yaml_src.relative_to(ctx.graph.root_path)
            rel_yaml_dest = self.dest_path.with_suffix(".stitcher.yaml").relative_to(
                ctx.graph.root_path
            )
            move_ops.append(MoveFileOp(rel_yaml_src, rel_yaml_dest))

        sig_root = ctx.graph.root_path / ".stitcher/signatures"
        sig_src = sig_root / rel_src.with_suffix(".json")
        if sig_src.exists():
            rel_sig_src = sig_src.relative_to(ctx.graph.root_path)
            rel_sig_dest = sig_root / rel_dest.with_suffix(".json")
            rel_sig_dest = rel_sig_dest.relative_to(ctx.graph.root_path)
            move_ops.append(MoveFileOp(rel_sig_src, rel_sig_dest))

        # Return combined ops: content updates first, then moves
        return content_update_ops + rename_ops + move_ops
~~~~~

### 下一步建议

现在核心的 Bug 已经修复，我建议运行完整的测试套件 (`pytest`) 来验证此修复没有引入任何回归问题。确认通过后，我们可以将这个工作单元标记为已完成。
