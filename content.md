好的，我们开始实施。

这是第一阶段的计划，专注于建立支撑“交互式调和向导”所需的、健壮的领域模型。我们将在 `stitcher-spec` 包中定义所有核心数据结构，为后续的逻辑和 UI 实现奠定坚实的基础。

## [WIP] feat: 定义交互式检查的领域模型

### 用户需求
根据我们讨论的技术提案和改进方案，开始实施“交互式引导与引导式调和模式”功能。第一步是创建所需的核心数据结构（领域模型），包括冲突类型、解决方案、原子操作单元和最终的计划表。

### 评论
这是一个关键的架构步骤。首先在 `stitcher-spec` 中明确定义这些数据模型，可以确保应用层 (`stitcher-application`) 和表现层 (`stitcher-cli`) 之间有一个清晰、稳定且类型安全的契约。这种方式遵循了领域驱动设计的原则，将核心概念与具体实现解耦，使得整个系统更加健壮和易于维护。

### 目标
1.  在 `stitcher.spec.models` 中创建 `ConflictType` 和 `ResolutionAction` 两个枚举，用于标准化地表示冲突类型和用户可选择的操作。
2.  创建 `Resolution` 数据类，用于封装一次原子性的调和操作（针对哪个 FQN，是什么冲突，用户选择了什么动作）。
3.  创建 `ResolutionPlan` 数据类，作为 `Resolution` 对象的容器，代表用户在交互过程中制定的完整“计划表”。
4.  将这些新模型导出到 `stitcher.spec` 包的公共 API 中。
5.  为所有新模型添加完整的文档字符串，并更新 `.stitcher.yaml` 文件。

### 基本原理
我们将所有这些新的数据模型集中放置在 `stitcher-spec` 包中。因为 `spec` 是所有其他 `stitcher-*` 包的底层依赖，这样做可以确保任何需要理解或处理这些数据结构的组件（无论是核心应用逻辑还是CLI）都可以直接导入它们，而不会造成循环依赖。这是构建可扩展、分层架构的基础。

### 标签
#intent/architect #flow/ready #priority/high #comp/spec #concept/state #scope/api #ai/instruct #task/domain/cli #task/object/interactive-check #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 在 `models.py` 中定义新的数据结构

我们将在 `packages/stitcher-spec/src/stitcher/spec/models.py` 文件的末尾追加新的枚举和数据类定义。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
        # Module-level public attributes
        for attr in self.attributes:
            if not attr.name.startswith("_") and not attr.docstring:
                keys.append(attr.name)

        return sorted(keys)
~~~~~
~~~~~python.new
        # Module-level public attributes
        for attr in self.attributes:
            if not attr.name.startswith("_") and not attr.docstring:
                keys.append(attr.name)

        return sorted(keys)


# --- Interactive Reconciliation Models ---


class ConflictType(str, Enum):
    SIGNATURE_DRIFT = "SIGNATURE_DRIFT"
    CO_EVOLUTION = "CO_EVOLUTION"


class ResolutionAction(str, Enum):
    RELINK = "RELINK"
    RECONCILE = "RECONCILE"
    SKIP = "SKIP"
    ABORT = "ABORT"


@dataclass
class Resolution:
    fqn: str
    conflict_type: ConflictType
    action: ResolutionAction


@dataclass
class ResolutionPlan:
    resolutions: List[Resolution] = field(default_factory=list)
~~~~~

#### Acts 2: 在 `__init__.py` 中导出新模型

现在，我们将这些新创建的类导出，使其成为 `stitcher.spec` 包公共 API 的一部分。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
__all__ = [
    "Argument",
    "ArgumentKind",
    "Attribute",
    "ClassDef",
    "FunctionDef",
    "ModuleDef",
]
~~~~~
~~~~~python.new
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

#### Acts 3: 在 `models.stitcher.yaml` 中添加文档

最后，我们为所有新模型添加文档字符串，确保代码的自文档化。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.stitcher.yaml
~~~~~
~~~~~yaml.old
"ModuleDef.is_documentable": |-
  Checks if the module contains any content that would warrant a doc file.
~~~~~
~~~~~yaml.new
"ModuleDef.is_documentable": |-
  Checks if the module contains any content that would warrant a doc file.
"ConflictType": |-
  Enumeration of possible conflict types detected by `check`.
"ConflictType.CO_EVOLUTION": |-
  Both the code signature and the documentation content have changed.
"ConflictType.SIGNATURE_DRIFT": |-
  The code signature has changed, but the documentation content has not.
"ResolutionAction": |-
  Enumeration of actions a user can take to resolve a conflict.
"ResolutionAction.ABORT": |-
  Abort the entire operation.
"ResolutionAction.RECONCILE": |-
  Accept both the new signature and new documentation as the correct baseline.
"ResolutionAction.RELINK": |-
  Accept the new signature but keep the existing (unchanged) documentation.
"ResolutionAction.SKIP": |-
  Skip resolving this conflict for now.
"Resolution": |-
  Represents a single, atomic resolution decision made by the user.
"Resolution.action": |-
  The action chosen by the user to resolve the conflict.
"Resolution.conflict_type": |-
  The type of conflict that was detected.
"Resolution.fqn": |-
  The fully qualified name of the symbol that has a conflict.
"ResolutionPlan": |-
  A container for a list of resolution decisions, representing the complete plan
  to be executed.
"ResolutionPlan.resolutions": |-
  The list of atomic resolution decisions.
~~~~~

### 下一步建议

我们已经成功地定义了交互式调和功能所需的核心数据结构。

下一步是进入 **阶段 2**：重构 `stitcher-application` 中的核心逻辑。我们将修改 `StitcherApp`，使其在 `run_check` 期间不再直接报错，而是使用这些新模型来识别冲突，并为与交互层对接做好准备。
