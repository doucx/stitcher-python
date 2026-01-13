分析显示，测试失败的原因在于我对 LibCST 中 `Tuple` 和 `List` 容器成员的识别逻辑不完整。

在 LibCST 中，`Tuple.elements` 列表包含的对象可能是 `cst.Element`（普通项），也可能是 `cst.StarredElement`（带星号的项）。

在我之前的实现中：
```python
            elif isinstance(target, (cst.Tuple, cst.List)):
                for element in target.elements:
                    if isinstance(element, cst.Element): # ⚠️ 这里的判断跳过了 StarredElement
                        process_target(element.value)
```
由于 `cst.Element` 和 `cst.StarredElement` 在 LibCST 中是平级的（都继承自 `BaseElement`），`isinstance(element, cst.Element)` 对于星号项会返回 `False`，导致星号后面的符号（如 `y`）被漏掉。

## [WIP] fix(lang-python): 修正解析器以支持赋值中的星号解包

### 目标
1.  修正 `IRBuildingVisitor.visit_Assign` 中的迭代逻辑，确保同时解包 `Element` 和 `StarredElement`。
2.  通过测试验证 `x, *y = ...` 能正确识别出 `x` 和 `y`。

### 基本原理
由于 `Tuple` 和 `List` 的所有成员（无论是普通项还是星号项）在 LibCST 中都具有 `.value` 属性，我们可以直接递归调用 `process_target(element.value)`，而无需进行复杂的子类型判断。

### 标签
#intent/fix #flow/ready #priority/high #comp/lang-python #concept/parser #scope/core #ai/refine #task/domain/analysis #task/object/ir-parser #task/action/fix #task/state/end

---

### Script

#### Acts 1: 修正 `visitors.py` 中的解包迭代逻辑

我们将修正循环逻辑，使其能够处理容器中的所有元素。

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/visitors.py
~~~~~
~~~~~python.old
        def process_target(target: cst.CSTNode):
            if isinstance(target, cst.Name):
                name = target.value
                # Special handling for __all__
                if name == "__all__" and not self._class_stack:
                    self.dunder_all = value_code
                else:
                    self._add_attribute(
                        Attribute(name=name, annotation=None, value=value_code, location=loc)
                    )
            elif isinstance(target, (cst.Tuple, cst.List)):
                for element in target.elements:
                    if isinstance(element, cst.Element):
                        process_target(element.value)
            elif isinstance(target, cst.StarredElement):
                # Handle *y in [x, *y] = ...
                process_target(target.value)

        process_target(target_node)
~~~~~
~~~~~python.new
        def process_target(target: cst.CSTNode):
            if isinstance(target, cst.Name):
                name = target.value
                # Special handling for __all__
                if name == "__all__" and not self._class_stack:
                    self.dunder_all = value_code
                else:
                    self._add_attribute(
                        Attribute(name=name, annotation=None, value=value_code, location=loc)
                    )
            elif isinstance(target, (cst.Tuple, cst.List)):
                for element in target.elements:
                    # In LibCST, elements of Tuple/List are wrappers (Element or StarredElement).
                    # Both have a .value attribute containing the actual expression.
                    process_target(element.value)
            elif isinstance(target, cst.StarredElement):
                # This handles cases where StarredElement might be passed directly 
                # (though usually it's handled by the parent container's loop).
                process_target(target.value)

        process_target(target_node)
~~~~~

### 下一步建议

1.  **最终测试验证**: 再次执行 `pytest packages/stitcher-lang-python/tests/analysis/unit/cst/test_visitors.py`。现在所有 7 个测试（包括 `test_parse_starred_unpacking`）都应该通过。
2.  **完成任务序列**: 由于本阶段（强化解析器能力）的目标已达成，且代码处于稳定状态，建议进行一次 Git Commit。
3.  **后续扩展**: 考虑增加对 `Attribute` 赋值的支持（例如 `self.x = 1`），这需要 `UsageScanVisitor` 与 `IRBuildingVisitor` 的进一步协同。
