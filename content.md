简要回答：
非常好的直觉。你的质疑是对的。在 `test_nexus.py` 中使用 `MockPointer` 是一种过度隔离（over-isolation）。

`pyneedle-spec` 定义了协议，而 `pyneedle-pointer` 是官方参考实现。既然 `pyneedle-nexus` 依赖于 `pyneedle-spec`，而测试环境可以轻易地访问 `pyneedle-pointer`，那么**直接使用真实的 `SemanticPointer` (L)** 来测试 `Nexus` 不仅更简单，而且更贴近真实使用场景，更能验证“集成”后的行为。

至于测试失败的问题，是因为我们修改了代码中的优先级（`NEEDLE_LANG` > `STITCHER_LANG`），但测试代码中的断言仍然是旧逻辑（认为 `STITCHER_LANG` 会覆盖 `NEEDLE_LANG`，因为当时我们还没有 `clean_env` 且 `NEEDLE_LANG` 被前面的测试设置为了 `fr`）。

我们将进行以下修正：
1.  **移除 `MockPointer`**: 直接从 `needle.pointer` 导入真实的 `L` 对象。
2.  **修正语言优先级测试**: 更新断言以反映新的、正确的优先级逻辑（`NEEDLE_LANG` > `STITCHER_LANG`）。

## [WIP] refactor: 在 Nexus 测试中使用真实 SemanticPointer 并修正优先级断言

### 用户需求
1.  **移除 Mock**: 在 `packages/pyneedle-nexus/tests/test_nexus.py` 中，删除 `MockPointer` 和 `L_TEST`，改用从 `needle.pointer` 导入的真实 `L` 对象。
2.  **修正测试逻辑**: 更新 `test_language_resolution_priority`，以匹配代码中修改后的环境变量优先级（`NEEDLE_LANG` > `STITCHER_LANG`）。

### 评论
使用真实组件进行测试（Integration Testing style for components）通常比纯 Mock 更能发现问题，尤其是在组件间耦合度极低的微内核架构中。这不仅简化了测试代码，还增加了测试的置信度。

### 目标
1.  修改 `packages/pyneedle-nexus/tests/test_nexus.py`：
    *   删除 `MockPointer` 类定义。
    *   导入 `needle.pointer.L`。
    *   将所有 `L_TEST` 替换为 `L`。
    *   修正 `test_language_resolution_priority` 中的断言逻辑。

### 标签
#intent/refine #intent/fix #flow/ready #priority/high
#comp/tests #scope/core
#task/domain/runtime #task/object/pyneedle-nexus #task/action/refactor
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 重构测试以使用真实 L 对象并修正断言
我们将一次性完成替换 Mock 和修正断言的工作。

~~~~~act
write_file
packages/pyneedle-nexus/tests/test_nexus.py
~~~~~
~~~~~python
import pytest
from needle.pointer import L
from needle.nexus import OverlayNexus, MemoryLoader


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
        "en": {"app.title": "My App (High Priority)", "app.welcome": "Welcome!"},
        "zh": {"app.title": "我的应用 (高优先级)"},
    }
    loader2_data = {
        "en": {"app.title": "My App (Low Priority)", "app.version": "1.0"},
        "zh": {"app.welcome": "欢迎！", "app.version": "1.0"},
    }
    
    # loader1 has higher priority
    return OverlayNexus(loaders=[MemoryLoader(loader1_data), MemoryLoader(loader2_data)])


def test_get_simple_retrieval_and_identity_fallback(nexus_instance: OverlayNexus):
    """Tests basic value retrieval and the ultimate fallback mechanism."""
    # From loader 1
    assert nexus_instance.get(L.app.welcome) == "Welcome!"
    # From loader 2
    assert nexus_instance.get(L.app.version) == "1.0"
    # Identity fallback
    assert nexus_instance.get("non.existent.key") == "non.existent.key"


