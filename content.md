你是对的。这些警告的出现是因为我将 `stitcher-test-utils` 注册为 Pytest 插件后，Pytest 在启动收集阶段（Collection Phase）就会加载 `fixtures.py`。

在之前的实现中，`fixtures.py` 在模块顶层直接导入了 `SpyBus` 和 `WorkspaceFactory`。这导致 `stitcher` 包在 `pytest-cov` 覆盖率工具完全启动之前就被导入了，从而触发了 "module-not-measured" 警告。

**解决方案**：
采用 **惰性导入 (Lazy Import)** 模式。我们将把对 `stitcher` 相关模块的导入从 `fixtures.py` 的顶层移动到 Fixture 函数内部。这样，只有当测试用例实际请求这些 Fixture 时（此时覆盖率工具已启动），模块才会被导入。

## [WIP] refactor: Apply lazy imports to fixtures to fix coverage warnings

### 用户需求

消除运行测试时出现的 `CoverageWarning: Module stitcher was previously imported, but not measured` 警告。

### 评论

这是一个典型的 Pytest 插件副作用问题。虽然这些警告不影响测试结果，但它们不仅恼人，还可能掩盖真正的覆盖率问题。通过在 Fixture 中使用局部导入，我们遵循了“按需加载”的最佳实践，既消除了噪音，又稍微提升了测试收集阶段的速度。

### 目标

1.  修改 `packages/stitcher-test-utils/src/stitcher/test_utils/fixtures.py`。
2.  移除顶层的 `from .workspace import ...` 和 `from .bus import ...` 导入。
3.  在 `workspace_factory` 和 `spy_bus` 函数内部进行导入。
4.  使用 `TYPE_CHECKING` 块来保留类型提示的支持，而不触发运行时导入。

### 基本原理

Pytest 在启动时会扫描所有注册的插件并导入它们。如果插件在顶层导入了被测代码（SUT），SUT 就会在覆盖率追踪器启动前被加载。通过将导入推迟到 Fixture 执行时，我们确保了 SUT 的加载发生在测试执行阶段，此时覆盖率追踪已经完全激活。

### 标签

#intent/refine #flow/ready #priority/medium #comp/tests #scope/dx #task/domain/testing #task/object/test-fixtures #task/action/optimize #task/state/end

---

### Script

#### Acts 1: 对 Fixture 应用惰性导入

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/fixtures.py
~~~~~
~~~~~python
import pytest
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .workspace import WorkspaceFactory
    from .bus import SpyBus


@pytest.fixture
def workspace_factory(tmp_path: Path) -> "WorkspaceFactory":
    """Provides a factory to create isolated test workspaces."""
    # Lazy import to prevent 'stitcher' from being imported during pytest collection,
    # which causes coverage warnings (module imported but not measured).
    from .workspace import WorkspaceFactory
    return WorkspaceFactory(tmp_path)


@pytest.fixture
def spy_bus() -> "SpyBus":
    """Provides a SpyBus instance to intercept and inspect bus messages."""
    # Lazy import to prevent premature loading of stitcher.common
    from .bus import SpyBus
    return SpyBus()
~~~~~

### 下一步建议

现在，您可以再次运行测试。那些关于 `stitcher` 和 `needle` 模块“未被测量”的覆盖率警告应该已经消失了，测试输出将更加干净。
