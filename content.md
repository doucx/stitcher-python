这个修复是稳定核心功能所必需的。我将按照请求创建一个 `[COMMIT]` 计划。

## [COMMIT] fix(scanner): Handle bare star (*) in function signatures

### 用户需求
确认修复已完成并通过测试，要求创建 Git 提交。

### 评论
这个修复解决了 Python 语法解析器中一个关键的健壮性问题，确保 `Stitcher` 能够处理所有标准函数签名，包括使用裸星号 (`*`) 作为关键字参数分隔符的情况。这对于项目的长期稳定性至关重要。

### 目标
1.  将 `packages/stitcher-scanner/src/stitcher/scanner/parser.py` 文件添加到 Git 暂存区。
2.  创建描述性提交，记录对 `libcst.ParamStar` 节点的裸星号处理逻辑的修复。

### 基本原理
根据 `d3-constraint-quipu-plan-script-rules` 约束，文件修改和 Git 提交必须隔离在不同的计划中。此计划专门用于将上一步骤中已执行和验证的变更进行版本控制。

### 标签
#intent/fix #flow/ready #priority/critical #comp/scanner #concept/parser #scope/core #ai/instruct #task/domain/parsing #task/object/signature-parser #task/action/bug-fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

将修复后的解析器文件添加到暂存区，并执行提交。

~~~~~act
git_add
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(scanner): Handle bare star (*) in function signatures

Fixes a crash in the IR parser when encountering a bare positional-only separator '*' in function signatures (e.g., `def func(a, *, b)`).

The libcst `ParamStar` node does not expose a `name` attribute in this case, leading to an `AttributeError`. The fix adds a robust `hasattr(param, "name")` check before accessing the property.
~~~~~

### 下一步建议
我们现在应该再次运行 `stitcher check`，以确认解析器在新的裸星号语法下不再崩溃，并且能正常进行文档一致性检查。

我建议运行：
```bash
stitcher check
```
