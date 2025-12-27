啊，这个问题非常刁钻，而且你的分析完全正确。

测试用例通过了，但现实世界的 `check` 失败了。这是一个典型的**测试覆盖不足**的案例。我们的测试用例验证了一个*真正为空*的文件，但没有验证一个*充满了我们认为是“样板代码”*的 `__init__.py` 文件。

正如你提供的文件内容所示，这些 `__init__.py` 文件并不为空。它们包含 `__path__ = ...` 和 `__all__ = [...]` 这样的赋值语句。

我们当前的 `is_documentable` 方法实现如下：
```python
def is_documentable(self) -> bool:
    return bool(
        self.docstring
        or self.attributes  # <--- 问题在这里
        or self.functions
        or self.classes
        or self.dunder_all # <--- 还有这里
    )
```
我们的解析器会把 `__path__ = ...` 解析为一个 `Attribute` 对象，并把 `__all__ = [...]` 赋值给 `dunder_all` 属性。因此，`self.attributes` 和 `self.dunder_all` 都不为空，导致 `is_documentable()` 返回 `True`，从而触发了 `UNTRACKED` 警告。

**结论**：我们的“可文档化”定义过于宽泛。像 `__path__` 和 `__all__` 这样的元数据赋值，用户几乎永远不会想为它们创建 `.stitcher.yaml` 文件。我们必须将这些样板代码从“可文档化内容”的定义中排除。

我将生成一个计划来精确地解决这个问题。

## [WIP] refactor(check): Exclude boilerplate from documentable check

### 用户需求
用户发现，即使在实现了对空模块的静默处理后，包含 `__path__` 或 `__all__` 等样板代码的 `__init__.py` 文件仍然会触发 `UNTRACKED` 警告。这是因为 `is_documentable` 方法错误地将这些样板代码识别为需要文档的内容。

### 评论
这是一个非常重要的精炼。通过让工具识别并忽略 Python 的标准元数据和样板代码，我们极大地减少了噪音，使用户能够专注于真正需要编写文档的 API。这标志着工具从“语法感知”向“语义感知”的又一次进化。

### 目标
1.  修改 `ModuleDef.is_documentable` 方法的实现。
2.  新的实现将**忽略**所有以下划线开头的属性（如 `_internal`, `__path__`）和 `dunder_all` 赋值。
3.  只有当模块包含模块级文档字符串、公共属性、函数或类时，才应被视为“可文档化”。
4.  更新集成测试，增加一个专门针对包含 `__all__` 和 `__path__` 的 `__init__.py` 文件的测试用例，并断言它被静默忽略。

### 基本原理
我们将收紧 `is_documentable` 的判定标准。原先简单的 `bool(self.attributes)` 检查将被替换为一个更智能的迭代表达式 `any(not attr.name.startswith("_") for attr in self.attributes)`，它能明确地将私有和“dunder”属性排除在外。同时，我们将从布尔检查中移除 `self.dunder_all`。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #comp/spec #scope/ux #task/domain/documentation #task/object/check-logic #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 精炼 `is_documentable` 方法

在 `stitcher-spec` 包中，我们更新 `is_documentable` 的逻辑。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
    def is_documentable(self) -> bool:
        """
        Checks if the module contains any content that would warrant a doc file.
        """
        # A module is documentable if it has a docstring, any public-facing
        # definitions, or any attributes. __all__ also implies it's a public API surface.
        return bool(
            self.docstring
            or self.attributes
            or self.functions
            or self.classes
            or self.dunder_all
        )
~~~~~
~~~~~python.new
    def is_documentable(self) -> bool:
        """
        Checks if the module contains any content that would warrant a doc file.
        """
        # A module is documentable if it has a docstring, public attributes,
        # functions, or classes. Boilerplate like __all__ or __path__ should be ignored.
        has_public_attributes = any(
            not attr.name.startswith("_") for attr in self.attributes
        )

        return bool(
            self.docstring or has_public_attributes or self.functions or self.classes
        )
~~~~~

#### Acts 2: 增强集成测试以覆盖样板代码场景

现在，我们的测试将不仅覆盖空文件，还将覆盖包含样板代码的文件，确保它们都被正确处理。

~~~~~act
patch_file
tests/integration/test_check_file_tracking.py
~~~~~
~~~~~python.old
def test_check_is_silent_for_empty_untracked_file(tmp_path, monkeypatch):
    """
    Verifies that 'check' does NOT report UNTRACKED for an untracked file
    that contains no documentable content (e.g., an empty __init__.py).
    """
    # 1. Arrange: An empty source file with no doc file
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/__init__.py", "# This file is intentionally empty")
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    # Crucially, assert that the overall success message (without warnings) was called
    spy_bus.assert_id_called(L.check.run.success, level="success")

    # And verify NO untracked message was sent
    messages = spy_bus.get_messages()
    assert not any(msg["id"] == str(L.check.file.untracked) for msg in messages)
~~~~~
~~~~~python.new
def test_check_is_silent_for_empty_untracked_file(tmp_path, monkeypatch):
    """
    Verifies that 'check' does NOT report UNTRACKED for an untracked file
    that contains no documentable content (e.g., an empty __init__.py).
    """
    # 1. Arrange: An empty source file with no doc file
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/__init__.py", "# This file is intentionally empty")
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.run.success, level="success")
    messages = spy_bus.get_messages()
    assert not any(msg["id"] == str(L.check.file.untracked) for msg in messages)


def test_check_is_silent_for_boilerplate_untracked_file(tmp_path, monkeypatch):
    """
    Verifies that 'check' also ignores untracked files that only contain
    boilerplate like __all__ or __path__.
    """
    # 1. Arrange: A source file with only boilerplate, and no doc file
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/namespace/__init__.py",
            """
            __path__ = __import__("pkgutil").extend_path(__path__, __name__)
            __all__ = ["some_module"]
            """,
        )
        .build()
    )

    app = StitcherApp(root_path=project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.app.core.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.run.success, level="success")
    messages = spy_bus.get_messages()
    assert not any(msg["id"] == str(L.check.file.untracked) for msg in messages)
~~~~~
