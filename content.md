测试已全部通过。现在我们将这些增强功能作为一个逻辑单元进行提交，标志着 IR 解析器对复杂 Python 赋值语法的支持达到了预期的 MVP 水准。

## [COMMIT] feat(lang-python): 增强 IR 解析器以支持解包赋值和星号解包

### 用户需求
1.  支持解包赋值（如 `x, y = 1, 2`）。
2.  支持带星号的解包赋值（如 `x, *y = [1, 2, 3]`）。
3.  确保嵌套类定义不会导致解析器状态混乱或符号泄露。

### 评论
这是对 `stitcher-lang-python` 静态分析能力的重大补全。通过支持递归解析赋值目标，我们能够更准确地捕捉库的公共 API 表面，减少因代码风格差异导致的索引遗漏。

### 目标
1.  将 `visitors.py` 和对应的单元测试 `test_visitors.py` 提交至仓库。
2.  确保 `[COMMIT]` 节点在历史图中清晰地标记了这一功能点的完成。

### 基本原理
我们遵循“先建立测试，再修复实现”的 TDD 流程。最终实现利用了 LibCST `Tuple`/`List` 元素包装器的通用性，通过递归处理 `.value` 属性，以最简洁的代码覆盖了所有解包场景。

### 标签
#intent/build #flow/ready #priority/high #comp/lang-python #concept/parser #scope/core #ai/refine #task/domain/analysis #task/object/ir-parser #task/action/enhancement #task/state/end

---

### Script

#### Acts 1: 提交代码与测试

我们将相关变更添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/visitors.py
packages/stitcher-lang-python/tests/analysis/unit/cst/test_visitors.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(lang-python): enhance IR parser to support unpacking and starred assignments

This commit enhances the `IRBuildingVisitor` to recursively resolve assignment targets.
Previously, only simple name assignments (e.g., `x = 1`) were captured. Now, the parser
correctly identifies symbols in unpacking and starred assignments:

- Supports tuple/list unpacking: `x, y = 1, 2`
- Supports starred unpacking: `head, *tail = items`
- Robustly handles nested classes by preventing symbol leakage to top-level IR

Added unit tests in `test_visitors.py` to verify these capabilities.
~~~~~

### 下一步建议

- **方法内属性捕捉**: 目前 `IRBuildingVisitor` 仅解析模块和类层级的赋值。下一步可以研究如何通过 `UsageScanVisitor` 识别 `self.attr = value` 并将其作为类属性（Class Attribute）加入 IR。
- **性能评估**: 随着递归解析逻辑的加入，可以针对包含极大规模常量列表（解包赋值）的文件进行性能测试。
