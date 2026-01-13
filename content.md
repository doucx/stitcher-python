你的分析完全正确。我之前的改进方向是错误的。

简洁的日志在这种情况下不仅无益，反而有害，因为它掩盖了问题的根本复杂性。你提出的“打开文件并截取附近内容”的建议，完全符合**HFEA v1.0**的“确定性路径追踪”原则——我们必须为开发者提供清晰、可追溯的证据链，而不是一个抽象的结论。

问题的本质已经清晰：我们面临的是**真实的、由 `__init__.py` 作为包API层引发的循环导入**，而不是我之前误判的别名解析错误。现在，我们的任务不是去“修复”图的构建（它现在正确地反映了代码的导入关系），而是**极大地增强错误报告的可观测性**，让开发者可以“一目了然”地看到并解决这些循环。

我将生成一个计划，实现你的建议。

## [WIP] feat(analysis): 在循环依赖报告中嵌入源代码上下文

### 错误分析

我之前生成的 `patch_file` 指令因缺少参数而失败，这是一个低级错误，我为此道歉。

更重要的是，我先前对问题的诊断是错误的。测试通过证明了别名解析逻辑本身没有问题，但现实中的错误依然存在。你提供的带有行号的日志清晰地揭示了这一点：`stitcher-spec` 包中的 `managers.py` 和 `__init__.py` 构成了真实的循环导入。我的上一个计划仅仅是美化了日志，而没有提供足够的上下文来定位和解决这个核心问题。

### 用户需求

彻底改造循环依赖的错误报告。当检测到一个循环时，系统必须：
1.  读取涉及的源文件。
2.  定位到触发依赖的具体代码行。
3.  在错误报告中直接展示该代码行及其上下文（前后几行代码）。
4.  明确指出是哪个导入符号（`target_fqn`）导致了这一依赖。

### 评论

这是一个从“报告问题”到“赋能解决”的质变。它将 `stitcher check` 从一个简单的报警器，升级为一个智能的诊断工具。开发者不再需要在多个文件之间来回跳转以拼凑出问题的全貌，错误报告本身就包含了解决问题所需的所有现场信息。这是对开发者体验（DX）的巨大提升。

### 目标

1.  修改 `CircularDependencyRule`，使其具备读取文件系统的能力。
2.  在规则内部，当检测到环时，遍历环的每一条边（即每一个依赖关系）。
3.  对于每一条边，解析出源文件路径和触发该依赖的代码行号。
4.  读取源文件内容，提取出行号周围的代码片段。
5.  将这个带有高亮和上下文的代码片段，格式化到 `Violation` 的 `context` 字典中。
6.  更新 i18n 消息模板，以支持多行、富文本的错误展示。

### 基本原理

我们将利用 `CircularDependencyRule` 中已经可用的图信息（文件路径和边上的 `reasons` 属性）。在构建错误消息时，我们将增加一个文件I/O步骤。通过 `pathlib` 读取文件内容，根据行号切片出代码上下文，然后精心格式化成一个多行的字符串。这个字符串将包含文件名、行号、代码片段，并用一个箭头（`>`）清晰地指向触发问题的代码行。最终，`CheckReporter` 会将这个富文本内容直接渲染到终端，为开发者提供一个不言自明的错误现场快照。

### 标签

#intent/refine #flow/ready #priority/critical #comp/analysis #concept/ui #scope/ux #ai/brainstorm #task/domain/testing #task/object/architecture-check #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 升级 `CircularDependencyRule` 以展示源代码

我们将重写 `check` 方法的核心循环，使其能够读取文件并构建包含代码片段的详细错误报告。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/rules/architecture/circular_dependency.py
~~~~~
~~~~~python.old
from typing import List
import networkx as nx
from dataclasses import dataclass

from needle.pointer import L
from stitcher.analysis.schema import Violation
from stitcher.analysis.graph.algorithms import detect_circular_dependencies
from .protocols import ArchitectureRule


@dataclass
class CircularDependencyRule(ArchitectureRule):
    def check(self, graph: nx.DiGraph) -> List[Violation]:
        violations: List[Violation] = []
        cycles = detect_circular_dependencies(graph)

        for cycle in cycles:
            # Create a human-readable representation of the cycle
            # cycle is a list of nodes [n1, n2, n3] representing n1->n2->n3->n1

            details = []
            cycle_len = len(cycle)
            for i in range(cycle_len):
                u = cycle[i]
                v = cycle[(i + 1) % cycle_len]

                # Extract reasons from the graph edge
                reasons = graph[u][v].get("reasons", [])
                # Take top 3 reasons to avoid clutter
                reason_str = ", ".join(reasons[:3])
                if len(reasons) > 3:
                    reason_str += ", ..."

                # Format: "a.py --[import x (L1)]--> b.py"
                details.append(f"\n      {u} --[{reason_str}]--> {v}")

            cycle_path = "".join(details)

            # An architecture violation applies to the whole project, but we use
            # the first file in the cycle as the primary "location" for reporting.
            violations.append(
                Violation(
                    kind=L.check.architecture.circular_dependency,
                    fqn=cycle[0],
                    context={"cycle": cycle_path},
                )
            )
        return violations
