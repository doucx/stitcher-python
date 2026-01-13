好的。测试失败是因为我修改了 `_update_sidecar_data` 方法的签名，但没有同步更新调用该方法的单元测试。这是一个典型的重构疏漏。

根据 `TypeError` 的明确提示，我需要将测试代码中所有对 `_update_sidecar_data` 的调用，把 `module_fqn` 参数重命名为 `old_module_fqn`，并根据测试场景补充 `new_module_fqn` 参数。

我将生成一个新计划来修复这些单元测试。

## [WIP] test(refactor): Update unit tests to match new sidecar update signature

### 错误分析

在上一个计划中，我重构了 `SidecarUpdateMixin._update_sidecar_data` 方法的签名，将 `module_fqn` 参数拆分为 `old_module_fqn` 和 `new_module_fqn`，以建立一个确定性的上下文传递契约。

然而，我遗漏了更新位于 `packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py` 中调用此方法的单元测试。因此，所有这些测试都因为 `TypeError: ... got an unexpected keyword argument 'module_fqn'` 而失败。

### 用户需求

修复 `test_sidecar_update_mixin.py` 中的所有单元测试，使其调用 `_update_sidecar_data` 时使用新的、正确的参数签名。

### 评论

这是一个标准的重构后清理工作。修复这些测试不仅是为了让测试套件通过，更是为了确保我们对新接口的假设（即 `Planner` 将如何提供上下文）在隔离环境中是正确和有效的。

### 目标

1.  打开 `packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py` 文件。
2.  在所有测试函数中，定位对 `mixin._update_sidecar_data` 的调用。
3.  将 `module_fqn=...` 参数重命名为 `old_module_fqn=...`。
4.  根据每个测试的逻辑场景，添加 `new_module_fqn=...` 参数。
    -   对于纯**重命名**场景，`new_module_fqn` 应与 `old_module_fqn` 相同。
    -   对于**文件移动**场景，`new_module_fqn` 应反映新的模块路径。

### 基本原理

通过逐一修正测试用例的函数调用，使其与重构后的方法签名完全匹配，我们可以消除 `TypeError` 并验证新架构的逻辑正确性。这将为我们验证整个重构流程（从 `Planner` 到 `Mixin`）的集成行为铺平道路。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #concept/refactoring-engine #scope/dx #ai/instruct #task/domain/refactoring #task/object/sidecar-updates #task/action/architectural-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `test_sidecar_update_mixin.py` 的单元测试

我们将一次性更新整个测试文件，以匹配新的方法签名。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py
~~~~~
~~~~~python.old
class TestJsonSuriUpdates:
    def test_updates_suri_on_symbol_rename(self, mixin):
        old_suri = "py://src/app.py#OldClass"
        new_suri = "py://src/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_nested_symbol_rename(self, mixin):
        old_suri = "py://src/app.py#MyClass.old_method"
        new_suri = "py://src/app.py#MyClass.new_method"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_parent_rename(self, mixin):
        old_suri = "py://src/app.py#OldClass.method"
        new_suri = "py://src/app.py#NewClass.method"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_file_move(self, mixin):
        old_suri = "py://src/old_path/app.py#MyClass"
        new_suri = "py://src/new_path/app.py#MyClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/old_path/app.json"),
            module_fqn="old_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_combined_move_and_rename(self, mixin):
        old_suri = "py://src/old_path/app.py#OldClass"
        new_suri = "py://src/new_path/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/old_path/app.json"),
            module_fqn="old_path.app",
            old_fqn="old_path.app.OldClass",
            new_fqn="new_path.app.NewClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        assert updated == {new_suri: {"hash": "1"}}


class TestYamlFragmentUpdates:
    def test_updates_fragment_on_symbol_rename(self, mixin):
        data = {"OldClass": "doc", "Other": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {"NewClass": "doc", "Other": "doc"}

    def test_updates_fragment_on_nested_symbol_rename(self, mixin):
        data = {"MyClass.old_method": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        assert updated == {"MyClass.new_method": "doc"}

    def test_updates_fragment_on_parent_rename(self, mixin):
        data = {"OldClass.method": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {"NewClass.method": "doc"}

    def test_does_not_update_fragment_on_pure_file_move(self, mixin):
        data = {"MyClass": "doc"}
        original_data = data.copy()
        updated = mixin._update_sidecar_data(
            data,
            Path("old_path/app.stitcher.yaml"),
            module_fqn="old_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass", # Symbol name 'MyClass' is unchanged
            old_file_path="old_path/app.py",
            new_file_path="new_path/app.py",
        )
        # The key is relative to the file, so a move should NOT change it.
        assert updated == original_data
~~~~~
~~~~~python.new
class TestJsonSuriUpdates:
    def test_updates_suri_on_symbol_rename(self, mixin):
        old_suri = "py://src/app.py#OldClass"
        new_suri = "py://src/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_nested_symbol_rename(self, mixin):
        old_suri = "py://src/app.py#MyClass.old_method"
        new_suri = "py://src/app.py#MyClass.new_method"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_parent_rename(self, mixin):
        old_suri = "py://src/app.py#OldClass.method"
        new_suri = "py://src/app.py#NewClass.method"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_file_move(self, mixin):
        old_suri = "py://src/old_path/app.py#MyClass"
        new_suri = "py://src/new_path/app.py#MyClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/old_path/app.json"),
            old_module_fqn="old_path.app",
            new_module_fqn="new_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_combined_move_and_rename(self, mixin):
        old_suri = "py://src/old_path/app.py#OldClass"
        new_suri = "py://src/new_path/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/old_path/app.json"),
            old_module_fqn="old_path.app",
            new_module_fqn="new_path.app",
            old_fqn="old_path.app.OldClass",
            new_fqn="new_path.app.NewClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        assert updated == {new_suri: {"hash": "1"}}


class TestYamlFragmentUpdates:
    def test_updates_fragment_on_symbol_rename(self, mixin):
        data = {"OldClass": "doc", "Other": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {"NewClass": "doc", "Other": "doc"}

    def test_updates_fragment_on_nested_symbol_rename(self, mixin):
        data = {"MyClass.old_method": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        assert updated == {"MyClass.new_method": "doc"}

    def test_updates_fragment_on_parent_rename(self, mixin):
        data = {"OldClass.method": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            old_module_fqn="app",
            new_module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {"NewClass.method": "doc"}

    def test_does_not_update_fragment_on_pure_file_move(self, mixin):
        data = {"MyClass": "doc"}
        original_data = data.copy()
        updated = mixin._update_sidecar_data(
            data,
            Path("old_path/app.stitcher.yaml"),
            old_module_fqn="old_path.app",
            new_module_fqn="new_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass", # Symbol name 'MyClass' is unchanged
            old_file_path="old_path/app.py",
            new_file_path="new_path/app.py",
        )
        # The key is relative to the file, so a move should NOT change it.
        assert updated == original_data
~~~~~

### 下一步建议

单元测试已修复，现在它们正确地反映了新的、确定性的接口。

下一步是重新运行完整的测试套件。如果我们的架构修正和测试修复都正确无误，那么之前失败的所有测试（包括单元测试和集成测试 `test_rename_suri_update.py`）现在都应该通过了。
