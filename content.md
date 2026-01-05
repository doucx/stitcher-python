简要回答
好的，我们将开始阶段四的工作。第一步是设计并实现 `MigrationSpec` API，这是用户定义重构逻辑的核心接口。它将提供一种声明式的方式来聚合多个重构操作（Operations），并为批量重命名提供便捷方法。

## [WIP] feat: 实现 MigrationSpec API 及其测试

### 用户需求
构建 `MigrationSpec` 类，作为 Stitcher Migration Pack (SMP) 的核心容器。它允许用户以编程方式定义一系列重构操作（如 `Rename`, `Move`），并支持批量添加重命名映射的语法糖。

### 评论
这是连接底层重构引擎与上层用户配置（迁移脚本）的桥梁。一个清晰、简洁的 API 设计对于开发者体验（DX）至关重要。我们将使用别名（如 `Rename` 代替 `RenameSymbolOperation`）来简化脚本编写。

### 目标
1.  在 `stitcher-refactor` 包中创建新的 `migration` 模块。
2.  实现 `MigrationSpec` 类，支持 `add` 和 `add_map` 方法。
3.  导出易用的操作别名 (`Rename`, `Move`, `MoveDir`)。
4.  编写单元测试验证 API 行为。

### 基本原理
`MigrationSpec` 本质上是一个操作队列的构建器。它不负责执行，只负责收集用户的意图。通过提供 `add_map`，我们大大简化了大规模重命名重构（这是最常见的场景）的配置工作量。

### 标签
#intent/architect #intent/build #flow/ready #priority/high
#comp/refactor #concept/api #scope/core #scope/dx
#ai/instruct
#task/domain/refactoring #task/object/migration-spec #task/action/implementation
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 创建 MigrationSpec API

我们将创建 `spec.py` 来定义类，并在 `__init__.py` 中暴露它以及操作的别名。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/migration/spec.py
~~~~~
~~~~~python
from typing import List, Dict, Union, TypeAlias
from pathlib import Path

from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation

# --- Aliases for better DX in migration scripts ---
Rename: TypeAlias = RenameSymbolOperation
Move: TypeAlias = MoveFileOperation
MoveDir: TypeAlias = MoveDirectoryOperation


class MigrationSpec:
    """
    A container for defining a set of refactoring operations.
    This serves as the API for Stitcher Migration Packs (SMP).
    """

    def __init__(self):
        self._operations: List[AbstractOperation] = []

    def add(self, operation: AbstractOperation) -> "MigrationSpec":
        """
        Register a single atomic operation.
        """
        self._operations.append(operation)
        return self

    def add_map(self, rename_map: Dict[str, str]) -> "MigrationSpec":
        """
        Syntactic sugar for adding multiple RenameSymbolOperation items.
        
        Args:
            rename_map: A dictionary mapping old FQNs to new FQNs.
        """
        for old_fqn, new_fqn in rename_map.items():
            self.add(RenameSymbolOperation(old_fqn, new_fqn))
        return self

    @property
    def operations(self) -> List[AbstractOperation]:
        """
        Returns the list of collected operations.
        """
        return self._operations
~~~~~

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/migration/__init__.py
~~~~~
~~~~~python
from .spec import MigrationSpec, Rename, Move, MoveDir

__all__ = ["MigrationSpec", "Rename", "Move", "MoveDir"]
~~~~~

#### Acts 2: 创建单元测试

测试 `MigrationSpec` 能正确收集操作，特别是 `add_map` 能正确转换为多个 `RenameSymbolOperation`。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/migration/__init__.py
~~~~~
~~~~~python
# Tests for migration package
~~~~~

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/migration/test_spec.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.refactor.migration import MigrationSpec, Rename, Move, MoveDir
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.operations.move_file import MoveFileOperation


def test_migration_spec_add_operations():
    spec = MigrationSpec()
    
    # 1. Add various operations
    spec.add(Rename("old.pkg", "new.pkg"))
    spec.add(Move(Path("src/old.py"), Path("src/new.py")))
    
    # 2. Verify collection
    assert len(spec.operations) == 2
    assert isinstance(spec.operations[0], RenameSymbolOperation)
    assert spec.operations[0].old_fqn == "old.pkg"
    
    assert isinstance(spec.operations[1], MoveFileOperation)
    assert spec.operations[1].src_path == Path("src/old.py")


def test_migration_spec_add_map():
    spec = MigrationSpec()
    
    # 1. Use syntactic sugar
    mapping = {
        "pkg.A": "pkg.B",
        "pkg.X": "pkg.Y"
    }
    spec.add_map(mapping)
    
    # 2. Verify conversion
    assert len(spec.operations) == 2
    
    op1 = spec.operations[0]
    assert isinstance(op1, RenameSymbolOperation)
    assert op1.old_fqn == "pkg.A"
    assert op1.new_fqn == "pkg.B"
    
    op2 = spec.operations[1]
    assert isinstance(op2, RenameSymbolOperation)
    assert op2.old_fqn == "pkg.X"
    assert op2.new_fqn == "pkg.Y"


def test_migration_spec_fluent_interface():
    spec = MigrationSpec()
    
    # Verify chaining works
    (
        spec
        .add(Rename("a", "b"))
        .add_map({"c": "d"})
    )
    
    assert len(spec.operations) == 2
~~~~~

### 下一步建议

实现 `MigrationLoader`，它负责动态加载用户的 Python 迁移脚本（例如 `migrations/001_xxx.py`），注入 `MigrationSpec` 实例，并执行其中的 `upgrade` 函数来填充 Spec。这将完成 SMP 系统的“读取”部分。
