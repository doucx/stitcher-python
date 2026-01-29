这是一个典型的“命名空间重叠”导致的错误。

在之前的 `sed` 替换中，我们将 `stitcher.bus.bus` 替换为了 `stitcher.common.bus.bus`。
但在 `stitcher-common` 的设计中：
1.  `packages/stitcher-common/src/stitcher/common/__init__.py` 已经通过 `from .bus import bus` 导出了实例。
2.  因此，当你 `import stitcher.common` 后，`stitcher.common.bus` **已经是那个 `FeedbackBus` 实例本身了**，而不是 `bus.py` 这个模块。
3.  所以访问 `stitcher.common.bus.bus` 就会报错，因为 `FeedbackBus` 对象下面没有一个叫 `bus` 的属性。

我们需要将 `stitcher-test-utils` 中的引用修正为单级访问。

## [FIX] refactor(tests): 修正 SpyBus 中的总线引用路径

### 错误分析
测试工具 `SpyBus` 在重构后尝试访问 `stitcher.common.bus.bus`，但由于 `stitcher.common` 已经扁平化导出了 `bus` 实例，导致了 `AttributeError`。

### 用户需求
修正 `stitcher-test-utils` 中对总线单例的引用，确保 `patch` 逻辑能够正确找到目标。

### 评论
在 `pyneedle-bus` 的架构下，我们倾向于通过 `common` 入口统一访问。这次修正不仅解决了 Bug，也统一了测试环境与生产环境的调用方式。

### 目标
1.  修改 `packages/stitcher-test-utils/src/stitcher/test_utils/bus.py`。
2.  将 `stitcher.common.bus.bus` 修正为 `stitcher.common.bus`。
3.  同步更新 `patch` 方法的默认 `target` 参数。

### 基本原理
直接引用 `stitcher.common.bus` 获取全局 `FeedbackBus` 实例。由于 `monkeypatch` 的 `target` 字符串需要能够被 `pytest` 解析，我们必须确保路径指向的是最终的属性（实例），而不是模块路径。

### 标签
#intent/fix #flow/ready #priority/high 
#comp/tests #scope/core
#ai/instruct
#task/domain/bus #task/object/spy-bus #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正 `SpyBus` 引用逻辑

我们将去掉多余的一层 `.bus`。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()

    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus.bus"):
        real_bus = stitcher.common.bus.bus

        def intercept_present(
            ptr: Union[str, SemanticPointer], level: str = "info", **kwargs: Any
        ) -> None:
~~~~~
~~~~~python.new
class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()

    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus"):
        real_bus = stitcher.common.bus

        def intercept_present(
            ptr: Union[str, SemanticPointer], level: str = "info", **kwargs: Any
        ) -> None:
~~~~~

### 下一步建议
修正后，请再次运行测试。如果仍然出现类似的 `AttributeError`，请检查 `Acts 2` 的 `sed` 结果是否在其他业务代码中也生成了 `stitcher.common.bus.bus`。

如果测试通过，说明**阶段一**的心脏移植手术已成功完成。我们可以开始**阶段二**：在 `AnalysisEngine` 中实现 `EventBus` 的集成，让分析结果能够流式输出。
