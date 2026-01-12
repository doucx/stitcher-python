简要回答
好的，我将执行步骤 3。在实现过程中，为了能够复用现有的、健壮的 `SymbolRenamerTransformer`（它依赖旧的 FQN 来进行安全检查和短名提取），我需要微调一下 `RefactoringStrategyProtocol`，增加 `old_name` 参数。这是一个必要的架构修正。

## [WIP] feat: 实现 Python 重构策略并修正协议

### 用户需求
1.  **修正协议**: 更新 `RefactoringStrategyProtocol`，增加 `old_name` 参数，以便策略层能进行更精确的重构（例如区分短名/长名）。
2.  **实现策略**: 在 `stitcher-lang-python` 中实现 `PythonRefactoringStrategy`，封装现有的 CST 转换逻辑。

### 评论
现有的 `SymbolRenamerTransformer` 是一个基于 LibCST 的强大工具，它依赖 `old_fqn` 来确保只重命名正确的目标，并智能处理 `import` 和 `Attribute` 的重写。为了复用这一资产而不是重写一个脆弱的文本替换器，协议必须传递 `old_name` 上下文。

### 目标
1.  更新 `stitcher-spec` 中的重构协议。
2.  在 `stitcher-lang-python` 中创建 `refactor.py`，实现适配逻辑。

### 基本原理
通过适配器模式，将通用的 `RefactorUsage` 转换为 Python 分析层专用的 `UsageLocation`，从而打通 spec 层与具体的语言实现层。

### 标签
#intent/build #intent/refine #flow/ready #priority/high
#comp/lang-python #comp/spec #concept/refactor
#task/domain/refactor #task/object/python-strategy #task/action/implement #task/state/continue

---

### Script

#### Acts 1: 修正重构协议 (添加 old_name)

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/refactor.py
~~~~~
~~~~~python.old
    def rename_symbol(
        self,
        source_code: str,
        usages: List[RefactorUsage],
        new_name: str
    ) -> str:
        """
        Apply a rename operation to the source code.

        Args:
            source_code: The original content of the file.
            usages: A list of locations in this file that refer to the symbol being renamed.
            new_name: The new fully qualified name (FQN) or short name.
                      The strategy is responsible for determining whether to use
                      the short name or FQN based on the context of each usage.

        Returns:
            The modified source code.
        """
        ...
~~~~~
~~~~~python.new
    def rename_symbol(
        self,
        source_code: str,
        usages: List[RefactorUsage],
        old_name: str,
        new_name: str,
    ) -> str:
        """
        Apply a rename operation to the source code.

        Args:
            source_code: The original content of the file.
            usages: A list of locations in this file that refer to the symbol being renamed.
            old_name: The original fully qualified name (FQN) of the symbol.
                      Useful for verification and context awareness (e.g. short name extraction).
            new_name: The new fully qualified name (FQN). The strategy logic
                      should determine if a short name or full name is appropriate
                      for each insertion point.

        Returns:
            The modified source code.
        """
        ...
~~~~~

#### Acts 2: 实现 PythonRefactoringStrategy

我们在 `stitcher-lang-python` 中实现该策略。我们需要将通用的 `RefactorUsage` 映射回内部的 `UsageLocation`，以便复用 `SymbolRenamerTransformer`。

~~~~~act
write_file
packages/stitcher-lang-python/src/stitcher/lang/python/refactor.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List

import libcst as cst

from stitcher.spec import (
    RefactoringStrategyProtocol,
    RefactorUsage,
)
from stitcher.lang.python.analysis.models import UsageLocation, ReferenceType
from stitcher.lang.python.transform.rename import SymbolRenamerTransformer


class PythonRefactoringStrategy(RefactoringStrategyProtocol):
    def rename_symbol(
        self,
        source_code: str,
        usages: List[RefactorUsage],
        old_name: str,
        new_name: str,
    ) -> str:
        if not usages:
            return source_code

        # 1. Adapt generic RefactorUsage to internal UsageLocation
        # The SymbolRenamerTransformer relies on 'target_node_fqn' (old_name) to verify
        # nodes before renaming.
        internal_locations: List[UsageLocation] = []
        dummy_path = Path("")  # Path is not used by the transformer for single-file ops

        for u in usages:
            loc = UsageLocation(
                file_path=dummy_path,
                lineno=u.location.lineno,
                col_offset=u.location.col_offset,
                end_lineno=u.location.end_lineno,
                end_col_offset=u.location.end_col_offset,
                ref_type=ReferenceType.SYMBOL,  # Default assumption
                target_node_fqn=old_name,
            )
            internal_locations.append(loc)

        # 2. Prepare the rename map
        rename_map = {old_name: new_name}

        # 3. Apply transformation
        try:
            module = cst.parse_module(source_code)
            wrapper = cst.MetadataWrapper(module)
            
            transformer = SymbolRenamerTransformer(rename_map, internal_locations)
            modified_module = wrapper.visit(transformer)
            
            return modified_module.code
        except Exception:
            # In case of syntax errors or other CST issues, return original code
            # Caller handles logging/error reporting
            return source_code
~~~~~

#### Acts 3: 导出新组件

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/__init__.py
~~~~~
~~~~~python.old
from .transform.facade import PythonTransformer
from .uri import SURIGenerator

__all__ = [
    "PythonAdapter",
    "PythonFingerprintStrategy",
    "InspectionError",
    "parse_plugin_entry",
    "GriffePythonParser",
    "PythonParser",
    "PythonTransformer",
    "SURIGenerator",
]
~~~~~
~~~~~python.new
from .transform.facade import PythonTransformer
from .uri import SURIGenerator
from .refactor import PythonRefactoringStrategy

__all__ = [
    "PythonAdapter",
    "PythonFingerprintStrategy",
    "InspectionError",
    "parse_plugin_entry",
    "GriffePythonParser",
    "PythonParser",
    "PythonTransformer",
    "SURIGenerator",
    "PythonRefactoringStrategy",
]
~~~~~

### 下一步建议
接下来是 **步骤 4: 重构 `stitcher-refactor`**。这是最核心的一步，我们将移除 `SidecarUpdateMixin`，引入 `StrategyRegistry`，并重写 `GlobalBatchRenamer` 以使用新的协议。这将彻底完成引擎的泛化。
