你的观察非常敏锐且准确。目前的 `CircularDependencyRule` 在报告循环依赖时，其描述逻辑存在语义上的“误导性”。

在目前的实现中，报告逻辑如下：
1. 它遍历循环中的每一条边 `u -> v`（即 `u` 依赖 `v`）。
2. 它打印：“Causes dependency on `v`”（导致了对 `v` 的依赖）。
3. 紧接着，它打印从 `u`（源文件）中提取的代码片段。

**问题在于**：用户在阅读报告时，习惯性地将紧随其后的代码片段视为对上方提到的“文件名”的解释。当看到 “Causes dependency on `cli.py`” 后面跟着 `sdk.py` 的代码时，会产生逻辑上的错位感。

正如你所说，理想的报告结构应该是“**文件归属明确**”：先声明“在文件 A 中”，然后展示代码片段，并解释这段代码导致了对文件 B 的依赖。

---

## [WIP] fix(analysis): 调整循环依赖报告结构，确保代码片段与文件名对齐

### 用户需求
修复循环依赖分析器的报告格式。确保在展示代码片段之前，先显式声明该片段所属的文件名，消除“文件名”与“后续代码内容”不对齐的歧义。

### 评论
这不仅是一个 UI 改进，更是一个逻辑严密性的修正。当前的输出方式在复杂的循环（超过 2 个节点）中会让人非常困惑。通过引入 `In {file}:` 层级，我们可以让架构师一眼看清依赖是从哪里产生的。

### 目标
1. 修改 `CircularDependencyRule` 中的循环处理逻辑。
2. 为多节点循环的每一个步骤增加 `- In {source_file}:` 声明，使其与单节点自循环（Self-loop）的报告风格保持一致。
3. 确保代码片段紧跟在其所属的文件声明之后。

### 基本原理
我们将修改 `CircularDependencyRule.check` 方法中的 `details` 构建逻辑。不再直接以 “Causes dependency on...” 开头，而是先追加一行 ` - In {u}:`。这样，下方的 `Causes dependency on {v}...` 和代码片段都会在逻辑上归属于文件 `u`。

### 标签
#intent/fix #flow/ready #comp/engine #concept/parser #scope/ux #task/domain/analysis #task/object/circular-dependency-rule #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 修正 `CircularDependencyRule` 的报告生成逻辑

我们将修改 `packages/stitcher-analysis/src/stitcher/analysis/rules/architecture/circular_dependency.py` 文件，为循环路径中的每个节点添加显式的文件声明。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/rules/architecture/circular_dependency.py
~~~~~
~~~~~python.old
                        details.append(
                            f"\n   - Causes dependency on `{v}` via import of `{first_reason}`"
                        )
                        if snippet:
                            details.append(f"\n{snippet}")
~~~~~
~~~~~python.new
                        details.append(f"\n  - In `{u}`:")
                        details.append(
                            f"    - Causes dependency on `{v}` via import of `{first_reason}`"
                        )
                        if snippet:
                            details.append(f"\n{snippet}")
~~~~~

### 下一步建议

1.  **验证输出**: 建议重新运行 `stitcher check`。现在的输出应该如下所示，逻辑非常清晰：
    ```text
    - [架构问题] (优先级 #1) 位于 sdk.py:
      - In `sdk.py`:
        - Causes dependency on `cli.py` via import of `...` (L66)
          66 | > from cascade.tools.cli import create_cli
      - In `cli.py`:
        - Causes dependency on `sdk.py` via import of `...` (L34)
          34 | > from cascade.sdk import run as cascade_run
    ```
2.  **提交更改**: 如果输出符合预期，你可以要求我生成一个 `[COMMIT]` 计划。
