简要回答：
分析测试失败原因，主要有两点：
1.  **`ChainMap` 的引用特性导致缓存测试失败**: `MemoryLoader` 直接返回了内部字典的引用，而 `ChainMap` 只是对这些字典的视图。因此，修改 `MemoryLoader` 的源数据会立即反映在 `ChainMap` 中，导致看起来像“缓存失效”（实际上是缓存的视图动态更新了）。这不符合我们想要测试的“快照加载”语义。
2.  **环境干扰导致语言解析不确定**: 某些测试失败（如返回中文，或返回莫名其妙的值）表明测试运行环境中的环境变量（如 `LANG` 或 `STITCHER_LANG`）干扰了 `_resolve_lang` 的逻辑，使其没有使用预期的默认语言 `en`。

我们将通过以下措施修复：
1.  修改 `MemoryLoader.load` 以返回数据的**浅拷贝**，模拟真实 I/O 的行为。
2.  在测试中使用 `monkeypatch` **强制清除相关环境变量**，确保测试环境纯净且确定。

## [WIP] fix: 修复 MemoryLoader 引用问题及测试环境隔离

### 用户需求
修复 `pyneedle-nexus` 的单元测试失败。
1.  **MemoryLoader**: 修改 `load` 方法，使其返回内部数据的副本 (`copy()`)，而不是直接引用。
2.  **Test Nexus**: 在运行测试前，强制清理 `STITCHER_LANG`, `NEEDLE_LANG`, `LANG` 等环境变量，确保语言解析逻辑回退到默认的 `en`。

### 评论
这些修复不仅能让测试通过，还纠正了 `MemoryLoader` 的语义，使其更准确地模拟真实的文件加载器（后者总是返回新的数据对象）。环境隔离则是编写可靠单元测试的标准实践。

### 目标
1.  Patch `packages/pyneedle-nexus/src/needle/nexus/loaders.py`。
2.  Patch `packages/pyneedle-nexus/tests/test_nexus.py`，添加 `clean_env` fixture 并应用到所有测试。

### 标签
#intent/fix #flow/ready #priority/high
#comp/runtime #comp/tests
#task/domain/runtime #task/object/pyneedle-nexus #task/action/bugfix
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修复 MemoryLoader 返回副本
这确保了 `ChainMap` 建立在数据快照上，从而使 `reload()` 测试（验证缓存清除）变得有效。

~~~~~act
patch_file
packages/pyneedle-nexus/src/needle/nexus/loaders.py
~~~~~
~~~~~python.old
    def load(self, lang: str) -> Dict[str, Any]:
        """
        Loads resources for a specific language from memory.
        """
        return self._data.get(lang, {})
~~~~~
~~~~~python.new
    def load(self, lang: str) -> Dict[str, Any]:
        """
        Loads resources for a specific language from memory.
        """
        # Return a copy to simulate I/O snapshotting and prevent
        # ChainMap from reflecting dynamic changes in source data immediately.
        return self._data.get(lang, {}).copy()
~~~~~

#### Acts 2: 增强测试环境隔离
添加 `clean_env` fixture，并在每个测试中自动使用它，消除环境变量的干扰。

~~~~~act
patch_file
packages/pyneedle-nexus/tests/test_nexus.py
~~~~~
~~~~~python.old
@pytest.fixture
def nexus_instance() -> OverlayNexus:
    """Provides a Nexus instance with two loaders for priority tests."""
    loader1_data = {
~~~~~
~~~~~python.new
@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure a clean environment for all tests to prevent flakiness."""
    monkeypatch.delenv("STITCHER_LANG", raising=False)
    monkeypatch.delenv("NEEDLE_LANG", raising=False)
    monkeypatch.delenv("LANG", raising=False)


@pytest.fixture
def nexus_instance() -> OverlayNexus:
    """Provides a Nexus instance with two loaders for priority tests."""
    loader1_data = {
~~~~~

### 下一步建议
测试通过后，我们将继续 **Phase 4: 电池组装 (pyneedle)**，实现 `FileSystemLoader` 并完成整个生态的组装。
