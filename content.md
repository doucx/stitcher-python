非常抱歉，我在使用 LibCST API 时出现了记忆偏差。在 `libcst` 中，`Tuple` 和 `List` 的子元素统一使用 `cst.Element` 类型，而没有 `TupleElement` 这种特定类型。

我已经根据 `libcst` 的实际定义修正了 `visitors.py` 的解析逻辑。

## [WIP] fix(lang-python): 修正 IR 解析器中的 LibCST 类型引用错误

### 错误分析
测试失败原因是 `AttributeError: module 'libcst' has no attribute 'TupleElement'`。在 LibCST 的抽象语法树中，`Tuple`、`List` 和 `Set` 容器内的包装对象统称为 `Element`。

### 目标
1.  将 `IRBuildingVisitor.visit_Assign` 内部的递归处理逻辑修正为使用 `cst.Element`。
2.  增加对 `cst.StarredElement` 的支持，以便处理 `x, *y = 1, 2, 3` 这种包含星号解包的赋值。

### 标签
#intent/fix #flow/ready #priority/high #comp/lang-python #concept/parser #scope/core #ai/refine #task/domain/analysis #task/object/ir-parser #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修正 `visitors.py` 中的解析逻辑

我们将 `TupleElement` 和 `ListElement` 替换为正确的 `cst.Element`，并增加对 `StarredElement` 的支持。

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/visitors.py
~~~~~
~~~~~python.old
    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        # Handle: x = 1 or x, y = 1, 2
        if len(node.targets) != 1:
            return False

        target_node = node.targets[0].target
        value_code = self._dummy_module.code_for_node(node.value).strip()
        loc = self._extract_location(node)

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
                    if isinstance(element, (cst.TupleElement, cst.ListElement)):
                        process_target(element.value)

        process_target(target_node)
        return False
~~~~~
~~~~~python.new
    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        # Handle: x = 1 or x, y = 1, 2 or [a, *b] = ...
        if len(node.targets) != 1:
            return False

        target_node = node.targets[0].target
        value_code = self._dummy_module.code_for_node(node.value).strip()
        loc = self._extract_location(node)

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
        return False
~~~~~

### 下一步建议

1.  **重新运行测试**: 再次执行 `pytest packages/stitcher-lang-python/tests/analysis/unit/cst/test_visitors.py`，确认 `test_parse_unpacking_assignment` 现在能够通过。
2.  **增加星号解包测试**: 如果上面的测试通过，建议在 `test_visitors.py` 中增加一个 `x, *y = 1, 2, 3` 的用例，以验证 `StarredElement` 的支持情况。
