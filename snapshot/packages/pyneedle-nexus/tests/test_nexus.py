import pytest
from needle.pointer import L
from needle.nexus import OverlayNexus, MemoryLoader
from needle.spec import WritableResourceLoaderProtocol
from pathlib import Path


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("STITCHER_LANG", raising=False)
    monkeypatch.delenv("NEEDLE_LANG", raising=False)
    monkeypatch.delenv("LANG", raising=False)


class MockWritableLoader(WritableResourceLoaderProtocol):
    def __init__(self, data):
        self.data = data
        self.put_calls = []

    def load(self, domain: str):
        return self.data.get(domain, {})

    def put(self, pointer, value, domain: str):
        self.put_calls.append({"pointer": str(pointer), "value": value, "domain": domain})
        return True

    def locate(self, pointer, domain: str):
        return Path(f"/{domain}/{str(pointer).replace('.', '/')}")


@pytest.fixture
def nexus_instance() -> OverlayNexus:
    loader1_data = {
        "en": {"app.title": "My App (High Priority)", "app.welcome": "Welcome!"},
        "zh": {"app.title": "我的应用 (高优先级)"},
    }
    loader2_data = {
        "en": {"app.title": "My App (Low Priority)", "app.version": "1.0"},
        "zh": {"app.welcome": "欢迎！", "app.version": "1.0"},
    }

    # loader1 has higher priority
    return OverlayNexus(
        loaders=[MemoryLoader(loader1_data), MemoryLoader(loader2_data)]
    )


def test_get_simple_retrieval_and_identity_fallback(nexus_instance: OverlayNexus):
    # From loader 1
    assert nexus_instance.get(L.app.welcome) == "Welcome!"
    # From loader 2
    assert nexus_instance.get(L.app.version) == "1.0"
    # Identity fallback
    assert nexus_instance.get("non.existent.key") == "non.existent.key"


def test_get_loader_priority_overlay(nexus_instance: OverlayNexus):
    # 'app.title' exists in both, should get the value from loader1
    assert nexus_instance.get("app.title") == "My App (High Priority)"


def test_get_language_specificity_and_fallback(nexus_instance: OverlayNexus):
    # 1. Specific domain (zh) is preferred when key exists
    assert nexus_instance.get("app.title", domain="zh") == "我的应用 (高优先级)"

    # 2. Key ('app.welcome') exists in loader2 for 'zh', so it resolves
    assert nexus_instance.get(L.app.welcome, domain="zh") == "欢迎！"

    # 3. Key only exists in 'en', so 'zh' request falls back to default 'en'
    loader_fallback = MemoryLoader({"en": {"only.in.en": "Fallback Value"}, "zh": {}})
    nexus_fallback = OverlayNexus([loader_fallback])
    assert nexus_fallback.get("only.in.en", domain="zh") == "Fallback Value"


def test_reload_clears_cache_and_refetches_data():
    initial_data = {"en": {"key": "initial_value"}}
    loader = MemoryLoader(initial_data)
    nexus = OverlayNexus(loaders=[loader])

    assert nexus.get("key") == "initial_value"
    initial_data["en"]["key"] = "updated_value"
    assert nexus.get("key") == "initial_value"  # Still cached

    nexus.reload()
    assert nexus.get("key") == "updated_value"


def test_domain_resolution_priority(monkeypatch):
    nexus = OverlayNexus(
        loaders=[
            MemoryLoader(
                {"de": {"key": "de"}, "fr": {"key": "fr"}, "en": {"key": "en"}}
            )
        ]
    )

    # Priority 1: Explicit `domain` argument
    assert nexus.get("key", domain="de") == "de"

    # Priority 2: NEEDLE_LANG env var
    monkeypatch.setenv("NEEDLE_LANG", "fr")
    monkeypatch.setenv("STITCHER_LANG", "de")
    assert nexus.get("key") == "fr"

    # Priority 3: STITCHER_LANG env var
    monkeypatch.delenv("NEEDLE_LANG")
    assert nexus.get("key") == "de"

    # Priority 4: System LANG env var
    monkeypatch.delenv("STITCHER_LANG")
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert nexus.get("key") == "fr"

    # Priority 5: Default domain
    monkeypatch.delenv("LANG")
    assert nexus.get("key") == "en"


def test_put_and_locate_delegate_to_first_writable_loader():
    # Arrange
    writable_loader = MockWritableLoader({"en": {}})
    read_only_loader = MemoryLoader({"en": {"key": "value"}})
    nexus = OverlayNexus(loaders=[writable_loader, read_only_loader])

    # Act
    put_result = nexus.put(L.new.key, "new_value", domain="en")
    locate_result = nexus.locate(L.some.path, domain="en")

    # Assert
    assert put_result is True
    assert len(writable_loader.put_calls) == 1
    assert writable_loader.put_calls[0] == {
        "pointer": "new.key",
        "value": "new_value",
        "domain": "en",
    }
    assert locate_result == Path("/en/some/path")