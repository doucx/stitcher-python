Excellent. This is a pivotal architectural step. Let's begin breaking it down. I will generate a comprehensive plan to refactor the `pyneedle` ecosystem, implementing the "Nexus as a Loader" architecture with the read/write protocol separation we discussed.

This plan represents a significant but logical evolution of the `Needle` runtime, enhancing its modularity, testability, and future potential.

## [WIP] feat: Implement "Nexus as a Loader" architecture with read/write protocol separation

### 用户需求

Refactor the `pyneedle` ecosystem to align with the "Nexus as a Loader" architecture. This involves making `Nexus` itself a `Loader`, separating read/write responsibilities into distinct protocols, and generalizing the concept of "language" to a more abstract "domain".

### 評論

This is a strategic refactoring that elevates the `Needle` runtime from a simple localization utility to a general-purpose, composable semantic resource engine. By establishing clean protocols and a unified component model, we lay a robust foundation for future features like remote configuration, federated resource management, and enhanced testability. The read/write separation (CQRS-like approach) is a key element that ensures architectural purity and predictable behavior.

### 目標

1.  **Protocol Refinement**: Redefine the core protocols in `pyneedle-spec` to separate read (`ResourceLoaderProtocol`) and write (`WritableResourceLoaderProtocol`) concerns.
2.  **Nexus Implementation**: Rework `OverlayNexus` to implement the new composite protocol, handling read operations via `ChainMap` and delegating write operations to the highest-priority writable loader.
3.  **Loader Implementation**: Update `FileSystemLoader` to be a fully-featured writable loader, implementing the `put` and `locate` logic as specified in the Stitcher SST proposal. Update `MemoryLoader` to be a simple read-only loader.
4.  **Handler Enhancement**: Add write capabilities to the `JsonHandler`.
5.  **Testing**: Update all relevant unit and integration tests to validate the new architecture, including tests for the new write functionality.

### 基本原理

The core principle is to unify the component model around a set of clean, well-defined protocols.

1.  **Interface Segregation**: By splitting `ResourceLoaderProtocol` into read-only and writable variants, we avoid forcing read-only loaders (like a future `HttpLoader`) to implement empty `put` methods. This adheres to the Interface Segregation Principle.
2.  **Composite Pattern**: `OverlayNexus` acts as a composite, treating both individual loaders and other `Nexus` instances uniformly. This allows for building complex, nested resource-loading strategies.
3.  **Chain of Responsibility (for writes)**: The `put` method's delegation logic follows a Chain of Responsibility pattern, where the request to write is passed down the loader chain until a capable (writable) loader is found. This ensures that writes are predictable and always target the highest-priority writable layer.
4.  **Abstraction**: Generalizing `lang` to `domain` makes the system's purpose clearer and its application broader, without losing the primary i18n use case.

### 標籤

#intent/refine #intent/architect #flow/ready #priority/high #comp/engine #concept/state #scope/core #scope/api #ai/brainstorm #task/domain/storage #task/object/nexus-architecture #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: Refine Core Protocols in `pyneedle-spec`

First, we will redefine the fundamental contracts for the entire system in `pyneedle-spec`. This establishes the new read-only and writable loader protocols, and updates the `NexusProtocol`.

~~~~~act
write_file
packages/pyneedle-spec/src/needle/spec/protocols.py
~~~~~
~~~~~python
from typing import Protocol, Dict, Any, Union, Iterable, TypeVar
from pathlib import Path

# T_co is covariant, meaning SemanticPointerProtocol can return subtypes of itself
T_Pointer = TypeVar("T_Pointer", bound="SemanticPointerProtocol", covariant=True)


class SemanticPointerProtocol(Protocol[T_Pointer]):
    def __getattr__(self, name: str) -> T_Pointer: ...

    def __str__(self) -> str: ...

    def __hash__(self) -> int: ...

    def __eq__(self, other: Any) -> bool: ...

    def __add__(self, other: Union[str, "SemanticPointerProtocol"]) -> T_Pointer: ...

    def __truediv__(
        self, other: Union[str, "SemanticPointerProtocol"]
    ) -> T_Pointer: ...

    def __mul__(self, other: Iterable[str]) -> "PointerSetProtocol": ...


