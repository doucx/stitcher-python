简要回答：
很好，测试正如预期地那样失败了。现在我们进入 **GREEN** 阶段，来收复这些失地。

我们需要处理三个主要任务：
1.  **Attribute 解析**: 实现 `visit_AnnAssign`（带注解的赋值）和 `visit_Assign`（普通赋值）的处理逻辑，提取模块级和类级变量。
2.  **Decorator 提取**: 从 `FunctionDef` 节点的 `decorators` 字段提取源码，并填充到我们的模型中。
3.  **Special Methods**: 在提取 Decorator 的同时，检查是否有 `staticmethod` 或 `classmethod`，并设置相应的布尔标志。

## [WIP] feat(scanner): 实现 Attribute 解析与高级函数元数据提取 (Green Phase)

### 用户需求
修复 3 个失败的测试用例：
1.  `test_parse_attributes`: 支持 `AnnAssign` (如 `x: int = 1`) 和 `Assign` (如 `x = 1`)。
2.  `test_parse_decorators`: 正确提取装饰器源码。
3.  `test_parse_special_methods`: 根据装饰器识别静态方法和类方法。

### 评论
**实现细节**：
*   **Assign**: `visit_Assign` 比较复杂，因为它可以是多重赋值（`a = b = 1`）。LibCST 的 `targets` 是一个列表。对于我们的场景，我们只关心简单的单目标赋值（`targets[0].target` 是 `Name`）。
*   **AnnAssign**: 结构更直接，`target` 就是变量名，`annotation` 是类型。
*   **Attributes 归属**: 同样依赖 `self._class_stack`。如果在堆栈中，归属给类；否则归属给模块。
*   **Decorator**: 使用 `dummy_module.code_for_node(dec.decorator)` 获取源码。注意，LibCST 的 `decorator` 字段包含了 `@` 之后的所有内容（可能是 `Name` 也可能是 `Call`）。

### 目标
1.  修改 `parser.py`。
2.  在 `visit_FunctionDef` 中增加 Decorator 处理逻辑。
3.  实现 `visit_AnnAssign`。
4.  实现 `visit_Assign`。
5.  在 `ModuleDef` 和 `ClassDef` 的构造逻辑中确保 `attributes` 列表被正确填充。

### 基本原理
通过扩展 Visitor 的能力，使其能够识别更多类型的语法节点，从而丰富我们的 IR 模型。

### 标签
#intent/build #flow/ready #priority/high
#comp/scanner #concept/parser #scope/core #ai/instruct
#task/domain/implementation #task/object/scanner-logic #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 更新 IRBuildingVisitor
这是对 `parser.py` 的第二次大修。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~python.old
    def __init__(self):
        # Module level containers
        self.functions: List[FunctionDef] = []
        self.classes: List[ClassDef] = []
        
        # Scope management: A stack of currently active ClassDefs being built.
        # If stack is empty, we are at module level.
        self._class_stack: List[ClassDef] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
~~~~~
~~~~~python.new
    def __init__(self):
        # Module level containers
        self.functions: List[FunctionDef] = []
        self.classes: List[ClassDef] = []
        self.attributes: List[Attribute] = []
        
        # Scope management: A stack of currently active ClassDefs being built.
        # If stack is empty, we are at module level.
        self._class_stack: List[ClassDef] = []
        self._dummy_module = cst.Module([]) # Helper for code generation

    def _add_attribute(self, attr: Attribute):
        if self._class_stack:
            self._class_stack[-1].attributes.append(attr)
        else:
            self.attributes.append(attr)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> Optional[bool]:
        # Handle: x: int = 1
        if not isinstance(node.target, cst.Name):
            return False
            
        name = node.target.value
        annotation = self._dummy_module.code_for_node(node.annotation.annotation).strip()
        
        value = None
        if node.value:
            value = self._dummy_module.code_for_node(node.value).strip()
            
        self._add_attribute(Attribute(name=name, annotation=annotation, value=value))
        return False

    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        # Handle: x = 1
        # Only handle simple assignment to a single name for now
        if len(node.targets) != 1:
            return False
            
        target = node.targets[0].target
        if not isinstance(target, cst.Name):
            return False
            
        name = target.value
        value = self._dummy_module.code_for_node(node.value).strip()
        
        self._add_attribute(Attribute(name=name, annotation=None, value=value))
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
~~~~~

#### Acts 2: 更新 visit_ClassDef 中的 Attribute 容器初始化
之前的代码中，Attribute 是手动初始化的，这没问题，但要注意 `visit_AnnAssign` 等会在 `visit_ClassDef` 返回 `True` 后被调用。

此部分无需更改，只要确认 `_class_stack` 机制工作正常即可。

#### Acts 3: 更新 visit_FunctionDef 处理 Decorators
~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~python.old
        # 3. Extract Return Annotation
        return_annotation = None
        if node.returns:
            return_annotation = cst.Module([]).code_for_node(node.returns.annotation).strip()

        # 4. Extract Arguments
        args = self._parse_parameters(node.params)

        # 5. Extract Async
        is_async = node.asynchronous is not None

        # 6. Build Object
        func_def = FunctionDef(
            name=func_name,
            args=args,
            return_annotation=return_annotation,
            docstring=docstring,
            is_async=is_async,
        )
~~~~~
~~~~~python.new
        # 3. Extract Return Annotation
        return_annotation = None
        if node.returns:
            return_annotation = self._dummy_module.code_for_node(node.returns.annotation).strip()

        # 4. Extract Arguments
        args = self._parse_parameters(node.params)

        # 5. Extract Async
        is_async = node.asynchronous is not None

        # 6. Extract Decorators and Special Flags
        decorators = []
        is_static = False
        is_class = False

        for dec in node.decorators:
            dec_code = self._dummy_module.code_for_node(dec.decorator).strip()
            decorators.append(dec_code)
            
            # Simple check for staticmethod/classmethod
            if dec_code == "staticmethod":
                is_static = True
            elif dec_code == "classmethod":
                is_class = True

        # 7. Build Object
        func_def = FunctionDef(
            name=func_name,
            args=args,
            return_annotation=return_annotation,
            docstring=docstring,
            is_async=is_async,
            decorators=decorators,
            is_static=is_static,
            is_class=is_class,
        )
~~~~~

#### Acts 4: 更新 parse_source_code 返回 attributes
~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~python.old
    return ModuleDef(
        file_path=file_path,
        docstring=cst_module.get_docstring() if isinstance(cst_module.get_docstring(), str) else None,
        functions=visitor.functions,
        classes=visitor.classes,
        # attributes to be added
    )
~~~~~
~~~~~python.new
    return ModuleDef(
        file_path=file_path,
        docstring=cst_module.get_docstring() if isinstance(cst_module.get_docstring(), str) else None,
        functions=visitor.functions,
        classes=visitor.classes,
        attributes=visitor.attributes,
    )
~~~~~

### 下一步建议
运行 `pytest`。如果所有测试通过，说明我们的 `Scanner` 已经具备了处理生产级代码的核心能力。

接下来，我们可以开始实现 `stitcher-io` 模块，即 **Generator** 部分。它是 IR 模型的消费者。我们可以沿用 TDD 模式：先写一个测试，断言 `StubGenerator.generate(module_def)` 能返回正确的 `.pyi` 字符串，然后再去实现它。
