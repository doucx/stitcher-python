你捕捉到了一个非常精准的错误。你的分析完全正确。

这是一个典型的 `ImportError`，它的根源在于我的疏忽：在**阶段 1** 的计划中，我虽然在 `stitcher.spec.models` 中定义了新的数据模型，并且在 `stitcher.spec.__init__` 中更新了 `__all__` 列表，但我**忘记了在 `__init__.py` 文件中真正地从 `models.py` 导入这些新的类和枚举**。

`__all__` 列表只影响 `from package import *` 的行为，但并不会自动将子模块中的名称提升到包的顶级命名空间。因此，当 `stitcher.app.core` 尝试 `from stitcher.spec import ConflictType` 时，它无法在 `stitcher.spec` 这个命名空间中找到这个名字。

我将立即生成一个修复计划来纠正这个问题。

## [WIP] fix: 修正 stitcher.spec 中缺失的模型导出

### 错误分析
在 `stitcher.app.core` 中尝试从 `stitcher.spec` 导入 `ConflictType` 时，系统抛出 `ImportError`。根本原因是在 `packages/stitcher-spec/src/stitcher/spec/__init__.py` 文件中，虽然 `__all__` 被更新了，但并未从 ` .models` 子模块中导入新的数据模型（`ConflictType`, `ResolutionAction` 等），导致它们没有被暴露在包的顶级命名空间中。

### 用户需求
修复此 `ImportError`，确保所有在 `stitcher.spec.models` 中定义的新数据结构都能被其他包正确地从 `stitcher.spec` 直接导入。

### 评论
这是一个关键的修复，它纠正了包API的暴露问题。正确的导出是维持清晰、稳定内部API的基石。

### 目标
1.  修改 `packages/stitcher-spec/src/stitcher/spec/__init__.py`。
2.  在现有的 `from .models import ...` 语句中，添加所有新创建的数据模型。

### 基本原理
通过在包的 `__init__.py` 文件中显式地从其子模块导入名称，我们可以控制包的公共API。此修复将使 `ConflictType` 等模型成为 `stitcher.spec` 包API的一部分，从而解决导入错误。

### 标签
#intent/fix #flow/ready #priority/critical #comp/spec #scope/api #ai/instruct #task/domain/cli #task/object/interactive-check #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 在 `spec/__init__.py` 中导入新模型

我们将修改 `from .models import ...` 这一行，将所有新的模型都包含进来。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
from .models import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
)

__all__ = [
    "Argument",
    "ArgumentKind",
    "Attribute",
    "ClassDef",
    "FunctionDef",
    "ModuleDef",
    # Reconciliation Models
    "ConflictType",
    "ResolutionAction",
    "Resolution",
    "ResolutionPlan",
]
~~~~~
~~~~~python.new
from .models import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
    ConflictType,
    ResolutionAction,
    Resolution,
    ResolutionPlan,
)

__all__ = [
    "Argument",
    "ArgumentKind",
    "Attribute",
    "ClassDef",
    "FunctionDef",
    "ModuleDef",
    # Reconciliation Models
    "ConflictType",
    "ResolutionAction",
    "Resolution",
    "ResolutionPlan",
]
~~~~~

### 下一步建议
这个修复非常直接且关键。一旦应用此修复，之前的导入错误将得到解决。

请执行此计划。执行后，我们可以重新审视并继续执行**阶段三**的计划。
