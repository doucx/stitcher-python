Excellent. This is a critical step to ensure the new abstraction is robust and reliable. By writing focused unit tests for `SidecarUpdateMixin`, we can verify its behavior in isolation and prevent future regressions.

I will now generate the plan to create these unit tests.

## [WIP] test: 添加 SidecarUpdateMixin 的单元测试

### 错误分析

N/A. This is a request to add tests, not fix a bug.

### 用户需求

为 `SidecarUpdateMixin._update_sidecar_data` 方法编写专门的单元测试，覆盖各种边界情况，包括：
*   完全限定名 (FQN) 的精确匹配和级联匹配。
*   在提供模块上下文 (`module_fqn`) 的情况下的短名称匹配。
*   当符号移动到不同模块时，从短名称到 FQN 的转换。
*   不应被修改的无关数据。

### 评论

这是保证重构引擎核心逻辑健壮性的关键一步。`_update_sidecar_data` 方法是“代码-元数据”同步的枢纽，为其配备一套全面的单元测试，可以有效捕捉在各种复杂重命名和移动场景下的边界情况错误，从而极大地提升整个重构功能的可靠性。

### 目标

1.  在 `packages/stitcher-refactor/tests/unit/operations/` 目录下创建一个新的测试文件 `test_sidecar_update_mixin.py`。
2.  在该文件中，为 `SidecarUpdateMixin` 创建一个测试类。
3.  实现一系列单元测试，系统性地验证 `_update_sidecar_data` 方法在不同输入下的行为是否符合预期。

### 基本原理

我们将创建一个新的测试文件，以保持测试的组织性和清晰性。测试将直接实例化 `SidecarUpdateMixin`，因为它不依赖于任何复杂的对象状态。每个测试方法将聚焦于一个特定的场景：

*   **Arrange**: 准备 `initial_data` 字典、`old_fqn`、`new_fqn` 和 `module_fqn`。
*   **Act**: 调用 `_update_sidecar_data` 方法。
*   **Assert**: 验证返回的字典是否与 `expected_data` 完全一致。

这种方法可以精确地隔离和验证 Mixin 的转换逻辑，而无需模拟整个 `RefactorContext` 或文件系统。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/refactoring #task/object/sidecar-updater-mixin #task/action/testing #task/state/continue

---

### Script

#### Acts 1: 创建 SidecarUpdateMixin 的单元测试文件

我们将创建一个全新的测试文件，并填充它以全面覆盖 `_update_sidecar_data` 方法的各种逻辑分支。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py
~~~~~
~~~~~python
import pytest
from stitcher.refactor.operations.base import SidecarUpdateMixin


@pytest.fixture
def mixin():
    return SidecarUpdateMixin()


class TestSidecarUpdateMixin:
    def test_update_exact_fqn_key(self, mixin):
        data = {"mypkg.core.OldClass": "doc"}
        updated = mixin._update_sidecar_data(
            data, None, "mypkg.core.OldClass", "mypkg.core.NewClass"
        )
        assert updated == {"mypkg.core.NewClass": "doc"}

    def test_update_cascading_fqn_key(self, mixin):
        data = {"mypkg.core.OldClass.method": "doc"}
        updated = mixin._update_sidecar_data(
            data, None, "mypkg.core.OldClass", "mypkg.core.NewClass"
        )
        assert updated == {"mypkg.core.NewClass.method": "doc"}

    def test_update_short_name_key_with_module_context(self, mixin):
        data = {"OldClass": "doc", "OldClass.method": "doc"}
        updated = mixin._update_sidecar_data(
            data, "mypkg.core", "mypkg.core.OldClass", "mypkg.core.NewClass"
        )
        assert updated == {"NewClass": "doc", "NewClass.method": "doc"}

    def test_update_short_name_to_fqn_on_module_move(self, mixin):
        data = {"OldClass": "doc"}
        updated = mixin._update_sidecar_data(
            data, "mypkg.core", "mypkg.core.OldClass", "mypkg.utils.NewClass"
        )
        # Key must become FQN because it's no longer in the same module
        assert updated == {"mypkg.utils.NewClass": "doc"}

    def test_no_change_for_unrelated_keys(self, mixin):
        data = {"other.Class": "doc", "mypkg.core.AnotherClass": "doc"}
        original_data = data.copy()
        updated = mixin._update_sidecar_data(
            data, "mypkg.core", "mypkg.core.OldClass", "mypkg.core.NewClass"
        )
        assert updated == original_data

    def test_no_change_for_short_name_without_module_context(self, mixin):
        data = {"OldClass": "doc"}
        original_data = data.copy()
        updated = mixin._update_sidecar_data(
            data, None, "mypkg.core.OldClass", "mypkg.core.NewClass"
        )
        assert updated == original_data

    def test_update_module_rename(self, mixin):
        data = {
            "mypkg.old_mod.MyClass": "doc",
            "mypkg.old_mod.MyClass.method": "doc",
            "mypkg.other_mod.MyClass": "doc",  # Should not change
        }
        updated = mixin._update_sidecar_data(
            data, "mypkg.old_mod", "mypkg.old_mod", "mypkg.new_mod"
        )
        assert updated == {
            "mypkg.new_mod.MyClass": "doc",
            "mypkg.new_mod.MyClass.method": "doc",
            "mypkg.other_mod.MyClass": "doc",
        }

    def test_update_short_name_when_module_is_renamed(self, mixin):
        data = {"MyClass": "doc", "MyClass.method": "doc"}
        updated = mixin._update_sidecar_data(
            data, "mypkg.old_mod", "mypkg.old_mod", "mypkg.new_mod"
        )
        # When renaming the module itself, short names remain short names
        assert updated == {"MyClass": "doc", "MyClass.method": "doc"}
~~~~~

### 下一步建议

我们已经为 `SidecarUpdateMixin` 添加了健壮的单元测试。现在，整个重构逻辑都得到了更好的测试覆盖。

下一步是运行整个 `stitcher-refactor` 的测试套件，确保所有测试（包括我们刚刚添加的和之前修复的）都能通过。如果一切顺利，这个任务就可以被认为是完成了，我们可以准备一个 `[COMMIT]` 计划来提交这些改进。
