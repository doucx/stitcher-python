好的，我们继续阶段四。现在我们来实现 `MigrationLoader`，它将负责解析用户编写的 Python 迁移脚本，并将其转换为 `MigrationSpec` 对象。

## [WIP] feat: 实现 MigrationLoader 以解析迁移脚本

### 用户需求
创建一个 `MigrationLoader` 类，它能够动态地加载一个指定的 Python 文件，执行其中的 `upgrade(spec: MigrationSpec)` 函数，并返回一个填充了重构操作的 `MigrationSpec` 实例。

### 评论
这是 SMP 系统的核心运行时组件。通过使用 `importlib`，我们可以安全地、动态地加载用户代码，而不会污染全局 `sys.modules`。定义一套清晰的自定义异常 (`MigrationScriptError`) 将有助于向用户提供明确的错误反馈，例如当脚本缺少 `upgrade` 函数或存在语法错误时。

### 目标
1.  在 `stitcher.refactor.migration` 模块中添加 `exceptions.py` 和 `loader.py`。
2.  实现 `MigrationLoader` 类及其核心方法 `load_from_path`。
3.  处理各种错误情况（文件未找到、语法错误、缺少 `upgrade` 函数等），并抛出自定义异常。
4.  编写单元测试，覆盖成功加载和所有预期的失败场景。

### 基本原理
`MigrationLoader` 利用 Python 的 `importlib.util` 库来实现动态模块加载。它通过文件路径创建一个模块规范 (`spec`)，然后基于该规范创建一个新的模块对象，并执行脚本文件中的代码。这个过程是隔离的，确保了用户脚本的执行不会干扰 Stitcher 的内部状态。加载成功后，它会查找并调用约定好的 `upgrade` 函数，将一个空的 `MigrationSpec` 实例作为参数传入，从而让用户脚本有机会填充这个实例。

### 标签
#intent/build #flow/ready #priority/high
#comp/refactor #concept/api #scope/core #dx
#ai/instruct
#task/domain/refactoring #task/object/migration-spec #task/action/implementation
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 定义自定义异常

我们首先创建一个 `exceptions.py` 文件来存放与迁移相关的错误类型。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/migration/exceptions.py
~~~~~
~~~~~python
class MigrationError(Exception):
    """Base exception for migration-related errors."""
    pass

class MigrationScriptError(MigrationError):
    """Raised when a migration script is invalid."""
    pass
~~~~~

#### Acts 2: 实现 MigrationLoader

现在，我们创建 `loader.py` 并实现 `MigrationLoader` 类。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/migration/loader.py
~~~~~
~~~~~python
import importlib.util
from pathlib import Path

from .spec import MigrationSpec
from .exceptions import MigrationScriptError


class MigrationLoader:
    def load_from_path(self, path: Path) -> MigrationSpec:
        """
        Dynamically loads a migration script and returns a populated MigrationSpec.
        """
        if not path.is_file():
            raise FileNotFoundError(f"Migration script not found at: {path}")

        # Create a unique module name to avoid polluting sys.modules with a common name
        module_name = f"stitcher.migrations.{path.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise MigrationScriptError(f"Could not create module spec for {path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise MigrationScriptError(f"Syntax error in migration script {path}: {e}") from e
        except Exception as e:
            raise MigrationScriptError(f"Failed to load migration script {path}: {e}") from e

        if not hasattr(module, "upgrade"):
            raise MigrationScriptError(f"Migration script {path} is missing the 'upgrade' function.")

        upgrade_func = getattr(module, "upgrade")
        if not callable(upgrade_func):
            raise MigrationScriptError(f"The 'upgrade' attribute in {path} is not a callable function.")

        migration_spec = MigrationSpec()
        upgrade_func(migration_spec)

        return migration_spec
~~~~~

#### Acts 3: 更新模块 `__init__.py`

我们将 `MigrationLoader` 导出到包的公共 API 中。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/migration/__init__.py
~~~~~
~~~~~python.old
from .spec import MigrationSpec, Rename, Move, MoveDir

__all__ = ["MigrationSpec", "Rename", "Move", "MoveDir"]
~~~~~
~~~~~python.new
from .spec import MigrationSpec, Rename, Move, MoveDir
from .loader import MigrationLoader
from .exceptions import MigrationError, MigrationScriptError

__all__ = [
    "MigrationSpec",
    "Rename",
    "Move",
    "MoveDir",
    "MigrationLoader",
    "MigrationError",
    "MigrationScriptError",
]
~~~~~

#### Acts 4: 编写单元测试

最后，我们为 `MigrationLoader` 编写全面的单元测试，以确保其健壮性。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/migration/test_loader.py
~~~~~
~~~~~python
import pytest
from pathlib import Path

from stitcher.refactor.migration.loader import MigrationLoader
from stitcher.refactor.migration.exceptions import MigrationScriptError
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation


def test_loader_happy_path(tmp_path: Path):
    # 1. Arrange: Create a valid migration script
    script_content = """
from stitcher.refactor.migration import MigrationSpec, Rename

def upgrade(spec: MigrationSpec):
    spec.add(Rename("old.name", "new.name"))
    spec.add_map({"a.b": "c.d"})
"""
    script_path = tmp_path / "001_valid_migration.py"
    script_path.write_text(script_content)

    # 2. Act
    loader = MigrationLoader()
    spec = loader.load_from_path(script_path)

    # 3. Assert
    assert len(spec.operations) == 2
    assert isinstance(spec.operations[0], RenameSymbolOperation)
    assert spec.operations[0].old_fqn == "old.name"
    assert isinstance(spec.operations[1], RenameSymbolOperation)
    assert spec.operations[1].old_fqn == "a.b"


def test_loader_missing_upgrade_function(tmp_path: Path):
    script_path = tmp_path / "002_no_upgrade.py"
    script_path.write_text("a = 1")
    loader = MigrationLoader()

    with pytest.raises(MigrationScriptError, match="missing the 'upgrade' function"):
        loader.load_from_path(script_path)


def test_loader_upgrade_not_callable(tmp_path: Path):
    script_path = tmp_path / "003_upgrade_is_var.py"
    script_path.write_text("upgrade = 'not a function'")
    loader = MigrationLoader()

    with pytest.raises(MigrationScriptError, match="is not a callable function"):
        loader.load_from_path(script_path)


def test_loader_syntax_error(tmp_path: Path):
    script_path = tmp_path / "004_syntax_error.py"
    script_path.write_text("def upgrade(spec):\\n  pass(")  # invalid syntax
    loader = MigrationLoader()

    with pytest.raises(MigrationScriptError, match="Syntax error"):
        loader.load_from_path(script_path)


def test_loader_file_not_found():
    loader = MigrationLoader()

    with pytest.raises(FileNotFoundError):
        loader.load_from_path(Path("non_existent_file.py"))
~~~~~

### 下一步建议

现在我们已经有了定义迁移 (`MigrationSpec`) 和加载迁移 (`MigrationLoader`) 的机制，下一步是创建 `Planner`。`Planner` 的职责是接收 `MigrationSpec` 中定义的所有操作，然后调用每个操作的 `analyze` 方法，最终将所有生成的 `FileOp` 汇集成一个完整的、可执行的事务计划。