def test_get_loader_priority_overlay(nexus_instance: OverlayNexus):
    """Tests that the first loader in the list overrides subsequent loaders."""
    # 'app.title' exists in both, should get the value from loader1
    assert nexus_instance.get("app.title") == "My App (High Priority)"


def test_get_language_specificity_and_fallback(nexus_instance: OverlayNexus):
    """Tests language selection and fallback to default language."""
    # 1. Specific language (zh) is preferred when key exists
    assert nexus_instance.get("app.title", lang="zh") == "我的应用 (高优先级)"

    # 2. Key missing in 'zh', falls back to default 'en'
    # Note: loader 2 has 'app.welcome' in 'zh', so it should be found there.
    # The previous test comment was slightly confusing.
    # ChainMap for 'zh' combines loader1(zh) and loader2(zh).
    # loader1(zh) has NO 'app.welcome'. loader2(zh) HAS 'app.welcome' ("欢迎！").
    # So it should resolve to "欢迎！".
    assert nexus_instance.get(L.app.welcome, lang="zh") == "欢迎！" 
    
    # 3. Key missing in both loaders for 'zh', falls back to 'en'
    # Let's add a key that is ONLY in EN
    # 'app.title' is in both. 'app.welcome' is in both (one en, one zh).
    # 'app.version' is in EN (loader2) and ZH (loader2).
    # We need a key that is truly missing in ZH.
    # Let's use a dynamic key for testing fallback.
    
    # Create a temporary nexus for precise fallback testing
    loader_fallback = MemoryLoader({
        "en": {"only.in.en": "Fallback Value"},
        "zh": {}
    })
    nexus_fallback = OverlayNexus([loader_fallback])
    
    assert nexus_fallback.get("only.in.en", lang="zh") == "Fallback Value"


def test_reload_clears_cache_and_refetches_data():
    """Tests that reload() forces a new data fetch after underlying data changes."""
    # Test data is isolated to this test function
    initial_data = {"en": {"key": "initial_value"}}
    
    # Create the loader and nexus
    loader = MemoryLoader(initial_data)
    nexus = OverlayNexus(loaders=[loader])

    # 1. First get, value is 'initial_value' and this is cached
    assert nexus.get("key") == "initial_value"

    # 2. Simulate an external change to the underlying data source
    initial_data["en"]["key"] = "updated_value" 
    
    # The cache is still holding the old view
    assert nexus.get("key") == "initial_value"

    # 3. Reload the cache
    nexus.reload()

    # 4. Get again, should now return the NEW value
    assert nexus.get("key") == "updated_value"


def test_language_resolution_priority(monkeypatch):
    """Tests the hierarchy of language resolution."""
    nexus = OverlayNexus(loaders=[MemoryLoader({"de": {"key": "de"}, "fr": {"key": "fr"}, "en": {"key": "en"}})])

    # Priority 1: Explicit `lang` argument
    assert nexus.get("key", lang="de") == "de"

    # Priority 2: NEEDLE_LANG env var
    monkeypatch.setenv("NEEDLE_LANG", "fr")
    # Even if STITCHER_LANG is set, NEEDLE_LANG should win
    monkeypatch.setenv("STITCHER_LANG", "de") 
    assert nexus.get("key") == "fr"

    # Priority 3: STITCHER_LANG env var (legacy compatibility)
    monkeypatch.delenv("NEEDLE_LANG")
    # Now STITCHER_LANG ("de") should take effect
    assert nexus.get("key") == "de"
    
    # Priority 4: System LANG env var
    monkeypatch.delenv("STITCHER_LANG")
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert nexus.get("key") == "fr"

    # Priority 5: Default language
    monkeypatch.delenv("LANG")
    assert nexus.get("key") == "en"
~~~~~

### 下一步建议
通过使用真实的 `SemanticPointer` 和正确的测试逻辑，我们现在应该拥有一个完全通过的测试套件。

一旦验证通过，我们将进入 **Phase 4: 电池组装 (pyneedle)**，这是将所有成果转化为最终用户产品的最后一步。
