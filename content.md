好的，完全理解。在深入修复之前，确保诊断信息的可读性是首要任务。你指出的格式问题确实存在，我会立即修复它，让输出变得清晰美观。

## [WIP] style(analysis): 优化循环依赖报告的输出格式

### 错误分析

我上次为了增强可观测性而修改的报告生成逻辑，在格式上存在瑕疵。`Causes dependency on...` 这一行与下面的代码片段之间缺少一个换行符，导致输出内容挤在一起，可读性很差。

### 用户需求

调整 `CircularDependencyRule` 的输出格式，在依赖原因说明行和源代码片段之间插入一个换行符，以提高报告的清晰度和美观度。

### 评论

这是一个简单但有效的改进。高质量的诊断输出是开发者工具的核心价值之一。我们追求的不仅是信息的准确性，还有信息呈现的优雅性。

### 目标

修改 `CircularDependencyRule.check` 方法中的字符串格式化逻辑，确保在适当的位置添加换行符。

### 基本原理

我将直接修改 `details.append()` 的调用，在源代码片段 `snippet` 前面加上一个换行符，从而在视觉上将“原因”和“证据”分离开来。

### 标签

#intent/tune #flow/ready #priority/low #comp/analysis #concept/ui #scope/ux #ai/instruct #task/domain/testing #task/object/architecture-check #task/action/refactor #task-state/continue

---

### Script

#### Acts 1: 调整循环依赖报告的换行

我们将修改 `circular_dependency.py` 文件，为代码片段前增加一个换行符。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/rules/architecture/circular_dependency.py
~~~~~
~~~~~python.old
                details.append(f"\n  - In `{u}`:")
                details.append(f"    - Causes dependency on `{v}` via import of `{first_reason}`")
                if snippet:
                    details.append(snippet)
~~~~~
~~~~~python.new
                details.append(f"\n  - In `{u}`:")
                details.append(f"    - Causes dependency on `{v}` via import of `{first_reason}`")
                if snippet:
                    details.append(f"\n{snippet}")
~~~~~

### 下一步建议

执行此计划后，再次运行 `stitcher check`。输出格式应该会变得更加清晰易读，为我们下一步修复实际的循环依赖问题做好准备。如果你对格式满意，我们就可以开始着手解决 `stitcher-spec` 包内的架构问题。