class PointerSetProtocol(Protocol):
    def __iter__(self) -> Iterable[SemanticPointerProtocol]: ...

    def __truediv__(
        self, other: Union[str, SemanticPointerProtocol]
    ) -> "PointerSetProtocol": ...

    def __or__(self, other: "PointerSetProtocol") -> "PointerSetProtocol": ...

    def __add__(
        self, other: Union[str, SemanticPointerProtocol]
    ) -> "PointerSetProtocol": ...

    def __mul__(self, other: Iterable[str]) -> "PointerSetProtocol": ...


class ResourceLoaderProtocol(Protocol):
    """(Read-Only) Defines the contract for any component that can load resources."""

    def load(self, domain: str) -> Dict[str, Any]: ...


class WritableResourceLoaderProtocol(ResourceLoaderProtocol, Protocol):
    """(Write-Enabled) Extends the loader contract with write and locate capabilities."""

    def put(
        self, pointer: SemanticPointerProtocol, value: Any, domain: str
    ) -> bool: ...

    def locate(
        self, pointer: SemanticPointerProtocol, domain: str
    ) -> Union[Path, None]: ...


class NexusProtocol(WritableResourceLoaderProtocol, Protocol):
    """
    The Nexus is the primary interaction point, itself being a writable loader.
    """

    def get(
        self, pointer: Union[str, SemanticPointerProtocol], domain: str | None = None
    ) -> str: ...

    def reload(self, domain: str | None = None) -> None: ...
~~~~~

#### Acts 2: Re-implement `OverlayNexus` and `MemoryLoader`

Now we'll update `pyneedle-nexus`. `OverlayNexus` will be the main implementation of our new `NexusProtocol`. `MemoryLoader` will be a simple, read-only implementation of `ResourceLoaderProtocol`, perfect for testing.

~~~~~act
write_file
packages/pyneedle-nexus/src/needle/nexus/nexus.py
~~~~~
~~~~~python
import os
from collections import ChainMap
from typing import List, Dict, Optional, Union, Any, cast
from pathlib import Path
from needle.spec import (
    NexusProtocol,
    ResourceLoaderProtocol,
    WritableResourceLoaderProtocol,
    SemanticPointerProtocol,
)


