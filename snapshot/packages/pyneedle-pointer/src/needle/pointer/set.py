from typing import Set, Iterable, Union, TYPE_CHECKING
from needle.spec import PointerSetProtocol, SemanticPointerProtocol

if TYPE_CHECKING:
    from .core import SemanticPointer


class PointerSet(Set["SemanticPointer"], PointerSetProtocol):
    """
    A collection of Semantic Pointers that supports algebraic broadcasting.
    
    Inherits from built-in set, so standard set operations (union, difference) work as expected.
    """

    def __truediv__(self, other: Union[str, "SemanticPointerProtocol"]) -> "PointerSet":
        """
        Operator '/': Broadcasts the join operation to all members.
        
        {L.a, L.b} / "end" -> {L.a.end, L.b.end}
        """
        # We assume elements are SemanticPointers which support __truediv__
        return PointerSet(p / other for p in self)

    def __add__(self, other: Union[str, "SemanticPointerProtocol"]) -> "PointerSet":
        """
        Operator '+': Broadcasts the add operation to all members.
        Same as __truediv__ but for '+' operator preference.
        """
        return PointerSet(p + other for p in self)

    def __mul__(self, other: Iterable[str]) -> "PointerSet":
        """
        Operator '*': Cartesian Product composition.
        
        {L.a, L.b} * {"1", "2"} -> {L.a.1, L.a.2, L.b.1, L.b.2}
        """
        new_set = PointerSet()
        for p in self:
            # p * other returns a PointerSet (from SemanticPointer.__mul__)
            # We union these sets together
            new_set.update(p * other)
        return new_set