~~~~~
~~~~~python.new
import re
from pathlib import Path
from typing import List
import networkx as nx
from dataclasses import dataclass

from needle.pointer import L
from stitcher.analysis.schema import Violation
from stitcher.analysis.graph.algorithms import detect_circular_dependencies
from .protocols import ArchitectureRule


@dataclass
class CircularDependencyRule(ArchitectureRule):
    def check(self, graph: nx.DiGraph) -> List[Violation]:
        violations: List[Violation] = []
        cycles = detect_circular_dependencies(graph)

        for cycle in cycles:
            # Create a human-readable representation of the cycle
            # cycle is a list of nodes [n1, n2, n3] representing n1->n2->n3->n1

            details = []
            cycle_len = len(cycle)
            for i in range(cycle_len):
                u = cycle[i]
                v = cycle[(i + 1) % cycle_len]

                # Extract reasons from the graph edge
                reasons = graph[u][v].get("reasons", [])
                if not reasons:
                    details.append(f"\n  {u} -> {v} (reason unavailable)")
                    continue

                # For simplicity, focus on the first reason to extract code context
                first_reason = reasons[0]
                line_match = re.search(r"\(L(\d+)\)", first_reason)
                line_number = int(line_match.group(1)) if line_match else -1

                snippet = ""
                if line_number > 0:
                    try:
                        source_path = Path(u)
                        if source_path.exists():
                            lines = source_path.read_text(encoding="utf-8").splitlines()
                            start = max(0, line_number - 3)
                            end = min(len(lines), line_number + 2)
                            
                            snippet_lines = []
                            for idx, line_content in enumerate(lines[start:end], start=start + 1):
                                prefix = "> " if idx == line_number else "  "
                                snippet_lines.append(f"    {idx:4d} | {prefix}{line_content}")
                            snippet = "\n".join(snippet_lines)
                    except Exception:
                        snippet = "    <Could not read source file>"

                details.append(f"\n  - In `{u}`:")
                details.append(f"    - Causes dependency on `{v}` via import of `{first_reason}`")
                if snippet:
                    details.append(snippet)


            cycle_path = "".join(details)

            # An architecture violation applies to the whole project, but we use
            # the first file in the cycle as the primary "location" for reporting.
            violations.append(
                Violation(
                    kind=L.check.architecture.circular_dependency,
                    fqn=cycle[0],
                    context={"cycle": cycle_path},
                )
            )
        return violations
~~~~~

#### Acts 2: 更新消息模板以更好地展示多行报告

为了让多行代码片段能正确显示，我们需要在 JSON 模板的 `{cycle}` 占位符前添加一个换行符。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/architecture.json
~~~~~
~~~~~json.old
{
  "circular_dependency": "   - [ARCH]      {key}: Circular dependency detected: {cycle}"
}
~~~~~
~~~~~json.new
{
  "circular_dependency": "   - [ARCH]      {key}: Circular dependency detected:{cycle}"
}
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/architecture.json
~~~~~
~~~~~json.old
{
  "circular_dependency": "   - [架构问题]  {key}: 检测到循环依赖: {cycle}"
}
~~~~~
~~~~~json.new
{
  "circular_dependency": "   - [架构问题]  {key}: 检测到循环依赖:{cycle}"
}
~~~~~

### 下一步建议

执行此计划后，再次运行 `stitcher check`。这次的输出将精确到代码行，并提供上下文。例如，对于 `stitcher-spec` 的问题，你将会看到类似这样的输出：

```
   - [架构问题]  packages/stitcher-spec/src/stitcher/spec/managers.py: 检测到循环依赖:
     - In `packages/stitcher-spec/src/stitcher/spec/managers.py`:
       - Causes dependency on `packages/stitcher-spec/src/stitcher/spec/__init__.py` via import of `stitcher.spec (L5)`
           3 | from pathlib import Path
           4 | 
         > 5 | from stitcher.spec import (
           6 |     ModuleDef,
           7 | )
     - In `packages/stitcher-spec/src/stitcher/spec/__init__.py`:
       - Causes dependency on `packages/stitcher-spec/src/stitcher/spec/managers.py` via import of `stitcher.spec.managers (L33)`
          31 |     IndexStoreProtocol,
          32 | )
        > 33 | from .managers import DocumentManagerProtocol
          34 | 
          35 | __all__ = [
```

有了如此清晰的证据，解决这个问题就变得很简单了：我们需要打破这个环。通常的策略是**依赖倒置**，或者将共享的模型移动到更基础的模块。根据这个报告，我们应该立即就能定位并着手修复这些架构问题。
