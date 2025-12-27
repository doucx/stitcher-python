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