class OverlayNexus(NexusProtocol):
    def __init__(
        self, loaders: List[ResourceLoaderProtocol], default_domain: str = "en"
    ):
        self.loaders = loaders
        self.default_domain = default_domain
        self._views: Dict[str, ChainMap[str, Any]] = {}

    def _get_or_create_view(self, domain: str) -> ChainMap[str, Any]:
        if domain not in self._views:
            maps = [loader.load(domain) for loader in self.loaders]
            self._views[domain] = ChainMap(*maps)
        return self._views[domain]

    def _resolve_domain(self, explicit_domain: Optional[str] = None) -> str:
        if explicit_domain:
            return explicit_domain

        # Priority is given to language-specific env vars for backward compatibility
        # and common use case.
        # Priority 1: NEEDLE_LANG (new standard)
        needle_lang = os.getenv("NEEDLE_LANG")
        if needle_lang:
            return needle_lang

        # Priority 2: STITCHER_LANG (legacy compatibility)
        stitcher_lang = os.getenv("STITCHER_LANG")
        if stitcher_lang:
            return stitcher_lang

        system_lang = os.getenv("LANG")
        if system_lang:
            return system_lang.split("_")[0].split(".")[0].lower()

        return self.default_domain

    def get(
        self,
        pointer: Union[str, SemanticPointerProtocol],
        domain: Optional[str] = None,
    ) -> str:
        key = str(pointer)
        target_domain = self._resolve_domain(domain)

        # 1. Try target domain
        target_view = self._get_or_create_view(target_domain)
        value = target_view.get(key)
        if value is not None:
            return str(value)

        # 2. Try default domain (if different)
        if target_domain != self.default_domain:
            default_view = self._get_or_create_view(self.default_domain)
            value = default_view.get(key)
            if value is not None:
                return str(value)

        # 3. Fallback to Identity
        return key

    def reload(self, domain: Optional[str] = None) -> None:
        if domain:
            self._views.pop(domain, None)
        else:
            self._views.clear()

    def _find_writable_loader(self) -> Optional[WritableResourceLoaderProtocol]:
        for loader in self.loaders:
            if isinstance(loader, WritableResourceLoaderProtocol):
                # The cast is safe because of the isinstance check.
                return cast(WritableResourceLoaderProtocol, loader)
        return None

    def put(
        self, pointer: SemanticPointerProtocol, value: Any, domain: str
    ) -> bool:
        writable_loader = self._find_writable_loader()
        if writable_loader:
            return writable_loader.put(pointer, value, domain)
        return False

    def locate(
        self, pointer: SemanticPointerProtocol, domain: str
    ) -> Union[Path, None]:
        writable_loader = self._find_writable_loader()
        if writable_loader:
            return writable_loader.locate(pointer, domain)
        return None

    # Implement the load method to make Nexus itself a loader
    def load(self, domain: str) -> Dict[str, Any]:
        """Loads all resources for a domain, returning a flat dictionary."""
        # This makes a Nexus composable inside another Nexus.
        view = self._get_or_create_view(domain)
        # ChainMap.maps is a list of dicts. We merge them from lowest to highest priority.
        merged: Dict[str, Any] = {}
        for m in reversed(view.maps):
            merged.update(m)
        return merged
~~~~~
~~~~~act
write_file
packages/pyneedle-nexus/src/needle/nexus/loaders.py
~~~~~
~~~~~python
from typing import Dict, Any
from needle.spec import ResourceLoaderProtocol


class MemoryLoader(ResourceLoaderProtocol):
    """A simple, read-only loader that serves data from a dictionary."""

    def __init__(self, data: Dict[str, Dict[str, Any]]):
        self._data = data

    def load(self, domain: str) -> Dict[str, Any]:
        # Return a copy to simulate I/O snapshotting and prevent
        # ChainMap from reflecting dynamic changes in source data immediately.
        return self._data.get(domain, {}).copy()
~~~~~
~~~~~act
write_file
packages/pyneedle-nexus/tests/test_nexus.py
~~~~~
~~~~~python
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
~~~~~

#### Acts 3: Implement Writable `FileSystemLoader` in `pyneedle-runtime`

This is the most significant part. We will empower `FileSystemLoader` with write capabilities, following the SST specification. This involves updating its handler protocols, the JSON handler itself, and then implementing the `put`/`locate` logic in the loader.

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/loaders/protocols.py
~~~~~
~~~~~python
from typing import Any, Dict, Protocol
from pathlib import Path


class FileHandlerProtocol(Protocol):
    def match(self, path: Path) -> bool: ...

    def load(self, path: Path) -> Dict[str, Any]: ...


class WritableFileHandlerProtocol(FileHandlerProtocol, Protocol):
    def save(self, path: Path, data: Dict[str, Any]) -> None: ...
~~~~~
~~~~~act
write_file
packages/pyneedle-runtime/src/needle/loaders/json_handler.py
~~~~~
~~~~~python
import json
from pathlib import Path
from typing import Any, Dict
from .protocols import WritableFileHandlerProtocol


