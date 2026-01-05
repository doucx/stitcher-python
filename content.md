Generate the Act.

# [WIP] fix: 实现事务中的路径重定向以解决“僵尸文件”问题

### 用户需求
解决重构过程中因操作顺序问题导致的“僵尸文件”现象（即文件被移动后，后续的写入操作错误的在原位置重建了该文件）。

### 评论
在复杂的批量重构中，一个文件可能既是移动操作的主体，又是其他重命名操作的修改目标。
如果 `Move(A->B)` 先于 `Write(A)` 执行，`Write(A)` 会错误地在位置 A 重新创建文件，且该文件仅包含部分修改。
正确行为应该是 `Write(A)` 自动重定向为 `Write(B)`，作用于移动后的文件。

### 目标
在 `TransactionManager` 中实现 `rebase_operations` 逻辑，在提交前动态调整操作的目标路径。

### 基本原理
引入一个路径映射表。遍历操作列表：
1. 对于 `MoveFileOp(src, dest)`，记录 `src -> dest` 的映射。
2. 对于 `WriteFileOp(path)`，检查 `path` 是否在映射表中。如果是，更新 `path` 为映射后的新路径。
3. 对于 `DeleteFileOp` 等，同理处理。

### 标签
#intent/fix #flow/ready #priority/critical #comp/refactor #concept/transaction #scope/core #ai/instruct #task/domain/refactoring #task/object/transaction-manager #task/action/implement-rebase #task/state/continue

---

### Script

#### Acts 1: 添加 Rebase 逻辑测试

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/engine/test_transaction_rebase.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    WriteFileOp,
    MoveFileOp,
    DeleteFileOp
)

def test_rebase_write_after_move():
    """
    Scenario:
    1. Move A -> B
    2. Write A (content updated)
    
    Expected:
    1. Move A -> B
    2. Write B (content updated)
    """
    tm = TransactionManager(Path("/"))
    tm.add_move("A", "B")
    tm.add_write("A", "new content")
    
    # We need to access the private logic or trigger it via commit (mocked fs)
    # Let's inspect the internal _rebase_ops method which we will implement
    rebased = tm._rebase_ops(tm._ops)
    
    assert len(rebased) == 2
    assert isinstance(rebased[0], MoveFileOp)
    assert rebased[0].path == Path("A")
    assert rebased[0].dest == Path("B")
    
    assert isinstance(rebased[1], WriteFileOp)
    assert rebased[1].path == Path("B")  # Rebased!
    assert rebased[1].content == "new content"

def test_rebase_chain_moves():
    """
    Scenario:
    1. Move A -> B
    2. Move B -> C
    3. Write A
    
    Expected:
    1. Move A -> B
    2. Move B -> C
    3. Write C
    """
    tm = TransactionManager(Path("/"))
    tm.add_move("A", "B")
    tm.add_move("B", "C")
    tm.add_write("A", "final content")
    
    rebased = tm._rebase_ops(tm._ops)
    
    assert len(rebased) == 3
    assert isinstance(rebased[2], WriteFileOp)
    assert rebased[2].path == Path("C")

def test_rebase_no_effect_if_write_first():
    """
    Scenario:
    1. Write A
    2. Move A -> B
    
    Expected: No change in paths (Write A happens before it moves)
    """
    tm = TransactionManager(Path("/"))
    tm.add_write("A", "content")
    tm.add_move("A", "B")
    
    rebased = tm._rebase_ops(tm._ops)
    
    assert rebased[0].path == Path("A")
    assert rebased[1].path == Path("A")
    assert rebased[1].dest == Path("B")

def test_rebase_delete_after_move():
    """
    Scenario:
    1. Move A -> B
    2. Delete A
    
    Expected:
    1. Move A -> B
    2. Delete B
    """
    tm = TransactionManager(Path("/"))
    tm.add_move("A", "B")
    tm.add_delete_file("A")
    
    rebased = tm._rebase_ops(tm._ops)
    
    assert rebased[1].path == Path("B")
~~~~~

#### Acts 2: 实现 TransactionManager._rebase_ops

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/transaction.py
~~~~~
~~~~~python.old
    def preview(self) -> List[str]:
        return [op.describe() for op in self._ops]

    def commit(self) -> None:
        for op in self._ops:
            op.execute(self.fs, self.root_path)
        self._ops.clear()

    @property
~~~~~
~~~~~python.new
    def preview(self) -> List[str]:
        # Preview should also show rebased operations to be accurate
        rebased = self._rebase_ops(self._ops)
        return [op.describe() for op in rebased]

    def commit(self) -> None:
        rebased_ops = self._rebase_ops(self._ops)
        for op in rebased_ops:
            op.execute(self.fs, self.root_path)
        self._ops.clear()

    def _rebase_ops(self, ops: List[FileOp]) -> List[FileOp]:
        """
        Rebases operations to handle cases where a file is moved and then modified.
        For example: [Move(A->B), Write(A)] becomes [Move(A->B), Write(B)].
        """
        rebased_ops = []
        # Map current_location -> known_location
        # But wait, we need to track the location of specific logical files.
        # Simple approach: Trace forward.
        
        # Mapping from original_path (or transient path) to current_effective_path
        # No, that's not right.
        # We need to map: "If an op refers to path P, change it to P'"
        
        path_map = {} 
        
        for op in ops:
            # 1. Resolve current path based on history
            # We copy the op to avoid mutating the original input list objects if reused
            # (Though dataclasses are mutable, let's be safe)
            import copy
            new_op = copy.copy(op)
            
            if new_op.path in path_map:
                new_op.path = path_map[new_op.path]
                
            # 2. Update map if this is a Move
            if isinstance(new_op, MoveFileOp):
                # Now, anything pointing to new_op.path should now point to new_op.dest
                # AND anything that mapped to new_op.path should now map to new_op.dest
                
                # Direct mapping:
                # If subsequent op targets 'src', it should target 'dest'
                src = new_op.path
                dest = new_op.dest
                
                # Update forward lookup
                path_map[src] = dest
                
                # Update existing transitive mappings
                # e.g. A->B, now B->C. We need A->C.
                for k, v in path_map.items():
                    if v == src:
                        path_map[k] = dest
            
            rebased_ops.append(new_op)
            
        return rebased_ops

    @property
~~~~~

### 下一步建议
运行测试 `uv run pytest packages/stitcher-refactor/tests/unit/engine/test_transaction_rebase.py`。
然后，建议用户重新尝试他们的重构脚本。有了这个修复，`engine.py` 的修改应该会正确应用到移动后的 `host/instance.py` 上，并且 `__init__.py` 的脚手架和引用更新也应该正常工作。
