好的，测试失败了，这正是 TDD 所期望的。现在我们进入 **GREEN** 阶段，目标是让这个测试通过。

我们将修改 `IRBuildingVisitor` 来识别和解析 `ClassDef` 节点。关键在于处理嵌套：当 Visitor 进入一个类时，我们需要为该类的内部创建一个新的、隔离的解析上下文，以收集其方法，而不是将它们错误地归入模块的顶层函数列表。

## [WIP] feat(scanner): 实现 ClassDef 解析逻辑 (Green Phase)

### 用户需求
在 `stitcher-scanner` 的 `IRBuildingVisitor` 中实现对 `cst.ClassDef` 节点的解析，使其能够正确提取类名、基类、文档字符串以及嵌套的方法定义。

### 评论
我们采用了一种递归的 Visitor 策略来处理嵌套。在 `visit_ClassDef` 方法中，我们会创建一个新的 `IRBuildingVisitor` 实例，并让它只访问当前类的主体部分 (`node.body`)。这种方法清晰地隔离了不同作用域的解析，使其易于扩展，未来可以同样的方式处理嵌套类或嵌套函数。

### 目标
1.  在 `IRBuildingVisitor` 的 `__init__` 中添加 `self.classes` 列表。
2.  实现 `visit_ClassDef` 方法，正确构建 `ClassDef` IR 对象。
3.  在 `visit_ClassDef` 内部，递归使用 `IRBuildingVisitor` 来解析类的方法。
4.  更新 `parse_source_code` 函数，将解析出的类附加到最终的 `ModuleDef` 对象上。
5.  运行测试，确保所有测试都通过。

### 基本原理
当 LibCST 的 `CSTVisitor` 遍历语法树时，它会为每个节点类型调用对应的 `visit_<NodeType>` 方法。我们将通过实现 `visit_ClassDef` 来捕获类的定义。`node.bases` 属性提供了基类列表，`node.body` 提供了类内部的代码块，我们可以对这个代码块再次调用 Visitor 来解析其内容。

### 标签
#intent/build #flow/ready #priority/high
#comp/scanner #concept/parser #scope/core #ai/instruct
#task/domain/implementation #task/object/scanner-logic #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 初始化 Visitor 状态
首先，我们需要在 Visitor 中添加一个位置来存储找到的类。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~python.old
class IRBuildingVisitor(cst.CSTVisitor):
    def __init__(self):
        self.functions: List[FunctionDef] = []
        # Future: attributes, classes, etc.
~~~~~
~~~~~python.new
class IRBuildingVisitor(cst.CSTVisitor):
    def __init__(self):
        self.functions: List[FunctionDef] = []
        self.classes: List[ClassDef] = []
        # Future: attributes, etc.
~~~~~

#### Acts 2: 实现 ClassDef 解析
这是核心逻辑。我们在 `FunctionDef` 访问器之后添加 `ClassDef` 访问器。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~python.old
        # Don't visit children for now (to avoid collecting nested functions into the top level)
        # In a real implementation, we need a stack to handle nesting.
        return False

    def _parse_parameters(self, params: cst.Parameters) -> List[Argument]:
~~~~~
~~~~~python.new
        # Don't visit children for now (to avoid collecting nested functions into the top level)
        # In a real implementation, we need a stack to handle nesting.
        return False

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        # 1. Extract Name
        class_name = node.name.value

        # 2. Extract Docstring
        docstring = node.get_docstring()
        if isinstance(docstring, bool):
            docstring = None

        # 3. Extract Bases
        bases = []
        dummy_module = cst.Module([])
        for base in node.bases:
            bases.append(dummy_module.code_for_node(base.value))

        # 4. Recursively visit the class body to find methods/attributes
        body_visitor = IRBuildingVisitor()
        # The class body is a cst.IndentedBlock, which has a 'body' attribute (tuple of statements)
        # We wrap it in a dummy module to visit it.
        class_body_node = cst.Module(body=node.body.body)
        class_body_node.visit(body_visitor)

        # 5. Build the ClassDef object
        class_def = ClassDef(
            name=class_name,
            bases=bases,
            docstring=docstring,
            methods=body_visitor.functions,
            attributes=body_visitor.attributes,
        )
        self.classes.append(class_def)

        # We have handled the children, so prevent the main visitor from descending further
        return False

    def _parse_parameters(self, params: cst.Parameters) -> List[Argument]:
~~~~~

#### Acts 3: 更新 ModuleDef 构造
最后，确保 `parse_source_code` 函数将收集到的类包含在其返回的 `ModuleDef` 中。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~python.old
    return ModuleDef(
        file_path=file_path,
        docstring=cst_module.get_docstring() if isinstance(cst_module.get_docstring(), str) else None,
        functions=visitor.functions,
        # classes and attributes to be added
    )
~~~~~
~~~~~python.new
    return ModuleDef(
        file_path=file_path,
        docstring=cst_module.get_docstring() if isinstance(cst_module.get_docstring(), str) else None,
        functions=visitor.functions,
        classes=visitor.classes,
        # attributes to be added
    )
~~~~~

### 下一步建议
运行 `pytest`。如果一切顺利，两个测试都应该通过。

通过后，我们可以继续 TDD 循环，为下一个目标编写失败的测试，例如：
*   解析模块级和类级的变量（`Attribute`）。
*   解析函数的装饰器。
*   处理更复杂的参数类型，如 `*args` 和 `**kwargs`。