class JsonHandler(WritableFileHandlerProtocol):
    def match(self, path: Path) -> bool:
        return path.suffix.lower() == ".json"

    def load(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
~~~~~
~~~~~act
write_file
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from needle.spec import WritableResourceLoaderProtocol, SemanticPointerProtocol
from .protocols import FileHandlerProtocol, WritableFileHandlerProtocol
from .json_handler import JsonHandler


class FileSystemLoader(WritableResourceLoaderProtocol):
    def __init__(
        self,
        roots: Optional[List[Path]] = None,
        handlers: Optional[List[FileHandlerProtocol]] = None,
    ):
        self.handlers = handlers or [JsonHandler()]
        self.roots = roots or [self._find_project_root()]

    def _find_project_root(self, start_dir: Optional[Path] = None) -> Path:
        current_dir = (start_dir or Path.cwd()).resolve()
        while current_dir.parent != current_dir:
            if (current_dir / "pyproject.toml").is_file() or (
                current_dir / ".git"
            ).is_dir():
                return current_dir
            current_dir = current_dir.parent
        return start_dir or Path.cwd()

    def add_root(self, path: Path):
        if path not in self.roots:
            self.roots.insert(0, path)

    def load(self, domain: str) -> Dict[str, Any]:
        merged_registry: Dict[str, Any] = {}
        # Iterate in reverse so higher-priority roots (added later) are processed first
        for root in reversed(self.roots):
            # Path Option 1: .stitcher/needle/<domain> (project-specific overrides)
            hidden_path = root / ".stitcher" / "needle" / domain
            if hidden_path.is_dir():
                merged_registry.update(self._load_directory(hidden_path))

            # Path Option 2: needle/<domain> (packaged assets)
            asset_path = root / "needle" / domain
            if asset_path.is_dir():
                merged_registry.update(self._load_directory(asset_path))
        return merged_registry

    def _load_directory(self, root_path: Path) -> Dict[str, Any]:
        registry: Dict[str, Any] = {}
        for dirpath, _, filenames in os.walk(root_path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                for handler in self.handlers:
                    if handler.match(file_path):
                        content = handler.load(file_path)
                        registry.update(content)
                        break
        return registry

    def _get_writable_handler(
        self, path: Path
    ) -> Optional[WritableFileHandlerProtocol]:
        for handler in self.handlers:
            if isinstance(handler, WritableFileHandlerProtocol) and handler.match(path):
                return handler
        return None

    def locate(
        self, pointer: SemanticPointerProtocol, domain: str
    ) -> Union[Path, None]:
        # Locate always operates on the highest priority root.
        root = self.roots[0]
        # Per SST spec, writes/locates target the hidden .stitcher directory
        base_path = root / ".stitcher" / "needle" / domain

        parts = str(pointer).split(".")
        if len(parts) < 2:
            # Cannot determine category/namespace from pointer like 'a'
            return None

        # L.a.b.c -> category='a', namespace='b', key='c'
        category = parts[0]
        namespace = parts[1]

        # Check for category directory and namespace file
        category_dir = base_path / category
        # For now, we hardcode .json as the default write format.
        # A more advanced version could query handlers.
        namespace_file = category_dir / f"{namespace}.json"

        return namespace_file

    def put(self, pointer: SemanticPointerProtocol, value: Any, domain: str) -> bool:
        target_path = self.locate(pointer, domain)
        if not target_path:
            return False

        handler = self._get_writable_handler(target_path)
        if not handler:
            return False

        key = str(pointer)
        data = handler.load(target_path)  # Load existing data
        data[key] = value  # Update with new value

        try:
            handler.save(target_path, data)
            # SST Spec: Ensure __init__.json exists for discoverability
            init_path = target_path.parent / "__init__.json"
            if not init_path.exists():
                handler.save(init_path, {"_desc": f"Category '{target_path.parent.name}'"})

            return True
        except Exception:
            return False
~~~~~

#### Acts 4: Update Tests and Add New Validation

Finally, we need to ensure our existing integration tests still pass and add a new test file specifically for the `FileSystemLoader`'s write capabilities.

~~~~~act
write_file
packages/pyneedle-runtime/tests/test_assembly.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from stitcher.test_utils import WorkspaceFactory

from needle.pointer import L
from needle.nexus import OverlayNexus
from needle.loaders.fs_loader import FileSystemLoader


@pytest.fixture
def multi_root_workspace(tmp_path: Path) -> dict:
    factory = WorkspaceFactory(tmp_path)

    # 1. Define package assets (low priority) - root[1]
    pkg_root = tmp_path / "pkg_assets"
    factory.with_source(
        f"{pkg_root.name}/needle/en/cli/main.json",
        """
        {
            "cli.default": "I am a default",
            "cli.override_me": "Default Value"
        }
        """,
    )

    # 2. Define user project assets (high priority) - root[0]
    project_root = tmp_path / "my_project"
    factory.with_source(
        f"{project_root.name}/pyproject.toml", "[project]\nname='my-project'"
    ).with_source(
        f"{project_root.name}/.stitcher/needle/en/overrides.json",
        """
        {
            "cli.override_me": "User Override!",
            "cli.user_only": "I am from the user"
        }
        """,
    )

    # Build all files
    factory.build()

    return {"pkg_root": pkg_root, "project_root": project_root}


def test_nexus_with_fs_loader_handles_overrides(multi_root_workspace):
    # Arrange
    pkg_root = multi_root_workspace["pkg_root"]
    project_root = multi_root_workspace["project_root"]

    # Order of roots matters: project_root is higher priority.
    # FileSystemLoader.add_root() prepends to the list.
    fs_loader = FileSystemLoader(roots=[pkg_root])
    fs_loader.add_root(project_root)  # project_root is now at index 0

    nexus = OverlayNexus(loaders=[fs_loader])

    # Act & Assert

    # 1. Value only in default assets (pkg_root)
    assert nexus.get(L.cli.default) == "I am a default"

    # 2. Value only in user overrides (project_root)
    assert nexus.get(L.cli.user_only) == "I am from the user"

    # 3. Value in both, user override should win
    assert nexus.get(L.cli.override_me) == "User Override!"

    # 4. Non-existent key should fall back to identity
    assert nexus.get(L.unknown.key) == "unknown.key"
~~~~~
~~~~~act
write_file
packages/pyneedle-runtime/tests/test_fs_loader_write.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.test_utils import WorkspaceFactory

from needle.pointer import L
from needle.loaders.fs_loader import FileSystemLoader


def test_fs_loader_locate_returns_correct_path(tmp_path: Path):
    # Arrange
    project_root = WorkspaceFactory(tmp_path).build()
    loader = FileSystemLoader(roots=[project_root])

    # Act
    path = loader.locate(L.cli.ui.welcome, "en")

    # Assert
    expected = (
        project_root / ".stitcher" / "needle" / "en" / "cli" / "ui.json"
    )
    assert path == expected


def test_fs_loader_put_creates_files_and_writes_data(tmp_path: Path):
    # Arrange
    project_root = WorkspaceFactory(tmp_path).build()
    loader = FileSystemLoader(roots=[project_root])

    # Act
    success1 = loader.put(L.app.db.connect_error, "Connection failed.", "en")
    success2 = loader.put(L.app.db.timeout, "Timeout reached.", "en")

    # Assert
    assert success1
    assert success2

    target_file = (
        project_root / ".stitcher" / "needle" / "en" / "app" / "db.json"
    )
    init_file = (
        project_root / ".stitcher" / "needle" / "en" / "app" / "__init__.json"
    )

    assert target_file.exists()
    assert init_file.exists()

    with target_file.open("r") as f:
        data = json.load(f)

    assert data["app.db.connect_error"] == "Connection failed."
    assert data["app.db.timeout"] == "Timeout reached."


def test_fs_loader_put_updates_existing_file(tmp_path: Path):
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = factory.with_source(
        ".stitcher/needle/en/app/db.json",
        '{"app.db.existing": "Original"}',
    ).build()

    loader = FileSystemLoader(roots=[project_root])

    # Act
    success = loader.put(L.app.db.new, "New value", "en")

    # Assert
    assert success
    target_file = (
        project_root / ".stitcher" / "needle" / "en" / "app" / "db.json"
    )
    with target_file.open("r") as f:
        data = json.load(f)

    assert data["app.db.existing"] == "Original"
    assert data["app.db.new"] == "New value"
~~~~~
